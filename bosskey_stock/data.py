"""Sina Finance 行情数据层"""

import re

import requests

SINA_URL = "https://hq.sinajs.cn/list={}"
HEADERS = {"Referer": "https://finance.sina.com.cn"}


# 沪市债券/回购代码段（其余 1 开头段位归深市，如 100/101/109/111/112/123/128/131）
SH_BOND_PREFIXES = ("010", "019", "110", "113", "118", "122", "124", "126", "127", "132", "204")


def _sina_code(raw):
    """A股代码转 Sina 前缀：沪/深/京按代码段划分。

    沪：5 (ETF)、6 (股票)、9 (B股)、债券段（01 国债 / 110/113/118 转债 / 122/124/126/127
    企业债 / 132 可交换 / 204 国债回购）；深：0/1/2/3（含 15/16 深 ETF、10-13 债券）；
    京（北交所）：4/8 开头及 92 开头。
    """
    if raw.startswith(("4", "8")) or raw.startswith("92"):
        return f"bj{raw}"
    if raw.startswith(("5", "6", "9")):
        return f"sh{raw}"
    if raw.startswith(SH_BOND_PREFIXES):
        return f"sh{raw}"
    return f"sz{raw}"


def _is_etf(code):
    """判断是否为 ETF/LOF：沪 5 开头（51/56/58），深 15/16 开头（159 等）。"""
    return code.startswith("5") or code.startswith(("15", "16"))


def _is_bond(code):
    """判断是否为债券/回购（价格 3 位小数）：沪市债券段 + 深市债券段（10-13，15+ 为基金）。"""
    if code.startswith(SH_BOND_PREFIXES):
        return True
    return code.startswith(("10", "11", "12", "13"))


def _build_url(codes):
    return SINA_URL.format(",".join(_sina_code(c) for c in codes))


def fetch(codes):
    """请求 Sina 接口，返回 list[dict]，网络异常返回 None。"""
    if not codes:
        return []
    try:
        resp = requests.get(_build_url(codes), headers=HEADERS, timeout=5)
        resp.encoding = "gbk"
        raw = resp.text.strip()
    except requests.RequestException:
        return None

    stocks = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        if s := _parse(line):
            stocks.append(s)
    return stocks


def _parse(line):
    """解析单行 Sina JS 返回。

    格式：var hq_str_sh600519="贵州茅台,...";
    """
    m = re.search(r'hq_str_[a-z]+(\d+)="', line)
    if not m:
        return None
    code = m.group(1)

    try:
        data = line.split('"')[1]
    except IndexError:
        return None
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
        dp = 3 if _is_etf(code) or _is_bond(code) else 2  # ETF/债券净值精确到 3 位
        chg = round(price - pre_close, dp)
        s["change"] = chg
        s["change_pct"] = round(chg / pre_close * 100, 2)
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
