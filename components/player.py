from __future__ import annotations
from dataclasses import dataclass
from components.map import DungeonMap


@dataclass
class Player:
    x: int
    y: int
    hp: int = 36
    max_hp: int = 36
    atk: int = 5
    def_: int = 0
    xp: int = 0
    arrows: int = 5
    shockwave_radius: int = 1

    DEFAULT_ATK: int = 5
    DEFAULT_DEF: int = 0

    def move(self, dx: int, dy: int, dungeon: DungeonMap) -> bool:
        """이동 시도. 이동 가능하면 좌표를 갱신하고 True 반환."""
        nx, ny = self.x + dx, self.y + dy
        if dungeon.is_walkable(nx, ny):
            self.x = nx
            self.y = ny
            return True
        return False

    def attack(self, enemy) -> int:
        damage = max(0, self.atk)
        enemy.hp -= damage
        return damage

    def area_attack(self, enemies: list, reachable_positions: set[tuple[int, int]] | None = None) -> list:
        hit_enemies = []
        for enemy in enemies:
            if reachable_positions is not None:
                if (enemy.x, enemy.y) in reachable_positions:
                    self.attack(enemy)
                    hit_enemies.append(enemy)
                continue

            distance = abs(enemy.x - self.x) + abs(enemy.y - self.y)
            if 0 < distance <= self.shockwave_radius:
                self.attack(enemy)
                hit_enemies.append(enemy)
        return hit_enemies

    @property
    def hp_ratio(self) -> float:
        return self.hp / self.max_hp
