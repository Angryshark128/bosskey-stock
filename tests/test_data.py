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


def test_sina_code_sz():
    assert data._sina_code("000001") == "sz000001"
    assert data._sina_code("300750") == "sz300750"


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
