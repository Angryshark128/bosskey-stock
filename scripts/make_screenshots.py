"""重新生成 docs/ 下的截图资源。

- screenshot-normal.svg   : 正常模式（mode 3，含持仓/成本/收益列 + 底部汇总）
- screenshot-boss.svg     : 老板模式（Docker build 伪日志）
- screenshot-demo.gif     : 演示动画（按 t 循环 4 种显示模式 → 按 b 切老板模式）

用法:
    python scripts/make_screenshots.py [--gif-only] [--width N]

依赖:
    rich（项目运行时依赖）；macOS qlmanage（SVG→PNG 栅格化，合成 GIF 时需要）。

SVG 由 Rich 的 export_svg 直接生成；PNG/GIF 仅用于 demo 动画。
"""

import argparse
import io
import subprocess
import tempfile
from pathlib import Path

from PIL import Image
from rich.console import Console

from bosskey_stock import app
from bosskey_stock.boss import BossGenerator

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

WIDTH = 132
GIF_WIDTH = 900


def _stocks():
    def mk(code, name, open_, pre, price, high, low, vol, change, pct):
        return {
            "code": code,
            "name": name,
            "open": open_,
            "pre_close": pre,
            "price": price,
            "high": high,
            "low": low,
            "vol": vol,
            "amount": None,
            "date": "2026-08-01",
            "trade_time": "14:32:05",
            "change": change,
            "change_pct": pct,
        }

    return [
        mk("600519", "贵州茅台", 1680.0, 1675.0, 1690.0, 1700.0, 1670.0, 5_000_000, 15.0, 0.90),
        mk("000001", "平安银行", 12.50, 12.40, 12.30, 12.70, 12.20, 9_000_000, -0.10, -0.81),
        mk("300750", "宁德时代", 200.0, 200.0, 200.0, 201.0, 199.0, 3_000_000, 0.0, 0.0),
        mk("601318", "中国平安", 46.0, 45.9, 45.6, 46.2, 45.3, 2_000_000, -0.30, -0.65),
        mk("000858", "五粮液", 143.1, 143.1, 145.2, 146.0, 142.8, 1_500_000, 2.10, 1.47),
    ]


HOLDINGS = {
    "600519": {"shares": 100, "cost": 1600.0},
    "000001": {"shares": 300, "cost": 12.34},
    "601318": {"shares": 200, "cost": 44.0},
}


def _export_svg(view, path, title, width):
    console = Console(
        force_terminal=True, color_system="truecolor", width=width, record=True, file=io.StringIO()
    )
    console.print(view)
    console.save_svg(str(path), title=title)
    # 校验：mode 3 全列应无截断（无 "…"）
    text = console.export_text()
    assert "…" not in text, f"width {width} too small, columns truncated: {path}"
    print(f"  SVG -> {path.name}  (ok, no truncation)")


def _boss_view():
    bg = BossGenerator()
    bg.reset()
    return bg.render()


def _render_gif_frames():
    """返回 (views, durations_ms, titles) 列表。"""
    stocks = _stocks()
    frames = [
        (app._build_view(stocks, HOLDINGS, 0, False, False, "14:32:05"), 900, "bosskey: basic"),
        (app._build_view(stocks, HOLDINGS, 1, False, False, "14:32:05"), 900, "press t: +Pos/Cost"),
        (app._build_view(stocks, HOLDINGS, 2, False, False, "14:32:05"), 900, "press t: +HoldP/L"),
        (
            app._build_view(stocks, HOLDINGS, 3, False, False, "14:32:05"),
            1000,
            "press t: +TodayP/L",
        ),
        (app._build_view(stocks, HOLDINGS, 3, False, False, "14:32:05"), 1500, "hold"),
        (_boss_view(), 2000, "press b: boss mode"),
        (_boss_view(), 700, "boss mode"),
    ]
    return frames


def _crop_to_content(im):
    """裁剪掉 qlmanage 的不透明白边，保留终端内容（暗色背景）。"""
    gray = im.convert("L")
    mask = gray.point(lambda p: 255 if p < 245 else 0)
    bbox = mask.getbbox()
    return im.crop(bbox) if bbox else im


def _svg_to_png(svg_path, out_png, size):
    """macOS qlmanage 栅格化 SVG → PNG，返回 PNG 路径。"""
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(
            ["qlmanage", "-t", "-s", str(size), "-o", d, str(svg_path)],
            check=True,
            capture_output=True,
        )
        produced = Path(d) / (svg_path.name + ".png")
        produced.replace(out_png)
    return out_png


def _make_gif(width):
    print("render GIF frames as SVG ...")
    frames = _render_gif_frames()
    svgs = []
    durations = []
    with tempfile.TemporaryDirectory() as d:
        for i, (view, dur, _title) in enumerate(frames):
            p = Path(d) / f"frame-{i}.svg"
            _export_svg(view, p, _title, width)
            svgs.append(p)
            durations.append(dur)

        print("rasterize SVG -> PNG via qlmanage ...")
        pngs = []
        for i, svg in enumerate(svgs):
            png = Path(d) / f"frame-{i}.png"
            _svg_to_png(svg, png, 2000)
            pngs.append(png)
            print(f"  PNG frame-{i}: {png.stat().st_size} bytes")

        print("assemble GIF ...")
        imgs = [Image.open(p).convert("RGBA") for p in pngs]
        # qlmanage 给 SVG 垫了不透明白底 → 按「非白像素」裁剪到终端内容包围盒
        imgs = [_crop_to_content(im) for im in imgs]
        max_w = max(im.width for im in imgs)
        max_h = max(im.height for im in imgs)
        scale = GIF_WIDTH / max_w
        frames_img = []
        for im in imgs:
            im = im.resize(
                (int(im.width * scale), int(im.height * scale)), Image.Resampling.LANCZOS
            )
            canvas = Image.new("RGBA", (GIF_WIDTH, int(max_h * scale)), (0, 0, 0, 0))
            canvas.paste(im, (0, 0))
            frames_img.append(canvas)
        gif = DOCS / "screenshot-demo.gif"
        frames_img[0].save(
            gif,
            save_all=True,
            append_images=frames_img[1:],
            duration=durations,
            loop=0,
            optimize=True,
        )
        print(
            f"  GIF -> {gif} ({gif.stat().st_size} bytes, {len(frames_img)} frames, "
            f"{GIF_WIDTH}x{int(max_h * scale)})"
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gif-only", action="store_true", help="只重新生成 demo GIF")
    ap.add_argument("--width", type=int, default=WIDTH)
    args = ap.parse_args()
    width = args.width

    stocks = _stocks()
    if not args.gif_only:
        print("normal mode SVG (mode 3) ...")
        _export_svg(
            app._build_view(stocks, HOLDINGS, 3, False, False, "14:32:05"),
            DOCS / "screenshot-normal.svg",
            "bosskey: 行情 + 持仓收益",
            width,
        )
        print("boss mode SVG ...")
        _export_svg(_boss_view(), DOCS / "screenshot-boss.svg", "bosskey: boss mode", width)

    _make_gif(width)


if __name__ == "__main__":
    main()
