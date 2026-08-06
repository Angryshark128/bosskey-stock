"""主循环：Rich Live + 非阻塞键盘输入

策略：只在输入侧设 raw 参数（去掉 ICANON/ECHO），保留输出侧的 OPOST
（\n → \r\n 转换），全程只需一次 tcsetattr，无需后台线程。
"""

import os
import select
import sys
import termios
from datetime import datetime

from rich.box import HORIZONTALS
from rich.console import Group
from rich.live import Live
from rich.table import Table
from rich.text import Text

from .boss import BossGenerator
from .data import fetch
from .i18n import lang

# ── 交易时段 ────────────────────────────────────────────

_MORNING = (9 * 60 + 30, 11 * 60 + 30)
_AFTERNOON = (13 * 60, 15 * 60)


def _in_session() -> bool:
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    m = now.hour * 60 + now.minute
    return (_MORNING[0] <= m <= _MORNING[1]) or (_AFTERNOON[0] <= m <= _AFTERNOON[1])


# ── 成交量格式化 ────────────────────────────────────────


def _fmt_vol(shares):
    if shares is None:
        return "--"
    lots = shares / 100
    if lots >= 10_000_0000:
        return f"{lots / 10_000_0000:.2f}亿"
    if lots >= 10_000:
        return f"{lots / 10_000:.2f}万"
    return f"{lots:.0f}"


# ── 持仓收益计算与列渲染 ──────────────────────────────

# 模式 0 基础列；change_pct 列按语言取表头（Chg% / 涨跌幅）
_BASE_COLS = ("Code", "Name", "Price", "Chg%", "Chg", "Vol", "Open", "High", "Low")
_DISPLAY_MODES = 4  # 0=基础, 1=+持仓/成本, 2=+持仓收益, 3=+今日收益


def _pos_metrics(s, holdings):
    """行情 + 持仓 → 持仓/今日收益指标；无持仓或缺数据返回 None。"""
    h = holdings.get(s["code"])
    if not h:
        return None
    shares = h.get("shares")
    cost = h.get("cost")
    price = s["price"]
    if not shares or not cost or price is None:
        return None
    return {
        "shares": shares,
        "cost": cost,
        "hold_pl": (price - cost) * shares,
        "hold_pct": (price - cost) / cost * 100,
        "today_pl": s["change"] * shares if s["change"] is not None else None,
        "today_pct": s["change_pct"],
    }


def _pl_style(v, colorize=True):
    """收益列着色：正红负绿，零/空无色；单色模式关闭时无色。"""
    if v is None or v == 0 or not colorize:
        return None
    return "red3" if v > 0 else "green3"


def _fmt_price(v):
    """价格/成本：最多 3 位小数，去尾零。None → '--'"""
    if v is None:
        return "--"
    return f"{v:.3f}".rstrip("0").rstrip(".")


# ── 终端：单键输入（保留输出侧 OPOST） ──────────────────


def _setup_tty(fd):
    """设置终端为逐键输入模式，不破坏 \n → \r\n 输出转换。"""
    attrs = termios.tcgetattr(fd)
    # IFLAG：关掉 BRKINT / ICRNL / INPCK / ISTRIP / IXON
    #   ICRNL 最关键 —— 否则回车会被转成 \n，干扰 select
    attrs[0] &= ~(termios.BRKINT | termios.ICRNL | termios.INPCK | termios.ISTRIP | termios.IXON)
    # OFLAG：保留（OPOST = 1），确保写入 \n 时终端自动补 \r
    # LFLAG：关掉 ECHO / ICANON / ISIG / IEXTEN
    #   ICANON 是关键 —— 关掉后输入不再等换行
    attrs[3] &= ~(termios.ECHO | termios.ICANON | termios.ISIG | termios.IEXTEN)
    # VMIN=1，VTIME=0 —— read 至少返回 1 字节
    attrs[6][termios.VMIN] = 1
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSAFLUSH, attrs)


_MAX_WAIT = 0.5  # select 最大等待秒数


def _read_key(fd):
    """非阻塞读一个按键。返回字符或 None。"""
    r, _, _ = select.select([fd], [], [], _MAX_WAIT)
    if r:
        return os.read(fd, 1).decode("utf-8", errors="replace")
    return None


# ── UI 构建 ─────────────────────────────────────────────


