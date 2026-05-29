import pygame
import pygame_gui
from components.map import DungeonMap
from components.player import Player
from components.enemy import EnemyManager
from components.item import ItemManager, ItemType
from renderer.sprites import Tileset
from renderer import tilemap

SCREEN_W, SCREEN_H = 1280, 720
VIEWPORT_W = 1020
HUD_X = VIEWPORT_W  # 1020
HUD_W = 260  # SCREEN_W - HUD_X
TILE_SIZE = 32
FPS = 60

OVERWORLD_PNG = "assets/sprites/overworld.png"
PLAYER_COLOR = (220, 200, 60)
ENEMY_COLOR = (200, 50, 50)
ATK_ITEM_COLOR = (255, 50, 50)   # Red
DEF_ITEM_COLOR = (255, 255, 50) # Yellow

WATER_ANIM_FPS = 4  # 초당 몇 번 파도 위상이 진행되는지 (4 = 0.25s 마다 한 칸)

KEY_TO_DIR: dict[int, tuple[int, int]] = {
    pygame.K_UP: (0, -1),
    pygame.K_w: (0, -1),
    pygame.K_DOWN: (0, 1),
    pygame.K_s: (0, 1),
    pygame.K_LEFT: (-1, 0),
    pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1, 0),
    pygame.K_d: (1, 0),
}


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Dungeon Crawler — Undo is Power")
        self.clock = pygame.time.Clock()
        self.ui_manager = pygame_gui.UIManager((SCREEN_W, SCREEN_H))
        self.running = True

        # 스프라이트 시트 로딩 (display 초기화 이후에 호출해야 함)
        self.tileset = Tileset(OVERWORLD_PNG, scale=TILE_SIZE // 16)

        self.dungeon_map = DungeonMap(80, 50)
        self.dungeon_map.generate()

        # 플레이어를 첫 번째 방 중심에 배치
        sx, sy = self.dungeon_map.rooms[0].center()
        self.player = Player(x=sx, y=sy)

        self.enemy_manager = EnemyManager()
        self.enemy_manager.spawn(self.dungeon_map)

        self.item_manager = ItemManager()

        self.cam_x = 0
        self.cam_y = 0
        self._center_camera()

        self._build_hud()

        self.state = "PLAYER_TURN"
        self.turn_delay_timer = 0.0
        self.TURN_TRANSITION_DELAY = 0.3

        # 물 애니메이션용 — 누적 시간 → 정수 프레임 인덱스로 환산
        self.water_time = 0.0
        self.water_frame = 0

    def _build_hud(self) -> None:
        pad = 12
        label_h = 24
        bar_h = 22
        panel_h = 200

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

        self.atk_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(pad, pad + label_h + 4 + bar_h + pad, inner_w, label_h),
            text=f"ATK: {self.player.atk}",
            manager=self.ui_manager,
            container=self.hud_panel,
        )

        self.def_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(pad, pad + label_h + 4 + bar_h + pad + label_h + 4, inner_w, label_h),
            text=f"DEF: {self.player.def_}",
            manager=self.ui_manager,
            container=self.hud_panel,
        )

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

                if self.state == "PLAYER_TURN":
                    if event.key == pygame.K_z:
                        # Z key
                        self.player.area_attack(self.enemy_manager.get_all())
                        self.state = "ENEMY_TURN"
                        self.turn_delay_timer = self.TURN_TRANSITION_DELAY
                    else:
                        direction = KEY_TO_DIR.get(event.key)
                        if direction:
                            dx, dy = direction
                            nx, ny = self.player.x + dx, self.player.y + dy
                            
                            target_enemy = self.enemy_manager.get_at(nx, ny)
                            if target_enemy:
                                target_enemy.attack(self.player)
                                self.state = "ENEMY_TURN"
                                self.turn_delay_timer = self.TURN_TRANSITION_DELAY
                            elif self.player.move(dx, dy, self.dungeon_map):
                                self._center_camera()

                                item = self.item_manager.get_at(self.player.x, self.player.y)
                                if item:
                                    if item.item_type == ItemType.ATK_UP:
                                        self.player.atk += 1
                                    elif item.item_type == ItemType.DEF_UP:
                                        self.player.def_ += 1
                                    self.item_manager.remove(item)
                                
                                self.state = "ENEMY_TURN"
                                self.turn_delay_timer = self.TURN_TRANSITION_DELAY

            self.ui_manager.process_events(event)

    def _update(self, dt: float) -> None:
        if self.state == "ENEMY_TURN":
            self.turn_delay_timer -= dt
            if self.turn_delay_timer <= 0:
                self.enemy_manager.remove_dead(self.item_manager)
                self.enemy_manager.update_enemies(self.player, self.dungeon_map)
                self.state = "PLAYER_TURN"

        # 물 애니메이션 위상 갱신
        self.water_time += dt
        self.water_frame = int(self.water_time * WATER_ANIM_FPS)

        # HUD 갱신
        self.hp_bar.percent_full = self.player.hp_ratio
        self.atk_label.set_text(f"ATK: {self.player.atk}")
        self.def_label.set_text(f"DEF: {self.player.def_}")
        
        self.ui_manager.update(dt)

    def _draw(self) -> None:
        self.screen.fill((0, 0, 0))
        self._draw_map()
        self._draw_items()
        self._draw_enemies()
        self._draw_player()
        self.ui_manager.draw_ui(self.screen)
        pygame.display.flip()

    def _draw_map(self) -> None:
        tiles_x = SCREEN_W // TILE_SIZE + 2
        tiles_y = SCREEN_H // TILE_SIZE + 2
        sub = TILE_SIZE // 2  # 한 사분면의 화면 픽셀 크기 (16)
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                wx, wy = self.cam_x + tx, self.cam_y + ty
                px, py = tx * TILE_SIZE, ty * TILE_SIZE

                plain = tilemap.plain_tile_for(
                    self.dungeon_map, wx, wy, self.water_frame
                )
                if plain is not None:
                    self.screen.blit(self.tileset.get(*plain), (px, py))
                    continue

                # 잔디(FLOOR/PATH) — corner-decomp 4-sub-blit
                for cqx, cqy, sc, sr, sqx, sqy in tilemap.grass_subtiles(
                    self.dungeon_map, wx, wy
                ):
                    self.screen.blit(
                        self.tileset.get_subtile(sc, sr, sqx, sqy),
                        (px + cqx * sub, py + cqy * sub),
                    )

    def _draw_player(self) -> None:
        sx = (self.player.x - self.cam_x) * TILE_SIZE
        sy = (self.player.y - self.cam_y) * TILE_SIZE
        pygame.draw.rect(
            self.screen, PLAYER_COLOR, pygame.Rect(sx, sy, TILE_SIZE, TILE_SIZE)
        )

    def _draw_enemies(self) -> None:
        for enemy in self.enemy_manager.get_all():
            sx = (enemy.x - self.cam_x) * TILE_SIZE
            sy = (enemy.y - self.cam_y) * TILE_SIZE

            color = (100, 100, 100) if enemy.stunned else ENEMY_COLOR
            pygame.draw.rect(
                self.screen, color, pygame.Rect(sx, sy, TILE_SIZE, TILE_SIZE)
            )

    def _draw_items(self) -> None:
        for item in self.item_manager.get_all():
            sx = (item.x - self.cam_x) * TILE_SIZE + TILE_SIZE // 2
            sy = (item.y - self.cam_y) * TILE_SIZE + TILE_SIZE // 2
            color = ATK_ITEM_COLOR if item.item_type == ItemType.ATK_UP else DEF_ITEM_COLOR
            pygame.draw.circle(self.screen, color, (sx, sy), TILE_SIZE // 4)
