from __future__ import annotations

from rich.console import Group, RenderableType
from rich.segment import Segment
from rich.table import Table
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.geometry import Size
from textual.scroll_view import ScrollView
from textual.strip import Strip
from textual.widgets import Footer, Header, Static

from components.enemy import EnemyType
from components.item import ItemType
from components.map import Tile
from game import Game


VIEW_W = 58
VIEW_H = 28
XP_GOAL = 100
TILE_WIDTH = 2
GLYPH_WALL = "  "
GLYPH_FLOOR = "  "
GLYPH_PATH = "  "
GLYPH_STAIRS_UP = "⌂"
GLYPH_STAIRS_DOWN = "⌄"
GLYPH_ATK_ITEM = "♦"
GLYPH_DEF_ITEM = "◆"
GLYPH_HEAL_ITEM = "✚"
GLYPH_RANGE_ITEM = "◇"
GLYPH_DEBUG_PATH = "※"
GLYPH_HIT = "×"
GLYPH_SHOCKWAVE = "✦"


class DungeonView(ScrollView):
    """던전 맵을 터미널 셀 단위로 그리는 렌더러.

    Textual의 render_line()은 한 번에 한 줄만 요청한다.
    거대한 문자열 전체를 매번 다시 만드는 방식보다 TUI 맵 갱신 비용이 낮다.
    """

    can_focus = False
    COMPONENT_CLASSES = {
        "wall",
        "floor",
        "path",
        "stairs",
        "player",
        "player-atk",
        "player-def",
        "player-heal",
        "player-range",
        "player-hit",
        "enemy",
        "enemy-scout",
        "enemy-brute",
        "enemy-hit",
        "hit-cell",
        "shockwave-cell",
        "item-atk",
        "item-def",
        "item-heal",
        "item-range",
        "debug-path",
        "ended",
    }

    DEFAULT_CSS = """
    DungeonView {
        width: 1fr;
        height: 1fr;
        border: solid $accent;
        background: $surface;
    }
    """

    def __init__(self, game: Game):
        super().__init__()
        self.game = game
        self.virtual_size = Size(1, 1)
        self.show_vertical_scrollbar = False
        self.show_horizontal_scrollbar = False
        self.camera_x = 0
        self.camera_y = 0
        self._camera_ready = False

    def render_line(self, y: int) -> Strip:
        if not self._camera_ready:
            self.follow_player()
        visible_width = max(1, self.size.width)
        world_width = max(1, (visible_width + TILE_WIDTH - 1) // TILE_WIDTH)
        world_y = self.camera_y + y
        debug_path = self.game.last_enemy_path if self.game.debug_paths else set()
        segments: list[Segment] = []
        rendered_width = 0

        for x in range(world_width):
            world_x = self.camera_x + x
            char, style_name = self._cell(world_x, world_y, debug_path)
            remaining = visible_width - rendered_width
            if remaining <= 0:
                break
            text = self._tile_text(char, min(TILE_WIDTH, remaining))
            segments.append(Segment(text, self.get_component_rich_style(style_name)))
            rendered_width += len(text)

        return Strip(segments, visible_width)

    def on_resize(self) -> None:
        self.follow_player()
        self.refresh()

    def follow_player(self) -> None:
        if self.size.width <= 0 or self.size.height <= 0:
            return
        px, py = self.game.player_pos
        visible_width = max(1, self.size.width // TILE_WIDTH)
        visible_height = max(1, self.size.height)
        max_x = max(0, self.game.dungeon_map.width - visible_width)
        max_y = max(0, self.game.dungeon_map.height - visible_height)
        target_x = max(0, min(px - visible_width // 2, max_x))
        target_y = max(0, min(py - visible_height // 2, max_y))
        self.camera_x = target_x
        self.camera_y = target_y
        self._camera_ready = True

    def _tile_text(self, char: str, width: int) -> str:
        if width <= 1:
            return char[:1] if char.strip() else " "
        if not char.strip():
            return " " * width
        return f"{char[:1]}{' ' * (width - 1)}"

    def _cell(
        self,
        x: int,
        y: int,
        debug_path: set[tuple[int, int]],
    ) -> tuple[str, str]:
        player = self.game.player
        if player.x == x and player.y == y:
            return "@", self._player_style()

        enemy = self.game.enemy_manager.get_at(x, y)
        if enemy is not None:
            if self._is_combat_position(x, y):
                return enemy.glyph, "enemy-hit"
            if enemy.enemy_type == EnemyType.SCOUT:
                return enemy.glyph, "enemy-scout"
            if enemy.enemy_type == EnemyType.BRUTE:
                return enemy.glyph, "enemy-brute"
            return enemy.glyph, "enemy"

        combat_style = self._combat_cell_style(x, y)
        if combat_style is not None:
            char = GLYPH_SHOCKWAVE if combat_style == "shockwave-cell" else GLYPH_HIT
            return char, combat_style

        item = self.game.item_manager.get_at(x, y)
        if item is not None:
            if item.category == ItemType.ATK.value:
                return GLYPH_ATK_ITEM, "item-atk"
            if item.category == ItemType.DEF.value:
                return GLYPH_DEF_ITEM, "item-def"
            if item.category == ItemType.RANGE.value:
                return GLYPH_RANGE_ITEM, "item-range"
            return GLYPH_HEAL_ITEM, "item-heal"

        if (x, y) in debug_path:
            return GLYPH_DEBUG_PATH, "debug-path"

        tile = self.game.dungeon_map.get_tile(x, y)
        if tile == Tile.WALL:
            return GLYPH_WALL, self._ended_style("wall")
        if tile == Tile.FLOOR:
            return GLYPH_FLOOR, self._ended_style("floor")
        if tile == Tile.PATH:
            return GLYPH_PATH, self._ended_style("path")
        if tile == Tile.STAIRS_UP:
            return GLYPH_STAIRS_UP, self._ended_style("stairs")
        if tile == Tile.STAIRS_DOWN:
            return GLYPH_STAIRS_DOWN, self._ended_style("stairs")
        return GLYPH_FLOOR, self._ended_style("floor")

    def _ended_style(self, style_name: str) -> str:
        if self.game.game_over:
            return "ended"
        return style_name

    def _player_style(self) -> str:
        if self.game.player_hit_effect is not None:
            return "player-hit"
        effect = self.game.item_effect
        if effect is None:
            return "player"
        if effect.category == ItemType.ATK.value:
            return "player-atk"
        if effect.category == ItemType.DEF.value:
            return "player-def"
        if effect.category == ItemType.HEAL.value:
            return "player-heal"
        if effect.category == ItemType.RANGE.value:
            return "player-range"
        return "player"

    def _is_combat_position(self, x: int, y: int) -> bool:
        effect = self.game.combat_effect
        return effect is not None and (x, y) in effect.positions

    def _combat_cell_style(self, x: int, y: int) -> str | None:
        effect = self.game.combat_effect
        if effect is None or (x, y) not in effect.positions:
            return None
        if effect.category == "shockwave":
            return "shockwave-cell"
        return "hit-cell"


class SidePanel(Static):
    DEFAULT_CSS = """
    SidePanel {
        width: 40;
        height: 1fr;
        border: solid $primary;
        padding: 1 1;
    }
    """


class MessagePanel(Static):
    DEFAULT_CSS = """
    MessagePanel {
        height: 10;
        border: solid $secondary;
        padding: 1 2;
    }
    """


class DungeonApp(App[None]):
    CSS = """
    Screen {
        background: #0f1117;
    }

    #main {
        height: 1fr;
    }

    DungeonView > .wall {
        color: #303a44;
        background: #303a44;
    }

    DungeonView > .floor {
        color: #141a20;
        background: #141a20;
    }

    DungeonView > .path {
        color: #201a12;
        background: #201a12;
    }

    DungeonView > .stairs {
        color: #001018;
        background: #7cc7ff;
        text-style: bold;
    }

    DungeonView > .player {
        color: #ffffff;
        background: #0057ff;
        text-style: bold;
    }

    DungeonView > .player-atk {
        color: #111111;
        background: #ff9d00;
        text-style: bold;
    }

    DungeonView > .player-def {
        color: #06130a;
        background: #66ff7a;
        text-style: bold;
    }

    DungeonView > .player-heal {
        color: #001818;
        background: #6fffe9;
        text-style: bold;
    }

    DungeonView > .player-range {
        color: #ffffff;
        background: #7b2cbf;
        text-style: bold;
    }

    DungeonView > .player-hit {
        color: #ffffff;
        background: #d00000;
        text-style: bold reverse;
    }

    DungeonView > .enemy {
        color: #ff1744;
        text-style: bold;
    }

    DungeonView > .enemy-scout {
        color: #ffd600;
        text-style: bold;
    }

    DungeonView > .enemy-brute {
        color: #ffffff;
        background: #b000ff;
        text-style: bold;
    }

    DungeonView > .enemy-hit {
        color: #111111;
        background: #ff4d4d;
        text-style: bold;
    }

    DungeonView > .hit-cell {
        color: #ff4d4d;
        text-style: bold;
    }

    DungeonView > .shockwave-cell {
        color: #111111;
        background: #ffd166;
        text-style: bold;
    }

    DungeonView > .item-atk {
        color: #ff9d6c;
        text-style: bold;
    }

    DungeonView > .item-def {
        color: #a1ff8f;
        text-style: bold;
    }

    DungeonView > .item-heal {
        color: #77e6d8;
        text-style: bold;
    }

    DungeonView > .item-range {
        color: #c77dff;
        text-style: bold;
    }

    DungeonView > .debug-path {
        color: #bb86fc;
        text-style: bold;
    }

    DungeonView > .ended {
        color: #343a46;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "종료"),
        Binding("escape", "quit", "종료"),
        Binding("up", "move('up')", "위로 이동"),
        Binding("w", "move('up')", "위로 이동", show=False),
        Binding("down", "move('down')", "아래로 이동"),
        Binding("s", "move('down')", "아래로 이동", show=False),
        Binding("left", "move('left')", "왼쪽 이동"),
        Binding("a", "move('left')", "왼쪽 이동", show=False),
        Binding("right", "move('right')", "오른쪽 이동"),
        Binding("d", "move('right')", "오른쪽 이동", show=False),
        Binding("z", "area_attack", "주변 공격"),
        Binding("u", "undo", "되감기"),
        Binding("i", "show_inventory", "인벤토리"),
        Binding("l", "show_leaderboard", "리더보드"),
        Binding("?", "show_help", "도움말"),
        Binding("ctrl+d", "toggle_debug", "A* 경로"),
    ]

    def __init__(self):
        super().__init__()
        self.game = Game()
        self.panel_mode = "stats"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            with Horizontal(id="main"):
                yield DungeonView(self.game)
                yield SidePanel(id="side")
            yield MessagePanel(id="messages")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_all()

    def action_move(self, direction: str) -> None:
        if self._block_if_ended():
            return
        directions = {
            "up": (0, -1),
            "down": (0, 1),
            "left": (-1, 0),
            "right": (1, 0),
        }
        dx, dy = directions[direction]
        self.game.move_player(dx, dy)
        self.panel_mode = "inventory" if self.game.last_collected_item is not None else "stats"
        self._refresh_all()

    def action_area_attack(self) -> None:
        if self._block_if_ended():
            return
        self.game.area_attack()
        self.panel_mode = "stats"
        self._refresh_all()

    def action_undo(self) -> None:
        if self._block_if_ended():
            return
        self.game.undo()
        self.panel_mode = "stats"
        self._refresh_all()

    def action_show_inventory(self) -> None:
        self.panel_mode = "inventory"
        self._refresh_all()

    def action_show_leaderboard(self) -> None:
        self.panel_mode = "leaderboard"
        self._refresh_all()

    def action_show_help(self) -> None:
        self.panel_mode = "help"
        self._refresh_all()

    def action_toggle_debug(self) -> None:
        self.game.toggle_debug_paths()
        self.panel_mode = "debug"
        self._refresh_all()

    def on_key(self, event: events.Key) -> None:
        if self.game.game_over:
            return
        if self.panel_mode != "inventory" or not event.key.isdigit():
            return
        self.game.use_inventory_slot(int(event.key) - 1)
        self.panel_mode = "stats"
        self._refresh_all()

    def _refresh_all(self) -> None:
        dungeon_view = self.query_one(DungeonView)
        dungeon_view.virtual_size = Size(1, 1)
        dungeon_view.follow_player()
        dungeon_view.refresh()
        self.query_one("#side", SidePanel).update(self._side_content())
        self.query_one("#messages", MessagePanel).update(self._message_text())

    def _side_content(self) -> RenderableType:
        if self.panel_mode == "inventory":
            return "\n".join(
                [
                    "인벤토리",
                    "",
                    *self.game.inventory.display_lines(),
                    "",
                    "1-9: 선택 아이템 사용",
                    "사용해야 스탯이 바뀝니다.",
                ]
            )
        if self.panel_mode == "leaderboard":
            return self._leaderboard_content()
        if self.panel_mode == "help":
            return "\n".join(
                [
                    "조작법",
                    "",
                    "WASD/방향키  이동",
                    "z            주변 공격",
                    "u            되감기",
                    "i            인벤토리",
                    "l            리더보드",
                    "Ctrl+D       A* 디버그 경로",
                    "q/Esc        종료",
                    "",
                    "범례",
                    "어두운 빈칸  방 바닥",
                    "어두운 길    통로",
                    "어두운 벽    벽",
                    f"{GLYPH_STAIRS_DOWN} 다음 층 계단",
                    f"{GLYPH_ATK_ITEM} 공격  {GLYPH_DEF_ITEM} 방어",
                    f"{GLYPH_HEAL_ITEM} 회복  {GLYPH_RANGE_ITEM} 범위",
                ]
            )
        if self.panel_mode == "debug":
            return self._debug_text()
        return self._stats_content()

    def _leaderboard_content(self) -> RenderableType:
        if not self.game.leaderboard.entries:
            return Text("리더보드\n\n아직 기록이 없습니다.", style="bold")

        title = Text("리더보드\n", style="bold #7cc7ff")
        table = Table.grid(padding=(0, 1))
        table.add_column(justify="right", no_wrap=True)
        table.add_column(no_wrap=True)
        table.add_column(justify="right", no_wrap=True)
        table.add_column(justify="right", no_wrap=True)
        table.add_column(justify="right", no_wrap=True)
        table.add_column(justify="right", no_wrap=True)
        table.add_row(
            Text("#", style="bold #7f8ea3"),
            Text("이름", style="bold #7f8ea3"),
            Text("점수", style="bold #7f8ea3"),
            Text("층", style="bold #7f8ea3"),
            Text("되감기", style="bold #7f8ea3"),
            Text("시간", style="bold #7f8ea3"),
        )

        for rank, entry in enumerate(self.game.leaderboard.entries, start=1):
            style = self._rank_style(rank)
            table.add_row(
                Text(self._rank_label(rank), style=style),
                Text(entry.name, style=style),
                Text(f"{entry.score:,}", style=style),
                Text(str(entry.floors_cleared), style=style),
                Text(str(entry.undo_used), style=style),
                Text(self._format_seconds(entry.time_seconds), style=style),
            )

        hint = Text("\nq/Esc 종료  i 인벤토리", style="#7f8ea3")
        return Group(title, table, hint)

    def _rank_label(self, rank: int) -> str:
        return str(rank)

    def _rank_style(self, rank: int) -> str:
        if rank == 1:
            return "bold #ffd166"
        if rank == 2:
            return "bold #cdd6e0"
        if rank == 3:
            return "bold #ff9d6c"
        return "#e6e8eb"

    def _format_seconds(self, seconds: int) -> str:
        minutes, remain = divmod(max(0, seconds), 60)
        return f"{minutes}:{remain:02d}"

    def _stats_content(self) -> Group:
        status = "승리" if self.game.victory else "게임 오버" if self.game.game_over else "진행 중"
        end_banner = self._end_banner()
        stats = Table.grid(padding=(0, 1))
        stats.add_column(width=8, no_wrap=True)
        stats.add_column(no_wrap=True)
        title = Text("던전 크롤러\n", style="bold")
        stats.add_row("", "", "")
        self._add_stat_row(stats, "상태", status)
        self._add_stat_row(stats, "현재 층", self.game.floor)
        self._add_stat_row(stats, "난이도", self._difficulty_label())
        self._add_stat_row(stats, "방 개수", len(self.game.dungeon_map.rooms))
        self._add_stat_row(stats, "클리어", self.game.floors_cleared)
        self._add_stat_row(stats, "턴", self.game.turn_count)
        stats.add_row("", "", "")
        self._add_stat_row(stats, "목표", f"{GLYPH_STAIRS_DOWN} 계단 도착")
        self._add_stat_row(stats, "방향", self.game.goal_direction)
        self._add_stat_row(stats, "거리", self.game.goal_distance)
        stats.add_row("", "", "")
        self._add_bar_row(stats, "HP", self.game.player.hp, self.game.player.max_hp, "bold red")
        self._add_bar_row(stats, "XP", self.game.player.xp % XP_GOAL, XP_GOAL, "bold cyan", f"{self.game.player.xp}/{XP_GOAL}")
        self._add_stat_row(stats, "공격력", self.game.player.atk, "bold #ff9d00")
        self._add_stat_row(stats, "방어력", self.game.player.def_, "bold #66ff7a")
        self._add_stat_row(stats, "범위", self.game.player.shockwave_radius, "bold #c77dff")
        self._add_stat_row(stats, "충격파", self.game.shockwave_cooldown, "bold #ffd166")
        self._add_bar_row(
            stats,
            "되감기",
            self.game.undo_stack.remaining(),
            self.game.undo_stack.max_size,
            "bold green",
        )
        stats.add_row("", "", "")
        self._add_stat_row(stats, "남은 적", len(self.game.enemy_manager.get_all()))
        self._add_stat_row(stats, "구성", self._enemy_summary())
        self._add_stat_row(stats, "점수", f"{self.game.score:,}")

        legend = Text(f"\n어두운 바닥  어두운 길  어두운 벽  {GLYPH_STAIRS_DOWN} 계단\n? 도움말", style="#7f8ea3")
        renderables: list[RenderableType] = [end_banner, title, stats]
        renderables.extend(self._effect_texts())
        renderables.append(legend)
        return Group(*renderables)

    def _add_stat_row(self, table: Table, label: str, value: object, value_style: str | None = None) -> None:
        table.add_row(Text(label, style="#c7ced8"), Text(str(value), style=value_style or "#e6e8eb"))

    def _add_bar_row(
        self,
        table: Table,
        label: str,
        current: int,
        maximum: int,
        style: str,
        value: str | None = None,
    ) -> None:
        display_value = value or f"{current}/{maximum}"
        table.add_row(Text(label, style="#c7ced8"), Text(display_value, style="#e6e8eb"))
        table.add_row(Text(""), self._bar(current, maximum, style))

    def _effect_texts(self) -> list[Text]:
        texts: list[Text] = []
        player_hit = self._player_hit_effect_text()
        combat = self._combat_effect_text()
        item = self._item_effect_text()
        for text in (player_hit, combat, item):
            if text is not None:
                texts.append(text)
        return texts

    def _combat_effect_text(self) -> Text | None:
        effect = self.game.combat_effect
        if effect is None:
            return None
        if effect.category == "shockwave":
            style = "bold black on #ffd166"
        else:
            style = "bold white on #b00020"
        return Text(f"  {effect.title}  {effect.detail}  \n", style=style)

    def _player_hit_effect_text(self) -> Text | None:
        effect = self.game.player_hit_effect
        if effect is None:
            return None
        return Text(f"  {effect.title}  {effect.detail}  \n", style="bold white on #d00000")

    def _item_effect_text(self) -> Text | None:
        effect = self.game.item_effect
        if effect is None:
            return None
        if effect.category == ItemType.ATK.value:
            style = "bold black on #ff9d00"
        elif effect.category == ItemType.DEF.value:
            style = "bold black on #66ff7a"
        elif effect.category == ItemType.RANGE.value:
            style = "bold white on #7b2cbf"
        else:
            style = "bold black on #6fffe9"
        return Text(f"  {effect.title}  {effect.detail}  \n", style=style)

    def _debug_text(self) -> str:
        graph_edges = sum(len(edges) for edges in self.game.dungeon_map.room_graph.values()) // 2
        return "\n".join(
            [
                "알고리즘 디버그",
                "",
                "맵: 2차원 배열 grid",
                f"방 개수: {len(self.game.dungeon_map.rooms)}",
                f"그래프 간선 수: {graph_edges}",
                "",
                "되감기: 크기 제한 스택",
                f"스냅샷 수: {len(self.game.undo_stack)}",
                "",
                "턴: FIFO 큐",
                "순서: 플레이어 -> 적",
                "",
                "적 AI: A*",
                f"디버그 경로 표시: {self.game.debug_paths}",
                "",
                "적 타입",
                "G: 빨강, 기본형",
                "S: 노랑, 넓은 감지",
                "B: 보라 배경, 높은 체력/공격",
            ]
        )

    def _message_text(self) -> str:
        if self.game.game_over:
            if self.game.victory:
                title = "████ 승리 ████"
                detail = f"최종 점수: {self.game.score}  클리어 층: {self.game.floors_cleared}"
            else:
                title = "████ 게임 오버 ████"
                detail = f"최종 점수: {self.game.score}  생존 턴: {self.game.turn_count}"
            return "\n".join(
                [
                    title,
                    detail,
                    "l: 리더보드 보기   q/Esc: 종료",
                    "",
                    *self.game.messages,
                ]
            )
        return "\n".join(["메시지 로그", "", *self.game.messages])

    def _end_banner(self) -> Text:
        if not self.game.game_over:
            return Text("")
        if self.game.victory:
            return Text("  승리! 던전을 클리어했습니다  \n", style="bold white on green")
        return Text("  게임 오버  \n", style="bold white on red")

    def _block_if_ended(self) -> bool:
        if not self.game.game_over:
            return False
        self.game.log("게임이 끝났습니다. l로 리더보드를 보거나 q로 종료하세요.")
        self._refresh_all()
        return True

    def _difficulty_label(self) -> str:
        if self.game.floor <= 1:
            return "보통"
        if self.game.floor == 2:
            return "위험"
        return "매우 위험"

    def _enemy_summary(self) -> str:
        counts = self.game.enemy_manager.type_counts()
        return f"G {counts[EnemyType.GRUNT]} / S {counts[EnemyType.SCOUT]} / B {counts[EnemyType.BRUTE]}"

    def _bar(self, current: int, maximum: int, style: str, width: int = 10) -> Text:
        bar = Text("")
        if maximum <= 0:
            bar.append("░" * width, style="dim")
            return bar
        filled = max(0, min(width, round(width * current / maximum)))
        bar.append("█" * filled, style=style)
        bar.append("░" * (width - filled), style="dim")
        return bar
