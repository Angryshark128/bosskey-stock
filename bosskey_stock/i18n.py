"""多语言文案：中英双语切换（默认英文，维持伪装）。

所有用户可见文案（表头/状态栏/底部汇总/CLI 输出/老板模式）统一走本模块，
`lang()` 返回 {code, t} 按当前语言取文案。
"""

# 语言显示名（用于 --list-langs / l 键切换时的状态提示）
LANG_NAMES = {"en": "English", "zh": "中文"}

# 文案表：key -> (en, zh)
_T = {
    # 表头
    "col_code": ("Code", "代码"),
    "col_name": ("Name", "名称"),
    "col_price": ("Price", "现价"),
    "col_chg_pct": ("Chg%", "涨跌幅"),
    "col_chg": ("Chg", "涨跌额"),
    "col_vol": ("Vol", "成交量"),
    "col_open": ("Open", "今开"),
    "col_high": ("High", "最高"),
    "col_low": ("Low", "最低"),
    "col_pos": ("Pos", "持仓"),
    "col_cost": ("Cost", "成本"),
    "col_hold_pl": ("HoldP/L", "持仓盈亏"),
    "col_hold_pct": ("HoldP/L%", "持仓收益率"),
    "col_today_pl": ("TodayP/L", "今日盈亏"),
    # 状态栏
    "offline": ("[Offline]", "[离线]"),
    "after_hours": ("[After Hours]", "[休市]"),
    "last_trade": ("Last trade:", "最近成交:"),
    "last_update": ("Last update:", "最近刷新:"),
    "cols": ("Cols:", "列:"),
    "col_group_pos_cost": ("Pos/Cost", "持仓/成本"),
    "col_group_hold_pl": ("HoldP/L", "持仓盈亏"),
    "col_group_today_pl": ("TodayP/L", "今日盈亏"),
    # 底部汇总
    "summary_value_cost": ("Value {v} · Cost {c}", "市值 {v} · 成本 {c}"),
    "summary_hold_pl": ("HoldP/L", "持仓盈亏"),
    "summary_today_pl": ("TodayP/L", "今日盈亏"),
    # 老板模式（仅底部状态行本地化；日志主体是英文 Docker 命令，见 boss.py）
    "boss_running": ("Running time: {elapsed}", "运行时间: {elapsed}"),
    # 快捷键提示
    "help_hint": (
        "q quit · r refresh · t columns · c color · b boss mode · l language · g group · h help",
        "q 退出 · r 刷新 · t 列模式 · c 单色 · b 老板模式 · l 中英 · g 分组 · h 隐藏提示",
    ),
    # 分组（状态栏 / CLI）
    "group_status": ("Group: {name}", "分组: {name}"),
    "view_all": ("All", "全部"),
    "cli_groups": ("Groups:", "分组:"),
    "group_empty": ("No groups.", "暂无分组。"),
    "group_added": ("Group created: {name} [{codes}]", "已创建分组: {name} [{codes}]"),
    "group_removed": ("Group removed: {name}", "已删除分组: {name}"),
    "group_renamed": ("Renamed: {old} → {new}", "已重命名: {old} → {new}"),
    "group_codes_added": ("Added to {name}: {codes}", "已加入 {name}: {codes}"),
    "group_codes_removed": ("Removed from {name}: {codes}", "已从 {name} 移除: {codes}"),
    "group_exists": ("Group already exists: {name}", "分组已存在: {name}"),
    "group_not_found": ("Group not found: {name}", "分组不存在: {name}"),
    "group_name_empty": ("Group name must not be empty.", "分组名不能为空。"),
    "cli_group_watchlist": ("Group [{name}]:", "分组 [{name}]:"),
    # CLI
    "cli_added": ("Added: {codes}", "已添加: {codes}"),
    "cli_removed": ("Removed: {codes}", "已移除: {codes}"),
    "cli_watchlist": ("Watchlist:", "监控列表:"),
    "cli_watchlist_empty": ("Watchlist is empty.", "监控列表为空。"),
    "cli_positions": ("Positions:", "持仓:"),
    "cli_no_positions": ("No positions.", "暂无持仓。"),
    "cli_pos_rm_ok": ("Removed position: {code}", "已移除持仓: {code}"),
    "cli_pos_empty": (
        "Watchlist is empty. Use `bosskey add CODE` first.",
        "监控列表为空, 请先 `bosskey add CODE` 添加股票。",
    ),
    "cli_available": ("Available stocks (* held):", "可选股票 (* 已持仓):"),
    "cli_select_prompt": (
        "Select stocks to add (e.g. 1,3; Enter to cancel): ",
        "选择要添加的股票 (如 1,3; 回车取消): ",
    ),
    "cli_cancelled": ("Cancelled.", "已取消。"),
    "cli_bad_number": (
        "Invalid input, use numbers and commas, e.g. 1,3.",
        "输入无效, 请用数字和逗号, 如 1,3。",
    ),
    "cli_range": (
        "Please enter a number from 1 to {n}.",
        "请输入 1 到 {n} 之间的编号。",
    ),
    "cli_shares_prompt": ("  Shares: ", "  股数: "),
    "cli_cost_prompt": ("  Cost: ", "  成本价: "),
    "cli_invalid": ("Invalid input, try again.", "输入无效, 请重试。"),
    "cli_saved": ("Saved: {codes}", "已保存: {codes}"),
    "cli_share_unit": ("sh", "股"),
    # CLI 同名代码消歧 / 入参校验
    "cli_bad_code": ("Not a 6-digit code: {code}", "不是 6 位代码: {code}"),
    "cli_no_quote": ("No quote for {code}, not added.", "{code} 查无行情，未添加。"),
    "cli_no_quote_fu": (
        "No NAV for {code}, not added — no such fund, or a money market fund (not supported).",
        "{code} 查不到净值，未添加 —— 代码不存在，或为不支持的场外货币基金。",
    ),
    "cli_multi_default": (
        "{code} = {name} (also {others})",
        "{code} = {name}（另有 {others}）",
    ),
    "cli_multi_match": ("{n} entries match {code}:", "匹配 {code} 的有 {n} 条："),
    "cli_no_position": ("No position: {code}", "未持有: {code}"),
    "cli_choose_rm": ("Select [1-{n}, a = all]: ", "请选择 [1-{n}，a = 全部]: "),
    "cli_not_in_list": ("Not in watchlist: {code}", "不在监控列表中: {code}"),
    "cli_already": ("Already in watchlist: {code}", "已在监控列表中: {code}"),
    # Reorder TUI
    "reorder_loading": ("Fetching names...", "正在获取名称..."),
    "reorder_title": (
        "Reorder/delete (↑/↓ or k/j move · Space pick/drop · d mark delete · s save · q cancel)",
        "调整顺序/删除 (↑/↓ 或 k/j 移动 · 空格 拿起/放下 · d 标记删除 · s 保存 · q 取消)",
    ),
    "reorder_empty": (
        "Watchlist is empty. Use `bosskey add CODE` first.",
        "监控列表为空, 请先 `bosskey add CODE` 添加股票。",
    ),
    "reorder_no_names": ("(name unavailable offline)", "(离线, 无名称)"),
    "reorder_saved": ("Saved order.", "已保存顺序。"),
    "reorder_cancelled": ("Cancelled.", "已取消。"),
    "reorder_grabbed": ("Picked up:", "已拿起:"),
    "reorder_deleted": ("marked for delete:", "标记删除:"),
}


_LANGS = ("en", "zh")


def _t(entry, fmt):
    s = entry
    return s.format(**fmt) if fmt else s


def lang(lang_code="en"):
    """返回当前语言的文案取词函数 t(key, **fmt)。"""
    idx = _LANGS.index(resolve(lang_code))
    return {
        "code": _LANGS[idx],
        # 形参命名为 _key：文案占位符允许叫 {key}（tr("x", key=...)）而不与形参冲突
        "t": lambda _key, **fmt: _t(_T[_key][idx], fmt),
    }


def resolve(code):
    """配置值 → 规范化语言代码；未知值回落 en。"""
    return code if code in _LANGS else "en"
