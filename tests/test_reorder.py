"""Tests for interactive reorder — 顺序调整纯逻辑。"""

from bosskey_stock.__main__ import _build_parser, _reorder_move_down, _reorder_move_up


def _parser():
    return _build_parser()


def test_list_plain_no_interactive():
    args = _parser().parse_args(["list"])
    assert args.interactive is False


def test_list_i_interactive():
    args = _parser().parse_args(["list", "-i"])
    assert args.interactive is True


def test_list_interactive_long_flag():
    args = _parser().parse_args(["list", "--interactive"])
    assert args.interactive is True


def test_reorder_subcommand_removed():
    import pytest

    with pytest.raises(SystemExit):
        _parser().parse_args(["reorder"])


# ── group 子命令与 --group 参数解析 ──────────────────────


def test_list_group_plain():
    args = _parser().parse_args(["list", "--group", "持仓"])
    assert args.group == "持仓"
    assert args.interactive is False


def test_list_group_interactive():
    args = _parser().parse_args(["list", "-i", "--group", "持仓"])
    assert args.group == "持仓"
    assert args.interactive is True


def test_add_group_flag():
    args = _parser().parse_args(["add", "600519", "--group", "持仓"])
    assert args.group == "持仓"


def test_group_subcommand_add():
    args = _parser().parse_args(["group", "add", "持仓", "600519", "000001"])
    assert args.group_cmd == "add"
    assert args.name == "持仓"
    assert args.codes == ["600519", "000001"]


def test_group_subcommand_add_no_codes():
    args = _parser().parse_args(["group", "add", "空组"])
    assert args.group_cmd == "add"
    assert args.codes == []


def test_group_subcommand_rm():
    args = _parser().parse_args(["group", "rm", "持仓"])
    assert args.group_cmd == "rm"
    assert args.name == "持仓"


def test_group_subcommand_rename():
    args = _parser().parse_args(["group", "rename", "A", "B"])
    assert args.group_cmd == "rename"
    assert args.old == "A"
    assert args.new == "B"


def test_group_subcommand_list():
    args = _parser().parse_args(["group", "list"])
    assert args.group_cmd == "list"


def test_group_subcommand_add_codes():
    args = _parser().parse_args(["group", "add-codes", "持仓", "600519"])
    assert args.group_cmd == "add-codes"


def test_group_subcommand_rm_codes():
    args = _parser().parse_args(["group", "rm-codes", "持仓", "600519"])
    assert args.group_cmd == "rm-codes"



def test_move_up_middle():
    lst, idx = _reorder_move_up(["a", "b", "c"], 1)
    assert lst == ["b", "a", "c"]
    assert idx == 0


def test_move_up_at_top_noop():
    lst, idx = _reorder_move_up(["a", "b", "c"], 0)
    assert lst == ["a", "b", "c"]
    assert idx == 0


def test_move_down_middle():
    lst, idx = _reorder_move_down(["a", "b", "c"], 1)
    assert lst == ["a", "c", "b"]
    assert idx == 2


def test_move_down_at_bottom_noop():
    lst, idx = _reorder_move_down(["a", "b", "c"], 2)
    assert lst == ["a", "b", "c"]
    assert idx == 2
