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
        "q quit · r refresh · t columns · b boss mode · l language · h help",
        "q 退出 · r 刷新 · t 列模式 · b 老板模式 · l 中英 · h 隐藏提示",
    ),
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
    # CLI 命令帮助
    "help_add": ("Add stocks to the watchlist", "添加股票到监控列表"),
    "help_add_codes": ("stock codes, e.g. 000001 600519", "股票代码，如 000001 600519"),
    "help_rm": ("Remove stocks from the watchlist", "从监控列表移除股票"),
    "help_rm_codes": ("stock codes", "股票代码"),
    "help_list": ("Show the current watchlist", "查看当前监控列表"),
    "help_pos": ("Manage positions (shares + cost)", "管理持仓 (股数 + 成本价)"),
    "help_pos_add": ("Interactively add/update positions", "交互式添加/更新持仓"),
    "help_pos_rm": ("Remove a position", "移除持仓"),
    "help_pos_rm_code": ("stock code", "股票代码"),
    "help_pos_list": ("Show all positions", "查看全部持仓"),
    "help_run": ("Start the monitoring UI (default)", "启动盯盘界面 (默认)"),
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
        "t": lambda key, **fmt: _t(_T[key][idx], fmt),
    }


def resolve(code):
    """配置值 → 规范化语言代码；未知值回落 en。"""
    return code if code in _LANGS else "en"
