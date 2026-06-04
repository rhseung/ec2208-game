from dataclasses import dataclass

from components.enemy import Enemy, EnemyType
from components.item import Item
from components.player import Player


@dataclass
class PlayerState:
    x: int
    y: int
    hp: int
    max_hp: int
    atk: int
    def_: int
    xp: int
    arrows: int
    shockwave_radius: int


@dataclass
class EnemyState:
    x: int
    y: int
    enemy_type: EnemyType
    hp: int
    max_hp: int
    atk: int
    stunned: bool
    detection_range: int


@dataclass
class GameSnapshot:
    player: PlayerState
    enemies: list[EnemyState]
    field_items: list[Item]
    inventory: list[Item]
    turn_count: int
    floor: int
    floors_cleared: int
    kill_xp: int
    shockwave_cooldown: int

    @classmethod
    def capture(
        cls,
        player: Player,
        enemies: list[Enemy],
        field_items: list[Item],
        inventory: list[Item],
        turn_count: int,
        floor: int,
        floors_cleared: int,
        kill_xp: int,
        shockwave_cooldown: int,
    ) -> "GameSnapshot":
        return cls(
            player=PlayerState(
                x=player.x,
                y=player.y,
                hp=player.hp,
                max_hp=player.max_hp,
                atk=player.atk,
                def_=player.def_,
                xp=player.xp,
                arrows=player.arrows,
                shockwave_radius=player.shockwave_radius,
            ),
            enemies=[
                EnemyState(
                    x=enemy.x,
                    y=enemy.y,
                    enemy_type=enemy.enemy_type,
                    hp=enemy.hp,
                    max_hp=enemy.max_hp,
                    atk=enemy.atk,
                    stunned=enemy.stunned,
                    detection_range=enemy.detection_range,
                )
                for enemy in enemies
            ],
            field_items=[item.copy() for item in field_items],
            inventory=[item.copy() for item in inventory],
            turn_count=turn_count,
            floor=floor,
            floors_cleared=floors_cleared,
            kill_xp=kill_xp,
            shockwave_cooldown=shockwave_cooldown,
        )

    def restore_player(self, player: Player) -> None:
        player.x = self.player.x
        player.y = self.player.y
        player.hp = self.player.hp
        player.max_hp = self.player.max_hp
        player.atk = self.player.atk
        player.def_ = self.player.def_
        player.xp = self.player.xp
        player.arrows = self.player.arrows
        player.shockwave_radius = self.player.shockwave_radius

    def restore_enemies(self) -> list[Enemy]:
        return [
            Enemy(
                x=state.x,
                y=state.y,
                enemy_type=state.enemy_type,
                hp=state.hp,
                max_hp=state.max_hp,
                atk=state.atk,
                stunned=state.stunned,
                detection_range=state.detection_range,
            )
            for state in self.enemies
        ]

    def restore_field_items(self) -> list[Item]:
        return [item.copy() for item in self.field_items]

    def restore_inventory(self) -> list[Item]:
        return [item.copy() for item in self.inventory]


class UndoStack:
    """크기 제한이 있는 LIFO 스택.

    행동 직전에 push하고, 되감기 입력이 들어오면 pop해서 직전 상태로 복원한다.
    """

    MAX_SIZE = 30

    def __init__(self, max_size: int = MAX_SIZE):
        self.max_size = max_size
        self._stack: list[GameSnapshot] = []

    def push(self, snapshot: GameSnapshot) -> None:
        self._stack.append(snapshot)
        if len(self._stack) > self.max_size:
            self._stack.pop(0)

    def pop(self) -> GameSnapshot | None:
        if not self._stack:
            return None
        return self._stack.pop()

    def peek(self) -> GameSnapshot | None:
        if not self._stack:
            return None
        return self._stack[-1]

    def remaining(self) -> int:
        return self.max_size - len(self._stack)

    def __len__(self) -> int:
        return len(self._stack)

    def is_empty(self) -> bool:
        return not self._stack

    def clear(self) -> None:
        self._stack.clear()
