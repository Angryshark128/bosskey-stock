"""Tests for config management."""

import os
import tempfile

_PREFIX = "bosskey_test_config"


def _monkey_patch_cfg(tmp):
    """Helper: return (patched_module, original_path)."""
    path = os.path.join(tmp, ".bosskey.toml")
    import bosskey_stock.config as cfg

    orig = cfg.CONFIG_PATH
    cfg.CONFIG_PATH = path
    return cfg, orig


def test_defaults():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            loaded = cfg.load()
            assert "display" in loaded
            assert "watchlist" in loaded
            assert loaded["display"]["refresh_interval"] == 3
            assert "000001" in loaded["watchlist"]["codes"]
        finally:
            cfg.CONFIG_PATH = orig


def test_add_and_list():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.add_codes("888888", "999999")
            codes = cfg.list_codes()
            assert "888888" in codes
            assert "999999" in codes
        finally:
            cfg.CONFIG_PATH = orig


def test_remove():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.add_codes("888888")
            assert "888888" in cfg.list_codes()
            cfg.remove_codes("888888")
            assert "888888" not in cfg.list_codes()
        finally:
            cfg.CONFIG_PATH = orig


def test_add_duplicates():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.add_codes("000001", "000001", "000001")
            assert cfg.list_codes().count("000001") == 1
        finally:
            cfg.CONFIG_PATH = orig


def test_add_preserves_insertion_order():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            # 默认已有 [000001, 600519, 300750]；追加新代码到末尾，已有顺序不变
            cfg.add_codes("000858")
            assert cfg.list_codes() == ["000001", "600519", "300750", "000858"]
            cfg.add_codes("600519", "000001")  # 重复代码不重复追加
            assert cfg.list_codes() == ["000001", "600519", "300750", "000858"]
        finally:
            cfg.CONFIG_PATH = orig


def test_remove_preserves_order():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.remove_codes("600519")
            assert cfg.list_codes() == ["000001", "300750"]
        finally:
            cfg.CONFIG_PATH = orig


def test_reorder_codes():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.reorder_codes(["300750", "000001", "600519"])
            assert cfg.list_codes() == ["300750", "000001", "600519"]
        finally:
            cfg.CONFIG_PATH = orig


def test_reorder_codes_rejects_non_permutation():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            try:
                cfg.reorder_codes(["000001", "600519"])  # 缺一个
                assert False, "应拒绝非排列的 new_order"
            except ValueError:
                pass
            assert cfg.list_codes() == ["000001", "600519", "300750"]  # 未改动
        finally:
            cfg.CONFIG_PATH = orig


def test_remove_nonexistent():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.remove_codes("non_existent")
        finally:
            cfg.CONFIG_PATH = orig


def test_position_add_and_list():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.add_position("600519", 100, 1500.0)
            cfg.add_position("000001", 300, 12.5)
            pos = cfg.list_positions()
            assert pos["600519"] == {"shares": 100, "cost": 1500.0}
            assert pos["000001"] == {"shares": 300, "cost": 12.5}
        finally:
            cfg.CONFIG_PATH = orig


def test_position_add_joins_watchlist():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.add_position("888888", 100, 10.0)
            assert "888888" in cfg.list_codes()
        finally:
            cfg.CONFIG_PATH = orig


def test_position_update():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.add_position("600519", 100, 1500.0)
            cfg.add_position("600519", 200, 1600.0)
            pos = cfg.list_positions()
            assert pos["600519"] == {"shares": 200, "cost": 1600.0}
        finally:
            cfg.CONFIG_PATH = orig


def test_position_remove():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.add_position("600519", 100, 1500.0)
            cfg.remove_position("600519")
            assert cfg.list_positions() == {}
        finally:
            cfg.CONFIG_PATH = orig


def test_position_remove_nonexistent():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.remove_position("non_existent")
        finally:
            cfg.CONFIG_PATH = orig


def test_default_lang_en():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            assert cfg.load()["display"]["lang"] == "en"
            assert cfg.get_lang() == "en"
        finally:
            cfg.CONFIG_PATH = orig


def test_set_lang_zh():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.set_lang("zh")
            assert cfg.get_lang() == "zh"
            assert cfg.load()["display"]["lang"] == "zh"
        finally:
            cfg.CONFIG_PATH = orig


def test_get_lang_unknown_falls_back_en():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.set_lang("fr")
            assert cfg.get_lang() == "en"
        finally:
            cfg.CONFIG_PATH = orig


# ── 分组 ──────────────────────────────────────────────


