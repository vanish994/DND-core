"""Testes unitários do tabuleiro tático, sem depender de regras de D&D."""
import unittest

from dungeon_game.combat_board import BoardPosition, CombatBoard
from dungeon_game.rule_adapter import DungeonRuleAdapter


class CombatBoardTests(unittest.TestCase):
    def test_distance_uses_explicit_rule_adapter(self):
        board = DungeonRuleAdapter.create_combat_board(8, 8)
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

    def test_diagonal_cannot_cut_between_two_blocked_cells(self):
        board = CombatBoard(3, 3, blocked=frozenset({BoardPosition(1, 0), BoardPosition(0, 1)}))
        self.assertNotIn(BoardPosition(1, 1), board.reachable_positions(BoardPosition(0, 0), 5))
        self.assertIsNone(board.shortest_path(BoardPosition(0, 0), BoardPosition(1, 1)))

    def test_occupied_target_is_not_a_valid_path_destination(self):
        board = CombatBoard(4, 4)
        self.assertIsNone(
            board.shortest_path(
                BoardPosition(0, 0),
                BoardPosition(2, 2),
                occupied={BoardPosition(2, 2)},
            )
        )

    def test_invalid_start_and_out_of_bounds_obstacles_are_rejected(self):
        with self.assertRaises(ValueError):
            CombatBoard(4, 4, blocked=frozenset({BoardPosition(9, 9)}))
        with self.assertRaises(ValueError):
            CombatBoard(4, 4, vision_blocked=frozenset({BoardPosition(9, 9)}))
        board = CombatBoard(4, 4, blocked=frozenset({BoardPosition(1, 1)}))
        with self.assertRaises(ValueError):
            board.reachable_positions(BoardPosition(1, 1), 30)

    def test_line_of_sight_and_cover_obstacles(self):
        wall = frozenset({BoardPosition(2, 2)})
        pillar = frozenset({BoardPosition(2, 1)})
        board = CombatBoard(5, 5, blocked=wall | pillar, vision_blocked=wall)
        self.assertFalse(board.has_line_of_sight(BoardPosition(0, 2), BoardPosition(4, 2)))
        self.assertTrue(board.has_line_of_sight(BoardPosition(0, 1), BoardPosition(4, 1)))
        self.assertTrue(board.has_cover_obstacle(BoardPosition(0, 1), BoardPosition(4, 1)))
        self.assertFalse(board.has_cover_obstacle(BoardPosition(0, 0), BoardPosition(4, 0)))
        self.assertTrue(
            board.has_cover_obstacle(
                BoardPosition(0, 0), BoardPosition(4, 0), occupied={BoardPosition(2, 0)}
            )
        )


if __name__ == "__main__":
    unittest.main()
