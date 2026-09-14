"""Tests for data layer — Sina API response parsing."""

import pytest

from bosskey_stock import data


def _make_sina_line(code, *fields):
    """Helper: build a simulated Sina JS response line."""
    data_str = ",".join(str(f) for f in fields)
    return f'var hq_str_sh{code}="{data_str}"'


def test_parse_normal():
    # 32 fields: name, open, pre_close, price, high, low, 24 empty, date, time
    fields = (
        ["贵州茅台", "1680.00", "1675.00", "1690.00", "1700.00", "1670.00"]
        + [""] * 24
        + ["2026-07-30", "16:30:00"]
    )
    line = _make_sina_line("600519", *fields)

    s = data._parse(line)
    assert s is not None
    assert s["code"] == "600519"
    assert s["name"] == "贵州茅台"
    assert s["open"] == 1680.00
    assert s["pre_close"] == 1675.00
    assert s["price"] == 1690.00
    assert s["high"] == 1700.00
    assert s["low"] == 1670.00
    assert s["vol"] is None  # empty field index 8
    assert s["amount"] is None
    assert s["date"] == "2026-07-30"
    assert s["trade_time"] == "16:30:00"
    assert s["change"] == 15.00
    assert s["change_pct"] == pytest.approx(0.90, rel=0.01)


def test_parse_shenzhen():
    """深市 000001 平安银行"""
    fields = (
        ["平安银行", "12.50", "12.40", "12.60", "12.70", "12.30", "0", "0", "1000000", "12600000"]
        + [""] * 21
        + ["2026-07-30", "16:30:00", ""]
    )
    line = _make_sina_line("000001", *fields)
    s = data._parse(line)
    assert s is not None
    assert s["code"] == "000001"
    assert s["name"] == "平安银行"
    assert s["price"] == 12.60


def test_parse_missing_fields():
    """字段数不足 32 时返回 None"""
    line = 'var hq_str_sh600519="茅台,1,2,3,4,5,6,7,8,9",;'
    assert data._parse(line) is None


def test_parse_no_match():
    """非预期格式返回 None"""
    assert data._parse("not a stock line") is None


def test_parse_zero_pre_close():
    """昨收为 0 时涨跌幅为 None（除零保护）"""
    fields = ["贵州茅台", "0.00", "0.00", "10.00", "0.00", "0.00"]
    fields += [""] * 24 + ["2026-07-30", "16:30:00"]
    line = _make_sina_line("600519", *fields)
    s = data._parse(line)
    assert s is not None
    assert s["change"] is None
    assert s["change_pct"] is None


def test_sina_code_sh():
    assert data._sina_code("600519") == "sh600519"
    assert data._sina_code("900901") == "sh900901"
    assert data._sina_code("510300") == "sh510300"  # 沪市 ETF
    assert data._sina_code("588000") == "sh588000"  # 沪市 ETF


def test_sina_code_sz():
    assert data._sina_code("000001") == "sz000001"
    assert data._sina_code("300750") == "sz300750"
    assert data._sina_code("159915") == "sz159915"  # 深市 ETF


def test_sina_code_etf():
    """沪市 ETF（5 开头）应映射到 sh，而不是 sz。"""
    assert data._sina_code("510050") == "sh510050"
    assert data._sina_code("588000") == "sh588000"
    assert data._sina_code("511990") == "sh511990"


def test_sina_code_bj():
    """北交所代码（4/8/92 开头）映射到 bj。"""
    assert data._sina_code("430047") == "bj430047"
    assert data._sina_code("832566") == "bj832566"
    assert data._sina_code("871981") == "bj871981"
    assert data._sina_code("920002") == "bj920002"


