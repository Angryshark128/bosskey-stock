"""Tests for config management."""

import os
import tempfile

from bosskey_stock import config

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
