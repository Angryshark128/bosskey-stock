"""Tests for CLI 代码消歧：同名代码选择、无行情提示、删除匹配。"""

import pytest

from bosskey_stock import __main__ as cli
from bosskey_stock import data
from bosskey_stock.i18n import lang

TR = lang("en")["t"]


@pytest.fixture
def watchlist(monkeypatch):
    """内存 watchlist 替掉 config 读写。"""
    store = {"codes": []}
    monkeypatch.setattr(cli.config, "list_codes", lambda: list(store["codes"]))
    monkeypatch.setattr(cli.config, "add_codes", lambda *ks: store["codes"].extend(ks))
    monkeypatch.setattr(
        cli.config,
        "remove_codes",
        lambda *ks: store.__setitem__("codes", [c for c in store["codes"] if c not in ks]),
    )
    return store


# ── add：探测 + 消歧 ─────────────────────────────────────


def test_resolve_add_bad_code(capsys):
    assert cli._resolve_add("abc", TR) is None
    assert cli._resolve_add("12345", TR) is None
    assert "Not a 6-digit code" in capsys.readouterr().out


def test_resolve_add_no_quote(monkeypatch, capsys):
    monkeypatch.setattr(data, "probe", lambda code, prefix=None: [])
    assert cli._resolve_add("999999", TR) is None
    assert "No quote" in capsys.readouterr().out


def test_resolve_add_single_candidate(monkeypatch):
    monkeypatch.setattr(data, "probe", lambda code, prefix=None: [("sz", "平安银行")])
    assert cli._resolve_add("000001", TR) == "000001"


def test_resolve_add_deviates_from_rule(monkeypatch):
    """唯一命中在非规则交易所时存显式前缀键（沪深 300 在 sh 段）。"""
    monkeypatch.setattr(data, "probe", lambda code, prefix=None: [("sh", "沪深300")])
    assert cli._resolve_add("000300", TR) == "sh:000300"


def test_resolve_add_offline_falls_back(monkeypatch):
    """探测失败（离线）按段位规则加入，保持可用。"""
    monkeypatch.setattr(data, "probe", lambda code, prefix=None: None)
    assert cli._resolve_add("000001", TR) == "000001"


def test_resolve_add_ambiguous_takes_rule_without_prompt(monkeypatch, capsys):
    """多命中：不打断输入，直接取段位规则那条（000001 -> sz 平安银行），
    并把另一条候选连同其强制前缀打成一行提示。"""
    monkeypatch.setattr(
        data,
        "probe",
        lambda code, prefix=None: [("sh", "上证指数"), ("sz", "平安银行")],
    )

    def no_prompt(prompt=""):
        raise AssertionError("多命中不应再询问用户")

    monkeypatch.setattr("builtins.input", no_prompt)
    assert cli._resolve_add("000001", TR) == "000001"
    out = capsys.readouterr().out
    assert "平安银行" in out
    assert "上证指数" in out and "sh:000001" in out


@pytest.mark.parametrize(
    "code",
    [
        "000001", "000002", "000003", "000004", "000006",
        "000009", "000011", "000016", "000060", "000099",
    ],
)
def test_resolve_add_index_stock_collision_never_prompts(monkeypatch, code):
    """实测回归：000xxx 段有 204 个代码在沪（上证系列指数）与深（主板股票）同时有行情，
    add 时会撞车。这类代码一律不追问，直接落段位规则那条（深市股票）。"""
    monkeypatch.setattr(
        data,
        "probe",
        lambda c, prefix=None: [("sh", "上证指数"), ("sz", "平安银行")],
    )

    def no_prompt(prompt=""):
        raise AssertionError(f"{code} 不应询问用户")

    monkeypatch.setattr("builtins.input", no_prompt)
    assert cli._resolve_add(code, TR) == code  # 裸代码 = 段位规则（sz）


def test_resolve_add_other_candidate_via_prefix(monkeypatch):
    """想取另一条候选：显式写前缀即可，同样不询问。"""
    monkeypatch.setattr(
        data,
        "probe",
        lambda code, prefix=None: [("sh", "上证指数")] if prefix == "sh" else [],
    )

    def no_prompt(prompt=""):
        raise AssertionError("显式前缀不应询问")

    monkeypatch.setattr("builtins.input", no_prompt)
    assert cli._resolve_add("sh:000001", TR) == "sh:000001"


def test_resolve_add_ambiguous_rule_missing_from_candidates(monkeypatch, capsys):
    """规则那条没行情时取第一个命中，且提示的「另一条」不会把已选中的又列一遍。"""
    monkeypatch.setattr(
        data,
        "probe",
        lambda code, prefix=None: [("sh", "上证指数"), ("bj", "北交所同码")],
    )
    assert cli._resolve_add("000001", TR) == "sh:000001"
    out = capsys.readouterr().out
    assert out.count("上证指数") == 1  # 选中的那条只出现一次
    assert "北交所同码" in out and "bj:000001" in out  # 另一条带前缀提示