_COL_KEYS = {
    "Code": "col_code",
    "Name": "col_name",
    "Price": "col_price",
    "Chg%": "col_chg_pct",
    "Chg": "col_chg",
    "Vol": "col_vol",
    "Open": "col_open",
    "High": "col_high",
    "Low": "col_low",
    "Pos": "col_pos",
    "Cost": "col_cost",
    "HoldP/L": "col_hold_pl",
    "HoldP/L%": "col_hold_pct",
    "TodayP/L": "col_today_pl",
}


def _is_etf(code):
    """沪 5 开头 / 深 15、16 开头视为 ETF/LOF。"""
    return code.startswith("5") or code.startswith(("15", "16"))


def _build_table(stocks, holdings, mode, tr, colorize=True):
    table = Table(
        box=HORIZONTALS,
        show_header=True,
        header_style="",
        show_edge=False,
        show_lines=True,
        padding=(0, 1),
    )
    cols = list(_BASE_COLS)
    if mode >= 1:
        cols += ["Pos", "Cost"]
    if mode >= 2:
        cols += ["HoldP/L", "HoldP/L%"]
    if mode >= 3:
        cols += ["TodayP/L"]
    for col in cols:
        table.add_column(tr(_COL_KEYS[col]))

    for s in stocks:
        price = s["price"]
        chg = s["change"]
        pct = s["change_pct"]
        up = price is not None and chg is not None and chg >= 0
        style = ("red3" if up else "green3") if colorize else None
        dp = 3 if _is_etf(s["code"]) else 2

        row = [
            Text(s["code"], style=style),
            Text(s["name"], style=style),
            Text(f"{price:.{dp}f}" if price is not None else "--", style=style),
            Text(f"{pct:+.2f}%" if pct is not None else "--", style=style),
            Text(f"{chg:+.{dp}f}" if chg is not None else "--", style=style),
            Text(_fmt_vol(s["vol"]), style=style),
            Text(f"{s['open']:.{dp}f}" if s["open"] is not None else "--", style=style),
            Text(f"{s['high']:.{dp}f}" if s["high"] is not None else "--", style=style),
            Text(f"{s['low']:.{dp}f}" if s["low"] is not None else "--", style=style),
        ]

        m = _pos_metrics(s, holdings)
        if mode >= 1:
            if m:
                row.append(Text(f"{int(m['shares']):,}"))
                row.append(Text(_fmt_price(m["cost"])))
            else:
                row.append(Text("--"))
                row.append(Text("--"))
        if mode >= 2:
            if m:
                row.append(Text(f"{m['hold_pl']:+,.2f}", style=_pl_style(m["hold_pl"], colorize)))
                row.append(Text(f"{m['hold_pct']:+.2f}%", style=_pl_style(m["hold_pct"], colorize)))
            else:
                row.append(Text("--"))
                row.append(Text("--"))
        if mode >= 3:
            if m:
                row.append(Text(f"{m['today_pl']:+,.2f}", style=_pl_style(m["today_pl"], colorize)))
            else:
                row.append(Text("--"))

        table.add_row(*row)

    return table


def _build_status(stocks, after_hours, offline, update_time, mode, tr):
    text = Text()
    if offline:
        text.append(tr("offline"), style="yellow bold")
    if after_hours:
        text.append(tr("after_hours"), style="bright_black")
        if stocks and stocks[0].get("trade_time") and stocks[0].get("date"):
            text.append(f" {tr('last_trade')} {stocks[0]['date']} {stocks[0]['trade_time']}")
        else:
            text.append(f" {tr('last_trade')} --")
    else:
        text.append(f"{tr('last_update')} {update_time}")

    if mode:
        labels = []
        if mode >= 1:
            labels.append(tr("col_group_pos_cost"))
        if mode >= 2:
            labels.append(tr("col_group_hold_pl"))
        if mode >= 3:
            labels.append(tr("col_group_today_pl"))
        text.append("  " + tr("cols") + " " + " · ".join(labels), style="bright_black")
    return text


