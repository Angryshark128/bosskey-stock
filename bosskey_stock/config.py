"""配置读写 ~/.bosskey.toml"""

import os
from pathlib import Path

import tomlkit

from . import i18n

CONFIG_PATH = os.path.expanduser("~/.bosskey.toml")

DEFAULT = {
    "display": {"refresh_interval": 3, "lang": "en"},
    "watchlist": {"codes": ["000001", "600519", "300750"], "groups": {}},
    "holdings": {},
}


class GroupError(ValueError):
    """分组操作错误：key 为 i18n 文案键，fmt 为格式化参数。"""

    def __init__(self, key, **fmt):
        self.key = key
        self.fmt = fmt
        super().__init__(key)


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
    groups = cfg.get("watchlist", {}).get("groups")
    if groups:
        for name in groups:
            groups[name] = [c for c in groups[name] if c not in removed]
    save(cfg)


def reorder_codes(new_order):
    """将监控列表重排为 new_order（须为当前代码集合的排列）。"""
    cfg = load()
    current = cfg["watchlist"]["codes"]
    if set(new_order) != set(current) or len(new_order) != len(current):
        raise ValueError("new_order must be a permutation of the current codes")
    cfg["watchlist"]["codes"] = list(new_order)
    save(cfg)


def _dedup(codes):
    return list(dict.fromkeys(codes))


def _extend_watchlist(cfg, codes):
    """代码不在 watchlist 则按序追加到尾部。"""
    lst = cfg["watchlist"]["codes"]
    seen = set(lst)
    for c in codes:
        if c not in seen:
            lst.append(c)
            seen.add(c)


# ── 分组 ──────────────────────────────────────────────


def get_groups():
    """返回 {name: [codes]} 保序副本；无分组时 {}。"""
    cfg = load()
    groups = cfg.get("watchlist", {}).get("groups") or {}
    return {name: list(codes) for name, codes in groups.items()}


def _groups_table(cfg):
    return cfg.setdefault("watchlist", {}).setdefault("groups", {})


def _check_group_name(groups, name):
    """校验分组名：非空、不与现有组重名；返回 strip 后的名字。"""
    name = (name or "").strip()
    if not name:
        raise GroupError("group_name_empty")
    if name in groups:
        raise GroupError("group_exists", name=name)
    return name


def group_add(name, *codes):
    """新建分组并归入代码（重名报错）；代码自动进 watchlist。"""
    cfg = load()
    groups = _groups_table(cfg)
    name = _check_group_name(groups, name)
    unique = _dedup(codes)
    groups[name] = list(unique)
    _extend_watchlist(cfg, unique)
    save(cfg)


def group_remove(name):
    """删除分组；组不存在报错。代码保留在 watchlist。"""
    cfg = load()
    groups = _groups_table(cfg)
    if name not in groups:
        raise GroupError("group_not_found", name=name)
    del groups[name]
    save(cfg)


def group_rename(old, new):
    """重命名分组；目标重名报错。组位置移到末尾。"""
    cfg = load()
    groups = _groups_table(cfg)
    if old not in groups:
        raise GroupError("group_not_found", name=old)
    new = (new or "").strip()
    if new == old:
        return
    if not new:
        raise GroupError("group_name_empty")
    if new in groups:
        raise GroupError("group_exists", name=new)
    groups[new] = list(groups[old])
    del groups[old]
    save(cfg)


def group_add_codes(name, *codes):
    """往分组追加代码（组不存在报错）；代码自动进 watchlist，组内去重。"""
    cfg = load()
    groups = _groups_table(cfg)
    if name not in groups:
        raise GroupError("group_not_found", name=name)
    arr = groups[name]
    seen = set(arr)
    for c in _dedup(codes):
        if c not in seen:
            arr.append(c)
            seen.add(c)
    _extend_watchlist(cfg, codes)
    save(cfg)


def group_remove_codes(name, *codes):
    """从分组移除代码（组不存在报错）；组保留（可为空）。"""
    cfg = load()
    groups = _groups_table(cfg)
    if name not in groups:
        raise GroupError("group_not_found", name=name)
    removed = set(codes)
    groups[name] = [c for c in groups[name] if c not in removed]
    save(cfg)


def reorder_group(name, new_order):
    """组内重排（须为该组代码集合的排列）。"""
    cfg = load()
    groups = _groups_table(cfg)
    if name not in groups:
        raise GroupError("group_not_found", name=name)
    current = groups[name]
    if set(new_order) != set(current) or len(new_order) != len(current):
        raise ValueError("new_order must be a permutation of the group codes")
    groups[name] = list(new_order)
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
