"""스프라이트 타일 좌표 인스펙터.

overworld.png를 4배 확대해 띄우고 격자/좌표 라벨을 오버레이.
마우스를 올리면 해당 (col, row)가 화면 하단에 표시되고, 클릭하면 콘솔에 출력.

실행:
    python tools/tile_inspector.py
"""
from __future__ import annotations
import os
import sys
import pygame

# 프로젝트 루트를 경로에 추가 (tools/ 에서 실행해도 import 가능하도록)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SHEET_PATH = "assets/sprites/overworld.png"
SOURCE_TILE_PX = 16
SCALE = 4
LABEL_EVERY = 1   # 1 = 모든 타일에 라벨, 5 = 5칸마다 라벨

GRID_COLOR = (255, 255, 255, 80)
LABEL_COLOR = (255, 255, 0)
HOVER_COLOR = (255, 50, 50)
INFO_BG = (0, 0, 0, 200)


def main() -> None:
    pygame.init()
    sheet = pygame.image.load(SHEET_PATH)
    src_w, src_h = sheet.get_size()
    out_tile = SOURCE_TILE_PX * SCALE
    cols = src_w // SOURCE_TILE_PX
    rows = src_h // SOURCE_TILE_PX

    sheet_w = cols * out_tile
    sheet_h = rows * out_tile
    info_h = 40
    screen = pygame.display.set_mode((sheet_w, sheet_h + info_h))
    pygame.display.set_caption("Tile Inspector — overworld.png")

    sheet = sheet.convert_alpha()
    scaled = pygame.transform.scale(sheet, (sheet_w, sheet_h))

    font = pygame.font.SysFont("monospace", 9)
    info_font = pygame.font.SysFont("monospace", 16, bold=True)

    # 격자 + 라벨을 한 번 미리 렌더해 두는 오버레이
    overlay = pygame.Surface((sheet_w, sheet_h), pygame.SRCALPHA)
    for c in range(cols + 1):
        x = c * out_tile
        pygame.draw.line(overlay, GRID_COLOR, (x, 0), (x, sheet_h))
    for r in range(rows + 1):
        y = r * out_tile
        pygame.draw.line(overlay, GRID_COLOR, (0, y), (sheet_w, y))
    for r in range(rows):
        for c in range(cols):
            if c % LABEL_EVERY == 0 and r % LABEL_EVERY == 0:
                label = font.render(f"{c},{r}", True, LABEL_COLOR)
                overlay.blit(label, (c * out_tile + 2, r * out_tile + 1))

    clock = pygame.time.Clock()
    running = True
    hover: tuple[int, int] | None = None

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                if my < sheet_h:
                    hover = (mx // out_tile, my // out_tile)
                else:
                    hover = None
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if hover is not None:
                    print(f"clicked: col={hover[0]}, row={hover[1]}")

        screen.fill((20, 20, 24))
        screen.blit(scaled, (0, 0))
        screen.blit(overlay, (0, 0))

        if hover is not None:
            c, r = hover
            rect = pygame.Rect(c * out_tile, r * out_tile, out_tile, out_tile)
            pygame.draw.rect(screen, HOVER_COLOR, rect, 3)

        # 하단 정보 패널
        pygame.draw.rect(screen, (0, 0, 0), (0, sheet_h, sheet_w, info_h))
        if hover is not None:
            c, r = hover
            text = f"hover  col={c:>2}  row={r:>2}   px=({c*SOURCE_TILE_PX:>3},{r*SOURCE_TILE_PX:>3})"
        else:
            text = "Move mouse over a tile. Click to print coords. Esc to quit."
        screen.blit(info_font.render(text, True, (230, 230, 230)), (12, sheet_h + 10))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
