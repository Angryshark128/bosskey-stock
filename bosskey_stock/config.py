"""配置读写 ~/.bosskey.toml"""

import os
from pathlib import Path

import tomlkit

from . import i18n

CONFIG_PATH = os.path.expanduser("~/.bosskey.toml")

DEFAULT = {
    "display": {"refresh_interval": 3, "lang": "en"},
    "watchlist": {"codes": ["000001", "600519", "300750"]},
    "holdings": {},
}


def _ensure():
    """Create default config if not exists."""
    if not os.path.exists(CONFIG_PATH):
        Path(CONFIG_PATH).parent.mkdir(parents=True, exist_ok=True)
        save(DEFAULT)
        return DEFAULT
    return None


def get_lang():
    """返回规范化的语言代码（未知值回落 en）。"""
    cfg = load()
    return i18n.resolve(cfg.get("display", {}).get("lang", "en"))


def set_lang(code):
    """写入语言设置并持久化。"""
    cfg = load()
    cfg.setdefault("display", {})["lang"] = code
    save(cfg)


def load():
    _ensure()
    with open(CONFIG_PATH) as f:
        return tomlkit.load(f)


def save(cfg):
    with open(CONFIG_PATH, "w") as f:
        tomlkit.dump(cfg, f)


def add_codes(*codes):
    cfg = load()
    existing = cfg["watchlist"]["codes"]
    seen = set(existing)
    for c in codes:
        if c not in seen:
            existing.append(c)
            seen.add(c)
    save(cfg)


def remove_codes(*codes):
    cfg = load()
    removed = set(codes)
    cfg["watchlist"]["codes"] = [c for c in cfg["watchlist"]["codes"] if c not in removed]
    save(cfg)


def reorder_codes(new_order):
    """将监控列表重排为 new_order（须为当前代码集合的排列）。"""
    cfg = load()
    current = cfg["watchlist"]["codes"]
    if set(new_order) != set(current) or len(new_order) != len(current):
        raise ValueError("new_order must be a permutation of the current codes")
    cfg["watchlist"]["codes"] = list(new_order)
    save(cfg)


def list_codes():
    return list(load()["watchlist"]["codes"])


def add_position(code, shares, cost):
    """记录/更新持仓，并把代码加入 watchlist，保证它出现在行情表中。"""
    cfg = load()
    pos = cfg.setdefault("holdings", {})
    pos[code] = {"shares": shares, "cost": cost}
    codes = cfg["watchlist"]["codes"]
    if code not in codes:
        cfg["watchlist"]["codes"] = sorted([*codes, code])
    save(cfg)


def remove_position(code):
    """移除持仓；未持仓时静默。"""
    cfg = load()
    pos = cfg.get("holdings")
    if pos is not None and code in pos:
        del pos[code]
        save(cfg)


def list_positions():
    """返回 {code: {"shares": int, "cost": float}} 纯 dict。"""
    cfg = load()
    pos = cfg.get("holdings") or {}
    return {code: dict(v) for code, v in pos.items()}
