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


class _ZhHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """帮助文本中文化：argparse 自带的 `usage: ` 前缀硬编码在 `add_usage()` 里，只能覆写。

    继承 RawDescriptionHelpFormatter 是为了保留多行 epilog（add 的用法说明）。
    """

    def add_usage(self, usage, actions, groups, prefix=None):
        super().add_usage(usage, actions, groups, "用法：" if prefix is None else prefix)


def _zh(parser):
    """把 argparse 的两个小标题换成中文（`positional arguments` / `options`）。

    argparse 没给公开 API，只能设这两个私有属性（社区通行做法）。
    """
    parser._positionals.title = "参数"
    parser._optionals.title = "选项"
    return parser


def _sub(sub, name, **kw):
    """建一个子命令 parser：中文帮助框架 + 中文 -h。"""
    p = sub.add_parser(name, formatter_class=_ZhHelpFormatter, add_help=False, **kw)
    p.add_argument("-h", "--help", action="help", help="显示帮助并退出")
    return _zh(p)


_HELP_ADD_EPILOG = """\
代码自动在 sh/sz/bj 三个交易所中匹配：
  命中一个  -> 直接使用
  零命中    -> 提示查无行情，不添加
  命中多个  -> 直接用段位规则那条，不打断（如 000001 -> 000001 平安银行），
             并把另一条候选连同其强制前缀打印出来。

前缀：sh: / sz: / bj: 强制指定交易所，fu: = 场外基金。
  bosskey add 600519 000858            股票
  bosskey add 510300 508000 113550     ETF / REITs / 可转债
  bosskey add fu:110022                场外基金（净值型，4 位小数）
  bosskey add sh:000001                强制取上证指数"""


def _build_parser():
    """构建 CLI 解析器。帮助文本一律中文，不随 --lang 切换。

    帮助是给人读的用法说明，不参与「英文伪装」（伪装只针对 TUI 界面与运行期输出），
    没必要让人为了看说明先猜语言；`--lang` 只影响运行期输出的语言。
    """
    parser = argparse.ArgumentParser(
        prog="bosskey",
        description="终端摸鱼盯盘工具 — 按一下 b 键，行情秒变 Docker 编译日志",
        formatter_class=_ZhHelpFormatter,
        add_help=False,
    )
    _zh(parser)
    parser.add_argument("-h", "--help", action="help", help="显示帮助并退出")
    parser.add_argument(
        "--lang",
        choices=sorted(LANG_NAMES),
        help="运行期输出语言，可选 "
        + ", ".join(sorted(LANG_NAMES))
        + "（默认取 ~/.bosskey.toml 的 display.lang，未设置时英文；不影响帮助）",
    )
    parser.add_argument(
        "--list-langs",
        action="store_true",
        help="列出支持的语言并退出",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    _sub(sub, "run", help="启动盯盘界面（默认）")

    p_add = _sub(
        sub,
        "add",
        help="添加股票/基金到监控列表",
        epilog=_HELP_ADD_EPILOG,
    )
    p_add.add_argument(
        "codes",
        nargs="+",
        metavar="CODE",
        help="代码，如 000001 600519；sh:000001 强制指定交易所；fu:110022 = 场外基金",
    )
    p_add.add_argument("--group", metavar="NAME", help="归入该分组（不存在则自动创建）")

    p_rm = _sub(sub, "rm", help="从监控列表移除代码")
    p_rm.add_argument(
        "codes",
        nargs="+",
        metavar="CODE",
        help="代码（或 sh:000001 / fu:110022 形式的键）",
    )

    p_list = _sub(sub, "list", help="查看当前监控列表")
    p_list.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="交互式调整监控列表顺序并删除",
    )
    p_list.add_argument("--group", metavar="NAME", help="只显示该分组")

    p_group = _sub(sub, "group", help="管理监控列表分组")
    pg = p_group.add_subparsers(dest="group_cmd", metavar="SUBCOMMAND", required=True)

    pg_add = _sub(pg, "add", help="创建分组并归入代码")
    pg_add.add_argument("name", metavar="NAME", help="分组名")
    pg_add.add_argument("codes", nargs="*", metavar="CODE", help="代码（可选）")

    pg_rm = _sub(pg, "rm", help="删除分组（代码保留）")
    pg_rm.add_argument("name", metavar="NAME", help="分组名")

    pg_ren = _sub(pg, "rename", help="重命名分组")
    pg_ren.add_argument("old", metavar="OLD", help="分组名")
    pg_ren.add_argument("new", metavar="NEW", help="分组名")

    _sub(pg, "list", help="查看全部分组")

    pg_ac = _sub(pg, "add-codes", help="向分组添加代码")
    pg_ac.add_argument("name", metavar="NAME", help="分组名")
    pg_ac.add_argument(
        "codes",
        nargs="+",
        metavar="CODE",
        help="代码，如 000001 600519；sh:000001 强制指定交易所；fu:110022 = 场外基金",
    )

    pg_rc = _sub(pg, "rm-codes", help="从分组移除代码")
    pg_rc.add_argument("name", metavar="NAME", help="分组名")
    pg_rc.add_argument(
        "codes",
        nargs="+",
        metavar="CODE",
        help="代码，如 000001 600519；sh:000001 强制指定交易所；fu:110022 = 场外基金",
    )

    p_pos = _sub(sub, "pos", help="管理持仓（股数 + 成本价）")
    ppos = p_pos.add_subparsers(dest="pos_cmd", metavar="SUBCOMMAND", required=True)

    _sub(ppos, "add", help="交互式添加/更新持仓")

    pr = _sub(ppos, "rm", help="移除持仓")
    pr.add_argument("code", metavar="CODE", help="代码（或 sh:000001 / fu:110022 形式的键）")

    _sub(ppos, "list", help="查看全部持仓")

    return parser