def test_group_add_and_get():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.group_add("持仓", "600519", "000001")
            cfg.group_add("ETF", "510300")
            groups = cfg.get_groups()
            assert groups == {"持仓": ["600519", "000001"], "ETF": ["510300"]}
        finally:
            cfg.CONFIG_PATH = orig


def test_group_add_joins_watchlist():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.group_add("新票", "888888", "999999")
            assert "888888" in cfg.list_codes()
            assert "999999" in cfg.list_codes()
        finally:
            cfg.CONFIG_PATH = orig


def test_group_add_duplicate_name():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.group_add("持仓", "600519")
            try:
                cfg.group_add("持仓", "000001")
                assert False, "重名分组应被拒绝"
            except cfg.GroupError as e:
                assert e.key == "group_exists"
        finally:
            cfg.CONFIG_PATH = orig


def test_group_add_empty_name():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            try:
                cfg.group_add("   ", "600519")
                assert False, "空分组名应被拒绝"
            except cfg.GroupError as e:
                assert e.key == "group_name_empty"
        finally:
            cfg.CONFIG_PATH = orig


def test_group_remove_keeps_codes():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.group_add("持仓", "600519")
            cfg.group_remove("持仓")
            assert cfg.get_groups() == {}
            assert "600519" in cfg.list_codes()  # 代码保留
        finally:
            cfg.CONFIG_PATH = orig


def test_group_remove_not_found():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            try:
                cfg.group_remove("不存在")
                assert False, "不存在的组应报错"
            except cfg.GroupError as e:
                assert e.key == "group_not_found"
        finally:
            cfg.CONFIG_PATH = orig


def test_group_rename():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.group_add("持仓", "600519", "000001")
            cfg.group_rename("持仓", "自选")
            assert cfg.get_groups() == {"自选": ["600519", "000001"]}
        finally:
            cfg.CONFIG_PATH = orig


def test_group_rename_duplicate_target():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.group_add("A", "600519")
            cfg.group_add("B", "000001")
            try:
                cfg.group_rename("A", "B")
                assert False, "重名目标应被拒绝"
            except cfg.GroupError as e:
                assert e.key == "group_exists"
        finally:
            cfg.CONFIG_PATH = orig


def test_group_rename_missing():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            try:
                cfg.group_rename("不存在", "X")
                assert False
            except cfg.GroupError as e:
                assert e.key == "group_not_found"
        finally:
            cfg.CONFIG_PATH = orig


def test_group_rename_same_name_noop():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.group_add("A", "600519")
            cfg.group_rename("A", "A")  # 同名不报错、不改变
            assert cfg.get_groups() == {"A": ["600519"]}
        finally:
            cfg.CONFIG_PATH = orig


def test_group_add_codes():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.group_add("持仓", "600519")
            cfg.group_add_codes("持仓", "000001", "000001", "888888")  # 去重 + 自动进 watchlist
            assert cfg.get_groups() == {"持仓": ["600519", "000001", "888888"]}
            assert "888888" in cfg.list_codes()
        finally:
            cfg.CONFIG_PATH = orig


def test_group_add_codes_not_found():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            try:
                cfg.group_add_codes("不存在", "600519")
                assert False
            except cfg.GroupError as e:
                assert e.key == "group_not_found"
        finally:
            cfg.CONFIG_PATH = orig


def test_group_remove_codes_keeps_empty_group():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.group_add("持仓", "600519", "000001")
            cfg.group_remove_codes("持仓", "600519", "000001")
            assert cfg.get_groups() == {"持仓": []}  # 空组保留
        finally:
            cfg.CONFIG_PATH = orig


def test_reorder_group():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.group_add("持仓", "600519", "000001", "300750")
            cfg.reorder_group("持仓", ["300750", "600519", "000001"])
            assert cfg.get_groups() == {"持仓": ["300750", "600519", "000001"]}
        finally:
            cfg.CONFIG_PATH = orig


def test_reorder_group_rejects_non_permutation():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.group_add("持仓", "600519", "000001")
            try:
                cfg.reorder_group("持仓", ["600519"])  # 缺一个
                assert False, "应拒绝非排列"
            except ValueError:
                pass
            assert cfg.get_groups() == {"持仓": ["600519", "000001"]}  # 未改动
        finally:
            cfg.CONFIG_PATH = orig


def test_remove_codes_cleans_groups():
    with tempfile.TemporaryDirectory(prefix=_PREFIX) as tmp:
        cfg, orig = _monkey_patch_cfg(tmp)
        try:
            cfg.group_add("A", "600519", "000001")
            cfg.group_add("B", "600519")
            cfg.remove_codes("600519")
            assert cfg.get_groups() == {"A": ["000001"], "B": []}  # 组内同步清除
        finally:
            cfg.CONFIG_PATH = orig
