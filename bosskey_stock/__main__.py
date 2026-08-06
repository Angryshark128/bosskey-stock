"""CLI 入口：子命令路由（含 --lang 语言切换）"""

import argparse
import os
import select
import sys
import termios

from rich.console import Console
from rich.table import Table
from rich.text import Text

from . import app, config, data
from .i18n import LANG_NAMES, lang


def _build_parser(tr):
    parser = argparse.ArgumentParser(
        prog="bosskey",
        description="终端摸鱼盯盘工具 — 按一下 b 键，行情秒变 Docker 编译日志",
    )
    parser.add_argument(
        "--lang",
        choices=sorted(LANG_NAMES),
        help="界面语言，可选 "
        + ", ".join(sorted(LANG_NAMES))
        + "（默认取 ~/.bosskey.toml 的 display.lang，未设置时英文）",
    )
    parser.add_argument(
        "--list-langs",
        action="store_true",
        help="列出支持的语言并退出",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser("run", help=tr("help_run"))

    p_add = sub.add_parser("add", help=tr("help_add"))
    p_add.add_argument("codes", nargs="+", metavar="CODE", help=tr("help_add_codes"))

    p_rm = sub.add_parser("rm", help=tr("help_rm"))
    p_rm.add_argument("codes", nargs="+", metavar="CODE", help=tr("help_rm_codes"))

    p_list = sub.add_parser("list", help=tr("help_list"))
    p_list.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help=tr("help_list_interactive"),
    )

    p_pos = sub.add_parser("pos", help=tr("help_pos"))
    ppos = p_pos.add_subparsers(dest="pos_cmd", metavar="SUBCOMMAND", required=True)

    ppos.add_parser("add", help=tr("help_pos_add"))

    pr = ppos.add_parser("rm", help=tr("help_pos_rm"))
    pr.add_argument("code", metavar="CODE", help=tr("help_pos_rm_code"))

    ppos.add_parser("list", help=tr("help_pos_list"))

    return parser


def _fmt_money(v):
    """金额输出：去尾零，如 1500.5 / 12.0 → '12'。"""
    return f"{v:.3f}".rstrip("0").rstrip(".")


def _prompt(desc, cast, validate, tr):
    """带校验的 input；EOF/Ctrl+D 返回 None。"""
    while True:
        try:
            raw = input(desc)
        except EOFError:
            print()
            return None
        try:
            v = cast(raw)
        except (ValueError, TypeError):
            print(tr("cli_invalid"))
            continue
        if validate(v):
            return v
        print(tr("cli_invalid"))


def _interactive_add(tr):
    codes = config.list_codes()
    if not codes:
        print(tr("cli_pos_empty"))
        return
    holdings = config.list_positions()

    print(tr("cli_available"))
    for i, c in enumerate(codes, 1):
        mark = " *" if c in holdings else ""
        print(f"  {i}) {c}{mark}")

    while True:
        try:
            raw = input(tr("cli_select_prompt")).strip()
        except EOFError:
            print()
            return
        if not raw:
            print(tr("cli_cancelled"))
            return
        try:
            idxs = [int(x) for x in raw.replace("，", ",").split(",") if x.strip()]
        except ValueError:
            print(tr("cli_bad_number"))
            continue
        if not idxs or any(i < 1 or i > len(codes) for i in idxs):
            print(tr("cli_range", n=len(codes)))
            continue
        break

    selected = list(dict.fromkeys(codes[i - 1] for i in idxs))  # 去重保序
    for code in selected:
        print(f"\n{code}:")
        shares = _prompt(tr("cli_shares_prompt"), int, lambda v: v > 0, tr)
        cost = _prompt(tr("cli_cost_prompt"), float, lambda v: v > 0, tr)
        if shares is None or cost is None:
            print(tr("cli_cancelled"))
            return
        config.add_position(code, shares, cost)
    print(f"\n{tr('cli_saved', codes=', '.join(selected))}")


def _print_positions(positions, tr):
    for code, h in sorted(positions.items()):
        unit = tr("cli_share_unit")
        print(f"  {code}  {h['shares']:,}{unit}  cost {_fmt_money(h['cost'])}")


# ── 交互式 reorder/删除 (list -i) ──────────────────────


def _reorder_move_up(lst, idx):
    """把 idx 处元素上移一位；越界返回 False。返回 (新列表, 新索引)。"""
    if idx <= 0:
        return lst, idx
    nl = lst[:]
    nl[idx], nl[idx - 1] = nl[idx - 1], nl[idx]
    return nl, idx - 1


def _reorder_move_down(lst, idx):
    """把 idx 处元素下移一位；越界返回 False。返回 (新列表, 新索引)。"""
    if idx >= len(lst) - 1:
        return lst, idx
    nl = lst[:]
    nl[idx], nl[idx + 1] = nl[idx + 1], nl[idx]
    return nl, idx + 1


def _reorder_read_key(fd):
    """读一个按键：方向键返回 '\x1b[A'/'\\x1b[B'，普通键返回字符。"""
    if not select.select([fd], [], [], 0.1)[0]:
        return None
    b = os.read(fd, 3)
    if b == b"\x1b[A":
        return "UP"
    if b == b"\x1b[B":
        return "DOWN"
    return b[0:1].decode("utf-8", errors="replace")


