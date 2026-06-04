from dataclasses import dataclass, field
from enum import Enum
from components.map import DungeonMap, Tile
from components.item import ItemManager, ItemType
from algorithms.pathfinding import astar
import random


class EnemyType(str, Enum):
    GRUNT = "GRUNT"
    SCOUT = "SCOUT"
    BRUTE = "BRUTE"


ENEMY_GLYPHS: dict[EnemyType, str] = {
    EnemyType.GRUNT: "G",
    EnemyType.SCOUT: "S",
    EnemyType.BRUTE: "B",
}

DETECTION_RANGES: dict[EnemyType, int] = {
    EnemyType.GRUNT: 7,
    EnemyType.SCOUT: 10,
    EnemyType.BRUTE: 5,
}


@dataclass
class Enemy:
    x: int
    y: int
    enemy_type: EnemyType = EnemyType.GRUNT
    hp: int = 10
    max_hp: int = 10
    atk: int = 3
    stunned: bool = False
    detection_range: int = 15
    last_path: list[tuple[int, int]] = field(default_factory=list)

    def move(self, dx: int, dy: int, dungeon: DungeonMap, enemies: list["Enemy"], player) -> bool:
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

    def move_towards(self, tx: int, ty: int, dungeon: DungeonMap, enemies: list["Enemy"], player) -> None:
        if self.stunned:
            self.stunned = False
            self.last_path = []
            return

        if abs(self.x - tx) + abs(self.y - ty) == 1:
            self.attack(player)
            self.last_path = []
            return

        path = astar(dungeon, (self.x, self.y), (tx, ty))
        self.last_path = path
        if path:
            next_x, next_y = path[0]
            dx = next_x - self.x
            dy = next_y - self.y
            
            self.move(dx, dy, dungeon, enemies, player)

    def attack(self, player) -> int:
        damage = max(0, self.atk - player.def_)
        player.hp = max(0, player.hp - damage)
        player.def_ = max(player.DEFAULT_DEF, player.def_ - 1)
        return damage

    @property
    def hp_ratio(self) -> float:
        return self.hp / self.max_hp

    @property
    def glyph(self) -> str:
        return ENEMY_GLYPHS[self.enemy_type]


class EnemyManager:
    def __init__(self):
        self.enemies: list[Enemy] = []

    def spawn(self, dungeon_map: DungeonMap, floor: int = 1) -> None:
        if not dungeon_map.rooms:
            return

        spawn_index = 0
        for room in dungeon_map.rooms[1:]:
            num_enemies = min(3, floor + 1)  # 1층 2마리, 2층 3마리, 이후 최대 3마리
            for _ in range(num_enemies):
                for _attempt in range(20):
                    rx = random.randint(room.x, room.x + room.w - 1)
                    ry = random.randint(room.y, room.y + room.h - 1)

                    if dungeon_map.get_tile(rx, ry) != Tile.FLOOR or self.get_at(rx, ry):
                        continue

                    self.enemies.append(_make_enemy(rx, ry, floor, spawn_index))
                    spawn_index += 1
                    break

    def update_enemies(self, player, dungeon: DungeonMap) -> None:
        for enemy in self.enemies:
            dist = abs(enemy.x - player.x) + abs(enemy.y - player.y)
            if dist <= enemy.detection_range:
                enemy.move_towards(player.x, player.y, dungeon, self.enemies, player)
            else:
                enemy.last_path = []

    def remove_dead(self, item_manager: ItemManager) -> list[Enemy]:
        dead = [e for e in self.enemies if e.hp <= 0]
        for e in dead:
            # 드롭 없음 40%, 공격 아이템 30%, 방어 아이템 30%
            roll = random.random()
            if roll < 0.3:
                item_manager.spawn(e.x, e.y, ItemType.ATK)
            elif roll < 0.6:
                item_manager.spawn(e.x, e.y, ItemType.DEF)
            # 나머지는 아이템을 떨어뜨리지 않는다.

        self.enemies = [e for e in self.enemies if e.hp > 0]
        return dead

    def get_all(self) -> list[Enemy]:
        return self.enemies

    def get_at(self, x: int, y: int) -> Enemy | None:
        for e in self.enemies:
            if e.x == x and e.y == y:
                return e
        return None

    def set_all(self, enemies: list[Enemy]) -> None:
        self.enemies = enemies

    def type_counts(self) -> dict[EnemyType, int]:
        counts = {enemy_type: 0 for enemy_type in EnemyType}
        for enemy in self.enemies:
            counts[enemy.enemy_type] += 1
        return counts


def _make_enemy(x: int, y: int, floor: int, spawn_index: int) -> Enemy:
    enemy_type = _choose_enemy_type(floor, spawn_index)
    hp_bonus = max(0, floor - 1) * 2
    atk_bonus = max(0, floor - 1)

    if enemy_type == EnemyType.SCOUT:
        return Enemy(
            x=x,
            y=y,
            enemy_type=enemy_type,
            hp=8 + hp_bonus,
            max_hp=8 + hp_bonus,
            atk=2 + atk_bonus,
            detection_range=DETECTION_RANGES[enemy_type] + floor,
        )
    if enemy_type == EnemyType.BRUTE:
        return Enemy(
            x=x,
            y=y,
            enemy_type=enemy_type,
            hp=14 + hp_bonus,
            max_hp=14 + hp_bonus,
            atk=4 + atk_bonus,
            detection_range=DETECTION_RANGES[enemy_type] + floor,
        )
    return Enemy(
        x=x,
        y=y,
        enemy_type=enemy_type,
        hp=10 + hp_bonus,
        max_hp=10 + hp_bonus,
        atk=3 + atk_bonus,
        detection_range=DETECTION_RANGES[enemy_type] + floor,
    )


def _choose_enemy_type(floor: int, spawn_index: int) -> EnemyType:
    if floor <= 1 and spawn_index % 4 == 1:
        return EnemyType.SCOUT
    if floor == 2 and spawn_index % 5 == 2:
        return EnemyType.BRUTE
    if floor >= 3 and spawn_index % 3 == 2:
        return EnemyType.BRUTE

    roll = random.random()
    if floor <= 1:
        if roll < 0.75:
            return EnemyType.GRUNT
        return EnemyType.SCOUT
    if floor == 2:
        if roll < 0.45:
            return EnemyType.GRUNT
        if roll < 0.8:
            return EnemyType.SCOUT
        return EnemyType.BRUTE
    if roll < 0.3:
        return EnemyType.GRUNT
    if roll < 0.6:
        return EnemyType.SCOUT
    return EnemyType.BRUTE
