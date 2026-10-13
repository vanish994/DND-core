"""Testes da fronteira entre dungeon, Orquestrador e Rule Engine."""
import unittest
from unittest.mock import Mock

from dungeon_game.combat_board import BoardPosition, CombatBoard
from dungeon_game.rule_adapter import DungeonRuleAdapter
from orchestrator import ResultadoAcao
from rule_engine.combat_geometry import distancia_grade


class DungeonRuleAdapterTests(unittest.TestCase):
    def test_board_can_be_tested_without_rule_engine_dependency(self):
        board = CombatBoard(8, 8, distance_in_squares=lambda dx, dy: max(abs(dx), abs(dy)))
        self.assertEqual(board.distance_feet(BoardPosition(1, 1), BoardPosition(4, 3)), 15)

    def test_board_requires_explicit_distance_adapter(self):
        board = CombatBoard(8, 8)
        with self.assertRaises(RuntimeError):
            board.distance_feet(BoardPosition(1, 1), BoardPosition(4, 3))

    def test_adapter_injects_rule_engine_distance_convention(self):
        board = DungeonRuleAdapter.create_combat_board(8, 8, tile_feet=5)
        self.assertEqual(board.distance_feet(BoardPosition(1, 1), BoardPosition(4, 3)),
                         distancia_grade(3, 2) * 5)

    def test_rule_action_is_translated_to_orchestrator_contract(self):
        orchestrator = Mock()
        expected = ResultadoAcao("resolvido", {"resultado": "ok"})
        orchestrator.executar.return_value = expected
        adapter = DungeonRuleAdapter(orchestrator)

        result = adapter.execute_rule({"type": "ability_check", "skill": "atletismo"})

        self.assertIs(result, expected)
        action = orchestrator.executar.call_args.args[0]
        self.assertEqual(action.ferramenta, "resolver_regra")
        self.assertEqual(action.tipo, "ability_check")
        self.assertEqual(action.para_fatos()["skill"], "atletismo")


if __name__ == "__main__":
    unittest.main()
