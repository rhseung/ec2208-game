# Dungeon Crawler RPG — 프로젝트 컨텍스트

## 개요

GIST AI2000 자료구조 & 알고리즘 수업 팀 프로젝트.
Python + pygame + pygame_gui로 구현하는 **턴제 던전 크롤러 RPG**.
핵심 차별점: **Undo(시간 되감기)가 단순 취소 기능이 아닌 핵심 게임플레이 메커닉**.

- 팀 인원: 2명
- 언어: Python
- 라이브러리: `pygame`, `pygame_gui`
- 장르: 턴제 던전 크롤러 (탑다운 2D)

---

## 핵심 컨셉 — Undo as Core Mechanic

플레이어는 "시간을 되감는 능력"을 가진 캐릭터. Undo가 실수 취소가 아니라 **퍼즐과 전투를 풀어나가는 핵심 도구**.

- Undo 횟수는 제한된 소모 자원 (최대 30회, 적 처치/아이템으로 충전)
- 되감으면 **적도 이전 위치로 돌아감** → 적을 함정으로 유도하는 전략 가능
- 특정 방은 Undo 없이 클리어 불가능하게 설계
- Undo 시 이전 행동의 **Ghost(잔상)** 가 시각적으로 표시됨

---

## 구현해야 할 6가지 컴포넌트

| # | 컴포넌트 | 자료구조 | 설명 |
|---|---------|---------|------|
| 1 | Dungeon Map | 2D Array + Graph | 맵 타일 저장, 방 간 연결 |
| 2 | Undo System | Stack (max 30) | 게임 상태 스냅샷 저장/복원 |
| 3 | Turn Management | Queue | 플레이어 → 적 순서 관리 |
| 4 | Item Inventories | Linked List | 카테고리별 아이템 관리 |
| 5 | Enemy AI | Priority Queue (A*) + Set | A* 경로탐색 |
| 6 | Leaderboard | Array + 정렬 | 점수 기록, JSON 영속성 |

---

## 점수 공식

```
점수 = 킬XP×10 + 클리어층×500 + Undo잔여×50 + max(0, 3000-경과초)×10
```

---

## 프로젝트 구조

```
dungeon_crawler/
├── main.py
├── game.py                  # 메인 게임 루프
├── components/
│   ├── map.py               # Dungeon Map
│   ├── player.py            # Player
│   ├── enemy.py             # Enemy + EnemyManager
│   ├── inventory.py         # Item Inventories
│   ├── undo.py              # Undo System
│   ├── turn.py              # Turn Management
│   └── leaderboard.py       # Leaderboard
├── algorithms/
│   ├── map_gen.py           # BSP 맵 생성
│   └── pathfinding.py       # A* 알고리즘
├── renderer/
│   ├── pygame_renderer.py   # 메인 렌더러
│   ├── hud.py               # HUD 패널
│   ├── message_log.py       # 메시지 로그
│   ├── screens/
│   │   ├── main_menu.py
│   │   ├── inventory_screen.py
│   │   └── leaderboard_screen.py
│   └── theme.json           # pygame_gui 테마
├── assets/
│   ├── sprites/
│   ├── fonts/
│   └── sounds/
└── data/
    └── leaderboard.json
```

---

## 화면 레이아웃

```
┌─────────────────────────────────┬──────────────┐
│                                 │   HUD Panel  │
│         Game Viewport           │  HP / XP bar │
│      (던전 맵 + 엔티티)           │  ATK / DEF   │
│         900×600                 │  Undo gauge  │
│                                 │  Inventory   │
├─────────────────────────────────┤   380×720    │
│         Message Log             │              │
│         900×120                 │              │
└─────────────────────────────────┴──────────────┘
         전체 해상도: 1280×720
```

---

## 세부 클래스 설계

### map.py