def test_resolve_add_explicit_prefix_skips_other_exchanges(monkeypatch):
    calls = []

    def fake_probe(code, prefix=None):
        calls.append((code, prefix))
        return [("sh", "上证指数")]

    monkeypatch.setattr(data, "probe", fake_probe)
    assert cli._resolve_add("sh:000001", TR) == "sh:000001"
    assert calls == [("000001", "sh")]


def test_resolve_add_explicit_prefix_normalized(monkeypatch):
    """与段位规则一致的前缀会被规范化掉，避免同一标的存两份。"""
    monkeypatch.setattr(data, "probe", lambda code, prefix=None: [("sz", "平安银行")])
    assert cli._resolve_add("sz:000001", TR) == "000001"


def test_resolve_add_explicit_prefix_no_quote(monkeypatch, capsys):
    """显式前缀但查无行情：提示并回显规范化后的键（300750 属深市，前缀与规则不符）。"""
    monkeypatch.setattr(data, "probe", lambda code, prefix=None: [])
    assert cli._resolve_add("sh:300750", TR) is None
    assert "sh:300750" in capsys.readouterr().out


# ── rm：匹配 + 消歧 ─────────────────────────────────────


def test_match_stored(watchlist):
    watchlist["codes"] = ["000001", "sh:000001", "510300"]
    assert cli._match_stored("000001") == ["000001", "sh:000001"]
    assert cli._match_stored("510300") == ["510300"]
    assert cli._match_stored("sh:000001") == ["sh:000001"]  # 带前缀 = 精确匹配
    assert cli._match_stored("600519") == []


def test_choose_remove_pick_one(monkeypatch):
    monkeypatch.setattr(data, "fetch", lambda ks: [{"code": "000001", "name": "平安银行"}])
    monkeypatch.setattr("builtins.input", lambda prompt="": "2")
    assert cli._choose_remove("000001", ["000001", "sh:000001"], TR) == ["sh:000001"]


def test_choose_remove_all(monkeypatch):
    monkeypatch.setattr(data, "fetch", lambda ks: [])
    monkeypatch.setattr("builtins.input", lambda prompt="": "a")
    assert cli._choose_remove("000001", ["000001", "sh:000001"], TR) == [
        "000001",
        "sh:000001",
    ]


