"""Tests for TUI — 持仓收益计算与列渲染。"""

import pytest

from bosskey_stock.app import _build_summary, _build_table, _build_view, _pos_metrics
from bosskey_stock.i18n import lang


def _stock():
    return {
        "code": "600519",
        "name": "贵州茅台",
        "open": 1680.0,
        "pre_close": 1675.0,
        "price": 1690.0,
        "high": 1700.0,
        "low": 1670.0,
        "vol": None,
        "amount": None,
        "date": "",
        "trade_time": "",
        "change": 15.0,
        "change_pct": 0.90,
    }


def test_pos_metrics():
    holdings = {"600519": {"shares": 100, "cost": 1600.0}}
    m = _pos_metrics(_stock(), holdings)
    assert m is not None
    assert m["shares"] == 100
    assert m["cost"] == 1600.0
    assert m["hold_pl"] == 9000.0
    assert m["hold_pct"] == pytest.approx(5.625)
    assert m["today_pl"] == 1500.0
    assert m["today_pct"] == 0.90


def test_pos_metrics_missing_holding():
    assert _pos_metrics(_stock(), {}) is None


def test_pos_metrics_incomplete():
    holdings = {"600519": {"shares": 0, "cost": 0}}
    assert _pos_metrics(_stock(), holdings) is None


def test_pos_metrics_no_price():
    s = _stock()
    s["price"] = None
    holdings = {"600519": {"shares": 100, "cost": 1600.0}}
    assert _pos_metrics(s, holdings) is None


def test_build_table_columns_grow_with_mode():
    stocks = [_stock()]
    h = {"600519": {"shares": 100, "cost": 1600.0}}
    en = lang("en")["t"]
    zh = lang("zh")["t"]
    assert len(_build_table(stocks, h, 0, en).columns) == 9
    assert len(_build_table(stocks, h, 1, en).columns) == 11
    assert len(_build_table(stocks, h, 2, en).columns) == 13
    # mode 3 不追加 TodayP/L%（与 Chg% 重复），共 14 列
    assert len(_build_table(stocks, h, 3, en).columns) == 14
    # 中文表头
    headers = [c.header for c in _build_table(stocks, h, 3, zh).columns]
    assert "今日盈亏" in headers
    assert "涨跌幅" in headers
    assert "TodayP/L%" not in headers
    assert "今日盈亏%" not in headers


def test_build_summary_modes():
    # price 1690.0, cost 1600.0, shares 100 → pos 169000, cost 160000,
    # hold_pl +9000 (5.62%), today_pl +1500 (0.90% vs pre_close 1675*100)
    stocks = [_stock()]
    h = {"600519": {"shares": 100, "cost": 1600.0}}
    en = lang("en")["t"]
    zh = lang("zh")["t"]
    s1 = _build_summary(stocks, h, 1, en).plain
    assert "Value 169,000.00" in s1
    assert "Cost 160,000.00" in s1
    s2 = _build_summary(stocks, h, 2, en).plain
    assert "HoldP/L +9,000.00 (+5.62%)" in s2
    s3 = _build_summary(stocks, h, 3, en).plain
    assert "TodayP/L +1,500.00 (+0.90%)" in s3
    # 中文汇总
    s1z = _build_summary(stocks, h, 1, zh).plain
    assert "市值 169,000.00" in s1z
    assert "成本 160,000.00" in s1z
    s3z = _build_summary(stocks, h, 3, zh).plain
    assert "今日盈亏 +1,500.00 (+0.90%)" in s3z


def test_build_summary_empty():
    stocks = [_stock()]
    tr = lang("en")["t"]
    assert _build_summary(stocks, {}, 3, tr).plain == ""
    assert _build_summary(stocks, {"600519": {"shares": 0, "cost": 0}}, 3, tr).plain == ""


def test_build_view_help_hidden_by_default():
    stocks = [_stock()]
    tr = lang("en")["t"]
    v = _build_view(stocks, {}, 0, False, False, "14:32:05", tr)
    assert v.renderables[0] is not None  # 表格
    assert len(v.renderables) == 2  # 无帮助行
    v2 = _build_view(stocks, {}, 0, False, False, "14:32:05", tr, show_help=True)
    assert len(v2.renderables) == 3  # 追加帮助行
    assert "q quit" in v2.renderables[2].plain
