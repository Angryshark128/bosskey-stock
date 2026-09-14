"""Sina Finance 行情数据层"""

import re

import requests

SINA_URL = "https://hq.sinajs.cn/list={}"
HEADERS = {"Referer": "https://finance.sina.com.cn"}


# 沪市债券/回购代码段（其余 1 开头段位归深市，如 100/101/109/111/112/123/128/131）
SH_BOND_PREFIXES = (
    "010", "019",  # 国债
    "110", "113", "118", "71",  # 可转债（71 为 2024 后新段）
    "122", "124", "126", "127",  # 企业债/公司债/分离债
    "132",  # 可交换债
    "204",  # 国债回购
)


# 深市场内基金代码段：15 (ETF)、16 (LOF)、18 (REITs/封闭式基金)
SZ_FUND_PREFIXES = ("15", "16", "18")

# 可显式指定的交易所前缀。存储键形如 "sh:000001"（同名代码靠它区分，
# 如 sh:000001 上证指数 vs 默认按段位规则得到的 sz000001 平安银行）。
# fu = 场外开放式基金（净值型），只能显式写，永远判不出来，见 default_prefix()。
EXCHANGES = ("sh", "sz", "bj", "fu")

# 未显式指定前缀时用来探测的交易所。**不含 fu**：场外代码段与 A 股/场内大面积重叠，
# 若一并探测，`add 000001` 会多出「华夏成长混合A」候选，股票消歧体验被破坏。
PROBE_EXCHANGES = ("sh", "sz", "bj")
KEY_SEP = ":"


def split_key(key):
    """存储键 -> (显式前缀 or None, 裸代码)："sh:000001" -> ("sh", "000001")。"""
    prefix, sep, rest = key.partition(KEY_SEP)
    if sep and prefix in EXCHANGES and rest.isdigit():
        return prefix, rest
    return None, key


def make_key(prefix, code):
    """前缀 + 裸代码 -> 存储键；与段位规则一致时存裸代码，不让配置无谓变脏。"""
    return code if prefix == default_prefix(code) else f"{prefix}{KEY_SEP}{code}"


def sina_key(key):
    """存储键 -> Sina 请求代码：带显式前缀直连，否则按段位规则。"""
    prefix, code = split_key(key)
    if prefix:
        return _join_sina(prefix, code)
    return _sina_code(code)


def _join_sina(prefix, code):
    """前缀 + 代码 -> Sina 请求代码：场外基金用下划线（fu_110022），
    场内与指数直接拼接（sh600519）。"""
    return f"{prefix}_{code}" if prefix == "fu" else f"{prefix}{code}"


def default_prefix(raw):
    """段位规则：裸代码 -> 交易所前缀。

    沪：5 (ETF/LOF/REITs 等场内基金)、6 (股票)、9 (B股)、债券段（01 国债 / 110/113/118/71
    转债 / 122/124/126/127 企业债 / 132 可交换 / 204 国债回购）；深：0/1/2/3（含 15/16/18
    场内基金、10-13 债券）；京（北交所）：4/8 开头及 92 开头。
    """
    if raw.startswith(("4", "8")) or raw.startswith("92"):
        return "bj"
    if raw.startswith(("5", "6", "9")):
        return "sh"
    if raw.startswith(SH_BOND_PREFIXES):
        return "sh"
    return "sz"


def _sina_code(raw):
    """裸代码 -> Sina 请求代码（按段位规则）。"""
    return f"{default_prefix(raw)}{raw}"


def _is_fund(key):
    """判断是否为场内基金（价格 3 位小数）：沪 5 段（ETF/LOF/REITs/货基/封闭式），
    深 15 (ETF) / 16 (LOF) / 18 (REITs、封闭式基金) 段。入参可为带前缀的存储键。"""
    code = split_key(key)[1]
    return code.startswith("5") or code.startswith(SZ_FUND_PREFIXES)


def _is_bond(key):
    """判断是否为债券/回购（价格 3 位小数）：沪市债券段 + 深市债券段（10-13）。"""
    code = split_key(key)[1]
    if code.startswith(SH_BOND_PREFIXES):
        return True
    return code.startswith(("10", "11", "12", "13"))


def price_decimals(key):
    """价格与涨跌额的显示精度：场外基金 4 位，场内基金 / 债券 3 位，股票（含北交所）2 位。

    行情层与 TUI 渲染共用同一入口，避免两处判定漂移（深市 REITs 18 段曾漏配 3 位小数）。
    入参可为带前缀的存储键：精度只看显式 `fu:` 前缀与代码段，其余前缀不影响判定。
    """
    if split_key(key)[0] == "fu":
        return 4
    return 3 if _is_fund(key) or _is_bond(key) else 2


