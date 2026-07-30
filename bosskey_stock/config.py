"""配置读写 ~/.bosskey.toml"""

import os
from pathlib import Path

import tomlkit

CONFIG_PATH = os.path.expanduser("~/.bosskey.toml")

DEFAULT = {
    "display": {"refresh_interval": 3},
    "watchlist": {"codes": ["000001", "600519", "300750"]},
}


def _ensure():
    """Create default config if not exists."""
    if not os.path.exists(CONFIG_PATH):
        Path(CONFIG_PATH).parent.mkdir(parents=True, exist_ok=True)
        save(DEFAULT)
        return DEFAULT
    return None


def load():
    _ensure()
    with open(CONFIG_PATH) as f:
        return tomlkit.load(f)


def save(cfg):
    with open(CONFIG_PATH, "w") as f:
        tomlkit.dump(cfg, f)


def add_codes(*codes):
    cfg = load()
    existing = set(cfg["watchlist"]["codes"])
    for c in codes:
        existing.add(c)
    cfg["watchlist"]["codes"] = sorted(existing)
    save(cfg)


def remove_codes(*codes):
    cfg = load()
    existing = set(cfg["watchlist"]["codes"])
    for c in codes:
        existing.discard(c)
    cfg["watchlist"]["codes"] = sorted(existing)
    save(cfg)


def list_codes():
    return list(load()["watchlist"]["codes"])
