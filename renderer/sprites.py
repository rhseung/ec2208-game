"""스프라이트 아틀라스 로더.

overworld.png는 16x16 픽셀 타일이 격자로 배치된 시트.
화면 타일 크기(32x32)에 맞춰 2배 스케일하여 캐싱한다.

corner-decomposition 오토타일을 위해 8x8 sub-chunk 단위 fetch도 지원.
"""

from __future__ import annotations
from pathlib import Path
import pygame

SOURCE_TILE_PX = 16  # 원본 시트의 한 타일 크기
SOURCE_SUB_PX = 8  # 8x8 sub-chunk (corner-decomp용)

# TODO: user, enemy 스프라이트도 여기서 관리하도록 확장하기


class Tileset:
    def __init__(self, path: str | Path, scale: int = 2):
        # convert_alpha는 display가 초기화된 뒤 호출해야 한다.
        self.image = pygame.image.load(str(path)).convert_alpha()
        self.scale = scale
        self.out_px = SOURCE_TILE_PX * scale
        self.sub_out_px = SOURCE_SUB_PX * scale
        self._cache: dict[tuple[int, int], pygame.Surface] = {}
        self._sub_cache: dict[tuple[int, int, int, int], pygame.Surface] = {}

    def get(self, col: int, row: int) -> pygame.Surface:
        """(col, row) 위치의 타일 한 칸을 스케일된 Surface로 반환."""
        key = (col, row)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        rect = pygame.Rect(
            col * SOURCE_TILE_PX,
            row * SOURCE_TILE_PX,
            SOURCE_TILE_PX,
            SOURCE_TILE_PX,
        )
        src = self.image.subsurface(rect).copy()
        scaled = pygame.transform.scale(src, (self.out_px, self.out_px))
        self._cache[key] = scaled
        return scaled

    def get_subtile(
        self, col: int, row: int, sub_col: int, sub_row: int
    ) -> pygame.Surface:
        """source 타일 (col, row) 안의 8x8 sub-chunk를 스케일하여 반환.
        sub_col, sub_row ∈ {0, 1}  (0=좌/상, 1=우/하).
        """
        key = (col, row, sub_col, sub_row)
        cached = self._sub_cache.get(key)
        if cached is not None:
            return cached

        rect = pygame.Rect(
            col * SOURCE_TILE_PX + sub_col * SOURCE_SUB_PX,
            row * SOURCE_TILE_PX + sub_row * SOURCE_SUB_PX,
            SOURCE_SUB_PX,
            SOURCE_SUB_PX,
        )
        src = self.image.subsurface(rect).copy()
        scaled = pygame.transform.scale(src, (self.sub_out_px, self.sub_out_px))
        self._sub_cache[key] = scaled
        return scaled