def test_choose_remove_retries_on_bad_input(monkeypatch):
    monkeypatch.setattr(data, "fetch", lambda ks: [])
    answers = iter(["9", "1"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    assert cli._choose_remove("000001", ["000001", "sh:000001"], TR) == ["000001"]


def test_choose_remove_eof_cancels(monkeypatch, capsys):
    monkeypatch.setattr(data, "fetch", lambda ks: [])

    def eof(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", eof)
    assert cli._choose_remove("000001", ["000001", "sh:000001"], TR) == []
    assert "Cancelled" in capsys.readouterr().out


# ── group add / pos rm：同样走消歧 ─────────────────────


def test_match_stored_with_explicit_keys():
    """keys 参数可用于持仓、分组等其它键集合。"""
    keys = ["000001", "sh:000001", "510300"]
    assert cli._match_stored("000001", keys) == ["000001", "sh:000001"]
    assert cli._match_stored("sh:000001", keys) == ["sh:000001"]


def test_group_add_resolves_codes(monkeypatch):
    """group add 与 group add-codes 行为一致：先消歧再入库。"""
    created = {}
    monkeypatch.setattr(cli.config, "get_lang", lambda: "en")
    monkeypatch.setattr(
        cli.config, "group_add", lambda name, *codes: created.update({name: codes})
    )
    monkeypatch.setattr(data, "probe", lambda code, prefix=None: [("sh", "上证指数")])
    monkeypatch.setattr(cli.sys, "argv", ["bosskey", "group", "add", "场内", "000001"])
    cli.main()
    assert created == {"场内": ("sh:000001",)}


def test_pos_rm_ambiguous_chooser(monkeypatch):
    """pos rm 命中多条持仓时让用户选（持仓键同样可带前缀）。"""
    removed = []
    monkeypatch.setattr(cli.config, "get_lang", lambda: "en")
    monkeypatch.setattr(
        cli.config,
        "list_positions",
        lambda: {
            "000001": {"shares": 1, "cost": 1.0},
            "sh:000001": {"shares": 2, "cost": 2.0},
        },
    )
    monkeypatch.setattr(cli.config, "remove_position", removed.append)
    monkeypatch.setattr(data, "fetch", lambda ks: [])
    monkeypatch.setattr("builtins.input", lambda prompt="": "2")
    monkeypatch.setattr(cli.sys, "argv", ["bosskey", "pos", "rm", "000001"])
    cli.main()
    assert removed == ["sh:000001"]


# ── 场外开放式基金（`fu:` 显式前缀） ──────────────────────


def _sina_line(prefix, code, name, pre_close, price, open_=None):
    """拼一条 32 字段的场内行情响应行。"""
    fields = [name, open_ or pre_close, pre_close, price, price, price] + [""] * 24
    fields += ["2026-09-14", "15:00:00"]
    return f'var hq_str_{prefix}{code}="{",".join(fields)}"'


class _SinaResp:
    encoding = "gbk"

    def __init__(self, text):
        self.text = text


def test_resolve_add_fu_explicit_prefix(monkeypatch):
    """fu: 走显式前缀路径，只探场外，不与 sh/sz/bj 混探。"""
    calls = []

    def fake_probe(code, prefix=None):
        calls.append((code, prefix))
        return [("fu", "易方达消费行业股票")]

    monkeypatch.setattr(data, "probe", fake_probe)
    assert cli._resolve_add("fu:110022", TR) == "fu:110022"
    assert calls == [("110022", "fu")]


def test_resolve_add_fu_money_fund_no_nav(monkeypatch, capsys):
    """场外货基探测为空：给专门提示，不跟普通「查无行情」混在一起。"""
    monkeypatch.setattr(data, "probe", lambda code, prefix=None: [])
    assert cli._resolve_add("fu:511990", TR) is None
    out = capsys.readouterr().out
    assert "fu:511990" in out
    assert "money market" in out
    assert "No quote" not in out


def test_resolve_add_bare_110022_probes_only_listed_exchanges(monkeypatch):
    """实测回归：裸 110022 命中的是深市贴现国债（sz110022），探测请求里没有 fu_
    —— 它偏离段位规则（110 段算沪市债券）故存显式键 sz:110022，但显示的是债券行情；
    想加易方达消费行业必须写 fu:110022。"""
    seen = {}

    def fake_get(url, headers=None, timeout=None):
        seen["url"] = url
        return _SinaResp(_sina_line("sz", "110022", "贴债2381", "100.000", "0.000"))

    monkeypatch.setattr(cli.data.requests, "get", fake_get)
    assert cli._resolve_add("110022", TR) == "sz:110022"  # 静默按深市债券加入
    assert "fu_" not in seen["url"]
    assert seen["url"].endswith("list=sh110022,sz110022,bj110022")


def test_resolve_add_bare_000001_still_two_candidates(monkeypatch, capsys):
    """回归保护：add 000001 只探 sh/sz/bj 三家，不出现场外候选；双命中不追问。"""
    seen = {}
    text = "\n".join(
        [
            _sina_line("sh", "000001", "上证指数", "3934.40", "3888.11"),
            _sina_line("sz", "000001", "平安银行", "11.740", "11.850"),
        ]
    )

    def fake_get(url, headers=None, timeout=None):
        seen["url"] = url
        return _SinaResp(text)

    def no_prompt(prompt=""):
        raise AssertionError("双命中不应询问")

    monkeypatch.setattr(cli.data.requests, "get", fake_get)
    monkeypatch.setattr("builtins.input", no_prompt)
    assert cli._resolve_add("000001", TR) == "000001"
    out = capsys.readouterr().out
    assert seen["url"].endswith("list=sh000001,sz000001,bj000001")
    assert "matches multiple" not in out  # 不再列候选让人选
    assert "平安银行" in out
    assert "上证指数" in out and "sh:000001" in out
    assert "fu" not in out


def test_prompt_accepts_fractional_and_integer_shares(monkeypatch):
    """pos add 录份额改为正数浮点：小数可用，整数输入行为不变。"""
    for raw, expected in (("352.4", 352.4), ("100", 100.0), ("100.0", 100.0)):
        monkeypatch.setattr("builtins.input", lambda prompt="", _r=raw: _r)
        assert cli._prompt(TR("cli_shares_prompt"), float, lambda v: v > 0, TR) == expected


def test_prompt_rejects_non_positive_shares(monkeypatch, capsys):
    answers = iter(["0", "-5", "352.4"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    assert cli._prompt(TR("cli_shares_prompt"), float, lambda v: v > 0, TR) == 352.4
    assert "Invalid input" in capsys.readouterr().out


def test_interactive_add_saves_fractional_shares(monkeypatch):
    """pos add 交互：场外基金小数份额能存进配置。"""
    saved = []
    monkeypatch.setattr(cli.config, "list_codes", lambda: ["fu:110022"])
    monkeypatch.setattr(cli.config, "list_positions", lambda: {})
    monkeypatch.setattr(
        cli.config, "add_position", lambda code, shares, cost: saved.append((code, shares, cost))
    )
    answers = iter(["1", "352.4", "2.8377"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    cli._interactive_add(TR)
    assert saved == [("fu:110022", 352.4, 2.8377)]


def test_print_positions_otc_and_listed(capsys):
    """pos list：场外小数份额 + 4 位成本净值；整数份额与 3 位成本显示不变。"""
    tr = lang("en")["t"]
    cli._print_positions({"fu:110022": {"shares": 352.4, "cost": 2.8377}}, tr)
    cli._print_positions({"600519": {"shares": 100, "cost": 1600.0}}, tr)
    out = capsys.readouterr().out
    assert "352.4sh" in out
    assert "cost 2.8377" in out
    assert "100sh" in out
    assert "cost 1600" in out