def test_sina_code_bond_sh():
    """沪市债券（01 国债 / 110-118 转债 / 122-127 企业债 / 132 / 204 回购）映射到 sh。"""
    assert data._sina_code("010107") == "sh010107"  # 沪市国债
    assert data._sina_code("019547") == "sh019547"  # 沪市国债
    assert data._sina_code("110079") == "sh110079"  # 沪市可转债
    assert data._sina_code("113550") == "sh113550"  # 沪市可转债
    assert data._sina_code("118001") == "sh118001"  # 沪市可转债
    assert data._sina_code("122009") == "sh122009"  # 沪市企业债
    assert data._sina_code("124112") == "sh124112"  # 沪市企业债
    assert data._sina_code("127111") == "sh127111"  # 沪市公司债
    assert data._sina_code("132001") == "sh132001"  # 沪市可交换债
    assert data._sina_code("204001") == "sh204001"  # 沪市国债回购
    assert data._sina_code("713123") == "sh713123"  # 沪市新可转债段（2024 后上市）


def test_sina_code_bond_sz():
    """深市债券（10-13 段）保持 sz：国债 / 企业债 / 公司债 / 可转债 / 回购。"""
    assert data._sina_code("100213") == "sz100213"  # 深市国债
    assert data._sina_code("101213") == "sz101213"  # 深市国债
    assert data._sina_code("109118") == "sz109118"  # 深市地方债
    assert data._sina_code("111051") == "sz111051"  # 深市企业债
    assert data._sina_code("112493") == "sz112493"  # 深市公司债
    assert data._sina_code("123118") == "sz123118"  # 深市可转债
    assert data._sina_code("128095") == "sz128095"  # 深市可转债
    assert data._sina_code("131810") == "sz131810"  # 深市国债回购


def test_is_bond():
    assert data._is_bond("010107") is True
    assert data._is_bond("113550") is True
    assert data._is_bond("713123") is True  # 沪市新可转债段
    assert data._is_bond("112493") is True
    assert data._is_bond("123118") is True
    assert data._is_bond("204001") is True
    assert data._is_bond("131810") is True
    # 股票 / ETF / 深市基金不受影响
    assert data._is_bond("600519") is False
    assert data._is_bond("000001") is False
    assert data._is_bond("510300") is False
    assert data._is_bond("159915") is False
    assert data._is_bond("161725") is False  # 深市 LOF 基金，非债券


def test_is_fund():
    """场内基金段位：沪 5 段 + 深 15/16/18 段（18 为 REITs/封闭式基金）。"""
    assert data._is_fund("510300") is True
    assert data._is_fund("588000") is True
    assert data._is_fund("508000") is True  # 沪市 REITs
    assert data._is_fund("159915") is True
    assert data._is_fund("161725") is True  # 深市 LOF
    assert data._is_fund("180101") is True  # 深市 REITs
    assert data._is_fund("184801") is True  # 深市封闭式基金
    assert data._is_fund("600519") is False
    assert data._is_fund("000001") is False


def test_price_decimals():
    """精度判定唯一入口：场内基金 / 债券 3 位，股票（含北交所）2 位。"""
    assert data.price_decimals("600519") == 2  # 沪市股票
    assert data.price_decimals("000001") == 2  # 深市股票
    assert data.price_decimals("430047") == 2  # 北交所
    assert data.price_decimals("510300") == 3  # 沪市 ETF
    assert data.price_decimals("508000") == 3  # 沪市 REITs
    assert data.price_decimals("159915") == 3  # 深市 ETF
    assert data.price_decimals("161725") == 3  # 深市 LOF
    assert data.price_decimals("180101") == 3  # 深市 REITs（此前误判为 2 位）
    assert data.price_decimals("113550") == 3  # 沪市可转债
    assert data.price_decimals("123118") == 3  # 深市可转债


def test_parse_reit_sz():
    """深市 REITs（180101 蛇口产园实测格式）：价格与涨跌额按 3 位小数。"""
    fields = (
        ["蛇口产园", "1.470", "1.470", "1.458", "1.470", "1.442", "1.456", "1.458"]
        + ["3775063", "5481176.800"]
        + [""] * 20
        + ["2026-09-11", "15:00:00"]
    )
    line = _make_sina_line("180101", *fields)
    s = data._parse(line)
    assert s is not None
    assert s["code"] == "180101"
    assert s["name"] == "蛇口产园"
    assert s["price"] == 1.458
    assert s["change"] == -0.012  # 3 位小数，不能被舍成 -0.01
    assert s["change_pct"] == pytest.approx(-0.82, rel=0.01)


