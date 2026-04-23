from __future__ import annotations
from dataclasses import dataclass, field
from components.map import DungeonMap, Tile
from algorithms.pathfinding import astar
import random


@dataclass
class Enemy:
    x: int
    y: int
    hp: int = 10
    max_hp: int = 10
    atk: int = 3

    def move(self, dx: int, dy: int, dungeon: DungeonMap) -> bool:
        nx, ny = self.x + dx, self.y + dy
        if dungeon.is_walkable(nx, ny):
            self.x = nx
            self.y = ny
            return True
        return False

    def move_towards(self, tx: int, ty: int, dungeon: DungeonMap, player) -> None:
        if abs(self.x - tx) + abs(self.y - ty) == 1:
            self.attack(player)
            return

        path = astar(dungeon, (self.x, self.y), (tx, ty))
        if path:
            next_x, next_y = path[0]
            if next_x == player.x and next_y == player.y:
                return
            
            self.x = next_x
            self.y = next_y

    def attack(self, player) -> int:
        damage = max(0, self.atk - player.def_)
        player.hp = max(0, player.hp - damage)
        return damage

    @property
    def hp_ratio(self) -> float:
        return self.hp / self.max_hp


class EnemyManager:
    def __init__(self):
        self.enemies: list[Enemy] = []

    def spawn(self, dungeon_map: DungeonMap) -> None:
        if not dungeon_map.rooms:
            return

        for room in dungeon_map.rooms[1:]:
            num_enemies = 1 # room에 존재하는 적 수
            for _ in range(num_enemies):
                rx = random.randint(room.x, room.x + room.w - 1)
                ry = random.randint(room.y, room.y + room.h - 1)
                
                if dungeon_map.get_tile(rx, ry) == Tile.FLOOR and not self.get_at(rx, ry):
                    self.enemies.append(Enemy(x=rx, y=ry))

    def update_enemies(self, player, dungeon: DungeonMap) -> None:
        for enemy in self.enemies:
            enemy.move_towards(player.x, player.y, dungeon, player)

    def remove_dead(self) -> list[Enemy]:
        dead = [e for e in self.enemies if e.hp <= 0]
        self.enemies = [e for e in self.enemies if e.hp > 0]
        return dead

    def get_all(self) -> list[Enemy]:
        return self.enemies

    def get_at(self, x: int, y: int) -> Enemy | None:
        for e in self.enemies:
            if e.x == x and e.y == y:
                return e
        return None
