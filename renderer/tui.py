from __future__ import annotations

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.geometry import Size
from textual.widgets import Footer, Header

from game import Game
from renderer.content import message_text, side_content
from renderer.dungeon_view import DungeonView
from renderer.panels import MessagePanel, SidePanel
from renderer.theme import APP_CSS


DIRECTIONS = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}


class DungeonApp(App[None]):
    CSS = APP_CSS

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
        dx, dy = DIRECTIONS[direction]
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
        if self._block_if_ended():
            return
        self.panel_mode = "inventory"
        self._refresh_all()

    def action_show_leaderboard(self) -> None:
        self.panel_mode = "leaderboard"
        self._refresh_all()

    def action_show_help(self) -> None:
        if self._block_if_ended():
            return
        self.panel_mode = "help"
        self._refresh_all()

    def action_toggle_debug(self) -> None:
        if self._block_if_ended():
            return
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
        self.query_one("#side", SidePanel).update(side_content(self.game, self.panel_mode))
        self.query_one("#messages", MessagePanel).update(message_text(self.game))

    def _block_if_ended(self) -> bool:
        if not self.game.game_over:
            return False
        self.game.log("게임이 끝났습니다. l로 리더보드를 보거나 q로 종료하세요.")
        self._refresh_all()
        return True
