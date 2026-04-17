from __future__ import annotations
from dataclasses import dataclass
from components.map import DungeonMap


@dataclass
class Player:
    x: int
    y: int
    hp: int = 30
    max_hp: int = 30
    atk: int = 5
    def_: int = 2
    xp: int = 0
    arrows: int = 5

    def move(self, dx: int, dy: int, dungeon: DungeonMap) -> bool:
        """이동 시도. 이동 가능하면 좌표를 갱신하고 True 반환."""
        nx, ny = self.x + dx, self.y + dy
        if dungeon.is_walkable(nx, ny):
            self.x = nx
            self.y = ny
            return True
        return False

    @property
    def hp_ratio(self) -> float:
        return self.hp / self.max_hp
