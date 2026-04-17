import pygame
import pygame_gui
from components.map import DungeonMap, Tile
from components.player import Player

SCREEN_W, SCREEN_H = 1280, 720
VIEWPORT_W = 1020
HUD_X = VIEWPORT_W  # 1020
HUD_W = 260          # SCREEN_W - HUD_X
TILE_SIZE = 32
FPS = 60

TILE_COLORS: dict[str, tuple[int, int, int]] = {
    Tile.WALL:        (25, 25, 40),
    Tile.FLOOR:       (75, 70, 60),
    Tile.DOOR:        (140, 100, 55),
    Tile.STAIRS_UP:   (80, 200, 120),
    Tile.STAIRS_DOWN: (200, 80, 80),
}
WALL_BORDER  = (15, 15, 25)
PLAYER_COLOR = (220, 200, 60)

KEY_TO_DIR: dict[int, tuple[int, int]] = {
    pygame.K_UP:    (0, -1), pygame.K_w: (0, -1),
    pygame.K_DOWN:  (0,  1), pygame.K_s: (0,  1),
    pygame.K_LEFT:  (-1, 0), pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1,  0), pygame.K_d: (1,  0),
}


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Dungeon Crawler — Undo is Power")
        self.clock = pygame.time.Clock()
        self.ui_manager = pygame_gui.UIManager((SCREEN_W, SCREEN_H))
        self.running = True

        self.dungeon_map = DungeonMap(80, 50)
        self.dungeon_map.generate()

        # 플레이어를 첫 번째 방 중심에 배치
        sx, sy = self.dungeon_map.rooms[0].center()
        self.player = Player(x=sx, y=sy)

        self.cam_x = 0
        self.cam_y = 0
        self._center_camera()

        self._build_hud()

    def _build_hud(self) -> None:
        pad = 12
        label_h = 18
        bar_h = 22
        panel_h = pad + label_h + 4 + bar_h + pad  # 68px

        self.hud_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(SCREEN_W - HUD_W - pad, pad, HUD_W, panel_h),
            manager=self.ui_manager,
            margins={"top": 0, "bottom": 0, "left": 0, "right": 0},
        )
        inner_w = HUD_W - pad * 2
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(pad, pad, inner_w, label_h),
            text="HP",
            manager=self.ui_manager,
            container=self.hud_panel,
        )
        self.hp_bar = pygame_gui.elements.UIStatusBar(
            relative_rect=pygame.Rect(pad, pad + label_h + 4, inner_w, bar_h),
            manager=self.ui_manager,
            container=self.hud_panel,
        )
        self.hp_bar.percent_full = self.player.hp_ratio

    def _center_camera(self) -> None:
        self.cam_x = self.player.x - (VIEWPORT_W // TILE_SIZE) // 2
        self.cam_y = self.player.y - (SCREEN_H // TILE_SIZE) // 2

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                direction = KEY_TO_DIR.get(event.key)
                if direction:
                    self.player.move(*direction, self.dungeon_map)
                    self._center_camera()
            self.ui_manager.process_events(event)

    def _update(self, dt: float) -> None:
        self.hp_bar.percent_full = self.player.hp_ratio
        self.ui_manager.update(dt)

    def _draw(self) -> None:
        self.screen.fill((0, 0, 0))
        self._draw_map()
        self._draw_player()
        self.ui_manager.draw_ui(self.screen)
        pygame.display.flip()

    def _draw_map(self) -> None:
        tiles_x = SCREEN_W // TILE_SIZE + 2
        tiles_y = SCREEN_H // TILE_SIZE + 2
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                wx, wy = self.cam_x + tx, self.cam_y + ty
                tile = self.dungeon_map.get_tile(wx, wy)
                color = TILE_COLORS.get(tile, (0, 0, 0))
                rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(self.screen, color, rect)
                if tile == Tile.WALL:
                    pygame.draw.rect(self.screen, WALL_BORDER, rect, 1)

    def _draw_player(self) -> None:
        sx = (self.player.x - self.cam_x) * TILE_SIZE
        sy = (self.player.y - self.cam_y) * TILE_SIZE
        pygame.draw.rect(self.screen, PLAYER_COLOR, pygame.Rect(sx, sy, TILE_SIZE, TILE_SIZE))
