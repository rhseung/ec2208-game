from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum



class Tile(StrEnum):
    WALL = '#'
    FLOOR = '.'
    DOOR = 'D'
    STAIRS_UP = '<'
    STAIRS_DOWN = '>'


@dataclass
class Room:
    x: int
    y: int
    w: int
    h: int

    def center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2

    def intersects(self, other: Room) -> bool:
        return (
            self.x < other.x + other.w
            and self.x + self.w > other.x
            and self.y < other.y + other.h
            and self.y + self.h > other.y
        )


class DungeonMap:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid: list[list[Tile]] = [[Tile.WALL] * width for _ in range(height)]
        self.rooms: list[Room] = []
        self.room_graph: dict[int, list[int]] = {}

    def generate(self) -> None:
        from algorithms.map_gen import generate_bsp
        generate_bsp(self)

    def get_tile(self, x: int, y: int) -> Tile:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x]
        return Tile.WALL

    def set_tile(self, x: int, y: int, tile: Tile) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = tile

    def is_walkable(self, x: int, y: int) -> bool:
        return self.get_tile(x, y) in (Tile.FLOOR, Tile.DOOR, Tile.STAIRS_UP, Tile.STAIRS_DOWN)

    def get_neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        result = []
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = x + dx, y + dy
            if self.is_walkable(nx, ny):
                result.append((nx, ny))
        return result