```python
class Tile:
    WALL = '#'
    FLOOR = '.'
    DOOR = 'D'
    STAIRS_UP = '<'
    STAIRS_DOWN = '>'

class Room:
    def __init__(self, x, y, w, h): ...
    def center(self) -> tuple[int, int]: ...
    def intersects(self, other: Room) -> bool: ...

class DungeonMap:
    def __init__(self, width: int, height: int): ...
    # grid: list[list[Tile]]          — 2D Array
    # rooms: list[Room]
    # room_graph: dict[int, list[int]] — 인접 리스트
    def generate(self) -> None          # BSP 맵 생성
    def get_tile(self, x, y) -> Tile
    def set_tile(self, x, y, tile) -> None
    def is_walkable(self, x, y) -> bool
    def get_neighbors(self, x, y) -> list[tuple]  # A*용
```

### undo.py

```python
@dataclass
class GameSnapshot:
    player_x: int
    player_y: int
    player_hp: int
    player_arrows: int
    inventory: list        # 깊은 복사
    enemies: list          # 적 상태 깊은 복사
    turn_count: int

class UndoStack:
    MAX_SIZE = 30
    # _stack: list[GameSnapshot]

    def push(self, snapshot: GameSnapshot) -> None
    def pop(self) -> GameSnapshot | None
    def peek(self) -> GameSnapshot | None
    def remaining(self) -> int
    def is_empty(self) -> bool
    def clear(self) -> None
```

### turn.py

```python
from collections import deque

class TurnManager:
    # _queue: deque[Actor]

    def enqueue(self, actor) -> None
    def dequeue(self) -> Actor
    def remove(self, actor) -> None      # 적 사망 시
    def current(self) -> Actor
    def advance(self) -> Actor
    def reset(self, actors: list) -> None
    def rebuild(self) -> None
```

### inventory.py

```python
class ItemNode:
    def __init__(self, item):
        self.item = item
        self.next: ItemNode | None = None

class ItemLinkedList:
    def append(self, item) -> None
    def remove(self, item_id: str) -> bool
    def find(self, item_id: str) -> Item | None
    def to_list(self) -> list
    def __iter__(self)

class Inventory:
    # categories: dict[str, ItemLinkedList]
    # 카테고리: 'ATK', 'DEF', 'HEAL'

    def add(self, item) -> None
    def use(self, item_id: str) -> Item | None
    def display(self) -> str

@dataclass
class Item:
    id: str
    name: str
    category: str    # 'ATK' | 'DEF' | 'HEAL'
    value: int
```

### enemy.py + pathfinding.py

```python
# pathfinding.py
import heapq

def astar(
    grid: DungeonMap,
    start: tuple[int, int],
    goal: tuple[int, int]
) -> list[tuple[int, int]]:
    # open_set: list[tuple[float, tuple]]  — min-heap
    # closed_set: set[tuple[int, int]]     — 방문 완료
    # came_from: dict                      — 경로 추적
    # heuristic: 맨해튼 거리

# enemy.py
class Enemy:
    def __init__(self, x, y, enemy_type: str): ...
    # path_cache: list[tuple]  — A* 결과 캐싱

    def take_turn(self, game_state) -> None
    def move_toward_player(self, dungeon_map, player_pos) -> None
    def attack(self, player) -> int
    def _recalculate_path(self, dungeon_map, player_pos) -> None

class EnemyManager:
    # enemies: list[Enemy]

    def spawn(self, dungeon_map) -> None
    def remove_dead(self) -> list[Enemy]
    def get_all(self) -> list[Enemy]
    def get_at(self, x, y) -> Enemy | None
```

### leaderboard.py

