"""CLI 入口：子命令路由（含 --lang 语言切换）"""

import argparse

from . import app, config
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

    sub.add_parser("list", help=tr("help_list"))

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
