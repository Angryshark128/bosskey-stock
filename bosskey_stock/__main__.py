"""CLI 入口：子命令路由"""

import argparse
import sys

from . import app, config


def main():
    parser = argparse.ArgumentParser(
        prog="bosskey",
        description="终端摸鱼盯盘工具 — 按一下 b 键，行情秒变 Docker 编译日志",
    )
    parser.add_argument("command", nargs="?", default="run",
                        choices=["run", "add", "rm", "list"])
    parser.add_argument("codes", nargs="*", metavar="CODE",
                        help="股票代码，例如 000001 600519")

    args = parser.parse_args()

    if args.command == "run":
        cfg = config.load()
        app.main_loop(cfg)
    elif args.command == "add":
        if not args.codes:
            print("用法: bosskey add CODE [CODE ...]")
            sys.exit(1)
        config.add_codes(*args.codes)
        print(f"已添加: {', '.join(args.codes)}")
    elif args.command == "rm":
        if not args.codes:
            print("用法: bosskey rm CODE [CODE ...]")
            sys.exit(1)
        config.remove_codes(*args.codes)
        print(f"已移除: {', '.join(args.codes)}")
    elif args.command == "list":
        codes = config.list_codes()
        if codes:
            print("监控列表:")
            for c in codes:
                print(f"  {c}")
        else:
            print("监控列表为空。")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