```python
@dataclass
class ScoreEntry:
    name: str
    score: int
    time_seconds: int
    undo_used: int
    floors_cleared: int

class Leaderboard:
    MAX_ENTRIES = 10
    SAVE_PATH = 'data/leaderboard.json'
    # entries: list[ScoreEntry]

    def add(self, entry: ScoreEntry) -> int  # 반환: 순위
    def _sort(self) -> None
    def get_rank(self, score: int) -> int
    def save(self) -> None
    def load(self) -> None
    def display(self) -> str

    @staticmethod
    def calculate_score(
        kill_xp: int,
        floors_cleared: int,
        undo_remaining: int,
        elapsed_seconds: int
    ) -> int:
        return (kill_xp * 10
              + floors_cleared * 500
              + undo_remaining * 50
              + max(0, 3000 - elapsed_seconds) * 10)
```

### renderer/pygame_renderer.py

```python
import pygame, pygame_gui

SCREEN_W, SCREEN_H = 1280, 720
VIEWPORT_W = 900
TILE_SIZE = 32

class Camera:
    def center_on(self, x, y, map_w, map_h) -> None
    def apply(self, x, y) -> tuple[int, int]  # 월드→스크린 좌표

class PygameRenderer:
    # screen, manager(pygame_gui), clock, camera, hud, message_log

    def render_frame(self, game_state) -> None
    def render_map(self, dungeon_map, offset) -> None
    def render_entities(self, player, enemies) -> None
    def render_astar_debug(self, path: list[tuple]) -> None  # A* 시각화
    def flip(self) -> None
    def process_events(self, event) -> None
```

### renderer/hud.py

```python
class HUD:
    # pygame_gui 요소:
    # - hp_bar, xp_bar, undo_bar: UIStatusBar
    # - stat_labels: dict[str, UILabel]  (ATK/DEF/화살)
    # - inventory_container: UIScrollingContainer
    # - score_label, floor_label: UILabel

    def update(self, player, undo_stack, score: int) -> None
```

### renderer/message_log.py

```python
class MessageLog:
    MAX_LINES = 6
    # box: UITextBox
    # _lines: deque[str]

    def add(self, message: str, color: str = 'white') -> None
    def clear(self) -> None
    def _refresh(self) -> None
```

### renderer/theme.json

```json
{
    "defaults": {
        "colours": {
            "normal_bg": "#1a2035",
            "hovered_bg": "#2a3a5c",
            "dark_bg": "#0d1520",
            "normal_text": "#e0e0e0",
            "normal_border": "#3a5a8a"
        },
        "font": { "name": "fira_code", "size": "14" }
    },
    "ui_status_bar": {
        "colours": {
            "status_bar_hp":   "#e05555",
            "status_bar_xp":   "#55aaff",
            "status_bar_undo": "#55dd88"
        }
    }
}
```

---

## 게임 루프 구조 (game.py)

```python
class Game:
    def __init__(self):
        self.renderer = PygameRenderer()
        self.dungeon_map = DungeonMap(80, 50)
        self.player = Player(...)
        self.enemy_manager = EnemyManager()
        self.turn_manager = TurnManager()
        self.undo_stack = UndoStack()
        self.leaderboard = Leaderboard()

    def run(self):
        while self.running:
            dt = self.clock.tick(60)
            for event in pygame.event.get():
                self._handle_input(event)
            self._update()
            self.renderer.render_frame(self._get_game_state())
            self.renderer.flip()

    def _handle_input(self, event): ...
    def _update(self): ...
    def _get_game_state(self) -> GameState: ...
```

---

## 개발 우선순위

1. **`map.py` + `map_gen.py`** — 모든 컴포넌트의 기반
2. **`player.py` + `renderer/pygame_renderer.py`** — 눈에 보이는 것 먼저
3. **`enemy.py` + `pathfinding.py`** — 기본 전투 동작
4. **`undo.py`** — 핵심 메커닉
5. **`turn.py` + `inventory.py` + `leaderboard.py`** — 나머지
6. **통합 + 밸런싱**

---

## 에셋

- 스프라이트: Kenney.nl — Roguelike/RPG Pack (CC0, 출처 표기 불필요)
- TILE_SIZE: 32×32px 기준
