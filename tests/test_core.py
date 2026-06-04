import tempfile
import unittest
from pathlib import Path

from algorithms.pathfinding import astar
from components.enemy import DETECTION_RANGES, Enemy, EnemyType, _make_enemy
from components.inventory import Inventory
from components.item import Item, ItemType
from components.leaderboard import Leaderboard, ScoreEntry
from components.map import DungeonMap, Tile
from components.turn import TurnManager
from components.undo import UndoStack
from game import Game, PLAYER_ACTOR, ENEMY_ACTOR


class CoreFeatureTests(unittest.TestCase):
    def test_map_generation_creates_rooms_and_walkable_stairs(self) -> None:
        dungeon = DungeonMap(50, 35)
        dungeon.generate()

        self.assertGreaterEqual(len(dungeon.rooms), 2)
        start = dungeon.rooms[0].center()
        end = dungeon.rooms[-1].center()
        self.assertTrue(dungeon.is_walkable(*start))
        self.assertTrue(dungeon.is_walkable(*end))
        self.assertIn(0, dungeon.room_graph)

    def test_astar_returns_walkable_path(self) -> None:
        dungeon = DungeonMap(50, 35)
        dungeon.generate()
        start = dungeon.rooms[0].center()
        goal = dungeon.rooms[-1].center()

        path = astar(dungeon, start, goal)

        self.assertTrue(path)
        self.assertEqual(path[-1], goal)
        self.assertTrue(all(dungeon.is_walkable(x, y) for x, y in path))

    def test_turn_manager_rotates_fifo(self) -> None:
        turns = TurnManager()
        turns.reset([PLAYER_ACTOR, ENEMY_ACTOR])

        self.assertEqual(turns.current(), PLAYER_ACTOR)
        self.assertEqual(turns.advance(), ENEMY_ACTOR)
        self.assertEqual(turns.advance(), PLAYER_ACTOR)

    def test_inventory_uses_linked_list_by_category(self) -> None:
        inventory = Inventory()
        item = Item("item-1", "공격 부적", ItemType.ATK.value, 1, -1, -1)

        inventory.add(item)

        found = inventory.find("item-1")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "공격 부적")

        used = inventory.use("item-1")
        self.assertIsNotNone(used)
        self.assertEqual(used.category, ItemType.ATK.value)
        self.assertIsNone(inventory.find("item-1"))

    def test_inventory_displays_same_items_as_stacks(self) -> None:
        inventory = Inventory()
        inventory.add(Item("item-1", "공격 부적", ItemType.ATK.value, 2, -1, -1))
        inventory.add(Item("item-2", "공격 부적", ItemType.ATK.value, 2, -1, -1))
        inventory.add(Item("item-3", "회복 약초", ItemType.HEAL.value, 12, -1, -1))

        stacks = inventory.stack_entries()

        self.assertEqual(len(stacks), 2)
        self.assertEqual(stacks[0].item.name, "공격 부적")
        self.assertEqual(stacks[0].count, 2)
        self.assertIn("공격 부적 x2", inventory.display_lines()[0])

    def test_item_values_are_noticeable(self) -> None:
        manager = Game(seed=1).item_manager

        atk_item = manager.spawn(0, 0, ItemType.ATK)
        def_item = manager.spawn(0, 0, ItemType.DEF)
        heal_item = manager.spawn(0, 0, ItemType.HEAL)
        range_item = manager.spawn(0, 0, ItemType.RANGE)

        self.assertEqual(atk_item.value, 2)
        self.assertEqual(def_item.value, 2)
        self.assertEqual(heal_item.value, 12)
        self.assertEqual(range_item.value, 1)

    def test_using_item_sets_visible_effect_and_changes_stat(self) -> None:
        game = Game(seed=1)
        item = Item("item-test", "공격 부적", ItemType.ATK.value, 2, -1, -1)
        game.inventory.add(item)
        before_atk = game.player.atk

        self.assertTrue(game.use_inventory_slot(0))
        self.assertEqual(game.player.atk, before_atk + 2)
        self.assertIsNotNone(game.item_effect)
        self.assertEqual(game.item_effect.category, ItemType.ATK.value)

    def test_collecting_item_opens_use_flow_without_changing_stat(self) -> None:
        game = Game(seed=1)
        dx, dy = next(
            (dx, dy)
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))
            if game.dungeon_map.is_walkable(game.player.x + dx, game.player.y + dy)
        )
        item = Item("item-pickup", "공격 부적", ItemType.ATK.value, 2, game.player.x + dx, game.player.y + dy)
        game.item_manager.set_all([item])
        before_atk = game.player.atk

        self.assertTrue(game.move_player(dx, dy))
        self.assertEqual(game.player.atk, before_atk)
        self.assertIsNotNone(game.last_collected_item)
        self.assertIsNotNone(game.inventory.find("item-pickup"))

    def test_using_stacked_items_consumes_one_and_stacks_stat_effect(self) -> None:
        game = Game(seed=1)
        game.inventory.add(Item("item-1", "공격 부적", ItemType.ATK.value, 2, -1, -1))
        game.inventory.add(Item("item-2", "공격 부적", ItemType.ATK.value, 2, -1, -1))
        before_atk = game.player.atk

        self.assertTrue(game.use_inventory_slot(0))
        self.assertEqual(game.player.atk, before_atk + 2)
        self.assertEqual(game.inventory.stack_entries()[0].count, 1)

        self.assertTrue(game.use_inventory_slot(0))
        self.assertEqual(game.player.atk, before_atk + 4)
        self.assertEqual(game.inventory.stack_entries(), [])

    def test_using_item_does_not_spend_turn_or_trigger_counterattack(self) -> None:
        game = Game(seed=1)
        dx, dy = next(
            (dx, dy)
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))
            if game.dungeon_map.is_walkable(game.player.x + dx, game.player.y + dy)
        )
        game.enemy_manager.set_all([Enemy(game.player.x + dx, game.player.y + dy, hp=20, max_hp=20, atk=3)])
        game.inventory.add(Item("item-test", "방어 부적", ItemType.DEF.value, 2, -1, -1))
        before_hp = game.player.hp
        before_turn = game.turn_count

        self.assertTrue(game.use_inventory_slot(0))
        self.assertEqual(game.turn_count, before_turn)
        self.assertEqual(game.player.hp, before_hp)
        self.assertIsNone(game.player_hit_effect)

    def test_range_item_expands_shockwave_radius_and_undo_restores_it(self) -> None:
        game = Game(seed=1)
        game.inventory.add(Item("item-range", "확산 수정", ItemType.RANGE.value, 1, -1, -1))

        self.assertTrue(game.use_inventory_slot(0))
        self.assertEqual(game.player.shockwave_radius, 2)
        self.assertIsNotNone(game.item_effect)
        self.assertEqual(game.item_effect.category, ItemType.RANGE.value)

        self.assertTrue(game.undo())
        self.assertEqual(game.player.shockwave_radius, 1)

    def test_expanded_shockwave_hits_farther_enemy(self) -> None:
        game = Game(seed=1)
        target = (game.player.x + 2, game.player.y)
        game.enemy_manager.set_all([Enemy(target[0], target[1], hp=20, max_hp=20, atk=0)])

        self.assertTrue(game.area_attack())
        self.assertIsNotNone(game.combat_effect)
        self.assertNotIn(target, game.combat_effect.positions)
        self.assertEqual(game.enemy_manager.get_all()[0].hp, 20)

        game.undo()
        game.inventory.add(Item("item-range", "확산 수정", ItemType.RANGE.value, 1, -1, -1))
        self.assertTrue(game.use_inventory_slot(0))
        self.assertTrue(game.area_attack())
        self.assertIsNotNone(game.combat_effect)
        self.assertIn(target, game.combat_effect.positions)

    def test_shockwave_range_uses_diamond_shape(self) -> None:
        game = Game(seed=1)
        game.inventory.add(Item("item-range", "확산 수정", ItemType.RANGE.value, 1, -1, -1))
        self.assertTrue(game.use_inventory_slot(0))

        straight_target = (game.player.x + 2, game.player.y)
        diagonal_target = (game.player.x + 2, game.player.y + 2)
        game.enemy_manager.set_all(
            [
                Enemy(straight_target[0], straight_target[1], hp=20, max_hp=20, atk=0),
                Enemy(diagonal_target[0], diagonal_target[1], hp=20, max_hp=20, atk=0),
            ]
        )

        self.assertTrue(game.area_attack())
        self.assertIsNotNone(game.combat_effect)
        self.assertIn(straight_target, game.combat_effect.positions)
        self.assertNotIn(diagonal_target, game.combat_effect.positions)

    def test_shockwave_is_blocked_by_walls(self) -> None:
        game = Game(seed=1)
        game.player.x = 5
        game.player.y = 5
        game.player.shockwave_radius = 2
        for y in range(game.dungeon_map.height):
            for x in range(game.dungeon_map.width):
                game.dungeon_map.set_tile(x, y, Tile.WALL)

        game.dungeon_map.set_tile(5, 5, Tile.FLOOR)
        game.dungeon_map.set_tile(7, 5, Tile.FLOOR)
        target = (7, 5)
        game.enemy_manager.set_all([Enemy(target[0], target[1], hp=20, max_hp=20, atk=0)])

        self.assertTrue(game.area_attack())
        self.assertIsNotNone(game.combat_effect)
        self.assertNotIn(target, game.combat_effect.positions)
        self.assertEqual(game.enemy_manager.get_all()[0].hp, 20)

    def test_full_hp_heal_item_is_not_consumed(self) -> None:
        game = Game(seed=1)
        item = Item("item-heal", "회복 약초", ItemType.HEAL.value, 12, -1, -1)
        game.inventory.add(item)

        self.assertFalse(game.use_inventory_slot(0))
        self.assertIsNotNone(game.inventory.find("item-heal"))
        self.assertIsNone(game.item_effect)

    def test_undo_restores_player_position(self) -> None:
        game = Game(seed=1)
        original = game.player_pos
        direction = next(
            (dx, dy)
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))
            if game.dungeon_map.is_walkable(game.player.x + dx, game.player.y + dy)
        )

        moved = game.move_player(*direction)
        undone = game.undo()

        self.assertTrue(moved)
        self.assertTrue(undone)
        self.assertEqual(game.player_pos, original)
        self.assertIsInstance(game.undo_stack, UndoStack)

    def test_leaderboard_sorts_and_caps_top_ten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            board = Leaderboard(Path(tmp) / "leaderboard.json")
            for score in range(12):
                board.add(ScoreEntry("P", score, 1, 0, 0))

            self.assertEqual(len(board.entries), 10)
            self.assertEqual(board.entries[0].score, 11)
            self.assertEqual(board.entries[-1].score, 2)

    def test_engine_smoke_move_enemy_turn_and_score(self) -> None:
        game = Game(seed=2)
        direction = next(
            (dx, dy)
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))
            if game.dungeon_map.is_walkable(game.player.x + dx, game.player.y + dy)
        )

        self.assertTrue(game.move_player(*direction))
        self.assertGreaterEqual(game.turn_count, 1)
        self.assertGreater(game.score, 0)

    def test_first_floor_combat_balance_is_forgiving(self) -> None:
        game = Game(seed=1)
        grunt = _make_enemy(0, 0, floor=1, spawn_index=0)

        self.assertEqual(game.player.hp, 36)
        self.assertEqual(grunt.enemy_type, EnemyType.GRUNT)
        self.assertLessEqual(grunt.max_hp, game.player.atk * 2)
        self.assertLessEqual(grunt.atk, 3)

    def test_melee_attack_sets_visible_combat_effect(self) -> None:
        game = Game(seed=1)
        dx, dy = next(
            (dx, dy)
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))
            if game.dungeon_map.is_walkable(game.player.x + dx, game.player.y + dy)
        )
        target = (game.player.x + dx, game.player.y + dy)
        game.enemy_manager.set_all([Enemy(target[0], target[1], hp=20, max_hp=20, atk=0)])

        self.assertTrue(game.move_player(dx, dy))
        self.assertIsNotNone(game.combat_effect)
        self.assertEqual(game.combat_effect.category, "melee")
        self.assertEqual(game.combat_effect.positions, (target,))

    def test_shockwave_sets_visible_combat_effect(self) -> None:
        game = Game(seed=1)
        dx, dy = next(
            (dx, dy)
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))
            if game.dungeon_map.is_walkable(game.player.x + dx, game.player.y + dy)
        )
        target = (game.player.x + dx, game.player.y + dy)
        game.enemy_manager.set_all([Enemy(target[0], target[1], hp=20, max_hp=20, atk=0)])

        self.assertTrue(game.area_attack())
        self.assertIsNotNone(game.combat_effect)
        self.assertEqual(game.combat_effect.category, "shockwave")
        self.assertIn(target, game.combat_effect.positions)

    def test_enemy_counterattack_sets_player_hit_effect(self) -> None:
        game = Game(seed=1)
        dx, dy = next(
            (dx, dy)
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))
            if game.dungeon_map.is_walkable(game.player.x + dx, game.player.y + dy)
        )
        target = (game.player.x + dx, game.player.y + dy)
        game.enemy_manager.set_all([Enemy(target[0], target[1], hp=20, max_hp=20, atk=3)])
        before_hp = game.player.hp

        self.assertTrue(game.move_player(dx, dy))
        self.assertLess(game.player.hp, before_hp)
        self.assertIsNotNone(game.player_hit_effect)
        self.assertEqual(game.player_hit_effect.category, "player-hit")
        self.assertEqual(game.player_hit_effect.positions, (game.player_pos,))

    def test_enemy_types_exist_and_survive_undo(self) -> None:
        game = Game(seed=4)
        before = [enemy.enemy_type for enemy in game.enemy_manager.get_all()]
        direction = next(
            (dx, dy)
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))
            if game.dungeon_map.is_walkable(game.player.x + dx, game.player.y + dy)
        )

        game.move_player(*direction)
        game.undo()
        after = [enemy.enemy_type for enemy in game.enemy_manager.get_all()]

        self.assertTrue(set(before).issubset(set(EnemyType)))
        self.assertEqual(before, after)

    def test_enemy_detection_range_stays_local_on_first_floor(self) -> None:
        game = Game(seed=4)

        for enemy in game.enemy_manager.get_all():
            expected = DETECTION_RANGES[enemy.enemy_type] + game.floor
            self.assertEqual(enemy.detection_range, expected)
            self.assertLessEqual(enemy.detection_range, 11)

    def test_shockwave_has_cooldown_and_does_not_stun_lock(self) -> None:
        game = Game(seed=0)
        direction = next(
            (dx, dy)
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))
            if game.dungeon_map.is_walkable(game.player.x + dx, game.player.y + dy)
        )

        self.assertTrue(game.area_attack())
        self.assertEqual(game.shockwave_cooldown, 1)
        self.assertFalse(game.area_attack())
        self.assertTrue(game.move_player(*direction))
        self.assertEqual(game.shockwave_cooldown, 0)
        self.assertTrue(game.area_attack())
        self.assertTrue(all(not enemy.stunned for enemy in game.enemy_manager.get_all()))

    def test_ended_game_freezes_score_and_blocks_gameplay_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game = Game(seed=1)
            game.leaderboard = Leaderboard(Path(tmp) / "leaderboard.json")
            game.inventory.add(Item("item-atk", "공격 부적", ItemType.ATK.value, 2, -1, -1))
            direction = next(
                (dx, dy)
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))
                if game.dungeon_map.is_walkable(game.player.x + dx, game.player.y + dy)
            )
            self.assertTrue(game.move_player(*direction))

            before_position = game.player_pos
            before_attack = game.player.atk
            before_undo_remaining = game.undo_stack.remaining()
            game._end_game(victory=False, message="테스트 종료")
            final_score = game.score
            final_elapsed = game.elapsed_seconds

            game.started_at -= 9999
            self.assertEqual(game.score, final_score)
            self.assertEqual(game.elapsed_seconds, final_elapsed)
            self.assertFalse(game.undo())
            self.assertFalse(game.use_inventory_slot(0))
            self.assertFalse(game.move_player(*direction))
            self.assertFalse(game.area_attack())
            self.assertEqual(game.player_pos, before_position)
            self.assertEqual(game.player.atk, before_attack)
            self.assertEqual(game.undo_stack.remaining(), before_undo_remaining)


if __name__ == "__main__":
    unittest.main()
