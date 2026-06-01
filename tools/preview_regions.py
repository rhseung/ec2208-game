"""스프라이트시트의 특정 영역을 Pillow로 잘라 좌표 라벨을 입혀 저장.

사용자가 알려준 영역:
  - 잔디 바닥:        (0, 0) ~ (1, 1)
  - 바다(물):         (0, 2) ~ (8, 6)
  - 오토타일 경계:     (4, 18) ~ (8, 22)

각 영역을 8배 확대하고 격자 + (col,row) 라벨을 그려 tools/_preview/에 PNG로 저장.
실행:
    python tools/preview_regions.py
"""
from __future__ import annotations
import os
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEET_PATH = os.path.join(ROOT, "assets/sprites/overworld.png")
OUT_DIR = os.path.join(ROOT, "tools/_preview")

TILE_PX = 16
SCALE = 8

# (이름, 좌상단 col,row, 우하단 col,row) — 끝점 포함(inclusive)
REGIONS: list[tuple[str, int, int, int, int]] = [
    ("01_grass",     0, 0, 1,  1),   # 잔디 바닥
    ("02_sea",       0, 2, 8,  6),   # 바다
    ("03_autotile",  4, 18, 8, 22),  # 오토타일 경계
]


def load_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, 14)
            except OSError:
                continue
    return ImageFont.load_default()


def crop_with_labels(
    sheet: Image.Image,
    name: str,
    c0: int, r0: int, c1: int, r1: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> str:
    """주어진 영역을 잘라 8배 확대하고 격자/라벨을 그려 저장. 출력 경로 반환."""
    cols = c1 - c0 + 1
    rows = r1 - r0 + 1
    src_w, src_h = cols * TILE_PX, rows * TILE_PX

    cropped = sheet.crop((
        c0 * TILE_PX, r0 * TILE_PX,
        (c1 + 1) * TILE_PX, (r1 + 1) * TILE_PX,
    ))
    out_w, out_h = src_w * SCALE, rows * TILE_PX * SCALE
    scaled = cropped.resize((out_w, out_h), Image.Resampling.NEAREST)

    canvas = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))
    canvas.paste(scaled, (0, 0))

    draw = ImageDraw.Draw(canvas)
    cell = TILE_PX * SCALE

    # 격자
    for c in range(cols + 1):
        x = c * cell
        draw.line([(x, 0), (x, out_h)], fill=(255, 255, 255, 160), width=1)
    for r in range(rows + 1):
        y = r * cell
        draw.line([(0, y), (out_w, y)], fill=(255, 255, 255, 160), width=1)

    # (col, row) 라벨 — 시트 절대 좌표 기준
    for r in range(rows):
        for c in range(cols):
            label = f"{c0 + c},{r0 + r}"
            tx = c * cell + 4
            ty = r * cell + 2
            # 가독성을 위해 배경 박스
            bbox = draw.textbbox((tx, ty), label, font=font)
            draw.rectangle(bbox, fill=(0, 0, 0, 180))
            draw.text((tx, ty), label, fill=(255, 230, 80), font=font)

    out_path = os.path.join(OUT_DIR, f"{name}.png")
    canvas.save(out_path)
    return out_path


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    sheet = Image.open(SHEET_PATH).convert("RGBA")
    print(f"sheet size: {sheet.size}  (cols={sheet.width // TILE_PX}, rows={sheet.height // TILE_PX})")

    font = load_font()
    for name, c0, r0, c1, r1 in REGIONS:
        out = crop_with_labels(sheet, name, c0, r0, c1, r1, font)
        cols = c1 - c0 + 1
        rows = r1 - r0 + 1
        print(f"  saved: {os.path.relpath(out, ROOT)}  ({cols}x{rows} tiles, region ({c0},{r0})-({c1},{r1}))")


if __name__ == "__main__":
    sys.exit(main())
