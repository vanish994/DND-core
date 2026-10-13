"""Testes do tabuleiro tático discreto."""
import unittest

from dungeon_game.combat_board import BoardPosition, CombatBoard


class CombatBoardTests(unittest.TestCase):
    def test_distance_uses_existing_rule_engine_grid_convention(self):
        board = CombatBoard(8, 8)
        self.assertEqual(board.distance_feet(BoardPosition(1, 1), BoardPosition(4, 3)), 15)

    def test_movement_respects_budget_walls_and_occupied_tiles(self):
        wall = frozenset({BoardPosition(2, 1), BoardPosition(2, 2), BoardPosition(2, 3)})
        board = CombatBoard(6, 5, blocked=wall)
        start = BoardPosition(1, 2)
        occupied = {BoardPosition(1, 3)}
        reachable = board.reachable_positions(start, 10, occupied=occupied)
        self.assertNotIn(BoardPosition(1, 3), reachable)
        self.assertNotIn(BoardPosition(3, 2), reachable)
        self.assertTrue(all(cost <= 10 for cost in reachable.values()))

    def test_shortest_path_avoids_blocked_cells(self):
        board = CombatBoard(5, 5, blocked=frozenset({BoardPosition(2, 2)}))
        path = board.shortest_path(BoardPosition(1, 2), BoardPosition(3, 2))
        self.assertIsNotNone(path)
        self.assertEqual(path[0], BoardPosition(1, 2))
        self.assertEqual(path[-1], BoardPosition(3, 2))
        self.assertNotIn(BoardPosition(2, 2), path)

    def test_invalid_start_and_out_of_bounds_obstacles_are_rejected(self):
        with self.assertRaises(ValueError):
            CombatBoard(4, 4, blocked=frozenset({BoardPosition(9, 9)}))
        board = CombatBoard(4, 4, blocked=frozenset({BoardPosition(1, 1)}))
        with self.assertRaises(ValueError):
            board.reachable_positions(BoardPosition(1, 1), 30)


if __name__ == "__main__":
    unittest.main()
