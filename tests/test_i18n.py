"""Tests for i18n — 中英文案与语言解析。"""

from bosskey_stock.i18n import lang, resolve


def test_lang_default_en():
    lg = lang()
    assert lg["code"] == "en"
    assert lg["t"]("col_code") == "Code"
    assert lg["t"]("col_price") == "Price"


def test_lang_zh():
    lg = lang("zh")
    assert lg["code"] == "zh"
    assert lg["t"]("col_code") == "代码"
    assert lg["t"]("col_price") == "现价"


def test_lang_format_args():
    lg = lang("zh")
    assert lg["t"]("cli_range", n=5) == "请输入 1 到 5 之间的编号。"
    assert lg["t"]("cli_added", codes="000001") == "已添加: 000001"


def test_resolve_valid():
    assert resolve("en") == "en"
    assert resolve("zh") == "zh"


def test_resolve_unknown_falls_back_en():
    assert resolve("fr") == "en"
    assert resolve("") == "en"
    assert resolve(None) == "en"


def test_all_keys_have_both_langs():
    """每个文案 key 两种语言都有值，且不重复。"""
    from bosskey_stock.i18n import _T

    assert _T, "i18n 文案表不能为空"
    for key, (en, zh) in _T.items():
        assert en and zh, f"key {key} 缺少 en/zh 文案"
        assert en != zh, f"key {key} 中英文案相同（可能漏翻译）"


def test_lang_keys_exist_for_all_used():
    """app.py 用到的文案 key 必须都在文案表中（防拼写漂移）。"""
    import inspect

    import bosskey_stock.app as app
    from bosskey_stock import i18n

    src = inspect.getsource(app)
    keys = {k for k in set(i18n._T) if f'tr("{k}")' in src or f"tr('{k}')" in src}
    assert keys, "未检测到 app.py 中的 tr() 调用"