def _build_summary(stocks, holdings, mode, tr, colorize=True):
    """底部汇总：总市值/总成本、总收益（率）、今日收益（率）。仅 mode>0 时调用。"""
    cost_val = 0.0
    pos_val = 0.0
    prev_val = 0.0
    today_pl = 0.0
    for s in stocks:
        m = _pos_metrics(s, holdings)
        if not m:
            continue
        cost_val += m["cost"] * m["shares"]
        pos_val += s["price"] * m["shares"]
        if m["today_pl"] is not None:
            today_pl += m["today_pl"]
        if s["pre_close"]:
            prev_val += s["pre_close"] * m["shares"]

    if not cost_val:
        return Text("")

    text = Text()
    if mode >= 1:
        text.append(tr("summary_value_cost", v=f"{pos_val:,.2f}", c=f"{cost_val:,.2f}"))
    if mode >= 2:
        hold_pl = pos_val - cost_val
        hold_pct = hold_pl / cost_val * 100
        text.append("  ·  ")
        text.append(tr("summary_hold_pl"))
        text.append(" ")
        text.append(f"{hold_pl:+,.2f} ({hold_pct:+.2f}%)", style=_pl_style(hold_pl, colorize))
    if mode >= 3:
        denom = prev_val or cost_val
        today_pct = today_pl / denom * 100 if denom else None
        text.append("  ·  ")
        text.append(tr("summary_today_pl"))
        text.append(" ")
        text.append(
            f"{today_pl:+,.2f}" + (f" ({today_pct:+.2f}%)" if today_pct is not None else ""),
            style=_pl_style(today_pl, colorize),
        )
    return text


def _build_help(tr):
    """快捷键提示行：q/r/t/l/b/h。灰色低调，不打断表格。"""
    return Text(tr("help_hint"), style="bright_black")


def _build_view(stocks, holdings, mode, after, offline, ts, tr, show_help=False, colorize=True):
    parts = [
        _build_table(stocks, holdings, mode, tr, colorize=colorize),
        _build_status(stocks, after, offline, ts, mode, tr),
    ]
    if mode:
        parts.append(_build_summary(stocks, holdings, mode, tr, colorize=colorize))
    if show_help:
        parts.append(_build_help(tr))
    return Group(*parts)


# ── 主循环 ──────────────────────────────────────────────


def main_loop(cfg, lang_code=None):
    codes = cfg["watchlist"]["codes"]
    holdings = dict(cfg.get("holdings") or {})
    interval = cfg["display"]["refresh_interval"]

    boss = BossGenerator()
    boss_mode = False
    mode = 0  # 显示模式：0=基础，1..3 渐进展开持仓/收益列
    show_help = False  # h 键：底部快捷键提示
    colorize = True  # c 键：彩色/单色切换
    lang_state = lang(lang_code if lang_code is not None else cfg["display"].get("lang", "en"))
    tr = lang_state["t"]

    # 先拉数据，再进备屏（避免用户看到 Loading… 后卡住）
    stocks_cache = fetch(codes)
    offline = stocks_cache is None
    if stocks_cache is None:
        stocks_cache = []
    last_refresh = datetime.now().timestamp()

    fd = sys.stdin.fileno()
    old_tty = termios.tcgetattr(fd)
    try:
        _setup_tty(fd)

        with Live(auto_refresh=False, screen=True) as live:
            # 进入备屏后立即渲染已有数据
            ts = datetime.now().strftime("%H:%M:%S")
            live.update(
                _build_view(
                    stocks_cache, holdings, mode, not _in_session(), offline, ts, tr, show_help,
                    colorize,
                ),
                refresh=True,
            )

            while True:
                # ── 键盘 ──
                key = _read_key(fd)
                if key == "q" or key == "\x03":  # q / Ctrl+C
                    break
                if key == "b":
                    boss_mode = not boss_mode
                    if boss_mode:
                        boss.reset()
                if key == "t":
                    mode = (mode + 1) % _DISPLAY_MODES
                if key == "l":  # 中英切换（会话内，不持久化）
                    lang_state = lang("zh" if lang_state["code"] == "en" else "en")
                    tr = lang_state["t"]
                if key == "h":  # 快捷键提示开关
                    show_help = not show_help
                if key == "c":  # 彩色/单色切换
                    colorize = not colorize
                force = key == "r"

                # ── boss 模式（跳过行情渲染） ──
                if boss_mode:
                    live.update(boss.render(tr), refresh=True)
                    continue

                # ── 行情 ──
                now = datetime.now()
                ts = now.strftime("%H:%M:%S")
                after = not _in_session()
                elapsed = now.timestamp() - last_refresh

                if force or (not after and elapsed >= interval):
                    result = fetch(codes)
                    if result is None:
                        offline = True
                    else:
                        offline = False
                        stocks_cache = result
                    last_refresh = now.timestamp()

                live.update(
                    _build_view(
                        stocks_cache, holdings, mode, after, offline, ts, tr, show_help, colorize
                    ),
                    refresh=True,
                )
    except KeyboardInterrupt:
        pass
    finally:
        # 恢复终端
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_tty)
        except (ValueError, termios.error, OSError):
            pass
