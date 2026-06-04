from collections import deque
from dataclasses import dataclass
import random
import time

from components.enemy import EnemyManager
from components.inventory import Inventory
from components.item import Item, ItemManager, ItemType
from components.leaderboard import Leaderboard, ScoreEntry
from components.map import DungeonMap, Tile
from components.player import Player
from components.turn import TurnManager
from components.undo import GameSnapshot, UndoStack


MAP_W = 58
MAP_H = 28
MAX_FLOORS = 3
SHOCKWAVE_COOLDOWN = 1


@dataclass(frozen=True)
class ActorToken:
    """TurnManager 큐에 들어가는 행위자 토큰."""

    name: str


PLAYER_ACTOR = ActorToken("PLAYER")
ENEMY_ACTOR = ActorToken("ENEMIES")


@dataclass(frozen=True)
class ItemEffect:
    """TUI에 잠깐 보여 줄 최근 아이템 발동 정보."""

    category: str
    title: str
    detail: str


@dataclass(frozen=True)
class CombatEffect:
    """TUI에 잠깐 보여 줄 최근 공격 효과."""

    category: str
    title: str
    detail: str
    positions: tuple[tuple[int, int], ...]


class Game:
    """Textual TUI가 사용하는 순수 턴제 게임 엔진.

    EC2208 평가 항목 대응:
    - 던전 맵: components/map.py의 2차원 배열과 방 그래프.
    - Undo: components/undo.py의 크기 제한 스택.
    - 턴 관리: components/turn.py의 큐.
    - 인벤토리: components/inventory.py의 카테고리 dict + 연결 리스트.
    - 적 AI: algorithms/pathfinding.py의 A*, heap, closed set.
    - 리더보드: components/leaderboard.py의 배열과 정렬.
    """

    def __init__(self, width: int = MAP_W, height: int = MAP_H, seed: int | None = None):
        self.width = width
        self.height = height
        self.random = random.Random(seed)
        if seed is not None:
            random.seed(seed)

        self.dungeon_map = DungeonMap(width, height)
        self.player = Player(0, 0)
        self.enemy_manager = EnemyManager()
        self.item_manager = ItemManager()
        self.inventory = Inventory()
        self.undo_stack = UndoStack()
        self.turn_manager = TurnManager()
        self.leaderboard = Leaderboard()

        self.floor = 1
        self.floors_cleared = 0
        self.turn_count = 0
        self.undo_used = 0
        self.kill_xp = 0
        self.shockwave_cooldown = 0
        self.started_at = time.monotonic()
        self.ended_elapsed_seconds: int | None = None
        self.final_score: int | None = None
        self.game_over = False
        self.victory = False
        self.debug_paths = False
        self.item_effect: ItemEffect | None = None
        self.combat_effect: CombatEffect | None = None
        self.player_hit_effect: CombatEffect | None = None
        self.last_collected_item: Item | None = None
        self.messages: deque[str] = deque(maxlen=8)

        self._new_floor(reset_player=True)
        self.turn_manager.reset([PLAYER_ACTOR, ENEMY_ACTOR])
        self.log("목표: > 계단에 도착해 다음 층으로 내려가세요.")

    @property
    def elapsed_seconds(self) -> int:
        if self.ended_elapsed_seconds is not None:
            return self.ended_elapsed_seconds
        return int(time.monotonic() - self.started_at)

    @property
    def score(self) -> int:
        if self.final_score is not None:
            return self.final_score
        return Leaderboard.calculate_score(
            kill_xp=self.kill_xp,
            floors_cleared=self.floors_cleared,
            undo_remaining=self.undo_stack.remaining(),
            elapsed_seconds=self.elapsed_seconds,
        )

    @property
    def player_pos(self) -> tuple[int, int]:
        return self.player.x, self.player.y

    @property
    def last_enemy_path(self) -> set[tuple[int, int]]:
        paths: set[tuple[int, int]] = set()
        for enemy in self.enemy_manager.get_all():
            paths.update(enemy.last_path)
        return paths

    @property
    def stairs_down_pos(self) -> tuple[int, int] | None:
        for y in range(self.dungeon_map.height):
            for x in range(self.dungeon_map.width):
                if self.dungeon_map.get_tile(x, y) == Tile.STAIRS_DOWN:
                    return x, y
        return None

    @property
    def goal_distance(self) -> int | None:
        stairs = self.stairs_down_pos
        if stairs is None:
            return None
        return abs(self.player.x - stairs[0]) + abs(self.player.y - stairs[1])

    @property
    def goal_direction(self) -> str:
        stairs = self.stairs_down_pos
        if stairs is None:
            return "계단 없음"

        dx = stairs[0] - self.player.x
        dy = stairs[1] - self.player.y
        horizontal = "동" if dx > 0 else "서" if dx < 0 else ""
        vertical = "남" if dy > 0 else "북" if dy < 0 else ""
        return vertical + horizontal if vertical or horizontal else "현재 위치"

    def log(self, message: str) -> None:
        self.messages.append(message)

    def move_player(self, dx: int, dy: int) -> bool:
        if self.game_over:
            return False
        self._clear_transient_effects()
        self.last_collected_item = None

        nx, ny = self.player.x + dx, self.player.y + dy
        target_enemy = self.enemy_manager.get_at(nx, ny)
        if target_enemy:
            self._push_snapshot()
            damage = self.player.attack(target_enemy)
            self.combat_effect = CombatEffect("melee", "근접 공격 명중", f"피해 {damage}", ((nx, ny),))
            self.log(f"근접 공격! 적에게 {damage} 피해를 입혔습니다.")
            self._finish_player_action()
            return True

        if not self.dungeon_map.is_walkable(nx, ny):
            self.log("벽에 막혀 이동할 수 없습니다.")
            return False

        self._push_snapshot()
        self.player.x = nx
        self.player.y = ny
        self.turn_count += 1
        self.last_collected_item = self._collect_item()
        self._check_stairs()
        if not self.game_over:
            self._finish_player_action()
        return True

    def area_attack(self) -> bool:
        if self.game_over:
            return False
        self._clear_transient_effects()
        self.last_collected_item = None
        if self.shockwave_cooldown > 0:
            self.log(f"충격파 재사용 대기 중: {self.shockwave_cooldown}턴 남았습니다.")
            return False

        self._push_snapshot()
        shockwave_positions = set(self._shockwave_positions())
        hit = self.player.area_attack(self.enemy_manager.get_all(), shockwave_positions)
        positions = tuple((enemy.x, enemy.y) for enemy in hit)
        if hit:
            total_damage = len(hit) * self.player.atk
            self.combat_effect = CombatEffect(
                "shockwave",
                "충격파 명중",
                f"반경 {self.player.shockwave_radius} / {len(hit)}명 / 총 피해 {total_damage}",
                positions,
            )
            self.log(f"충격파가 주변 적 {len(hit)}명을 맞혔습니다.")
        else:
            self.combat_effect = CombatEffect(
                "shockwave",
                "충격파 방출",
                "주변에 맞은 적 없음",
                self._shockwave_positions(),
            )
            self.log("충격파가 아무것도 맞히지 못했습니다.")
        self.shockwave_cooldown = SHOCKWAVE_COOLDOWN + 1
        self.turn_count += 1
        self._finish_player_action()
        return True

    def undo(self) -> bool:
        if self.game_over:
            self.log("게임이 끝나 되감기를 사용할 수 없습니다.")
            return False
        snapshot = self.undo_stack.pop()
        if snapshot is None:
            self.log("되감기 스택이 비어 있습니다.")
            return False
        self._clear_transient_effects()
        self.last_collected_item = None
        self._restore_snapshot(snapshot)
        self.undo_used += 1
        self.log("시간을 한 턴 되감았습니다.")
        return True

    def use_inventory_slot(self, slot_index: int) -> bool:
        if self.game_over:
            self.log("게임이 끝나 아이템을 사용할 수 없습니다.")
            return False
        stacks = self.inventory.stack_entries()
        if not (0 <= slot_index < len(stacks)):
            self.log("해당 슬롯에 아이템이 없습니다.")
            return False

        selected = stacks[slot_index].item
        if selected.category == ItemType.HEAL.value and self.player.hp >= self.player.max_hp:
            self.log("HP가 이미 가득합니다. 회복 아이템을 아꼈습니다.")
            return False

        self._push_snapshot()
        self._clear_transient_effects()
        self.last_collected_item = None
        item = self.inventory.use(selected.id)
        if item is None:
            self.log("사용하려던 아이템을 찾을 수 없습니다.")
            return False

        if item.category == ItemType.ATK.value:
            before = self.player.atk
            self.player.atk += item.value
            self.item_effect = ItemEffect(item.category, "공격 부스트 발동", f"공격력 {before} -> {self.player.atk}")
            self.log(f"{item.name} 발동! 공격력 {before} -> {self.player.atk}.")
        elif item.category == ItemType.DEF.value:
            before = self.player.def_
            self.player.def_ += item.value
            self.item_effect = ItemEffect(item.category, "방어막 발동", f"방어력 {before} -> {self.player.def_}")
            self.log(f"{item.name} 발동! 방어력 {before} -> {self.player.def_}.")
        elif item.category == ItemType.HEAL.value:
            before = self.player.hp
            self.player.hp = min(self.player.max_hp, self.player.hp + item.value)
            healed = self.player.hp - before
            self.item_effect = ItemEffect(item.category, "회복 효과 발동", f"HP {before} -> {self.player.hp}")
            self.log(f"{item.name} 발동! HP {before} -> {self.player.hp}. 회복 +{healed}.")
        elif item.category == ItemType.RANGE.value:
            before = self.player.shockwave_radius
            self.player.shockwave_radius += item.value
            self.item_effect = ItemEffect(
                item.category,
                "충격파 범위 확장",
                f"반경 {before} -> {self.player.shockwave_radius}",
            )
            self.log(f"{item.name} 발동! 충격파 반경 {before} -> {self.player.shockwave_radius}.")

        return True

    def save_score(self, name: str = "PLAYER") -> int:
        entry = ScoreEntry(
            name=name,
            score=self.score,
            time_seconds=self.elapsed_seconds,
            undo_used=self.undo_used,
            floors_cleared=self.floors_cleared,
        )
        rank = self.leaderboard.add(entry)
        self.leaderboard.save()
        return rank

    def toggle_debug_paths(self) -> None:
        self.debug_paths = not self.debug_paths
        state = "표시" if self.debug_paths else "숨김"
        self.log(f"A* 디버그 경로: {state}.")

    def _clear_transient_effects(self) -> None:
        self.item_effect = None
        self.combat_effect = None
        self.player_hit_effect = None

    def _shockwave_positions(self) -> tuple[tuple[int, int], ...]:
        radius = self.player.shockwave_radius
        start = self.player_pos
        positions: list[tuple[int, int]] = []
        visited = {start}
        queue: deque[tuple[int, int, int]] = deque([(self.player.x, self.player.y, 0)])

        while queue:
            x, y, distance = queue.popleft()
            if distance >= radius:
                continue

            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = x + dx, y + dy
                if (nx, ny) in visited or not self.dungeon_map.is_walkable(nx, ny):
                    continue
                visited.add((nx, ny))
                positions.append((nx, ny))
                queue.append((nx, ny, distance + 1))

        return tuple(positions)

    def _finish_player_action(self) -> None:
        self._remove_dead_enemies()
        if self.game_over:
            return

        self._tick_cooldowns()
        self.turn_manager.advance()
        if self.turn_manager.current() == ENEMY_ACTOR:
            before_hp = self.player.hp
            self.enemy_manager.update_enemies(self.player, self.dungeon_map)
            damage_taken = before_hp - self.player.hp
            if damage_taken > 0:
                self.player_hit_effect = CombatEffect(
                    "player-hit",
                    "피격",
                    f"받은 피해 {damage_taken}",
                    (self.player_pos,),
                )
                self.log(f"적의 반격! 플레이어가 {damage_taken} 피해를 받았습니다.")
            self._remove_dead_enemies()
            if self.player.hp <= 0:
                self.player.hp = 0
                self._end_game(victory=False, message="게임 오버. 던전에게 패배했습니다.")
        self.turn_manager.advance()

    def _tick_cooldowns(self) -> None:
        if self.shockwave_cooldown > 0:
            self.shockwave_cooldown -= 1

    def _remove_dead_enemies(self) -> None:
        dead = self.enemy_manager.remove_dead(self.item_manager)
        if not dead:
            return
        gained = len(dead) * 10
        self.player.xp += gained
        self.kill_xp += gained
        self.log(f"적 {len(dead)}명을 처치했습니다. XP +{gained}.")

    def _collect_item(self) -> Item | None:
        item = self.item_manager.get_at(self.player.x, self.player.y)
        if item is None:
            return None
        self.inventory.add(item)
        self.item_manager.remove(item)
        self.log(f"{item.name}을(를) 획득했습니다. i 또는 숫자로 사용하세요.")
        return item

    def _check_stairs(self) -> None:
        if self.dungeon_map.get_tile(self.player.x, self.player.y) != Tile.STAIRS_DOWN:
            return

        self.floors_cleared += 1
        if self.floor >= MAX_FLOORS:
            self._end_game(victory=True, message="승리! 마지막 층을 클리어했습니다.")
            return

        self.floor += 1
        self.log(f"{self.floor}층으로 내려갑니다.")
        self._new_floor(reset_player=False)

    def _new_floor(self, reset_player: bool) -> None:
        self.dungeon_map = DungeonMap(self.width, self.height)
        self.dungeon_map.generate()
        sx, sy = self.dungeon_map.rooms[0].center()

        if reset_player:
            self.player = Player(x=sx, y=sy)
        else:
            self.player.x = sx
            self.player.y = sy

        self.enemy_manager = EnemyManager()
        self.enemy_manager.spawn(self.dungeon_map, floor=self.floor)
        self.item_manager = ItemManager()
        self._scatter_items()

    def _end_game(self, victory: bool, message: str) -> None:
        if self.game_over:
            return
        self.ended_elapsed_seconds = int(time.monotonic() - self.started_at)
        self.final_score = Leaderboard.calculate_score(
            kill_xp=self.kill_xp,
            floors_cleared=self.floors_cleared,
            undo_remaining=self.undo_stack.remaining(),
            elapsed_seconds=self.ended_elapsed_seconds,
        )
        self.game_over = True
        self.victory = victory
        self.log(message)
        self.save_score()

    def _scatter_items(self) -> None:
        rooms = self.dungeon_map.rooms[1:]
        for room in rooms[: min(6, len(rooms))]:
            if self.random.random() > 0.65:
                continue
            x = self.random.randint(room.x, room.x + room.w - 1)
            y = self.random.randint(room.y, room.y + room.h - 1)
            item_type = self.random.choice([ItemType.ATK, ItemType.DEF, ItemType.HEAL, ItemType.RANGE])
            self.item_manager.spawn(x, y, item_type)

    def _push_snapshot(self) -> None:
        self.undo_stack.push(
            GameSnapshot.capture(
                player=self.player,
                enemies=self.enemy_manager.get_all(),
                field_items=self.item_manager.get_all(),
                inventory=self.inventory.to_list(),
                turn_count=self.turn_count,
                floor=self.floor,
                floors_cleared=self.floors_cleared,
                kill_xp=self.kill_xp,
                shockwave_cooldown=self.shockwave_cooldown,
            )
        )

    def _restore_snapshot(self, snapshot: GameSnapshot) -> None:
        snapshot.restore_player(self.player)
        self.enemy_manager.set_all(snapshot.restore_enemies())
        self.item_manager.set_all(snapshot.restore_field_items())
        self.inventory.replace_all(snapshot.restore_inventory())
        self.turn_count = snapshot.turn_count
        self.floor = snapshot.floor
        self.floors_cleared = snapshot.floors_cleared
        self.kill_xp = snapshot.kill_xp
        self.shockwave_cooldown = snapshot.shockwave_cooldown
        self.game_over = False
        self.victory = False
        self.ended_elapsed_seconds = None
        self.final_score = None
        self.item_effect = None
        self.combat_effect = None
        self.player_hit_effect = None
        self.last_collected_item = None
        self.turn_manager.reset([PLAYER_ACTOR, ENEMY_ACTOR])