def test_parse_etf():
    """ETF 行情与股票同字段布局（510300 沪深300ETF 实测格式）"""
    fields = (
        ["沪深300ETF", "4.750", "4.759", "4.728", "4.775", "4.722", "4.727", "4.728"]
        + ["535321917", "2541400132"]
        + [""] * 20
        + ["2026-07-30", "16:30:00"]
    )
    line = _make_sina_line("510300", *fields)
    s = data._parse(line)
    assert s is not None
    assert s["code"] == "510300"
    assert s["name"] == "沪深300ETF"
    assert s["price"] == 4.728
    assert s["vol"] == 535321917
    assert s["change"] == -0.031
    assert s["change_pct"] == pytest.approx(-0.65, rel=0.01)


def test_parse_bond():
    """债券行情 3 位小数，涨跌额按 3 位取整（123118 惠城转债实测格式）"""
    fields = (
        ["惠城转债", "961.500", "961.500", "952.725", "963.000", "923.650"]
        + ["0", "0", "356170", "334831401.070"]
        + [""] * 20
        + ["2026-08-12", "10:28:03"]
    )
    line = _make_sina_line("123118", *fields)
    s = data._parse(line)
    assert s is not None
    assert s["code"] == "123118"
    assert s["name"] == "惠城转债"
    assert s["price"] == 952.725
    assert s["vol"] == 356170
    assert s["change"] == -8.775
    assert s["change_pct"] == pytest.approx(-0.91, rel=0.01)


def test_parse_bond_sh():
    """沪市债券（113550 常汽转债实测格式）"""
    fields = (
        ["常汽转债", "154.460", "154.460", "154.460", "0.000", "0.000"]
        + ["0", "0", "0", "0.000"]
        + [""] * 20
        + ["2026-06-10", "09:00:00"]
    )
    line = _make_sina_line("113550", *fields)
    s = data._parse(line)
    assert s is not None
    assert s["code"] == "113550"
    assert s["price"] == 154.460
    assert s["change"] == 0.0


def test_fetch_empty():
    assert data.fetch([]) == []


def test_f():  # noqa: N802 — mimic internal helper name
    assert data._f("12.50") == 12.50
    assert data._f("") is None
    assert data._f("abc") is None


def test_i():  # noqa: N802
    assert data._i("5000000") == 5_000_000
    assert data._i("") is None
    assert data._i("abc") is None


def test_split_key():
    assert data.split_key("000001") == (None, "000001")
    assert data.split_key("sh:000001") == ("sh", "000001")
    assert data.split_key("sz:159915") == ("sz", "159915")
    assert data.split_key("bj:920002") == ("bj", "920002")
    # 未知前缀 / 非数字后缀按裸代码处理，不当显式前缀
    assert data.split_key("xx:000001") == (None, "xx:000001")
    assert data.split_key("sh:abc") == (None, "sh:abc")


def test_make_key():
    """与段位规则一致时存裸代码；只有偏离规则才存显式前缀键。"""
    assert data.make_key("sz", "000001") == "000001"
    assert data.make_key("sh", "600519") == "600519"
    assert data.make_key("sh", "000001") == "sh:000001"  # 上证指数：规则给 sz
    assert data.make_key("sh", "000300") == "sh:000300"  # 沪深 300：规则给 sz
    assert data.make_key("sz", "510300") == "sz:510300"  # 强制深市


def test_sina_key():
    assert data.sina_key("000001") == "sz000001"
    assert data.sina_key("sh:000001") == "sh000001"
    assert data.sina_key("sh:000300") == "sh000300"
    assert data.sina_key("bj:920002") == "bj920002"


def test_price_decimals_accepts_keys():
    """精度只看代码段，不受交易所前缀影响。"""
    assert data.price_decimals("sh:000001") == 2  # 上证指数
    assert data.price_decimals("sz:510300") == 3
    assert data.price_decimals("sh:508000") == 3


