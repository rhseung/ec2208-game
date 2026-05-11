"""타일맵 렌더링: corner-decomposition 오토타일링 + 스프라이트 좌표.

좌표 체계
----------
스프라이트시트는 overworld.png. 모든 좌표는 16x16 타일 단위 (col, row).

오토타일링: corner-decomposition (RPG Maker A1/A2 스타일)
---------------------------------------------------------
2x2 의 "잔디 섬" 코너 블록 4개 타일을 8x8 단위로 4등분해서, 셀 한 칸을
4개의 8x8 sub-chunk 으로 합성한다. 16가지 카디널 경계 케이스를 모두 커버.

원본 2x2 블록 (top-left 타일이 GRASS_CORNER_BASE):

    (bc, br)        (bc+1, br)            ← 위 행
    T_NW (NW각)     T_NE (NE각)
    (bc, br+1)      (bc+1, br+1)          ← 아래 행
    T_SW (SW각)     T_SE (SE각)

각 source 타일 안의 8x8 sub-chunk 4개:

    sub(0,0)=NW   sub(1,0)=NE
    sub(0,1)=SW   sub(1,1)=SE

규칙: 셀의 사분면 Q를 그릴 때, 그 사분면이 닿는 두 카디널 이웃이
물(WALL)인지 여부에 따라 source 타일을 고른다. sub-chunk는 항상 Q와 같은 위치.

  - 둘 다 물            → 같은 위치의 source     (NW Q + N&W water  → T_NW)
  - 수직만 물(N or S)    → 수평으로 뒤집은 source (NW Q + N water    → T_NE)
  - 수평만 물(W or E)    → 수직으로 뒤집은 source (NW Q + W water    → T_SW)
  - 둘 다 잔디           → 대각으로 뒤집은 source (NW Q + neither    → T_SE)

이 한 가지 규칙으로 4 사분면 × 4 케이스 = 16 케이스를 모두 처리.
inner-corner(대각만 물) 케이스는 본 규칙에서 무시되며 interior 로 폴백.
"""
from __future__ import annotations
from typing import Iterator
from components.map import DungeonMap, Tile

# =============================================================================
# 스프라이트 좌표 — TWEAK ME
# =============================================================================

# 잔디 2x2 코너 블록의 좌상단 (T_NW 의 위치)
# notebooks/_out/grass_edge_variants.png 를 시트 어디서 잘라냈는지의 좌상단 좌표.
GRASS_CORNER_BASE: tuple[int, int] = (2, 9)   # 2x2 잔디 섬 코너 블록 좌상단

# 깊은 물 (WALL) — 6종 변형을 (x, y) 해시로 결정적으로 분산
WATER_VARIANTS: tuple[tuple[int, int], ...] = (
    (3, 3), (4, 3), (5, 3),
    (3, 4), (4, 4), (5, 4),
)

# 자갈길(통로) — 일단 잔디 오토타일과 동일하게 처리.
# 추후: 별도 코너 블록을 두거나, 잔디 위에 path 오버레이로 구분.
PATH_PLAIN: tuple[int, int] = (0, 0)          # TWEAK ME (지금은 미사용)

# 계단 / 문 — 임시로 잔디 평면
STAIRS_UP_TILE:   tuple[int, int] = (0, 0)    # TWEAK ME
STAIRS_DOWN_TILE: tuple[int, int] = (0, 0)    # TWEAK ME
DOOR_TILE:        tuple[int, int] = (0, 0)    # TWEAK ME


# =============================================================================
# 헬퍼
# =============================================================================

def _is_water(dungeon: DungeonMap, x: int, y: int) -> bool:
    """맵 밖은 물로 간주. WALL = 물."""
    if 0 <= x < dungeon.width and 0 <= y < dungeon.height:
        return dungeon.grid[y][x] == Tile.WALL
    return True


# 셀 사분면 정의: (cell_qx, cell_qy, v_role, h_role)
# v_role: 0=북쪽 사분면(N과 닿음), 1=남쪽 사분면(S과 닿음)
# h_role: 0=서쪽 사분면(W과 닿음), 1=동쪽 사분면(E와 닿음)
_QUADRANTS: tuple[tuple[int, int, int, int], ...] = (
    (0, 0, 0, 0),   # NW
    (1, 0, 0, 1),   # NE
    (0, 1, 1, 0),   # SW
    (1, 1, 1, 1),   # SE
)


def grass_subtiles(
    dungeon: DungeonMap, x: int, y: int,
) -> Iterator[tuple[int, int, int, int, int, int]]:
    """잔디 셀 (x, y) 를 그릴 4개의 sub-chunk 정보를 생성.

    각 항목: (cell_qx, cell_qy, src_col, src_row, sub_col, sub_row)
      - cell_qx, cell_qy: 셀 안에서의 사분면 위치(0/1)
      - src_col, src_row: 가져올 source 타일 좌표
      - sub_col, sub_row: source 타일 안에서의 8x8 sub-chunk 위치(0/1)
    """
    bc, br = GRASS_CORNER_BASE

    # 4 카디널 이웃이 물인지
    n_water = _is_water(dungeon, x,     y - 1)
    s_water = _is_water(dungeon, x,     y + 1)
    w_water = _is_water(dungeon, x - 1, y    )
    e_water = _is_water(dungeon, x + 1, y    )

    for cell_qx, cell_qy, v_role, h_role in _QUADRANTS:
        # 이 사분면이 닿는 카디널 두 개
        v_water = n_water if v_role == 0 else s_water
        h_water = w_water if h_role == 0 else e_water

        # source 타일 선택: 같은 방향이면 v_role/h_role, 아니면 반대
        src_row = br + (v_role if v_water else 1 - v_role)
        src_col = bc + (h_role if h_water else 1 - h_role)

        # sub-chunk 위치는 항상 셀 사분면과 동일
        yield (cell_qx, cell_qy, src_col, src_row, cell_qx, cell_qy)


def water_tile_for(x: int, y: int, frame: int = 0) -> tuple[int, int]:
    """좌표 (x, y) + 프레임 인덱스로 6 변형 중 하나를 고른다.

    위상 = x + y → 같은 대각선(x+y == const) 위의 셀들이 같은 변형.
    frame 이 +1 늘면 모든 셀의 변형 인덱스가 +1 → 패턴이 NW→SE 로 흐른다.
    같은 (x, y, frame) 은 항상 같은 결과(결정적) 라 부드럽게 cycle.
    """
    phase = x + y
    return WATER_VARIANTS[(phase + frame) % len(WATER_VARIANTS)]


def plain_tile_for(
    dungeon: DungeonMap, x: int, y: int, water_frame: int = 0,
) -> tuple[int, int] | None:
    """오토타일이 아닌 단일 타일을 쓸 경우 (col, row) 반환. 잔디면 None."""
    t = dungeon.get_tile(x, y)
    if t == Tile.WALL:
        return water_tile_for(x, y, water_frame)
    if t == Tile.STAIRS_UP:
        return STAIRS_UP_TILE
    if t == Tile.STAIRS_DOWN:
        return STAIRS_DOWN_TILE
    if t == Tile.DOOR:
        return DOOR_TILE
    # FLOOR, PATH 는 잔디 오토타일로 처리 (PATH 는 추후 구분 예정)
    return None
