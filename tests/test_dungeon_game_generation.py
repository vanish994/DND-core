"""Testes do primeiro incremento do crawler: geometria procedural isolada."""

import unittest
from collections import deque

from dungeon_game import DungeonGenerator, RoomKind


class DungeonGenerationTests(unittest.TestCase):
    def setUp(self):
        self.generator = DungeonGenerator()

    def test_same_seed_generates_same_floor(self):
        first = self.generator.generate(floor_number=2, seed=12345)
        second = self.generator.generate(floor_number=2, seed=12345)
        self.assertEqual(first, second)

    def test_different_seed_changes_floor(self):
        first = self.generator.generate(floor_number=2, seed=12345)
        second = self.generator.generate(floor_number=2, seed=54321)
        self.assertNotEqual(first.tiles, second.tiles)

    def test_floor_has_start_exit_and_valid_rooms(self):
        floor = self.generator.generate(floor_number=1, seed=42)
        self.assertGreaterEqual(len(floor.rooms), 6)
        self.assertEqual(floor.room(floor.start_room_id).kind, RoomKind.START)
        self.assertEqual(floor.room(floor.exit_room_id).kind, RoomKind.STAIRS)
        for room in floor.rooms:
            self.assertGreater(room.width, 0)
            self.assertGreater(room.height, 0)
            self.assertGreaterEqual(room.x, 0)
            self.assertGreaterEqual(room.y, 0)
            self.assertLess(room.x + room.width, floor.width)
            self.assertLess(room.y + room.height, floor.height)

    def test_all_rooms_are_reachable_on_walkable_tiles(self):
        floor = self.generator.generate(floor_number=3, seed=987)
        start = floor.room(floor.start_room_id).center
        seen = {start}
        queue = deque([start])
        while queue:
            x, y = queue.popleft()
            for point in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                px, py = point
                if not (0 <= px < floor.width and 0 <= py < floor.height):
                    continue
                if point in seen or floor.tile_at(px, py) != DungeonGenerator.FLOOR:
                    continue
                seen.add(point)
                queue.append(point)
        for room in floor.rooms:
            self.assertIn(room.center, seen, f"Sala inacessível: {room.id}")

    def test_every_fifth_floor_has_boss_room(self):
        floor = self.generator.generate(floor_number=5, seed=101)
        self.assertEqual(sum(room.kind == RoomKind.BOSS for room in floor.rooms), 1)

    def test_invalid_floor_number_is_rejected(self):
        with self.assertRaises(ValueError):
            self.generator.generate(floor_number=0, seed=1)


if __name__ == "__main__":
    unittest.main()
