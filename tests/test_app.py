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


def test_build_table_etf_price_precision():
    """ETF 价格显示 3 位小数（4.728 不四舍五入成 4.73），股票仍 2 位"""
    etf = _stock()
    etf["code"] = "510300"
    etf["price"] = 4.728
    etf["open"] = 4.750
    tr = lang("en")["t"]
    table = _build_table([etf], {}, 0, tr)
    assert "4.728" in table.columns[2]._cells[0].plain  # Price
    assert "4.750" in table.columns[6]._cells[0].plain  # Open
    # 股票保持 2 位
    stk_table = _build_table([_stock()], {}, 0, tr)
    assert "1690.00" in stk_table.columns[2]._cells[0].plain


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


def test_group_filter_all():
    """group_view=None 时原样返回。"""
    from bosskey_stock.app import _group_filter

    stocks = [{"code": "600519"}, {"code": "000001"}]
    assert _group_filter(stocks, {}, None) is stocks


def test_group_filter_by_group_order():
    """分组视图按组内顺序排列，忽略全局顺序；无行情的组内代码跳过。"""
    from bosskey_stock.app import _group_filter

    stocks = [{"code": "600519"}, {"code": "000001"}, {"code": "300750"}]
    groups = {"持仓": ["000001", "600519"], "自选": ["888888"]}
    assert [s["code"] for s in _group_filter(stocks, groups, "持仓")] == ["000001", "600519"]
    assert [s["code"] for s in _group_filter(stocks, groups, "自选")] == []  # 无行情跳过


def test_group_filter_missing_group():
    """分组不存在时为空列表。"""
    from bosskey_stock.app import _group_filter

    stocks = [{"code": "600519"}]
    assert _group_filter(stocks, {}, "不存在") == []


def test_build_table_group_title():
    """有分组时表格标题始终显示当前视图（分组名 / 全部），无分组时无标题。"""
    from bosskey_stock.app import _build_table

    tr = lang("zh")["t"]
    stocks = [_stock()]
    t1 = _build_table(stocks, {}, 0, tr, group_name="持仓", has_groups=True)
    assert t1.title == "分组: 持仓"
    t2 = _build_table(stocks, {}, 0, tr, group_name=None, has_groups=True)
    assert t2.title == "全部"
    t3 = _build_table(stocks, {}, 0, tr)
    assert t3.title is None  # 无分组时保持极简


# ── 主循环：默认单色 ──────────────────────────────────────


class _FakeLive:
    """替代 rich Live 的桩：仅记录 update 调用。"""

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def update(self, *a, **k):
        pass


class _FakeStdin:
    def fileno(self):
        return 0


def _run_main_loop(monkeypatch, display_cfg, keys=("q",)):
    """跑一轮 main_loop，返回 _build_view 调用记录；keys 为依次返回的按键队列。"""
    import termios

    import bosskey_stock.app as app

    cfg = {
        "watchlist": {"codes": ["000001"], "groups": {}},
        "holdings": {},
        "display": display_cfg,
    }
    calls = []
    real_build_view = app._build_view

    def spy(*args, **kwargs):
        calls.append((args, kwargs))
        return real_build_view(*args, **kwargs)

    key_iter = iter(keys)
    monkeypatch.setattr(app, "fetch", lambda codes: None)
    monkeypatch.setattr(app, "_read_key", lambda fd: next(key_iter, "q"))
    monkeypatch.setattr(app, "_setup_tty", lambda fd: None)
    monkeypatch.setattr(app, "Live", _FakeLive)
    monkeypatch.setattr(app, "_build_view", spy)
    monkeypatch.setattr(app.sys, "stdin", _FakeStdin())
    monkeypatch.setattr(termios, "tcgetattr", lambda fd: None)
    monkeypatch.setattr(termios, "tcsetattr", lambda *a, **k: None)
    app.main_loop(cfg)
    return calls


def test_main_loop_defaults_to_mono(monkeypatch):
    """默认单色：display 无 colorize 键时首次渲染 colorize=False。"""
    calls = _run_main_loop(monkeypatch, {"refresh_interval": 3, "lang": "en"})
    assert calls and calls[0][0][8] is False


def test_main_loop_defaults_to_all_columns(monkeypatch):
    """默认展示全部列：首次渲染 mode=3（全 14 列）。"""
    calls = _run_main_loop(monkeypatch, {"refresh_interval": 3, "lang": "en"})
    assert calls and calls[0][0][2] == 3


def test_main_loop_t_key_collapses_columns(monkeypatch):
    """默认全列下 t 键逐层收起：3 → 2 → 1 → 0 循环。"""
    calls = _run_main_loop(
        monkeypatch, {"refresh_interval": 3, "lang": "en"}, keys=("t", "t", "t", "q")
    )
    assert [c[0][2] for c in calls] == [3, 2, 1, 0]


def test_main_loop_colorize_from_config(monkeypatch):
    """配置 colorize=true 时启动即彩色。"""
    calls = _run_main_loop(monkeypatch, {"refresh_interval": 3, "lang": "en", "colorize": True})
    assert calls and calls[0][0][8] is True
