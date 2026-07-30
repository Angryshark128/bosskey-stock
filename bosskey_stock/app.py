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


def _build_table(stocks):
    table = Table(
        box=HORIZONTALS,
        show_header=True,
        header_style="",
        show_edge=False,
        show_lines=True,
        padding=(0, 1),
    )
    for col in ("Code", "Name", "Price", "Chg%", "Chg", "Vol", "Open", "High", "Low"):
        table.add_column(col)

    for s in stocks:
        price = s["price"]
        chg = s["change"]
        pct = s["change_pct"]
        up = price is not None and chg is not None and chg >= 0
        style = "red3" if up else "green3"

        table.add_row(
            Text(s["code"], style=style),
            Text(s["name"], style=style),
            Text(f"{price:.2f}" if price is not None else "--", style=style),
            Text(f"{pct:+.2f}%" if pct is not None else "--", style=style),
            Text(f"{chg:+.2f}" if chg is not None else "--", style=style),
            Text(_fmt_vol(s["vol"]), style=style),
            Text(f"{s['open']:.2f}" if s["open"] is not None else "--", style=style),
            Text(f"{s['high']:.2f}" if s["high"] is not None else "--", style=style),
            Text(f"{s['low']:.2f}" if s["low"] is not None else "--", style=style),
        )

    return table


def _build_status(stocks, after_hours, offline, update_time):
    text = Text()
    if offline:
        text.append("[Offline]  ", style="yellow bold")
    if after_hours:
        text.append("[After Hours]  ", style="bright_black")
        if stocks and stocks[0].get("trade_time") and stocks[0].get("date"):
            text.append(f"Last trade: {stocks[0]['date']} {stocks[0]['trade_time']}")
        else:
            text.append("Last trade: --")
    else:
        text.append(f"Last update: {update_time}")
    return text


# ── 主循环 ──────────────────────────────────────────────


def main_loop(cfg):
    codes = cfg["watchlist"]["codes"]
    interval = cfg["display"]["refresh_interval"]

    boss = BossGenerator()
    boss_mode = False

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
                Group(
                    _build_table(stocks_cache),
                    _build_status(stocks_cache, not _in_session(), offline, ts),
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
                force = key == "r"

                # ── boss 模式（跳过行情渲染） ──
                if boss_mode:
                    live.update(boss.render(), refresh=True)
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
                    Group(
                        _build_table(stocks_cache),
                        _build_status(stocks_cache, after, offline, ts),
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
