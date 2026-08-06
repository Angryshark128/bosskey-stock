"""Tests for interactive reorder — 顺序调整纯逻辑。"""

from bosskey_stock.__main__ import _build_parser, _reorder_move_down, _reorder_move_up
from bosskey_stock.i18n import lang


def _parser():
    return _build_parser(lang("en")["t"])


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
