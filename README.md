# Dungeon Crawler RPG — EC2208 팀 프로젝트

턴제 던전 크롤러 RPG. **Undo(시간 되감기)** 가 핵심 게임플레이 메커닉.

---

## 진행 상황

### 완료

| 파일 | 내용 |
| ------ | ------ |
| `components/map.py` | `Tile`, `Room`, `DungeonMap` — 타일 CRUD, 이웃 탐색, 보행 가능 판정 |
| `algorithms/map_gen.py` | BSP 맵 생성 — 재귀 분할 → 방 배치 → 터널 연결 → 방 그래프 → 계단 배치 |
| `algorithms/pathfinding.py` | A* (맨해튼 거리 휴리스틱, min-heap, closed-set 미사용 최적화) |
| `components/player.py` | `Player` — 이동, stat(HP/ATK/DEF/XP/화살), `hp_ratio` |
| `components/enemy.py` | `Enemy` (A* 이동, 인접 공격, 충돌 처리), `EnemyManager` (스폰, 턴 실행, 사망 처리) |
| `game.py` | 메인 게임 루프, 플레이어·적 렌더, 카메라, HP HUD, **턴제 상태머신** (`PLAYER_TURN` <-> `ENEMY_TURN`) |
| `main.py` | 진입점 |

### 미구현

| 파일 | 우선순위 | 내용 |
| ------ | --------- | ------ |
| `components/undo.py` | ★★★ | `GameSnapshot`, `UndoStack` (max 30) — 핵심 메커닉 |
| `components/turn.py` | ★★☆ | `TurnManager` (deque) — 현재 `game.py`에 인라인으로 존재 |
| `components/inventory.py` | ★★☆ | `ItemLinkedList`, `Inventory`, `Item` |
| `components/leaderboard.py` | ★☆☆ | `Leaderboard`, `ScoreEntry`, JSON 영속성 |
| `renderer/pygame_renderer.py` | ★★☆ | `Camera`, `PygameRenderer` — 현재 `game.py`에 인라인으로 존재 |
| `renderer/hud.py` | ★★☆ | `HUD` — HP/XP/Undo 게이지, 인벤토리 패널 |
| `renderer/message_log.py` | ★☆☆ | `MessageLog` — 전투 로그 |
| `renderer/screens/` | ★☆☆ | 메인메뉴, 인벤토리, 리더보드 화면 |
| `renderer/theme.json` | ★☆☆ | pygame_gui 다크 테마 |

---

## 현재 동작

- BSP 알고리즘으로 매 실행마다 다른 던전 생성
- WASD / 방향키로 플레이어 이동
- 적이 A*로 플레이어를 추적, 인접 시 공격
- 플레이어 이동 → 적 턴 순서의 기본 턴제 동작
- pygame_gui HP 게이지 HUD

## 설계와의 차이점

- `VIEWPORT_W` = 1020 (설계: 900) / `HUD_W` = 260 (설계: 380)
- `Camera` 클래스 없이 `cam_x/cam_y` 변수로 단순 처리
- `TurnManager` 없이 `game.py` 내 상태머신으로 처리
- `enemy.py`에 `take_turn` / `_recalculate_path` 대신 `move_towards` 단일 메서드로 단순화