def fetch(codes):
    """请求 Sina 接口，返回 list[dict]，网络异常返回 None。

    codes 为存储键（裸代码或带显式前缀的 "sh:000001"）；向接口请求的是 sina_key()
    解析后的代码，返回项的 code 字段再回填为原存储键，使行情、持仓、分组按同一个键对齐。
    """
    if not codes:
        return []

    # 同一 Sina 代码只请求一次；sina 代码 -> 存储键，供 _parse 回填
    mapping = {}
    for c in codes:
        mapping.setdefault(sina_key(c), c)

    try:
        resp = requests.get(SINA_URL.format(",".join(mapping)), headers=HEADERS, timeout=5)
        resp.encoding = "gbk"
        raw = resp.text.strip()
    except requests.RequestException:
        return None

    stocks = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        if s := _parse(line, mapping):
            stocks.append(s)
    return stocks


def probe(code, prefix=None):
    """探测一个代码在各交易所有没有行情，用于同名代码消歧与「无行情」提示。

    返回 [(交易所前缀, 名称), ...]，保序。未指定 prefix 时只探 sh/sz/bj —— 场外基金
    （`fu`）代码段与 A 股/场内重叠，不参与裸代码探测，只能靠显式前缀查。
    prefix 指定时只查该交易所（含 `fu`）。网络异常返回 None，调用方据此回退段位规则。
    """
    prefixes = (prefix,) if prefix else PROBE_EXCHANGES
    stocks = fetch([f"{p}{KEY_SEP}{code}" for p in prefixes])
    if stocks is None:
        return None
    return [(split_key(s["code"])[0], s["name"]) for s in stocks]


def _parse(line, mapping=None):
    """解析单行 Sina JS 返回，按前缀分派场内 / 场外两套字段布局。

    场内：var hq_str_sh600519="贵州茅台,32+ 字段...";
    场外：var hq_str_fu_110022="易方达消费行业股票,10 字段...";
    code 字段取 mapping（Sina 代码 -> 存储键）命中值，未命中时用响应里的裸代码。
    """
    m = re.search(r'hq_str_([a-z]+)_?(\d+)="', line)
    if not m:
        return None
    prefix, digits = m.group(1), m.group(2)
    code = (mapping or {}).get(_join_sina(prefix, digits), digits)

    try:
        data = line.split('"')[1]
    except IndexError:
        return None
    if prefix == "fu":
        return _parse_fu(code, data)
    f = data.split(",")
    if len(f) < 32:
        return None

    name = f[0]
    pre_close = _f(f[2])
    price = _f(f[3])
    vol = _i(f[8])

    s = {
        "code": code,
        "name": name,
        "open": _f(f[1]),
        "pre_close": pre_close,
        "price": price,
        "high": _f(f[4]),
        "low": _f(f[5]),
        "vol": vol,
        "amount": _f(f[9]),
        "date": f[30],
        "trade_time": f[31],
    }

    if price is not None and pre_close and pre_close != 0:
        dp = price_decimals(code)  # 场内基金/债券精确到 3 位
        chg = round(price - pre_close, dp)
        s["change"] = chg
        s["change_pct"] = round(chg / pre_close * 100, 2)
    else:
        s["change"] = None
        s["change_pct"] = None

    return s


def _parse_fu(code, data):
    """解析场外开放式基金（净值型）行情：10 个字段，无开高低/成交量/成交额。

    字段：f[0] 名称 / f[1] 估值时间 / f[2] 当日估算净值 / f[3] 最近披露单位净值 /
    f[4] 累计净值 / f[6] 估算涨跌幅(%) / f[7] 净值日期；f[5]、f[8]、f[9] 含义未确证不使用。
    空串（场外货币基金，接口不返回净值）返回 None。
    """
    f = data.split(",")
    if len(f) < 10 or not f[0].strip():
        return None

    price = _f(f[2])
    pre_close = _f(f[3])
    s = {
        "code": code,
        "name": f[0],
        "open": None,
        "pre_close": pre_close,
        "price": price,
        "high": None,
        "low": None,
        "vol": None,
        "amount": None,
        "date": f[7],
        "trade_time": f[1],
    }

    if price is not None and pre_close and pre_close != 0:
        chg = round(price - pre_close, 4)
        s["change"] = chg
        pct = _f(f[6])
        s["change_pct"] = pct if pct is not None else round(chg / pre_close * 100, 2)
    else:
        s["change"] = None
        s["change_pct"] = None

    return s


def _f(v):
    try:
        return float(v) if v.strip() else None
    except (ValueError, AttributeError):
        return None


def _i(v):
    try:
        return int(v) if v.strip() else None
    except (ValueError, AttributeError):
        return None