def _interactive_reorder(tr):
    codes = config.list_codes()
    if not codes:
        print(tr("reorder_empty"))
        return

    names = {}
    stocks = data.fetch(codes)
    if stocks:
        names = {s["code"]: s["name"] for s in stocks}
    for c in codes:
        names.setdefault(c, tr("reorder_no_names"))

    order = list(codes)
    cursor = 0
    grabbed = None  # 当前被抓取行的原始索引，或 None
    deleted = set()  # 标记删除的代码集合

    console = Console()
    fd = sys.stdin.fileno()
    old_tty = termios.tcgetattr(fd)
    try:
        _setup_reorder_tty(fd)
        with console.screen() as screen:
            while True:
                _render_reorder(screen, order, names, cursor, grabbed, deleted, tr)

                key = _reorder_read_key(fd)
                if key is None:
                    continue
                if key == "q" or key == "\x03":  # q / Ctrl+C
                    console.print(tr("reorder_cancelled"))
                    return
                if key == "s":  # 保存：先按完整 order 排序，再删除标记项
                    config.reorder_codes(order)
                    if deleted:
                        config.remove_codes(*deleted)
                    console.print(tr("reorder_saved"))
                    return
                if key == "d":  # 标记/取消标记删除
                    code = order[cursor]
                    if code in deleted:
                        deleted.discard(code)
                    else:
                        deleted.add(code)
                    continue
                if key == " ":  # 抓取/放下
                    if grabbed is None:
                        grabbed = cursor
                    else:
                        grabbed = None
                    continue
                if key == "UP" or key == "k":
                    if grabbed is not None:
                        order, grabbed = _reorder_move_up(order, grabbed)
                        cursor = grabbed
                    else:
                        cursor = max(0, cursor - 1)
                elif key == "DOWN" or key == "j":
                    if grabbed is not None:
                        order, grabbed = _reorder_move_down(order, grabbed)
                        cursor = grabbed
                    else:
                        cursor = min(len(order) - 1, cursor + 1)
    except KeyboardInterrupt:
        console.print()
        console.print(tr("reorder_cancelled"))
    finally:
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_tty)
        except (ValueError, termios.error, OSError):
            pass


def _setup_reorder_tty(fd):
    """逐键输入，关 ECHO/ICANON/ICRNL，保留输出侧 OPOST。"""
    attrs = termios.tcgetattr(fd)
    attrs[0] &= ~(termios.BRKINT | termios.ICRNL | termios.INPCK | termios.ISTRIP | termios.IXON)
    attrs[3] &= ~(termios.ECHO | termios.ICANON | termios.ISIG | termios.IEXTEN)
    attrs[6][termios.VMIN] = 1
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSAFLUSH, attrs)


def _render_reorder(screen, order, names, cursor, grabbed, deleted, tr):
    table = Table(box=None, show_header=True, show_edge=False, padding=(0, 1))
    table.add_column("#", justify="right")
    table.add_column(tr("col_code"))
    table.add_column(tr("col_name"))

    for i, code in enumerate(order):
        if code in deleted:
            style = "red strike"
        elif i == cursor:
            style = "reverse" if grabbed == i else "bold cyan"
        elif i == grabbed:
            style = "bold yellow"
        else:
            style = ""
        table.add_row(
            Text(str(i + 1), style=style),
            Text(code, style=style),
            Text(names.get(code, ""), style=style),
        )

    title = tr("reorder_title")
    if grabbed is not None:
        title += f"  {tr('reorder_grabbed')} {order[grabbed]}"
    if deleted:
        title += f"  {tr('reorder_deleted')} {len(deleted)}"
    screen.update(GroupTitle(title, table))


class GroupTitle:
    def __init__(self, title, table):
        self._title = title
        self._table = table

    def __rich_console__(self, console, options):
        from rich.console import Group

        yield from console.render(
            Group(Text(self._title, style="bold"), self._table), options
        )


def main():
    parser = _build_parser(tr=lang(config.get_lang())["t"])
    args = parser.parse_args()

    if args.list_langs:
        for code in sorted(LANG_NAMES):
            print(f"{code}: {LANG_NAMES[code]}")
        return

    lang_code = args.lang if args.lang else config.get_lang()
    tr = lang(lang_code)["t"]

    cmd = args.command
    if cmd is None or cmd == "run":
        cfg = config.load()
        app.main_loop(cfg, lang_code=lang_code)
        return

    if cmd == "add":
        config.add_codes(*args.codes)
        print(tr("cli_added", codes=", ".join(args.codes)))
    elif cmd == "rm":
        config.remove_codes(*args.codes)
        print(tr("cli_removed", codes=", ".join(args.codes)))
    elif cmd == "list":
        if args.interactive:
            _interactive_reorder(tr)
        else:
            codes = config.list_codes()
            if codes:
                print(tr("cli_watchlist"))
                for c in codes:
                    print(f"  {c}")
            else:
                print(tr("cli_watchlist_empty"))
    elif cmd == "pos":
        sub = args.pos_cmd
        if sub == "add":
            _interactive_add(tr)
        elif sub == "rm":
            config.remove_position(args.code)
            print(tr("cli_pos_rm_ok", code=args.code))
        elif sub == "list":
            positions = config.list_positions()
            if positions:
                print(tr("cli_positions"))
                _print_positions(positions, tr)
            else:
                print(tr("cli_no_positions"))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