def _fmt_money(v, dp=3):
    """金额输出：最多 dp 位小数，去尾零，如 1500.5 / 12.0 → '12'。

    场外基金传入 4，避免成本净值 2.8377 被截成 2.838。
    """
    return f"{v:.{dp}f}".rstrip("0").rstrip(".")


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
        shares = _prompt(tr("cli_shares_prompt"), float, lambda v: v > 0, tr)
        cost = _prompt(tr("cli_cost_prompt"), float, lambda v: v > 0, tr)
        if shares is None or cost is None:
            print(tr("cli_cancelled"))
            return
        config.add_position(code, shares, cost)
    print(f"\n{tr('cli_saved', codes=', '.join(selected))}")


def _print_positions(positions, tr):
    for code, h in sorted(positions.items()):
        unit = tr("cli_share_unit")
        shares = app._fmt_shares(h["shares"])
        print(f"  {code}  {shares}{unit}  cost {_fmt_money(h['cost'], app._cost_decimals(code))}")


# ── 代码消歧：同名代码 / 无行情 ─────────────────────────


def _match_stored(code, keys=None):
    """keys（缺省为监控列表）里与 code 同代码的已存键；显式前缀时要求完全相同。"""
    prefix, digits = data.split_key(code)
    keys = config.list_codes() if keys is None else keys
    if prefix:
        return [k for k in keys if k == code]
    return [k for k in keys if data.split_key(k)[1] == digits]


def _pick_by_rule(code, cands, tr):
    """同名代码多命中：不打断输入，直接取段位规则那条，另一条打成一行提示。

    如 `000001` 沪为上证指数、深为平安银行，取规则那条（深，平安银行）并打印
    「000001 = 平安银行（另有 上证指数 → sh:000001）」，想加指数写前缀即可。
    """
    rule = data.default_prefix(code)
    picked = next(((p, n) for p, n in cands if p == rule), cands[0])
    others = " / ".join(
        f"{name} → {data.make_key(p, code)}" for p, name in cands if p != picked[0]
    )
    print(tr("cli_multi_default", code=code, name=picked[1], others=others))
    return data.make_key(picked[0], code)


def _resolve_add(code, tr):
    """输入 -> 存储键；代码非法或查无行情返回 None。

    探测 sh/sz/bj 三个交易所：命中一个直接用；命中多个（同名代码，如 000001 既是
    上证指数又是平安银行）取段位规则那条，不打断输入，只把另一条候选打成一行提示；
    探测失败（离线）回退段位规则，保持离线可用。
    """
    prefix, digits = data.split_key(code)
    if len(digits) != 6 or not digits.isdigit():
        print(tr("cli_bad_code", code=code))
        return None
    if prefix:  # 已显式指定交易所，不再看其它交易所
        cands = data.probe(digits, prefix=prefix)
        if cands is None or cands:
            return data.make_key(prefix, digits)
        key = data.make_key(prefix, digits)
        # 场外货币基金接口返回空串，与「代码查无行情」区分提示
        print(tr("cli_no_quote_fu", code=key) if prefix == "fu" else tr("cli_no_quote", code=key))
        return None
    cands = data.probe(digits)
    if cands is None:
        return digits  # 离线：按段位规则加入
    if not cands:
        print(tr("cli_no_quote", code=digits))
        return None
    if len(cands) == 1:
        return data.make_key(cands[0][0], digits)
    return _pick_by_rule(digits, cands, tr)


def _choose_remove(code, matches, tr):
    """多条命中：列出存储键 + 名称，让用户选一条或全部；EOF 取消。"""
    names = {s["code"]: s["name"] for s in (data.fetch(matches) or [])}
    print(tr("cli_multi_match", code=code, n=len(matches)))
    for i, k in enumerate(matches, 1):
        name = names.get(k)
        print(f"  {i}) {k}" + (f"  {name}" if name else ""))
    while True:
        try:
            raw = input(tr("cli_choose_rm", n=len(matches))).strip().lower()
        except EOFError:
            print()
            print(tr("cli_cancelled"))
            return []
        if raw in ("a", "all"):
            return matches
        if raw.isdigit() and 1 <= int(raw) <= len(matches):
            return [matches[int(raw) - 1]]
        print(tr("cli_range", n=len(matches)))


