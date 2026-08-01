"""CLI 入口：子命令路由"""

import argparse

from . import app, config


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="bosskey",
        description="终端摸鱼盯盘工具 — 按一下 b 键，行情秒变 Docker 编译日志",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser("run", help="启动盯盘界面（默认）")

    p_add = sub.add_parser("add", help="Add stocks to the watchlist")
    p_add.add_argument("codes", nargs="+", metavar="CODE", help="stock codes, e.g. 000001 600519")

    p_rm = sub.add_parser("rm", help="Remove stocks from the watchlist")
    p_rm.add_argument("codes", nargs="+", metavar="CODE", help="stock codes")

    sub.add_parser("list", help="Show the current watchlist")

    p_pos = sub.add_parser("pos", help="Manage positions (shares + cost)")
    ppos = p_pos.add_subparsers(dest="pos_cmd", metavar="SUBCOMMAND", required=True)

    ppos.add_parser("add", help="Interactively add/update positions")

    pr = ppos.add_parser("rm", help="Remove a position")
    pr.add_argument("code", metavar="CODE", help="stock code")

    ppos.add_parser("list", help="Show all positions")

    return parser


def _fmt_money(v):
    """金额输出：去尾零，如 1500.5 / 12.0 → '12'。"""
    return f"{v:.3f}".rstrip("0").rstrip(".")


def _prompt(desc, cast, validate):
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
            print("Invalid input, try again.")
            continue
        if validate(v):
            return v
        print("Invalid input, try again.")


def _interactive_add():
    codes = config.list_codes()
    if not codes:
        print("Watchlist is empty. Use `bosskey add CODE` first.")
        return
    holdings = config.list_positions()

    print("Available stocks (* held):")
    for i, c in enumerate(codes, 1):
        mark = " *" if c in holdings else ""
        print(f"  {i}) {c}{mark}")

    while True:
        try:
            raw = input("Select stocks to add (e.g. 1,3; Enter to cancel): ").strip()
        except EOFError:
            print()
            return
        if not raw:
            print("Cancelled.")
            return
        try:
            idxs = [int(x) for x in raw.replace("，", ",").split(",") if x.strip()]
        except ValueError:
            print("Invalid input, use numbers and commas, e.g. 1,3.")
            continue
        if not idxs or any(i < 1 or i > len(codes) for i in idxs):
            print(f"Please enter a number from 1 to {len(codes)}.")
            continue
        break

    selected = list(dict.fromkeys(codes[i - 1] for i in idxs))  # 去重保序
    for code in selected:
        print(f"\n{code}:")
        shares = _prompt("  Shares: ", int, lambda v: v > 0)
        cost = _prompt("  Cost: ", float, lambda v: v > 0)
        if shares is None or cost is None:
            print("Cancelled.")
            return
        config.add_position(code, shares, cost)
    print(f"\nSaved: {', '.join(selected)}")


def main():
    parser = _build_parser()
    args = parser.parse_args()

    cmd = args.command
    if cmd is None or cmd == "run":
        cfg = config.load()
        app.main_loop(cfg)
        return

    if cmd == "add":
        config.add_codes(*args.codes)
        print(f"Added: {', '.join(args.codes)}")
    elif cmd == "rm":
        config.remove_codes(*args.codes)
        print(f"Removed: {', '.join(args.codes)}")
    elif cmd == "list":
        codes = config.list_codes()
        if codes:
            print("Watchlist:")
            for c in codes:
                print(f"  {c}")
        else:
            print("Watchlist is empty.")
    elif cmd == "pos":
        sub = args.pos_cmd
        if sub == "add":
            _interactive_add()
        elif sub == "rm":
            config.remove_position(args.code)
            print(f"Removed position: {args.code}")
        elif sub == "list":
            positions = config.list_positions()
            if positions:
                print("Positions:")
                for code, h in sorted(positions.items()):
                    print(f"  {code}  {h['shares']:,}sh  cost {_fmt_money(h['cost'])}")
            else:
                print("No positions.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
