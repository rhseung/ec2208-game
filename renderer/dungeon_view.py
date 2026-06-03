from __future__ import annotations

from rich.segment import Segment
from textual.geometry import Size
from textual.scroll_view import ScrollView
from textual.strip import Strip

from components.enemy import EnemyType
from components.item import ItemType
from components.map import Tile
from game import Game
from renderer import glyphs


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
        world_width = max(1, (visible_width + glyphs.TILE_WIDTH - 1) // glyphs.TILE_WIDTH)
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
            text = self._tile_text(char, min(glyphs.TILE_WIDTH, remaining))
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
        visible_width = max(1, self.size.width // glyphs.TILE_WIDTH)
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
            char = glyphs.SHOCKWAVE if combat_style == "shockwave-cell" else glyphs.HIT
            return char, combat_style

        item = self.game.item_manager.get_at(x, y)
        if item is not None:
            if item.category == ItemType.ATK.value:
                return glyphs.ATK_ITEM, "item-atk"
            if item.category == ItemType.DEF.value:
                return glyphs.DEF_ITEM, "item-def"
            if item.category == ItemType.RANGE.value:
                return glyphs.RANGE_ITEM, "item-range"
            return glyphs.HEAL_ITEM, "item-heal"

        if (x, y) in debug_path:
            return glyphs.DEBUG_PATH, "debug-path"

        tile = self.game.dungeon_map.get_tile(x, y)
        if tile == Tile.WALL:
            return glyphs.WALL, self._ended_style("wall")
        if tile == Tile.FLOOR:
            return glyphs.FLOOR, self._ended_style("floor")
        if tile == Tile.PATH:
            return glyphs.PATH, self._ended_style("path")
        if tile == Tile.STAIRS_UP:
            return glyphs.STAIRS_UP, self._ended_style("stairs")
        if tile == Tile.STAIRS_DOWN:
            return glyphs.STAIRS_DOWN, self._ended_style("stairs")
        return glyphs.FLOOR, self._ended_style("floor")

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