def test_parse_fills_stored_key():
    """mapping 命中时 code 回填原存储键（持仓/分组按同一键对齐），未命中用裸代码。"""
    fields = (
        ["上证指数", "3910.92", "3934.40", "3888.11", "3912.32", "3852.03"]
        + [""] * 24
        + ["2026-09-11", "15:00:00"]
    )
    line = f'var hq_str_sh000001="{",".join(fields)}"'
    assert data._parse(line, {"sh000001": "sh:000001"})["code"] == "sh:000001"
    assert data._parse(line)["code"] == "000001"


def test_fetch_resolves_keys_and_dedupes(monkeypatch):
    """请求用 sina_key 解析后的代码，同一 Sina 代码只发一次。"""
    seen = {}

    class _Resp:
        encoding = "gbk"
        text = ""

    def fake_get(url, headers=None, timeout=None):
        seen["url"] = url
        return _Resp()

    monkeypatch.setattr(data.requests, "get", fake_get)
    assert data.fetch(["000001", "000001", "sh:000001"]) == []
    assert seen["url"].endswith("list=sz000001,sh000001")


def test_probe_returns_prefixes(monkeypatch):
    """probe 把 fetch 结果映射成 [(前缀, 名称)]，保序。"""

    def fake_fetch(keys):
        assert keys == ["sh:000001", "sz:000001", "bj:000001"]
        return [
            {"code": "sh:000001", "name": "上证指数"},
            {"code": "sz:000001", "name": "平安银行"},
        ]

    monkeypatch.setattr(data, "fetch", fake_fetch)
    assert data.probe("000001") == [("sh", "上证指数"), ("sz", "平安银行")]


def test_probe_single_prefix(monkeypatch):
    def fake_fetch(keys):
        assert keys == ["sh:000001"]
        return []

    monkeypatch.setattr(data, "fetch", fake_fetch)
    assert data.probe("000001", prefix="sh") == []


def test_probe_offline(monkeypatch):
    """网络异常返回 None，调用方据此回退段位规则。"""
    monkeypatch.setattr(data, "fetch", lambda keys: None)
    assert data.probe("000001") is None


# ── 场外开放式基金（`fu:` 显式前缀） ──────────────────────

# 110022 易方达消费行业股票 实测原文（10 字段净值格式）
FU_LINE = (
    'var hq_str_fu_110022="易方达消费行业股票,16:04:00,2.8377,2.8260,2.8260,0,'
    '0.4149,2026-09-14,2.8378,0.4184";'
)


def test_split_key_fu():
    assert data.split_key("fu:110022") == ("fu", "110022")


def test_sina_key_fu():
    """场外基金用下划线连接（fu_110022）；场内/指数仍是直接拼接。"""
    assert data.sina_key("fu:110022") == "fu_110022"
    assert data.sina_key("fu:511990") == "fu_511990"
    assert data.sina_key("sh:600519") == "sh600519"  # 场内格式不变
    assert data.sina_key("600519") == "sh600519"


def test_make_key_fu():
    """fu 永远判不出来（default_prefix 只给 sh/sz/bj），故必存显式前缀键。"""
    assert data.make_key("fu", "110022") == "fu:110022"
    assert data.make_key("fu", "000001") == "fu:000001"


def test_default_prefix_ignores_fu():
    """裸代码段位规则零改动：永远不会判成场外基金，fu 只能显式写。

    110022 落沪市可转债段（110）→ `sh`（实测 sh110022 无行情，旧的静默跳过即源于此），
    000001 → `sz`；两者都不受本次新增的 `fu` 影响。
    """
    assert data.default_prefix("110022") == "sh"
    assert data.default_prefix("000001") == "sz"
    assert data.default_prefix("600519") == "sh"
    assert data.default_prefix("430047") == "bj"
    assert data.make_key("fu", "110022") == "fu:110022"  # 与规则不符 → 存显式键


def test_price_decimals_fu():
    """场外基金 4 位小数；股票 2 位、场内基金/债券 3 位（既有行为）不变。"""
    assert data.price_decimals("fu:110022") == 4
    assert data.price_decimals("fu:511990") == 4  # 前缀优先于代码段
    assert data.price_decimals("510300") == 3
    assert data.price_decimals("600519") == 2
    assert data.price_decimals("sh:600519") == 2
    assert data.price_decimals("180101") == 3
    assert data.price_decimals("123118") == 3


