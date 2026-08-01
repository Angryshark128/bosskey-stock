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
