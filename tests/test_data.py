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


def test_is_etf():
    assert data._is_etf("510300") is True
    assert data._is_etf("588000") is True
    assert data._is_etf("159915") is True
    assert data._is_etf("600519") is False
    assert data._is_etf("000001") is False


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
