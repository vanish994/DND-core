"""Testes do fluxo de turnos sem resolver mecânicas de D&D."""
import unittest
from unittest.mock import Mock

from dungeon_game.combat_board import BoardPosition, CombatBoard
from dungeon_game.combat_session import Combatant, CombatSession, EncounterStatus
from orchestrator import ResultadoAcao


class CombatSessionTests(unittest.TestCase):
    def setUp(self):
        self.board = CombatBoard(8, 8)
        self.player = Combatant("hero", BoardPosition(1, 1), 15, is_player=True)
        self.goblin = Combatant("goblin", BoardPosition(4, 1), 12)
        self.orc = Combatant("orc", BoardPosition(6, 1), 8)
        self.session = CombatSession(self.board, [self.goblin, self.orc, self.player])

    def test_orders_turns_by_initiative_and_advances_round(self):
        self.assertEqual(self.session.current_combatant.id, "hero")
        self.session.end_turn("hero")
        self.assertEqual(self.session.current_combatant.id, "goblin")
        self.session.end_turn("goblin")
        self.session.end_turn("orc")
        self.assertEqual(self.session.current_combatant.id, "hero")
        self.assertEqual(self.session.round_number, 2)

    def test_only_current_actor_can_act_or_end_turn(self):
        with self.assertRaises(ValueError):
            self.session.end_turn("goblin")
        with self.assertRaises(ValueError):
            self.session.resolve_action(Mock(), "goblin", {"type": "attack"})

    def test_action_is_delegated_without_local_rule_resolution(self):
        adapter = Mock()
        adapter.execute_rule.return_value = ResultadoAcao("resolved", {"result": "hit"})
        result = self.session.resolve_action(adapter, "hero", {"type": "attack"})
        self.assertEqual(result.status, "resolved")
        facts = adapter.execute_rule.call_args.args[0]
        self.assertEqual(facts["character_id"], "hero")

    def test_defeated_combatant_is_skipped_and_victory_is_recorded(self):
        self.session.mark_defeated("goblin")
        self.session.end_turn("hero")
        self.assertEqual(self.session.current_combatant.id, "orc")
        self.session.mark_defeated("orc")
        self.assertEqual(self.session.status, EncounterStatus.COMPLETED)

    def test_defeat_of_player_ends_encounter(self):
        self.session.mark_defeated("hero")
        self.assertEqual(self.session.status, EncounterStatus.DEFEATED)

    def test_rejects_duplicate_positions_or_missing_player(self):
        with self.assertRaises(ValueError):
            CombatSession(self.board, [self.player, Combatant("goblin", self.player.position, 2)])
        with self.assertRaises(ValueError):
            CombatSession(self.board, [self.goblin, self.orc])


if __name__ == "__main__":
    unittest.main()