def test_parse_fu():
    """场外 10 字段：f[2] 估算净值 → price，f[3] 单位净值 → pre_close，无开高低/量额。"""
    s = data._parse(FU_LINE, {"fu_110022": "fu:110022"})
    assert s is not None
    assert s["code"] == "fu:110022"  # 回填存储键，持仓/分组才对得上
    assert s["name"] == "易方达消费行业股票"
    assert s["price"] == 2.8377
    assert s["pre_close"] == 2.8260
    assert s["change"] == 0.0117  # 4 位小数
    assert s["change_pct"] == pytest.approx(0.4149, rel=0.01)  # 取 f[6]
    assert s["date"] == "2026-09-14"
    assert s["trade_time"] == "16:04:00"
    for k in ("open", "high", "low", "vol", "amount"):
        assert s[k] is None


def test_parse_fu_same_shape_as_listed():
    """场外输出与场内同构（同一套列渲染代码直接可用）。"""
    fields = (
        ["沪深300ETF", "4.750", "4.759", "4.728", "4.775", "4.722"]
        + [""] * 26
        + ["2026-07-30", "16:30:00"]
    )
    listed = data._parse(_make_sina_line("510300", *fields))
    assert set(data._parse(FU_LINE)) == set(listed)


def test_parse_fu_money_fund_empty():
    """场外货币基金返回空串（接口不返回净值）→ None，按查无行情处理。"""
    assert data._parse('var hq_str_fu_511990="";') is None
    assert data._parse('var hq_str_fu_511990="";', {"fu_511990": "fu:511990"}) is None


def test_parse_fu_change_pct_fallback():
    """f[6] 解析不出时用 price/pre_close 自算。"""
    line = (
        'var hq_str_fu_110022="易方达消费行业股票,16:04:00,2.8377,2.8260,2.8260,0,,2026-09-14,,";'
    )
    s = data._parse(line)
    assert s["change"] == 0.0117
    assert s["change_pct"] == pytest.approx(0.41, rel=0.01)


def test_parse_fu_zero_pre_close():
    """单位净值为 0（无披露）时涨跌与涨跌幅为 None（除零保护）。"""
    line = 'var hq_str_fu_110022="某基金,16:04:00,2.8377,0,0,0,0,2026-09-14,,";'
    s = data._parse(line)
    assert s is not None
    assert s["change"] is None
    assert s["change_pct"] is None


def test_probe_default_excludes_fu(monkeypatch):
    """回归保护：裸代码探测只查 sh/sz/bj，绝不请求 fu_ —— 否则 `add 000001`
    会多出一个「华夏成长混合A」候选，股票消歧体验被破坏。"""
    keys = []

    def fake_fetch(ks):
        keys.extend(ks)
        return []

    monkeypatch.setattr(data, "fetch", fake_fetch)
    assert data.probe("000001") == []
    assert keys == ["sh:000001", "sz:000001", "bj:000001"]
    assert data.PROBE_EXCHANGES == ("sh", "sz", "bj")
    assert "fu" in data.EXCHANGES  # 可显式指定，只是不参与探测


def test_probe_fu_explicit_prefix(monkeypatch):
    """显式 fu: 前缀才查场外。"""
    calls = []

    def fake_fetch(keys):
        calls.append(keys)
        return [{"code": "fu:110022", "name": "易方达消费行业股票"}]

    monkeypatch.setattr(data, "fetch", fake_fetch)
    assert data.probe("110022", prefix="fu") == [("fu", "易方达消费行业股票")]
    assert calls == [["fu:110022"]]


def test_fetch_fu_backfills_stored_key(monkeypatch):
    """请求 fu_110022（下划线），响应回填原存储键 fu:110022。"""

    class _Resp:
        encoding = "gbk"
        text = FU_LINE

    seen = {}

    def fake_get(url, headers=None, timeout=None):
        seen["url"] = url
        return _Resp()

    monkeypatch.setattr(data.requests, "get", fake_get)
    stocks = data.fetch(["fu:110022"])
    assert seen["url"].endswith("list=fu_110022")
    assert stocks[0]["code"] == "fu:110022"
    assert stocks[0]["price"] == 2.8377
