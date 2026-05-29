from __future__ import annotations
from dataclasses import dataclass, field
from components.map import DungeonMap, Tile
from components.item import ItemType, ItemManager
from algorithms.pathfinding import astar
import random


@dataclass
class Enemy:
    x: int
    y: int
    hp: int = 10
    max_hp: int = 10
    atk: int = 3
    stunned: bool = False

    def move(self, dx: int, dy: int, dungeon: DungeonMap, enemies: list[Enemy], player) -> bool:
        nx, ny = self.x + dx, self.y + dy
        
        if not dungeon.is_walkable(nx, ny):
            return False
            
        if nx == player.x and ny == player.y:
            return False
            
        for other in enemies:
            if other is not self and other.x == nx and other.y == ny:
                return False
                
        self.x = nx
        self.y = ny
        return True

    def move_towards(self, tx: int, ty: int, dungeon: DungeonMap, enemies: list[Enemy], player) -> None:
        if self.stunned:
            self.stunned = False
            return

        if abs(self.x - tx) + abs(self.y - ty) == 1:
            self.attack(player)
            return

        path = astar(dungeon, (self.x, self.y), (tx, ty))
        if path:
            next_x, next_y = path[0]
            dx = next_x - self.x
            dy = next_y - self.y
            
            self.move(dx, dy, dungeon, enemies, player)

    def attack(self, player) -> int:
        damage = max(0, self.atk - player.def_)
        player.hp = max(0, player.hp - damage)
        player.def_ = max(0, player.def_ - 1)  # 방어력 1 감소
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
            enemy.move_towards(player.x, player.y, dungeon, self.enemies, player)

    def remove_dead(self, item_manager: ItemManager) -> list[Enemy]:
        dead = [e for e in self.enemies if e.hp <= 0]
        for e in dead:
            # None (40%), ATK (30%), DEF (30%)
            roll = random.random()
            if roll < 0.3:
                item_manager.spawn(e.x, e.y, ItemType.ATK_UP)
            elif roll < 0.6:
                item_manager.spawn(e.x, e.y, ItemType.DEF_UP)
            # else: no drop (40%)

        self.enemies = [e for e in self.enemies if e.hp > 0]
        return dead

    def get_all(self) -> list[Enemy]:
        return self.enemies

    def get_at(self, x: int, y: int) -> Enemy | None:
        for e in self.enemies:
            if e.x == x and e.y == y:
                return e
        return None