def _run_group_cmd(args, tr):
    sub = args.group_cmd
    try:
        if sub == "add":
            keys = [k for k in (_resolve_add(c, tr) for c in args.codes) if k]
            config.group_add(args.name, *keys)
            print(tr("group_added", name=args.name, codes=", ".join(keys) or "-"))
        elif sub == "rm":
            config.group_remove(args.name)
            print(tr("group_removed", name=args.name))
        elif sub == "rename":
            config.group_rename(args.old, args.new)
            print(tr("group_renamed", old=args.old, new=args.new))
        elif sub == "add-codes":
            keys = [k for k in (_resolve_add(c, tr) for c in args.codes) if k]
            if keys:
                config.group_add_codes(args.name, *keys)
                print(tr("group_codes_added", name=args.name, codes=", ".join(keys)))
        elif sub == "rm-codes":
            in_group = config.get_groups().get(args.name)
            if in_group is None:
                config.group_remove_codes(args.name, *args.codes)  # 触发 group_not_found
            else:
                keys = []
                for c in args.codes:
                    matches = [k for k in _match_stored(c) if k in in_group]
                    if not matches:
                        print(tr("cli_not_in_list", code=c))
                    elif len(matches) == 1:
                        keys.append(matches[0])
                    else:
                        keys.extend(_choose_remove(c, matches, tr))
                if keys:
                    config.group_remove_codes(args.name, *keys)
                    print(tr("group_codes_removed", name=args.name, codes=", ".join(keys)))
        elif sub == "list":
            groups = config.get_groups()
            if not groups:
                print(tr("group_empty"))
            else:
                print(tr("cli_groups"))
                for name, codes in groups.items():
                    line = f"  {name}"
                    if codes:
                        line += f": {' '.join(codes)}"
                    print(line)
    except config.GroupError as e:
        print(tr(e.key, **e.fmt))


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


def _interactive_reorder(tr, group=None):
    if group is None:
        codes = config.list_codes()
    else:
        groups = config.get_groups()
        if group not in groups:
            print(tr("group_not_found", name=group))
            return
        codes = groups[group]
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
                _render_reorder(screen, order, names, cursor, grabbed, deleted, tr, group)

                key = _reorder_read_key(fd)
                if key is None:
                    continue
                if key == "q" or key == "\x03":  # q / Ctrl+C
                    console.print(tr("reorder_cancelled"))
                    return
                if key == "s":  # 保存：先按完整 order 排序，再删除标记项
                    if group is None:
                        config.reorder_codes(order)
                    else:
                        config.reorder_group(group, order)
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


def _render_reorder(screen, order, names, cursor, grabbed, deleted, tr, group=None):
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
    if group:
        title += f"  [{group}]"
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
    parser = _build_parser()
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
        keys = list(dict.fromkeys(k for k in (_resolve_add(c, tr) for c in args.codes) if k))
        if keys:
            existing = set(config.list_codes())
            config.add_codes(*keys)
            if args.group:
                if args.group in config.get_groups():
                    config.group_add_codes(args.group, *keys)
                else:
                    config.group_add(args.group, *keys)
            added = [k for k in keys if k not in existing]
            if added:
                print(tr("cli_added", codes=", ".join(added)))
            for k in keys:
                if k in existing:
                    print(tr("cli_already", code=k))
    elif cmd == "rm":
        removed = []
        for c in args.codes:
            matches = _match_stored(c)
            if not matches:
                print(tr("cli_not_in_list", code=c))
                continue
            chosen = matches if len(matches) == 1 else _choose_remove(c, matches, tr)
            if chosen:
                config.remove_codes(*chosen)
                removed.extend(chosen)
        if removed:
            print(tr("cli_removed", codes=", ".join(removed)))
    elif cmd == "list":
        if args.interactive:
            _interactive_reorder(tr, group=args.group)
        else:
            if args.group:
                groups = config.get_groups()
                if args.group not in groups:
                    print(tr("group_not_found", name=args.group))
                    return
                codes = groups[args.group]
                title = tr("cli_group_watchlist", name=args.group)
            else:
                codes = config.list_codes()
                title = tr("cli_watchlist")
            if codes:
                print(title)
                for c in codes:
                    print(f"  {c}")
            else:
                print(tr("cli_watchlist_empty"))
    elif cmd == "group":
        _run_group_cmd(args, tr)
    elif cmd == "pos":
        sub = args.pos_cmd
        if sub == "add":
            _interactive_add(tr)
        elif sub == "rm":
            matches = _match_stored(args.code, list(config.list_positions()))
            if not matches:
                print(tr("cli_no_position", code=args.code))
            else:
                chosen = matches if len(matches) == 1 else _choose_remove(args.code, matches, tr)
                for k in chosen:
                    config.remove_position(k)
                    print(tr("cli_pos_rm_ok", code=k))
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
