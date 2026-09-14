"""Tests for CLI 帮助文本：一律中文、不随 --lang 切换。

帮助是给人读的用法说明，不参与「英文伪装」（伪装只针对 TUI 界面与运行期输出）。
"""

import pytest

from bosskey_stock import __main__ as cli


def _help(argv, capsys):
    """跑一次 --help，返回输出（argparse 打印后以 SystemExit(0) 退出）。"""
    with pytest.raises(SystemExit) as e:
        cli._build_parser().parse_args(argv)
    assert e.value.code == 0
    return capsys.readouterr().out


def test_help_is_chinese(capsys):
    """argparse 自带的框架词也要中文化（usage / positional arguments / options / -h 说明）。"""
    out = _help(["--help"], capsys)
    assert "用法：" in out
    assert "参数:" in out and "选项:" in out
    assert "显示帮助并退出" in out
    assert "usage:" not in out
    assert "positional arguments" not in out
    assert "options:" not in out
    assert "show this help message" not in out


def test_help_lists_subcommands_in_chinese(capsys):
    out = _help(["--help"], capsys)
    for text in ("启动盯盘界面", "添加股票/基金到监控列表", "查看当前监控列表", "管理持仓"):
        assert text in out


def test_add_help_documents_resolution(capsys):
    """add 的用法说明：三种命中情形 + 前缀示例（本次改动的重点）。"""
    out = _help(["add", "--help"], capsys)
    assert "命中一个" in out and "命中多个" in out and "零命中" in out
    assert "不打断" in out
    assert "fu:110022" in out and "sh:000001" in out
    assert "bosskey add 510300 508000 113550" in out


@pytest.mark.parametrize(
    "argv",
    [
        ["rm", "--help"],
        ["list", "--help"],
        ["group", "--help"],
        ["group", "add", "--help"],
        ["group", "rm-codes", "--help"],
        ["pos", "--help"],
        ["pos", "rm", "--help"],
    ],
)
def test_subcommand_help_all_chinese(argv, capsys):
    out = _help(argv, capsys)
    assert "用法：" in out
    assert "显示帮助并退出" in out
    assert "usage:" not in out and "positional arguments" not in out


@pytest.mark.parametrize("lang_args", [["--lang", "en"], ["--lang", "zh"], ["--lang=zh"]])
def test_help_ignores_lang_flag(lang_args, capsys):
    """--lang 只影响运行期输出，不影响帮助：两种语言下帮助都是中文。"""
    out = _help([*lang_args, "--help"], capsys)
    assert "用法：" in out
    assert "usage:" not in out
