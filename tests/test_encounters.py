"""Testes de construção de encontros — exemplos literais do DMG 2024."""

import unittest

from rule_engine import (
    XP_BUDGET_POR_PERSONAGEM,
    atitude_inicial,
    avaliar_encontro,
    avaliar_encontro_de_monstros,
    budgets_do_grupo,
    build_default_engine,
    orcamento_xp,
    personalidade_monstro,
    relacoes_monstros,
)


class EncounterBuildingTests(unittest.TestCase):
    def setUp(self):
        self.engine = build_default_engine()

    def test_budget_matches_dmg_examples(self):
        # Exemplo 1: encontro Baixa para quatro personagens de nível 1 → 50 × 4 = 200.
        self.assertEqual(orcamento_xp(1, 4, "baixa"), 200)
        # Exemplo 2: encontro Moderado para cinco personagens de nível 3 → 225 × 5 = 1.125.
        self.assertEqual(orcamento_xp(3, 5, "moderada"), 1125)
        # Exemplo 3: encontro Alto para seis personagens de nível 15 → 7.800 × 6 = 46.800.
        self.assertEqual(orcamento_xp(15, 6, "alta"), 46800)

    def test_budget_table_has_all_twenty_levels(self):
        self.assertEqual(sorted(XP_BUDGET_POR_PERSONAGEM), list(range(1, 21)))
        self.assertEqual(budgets_do_grupo(1, 4), {"baixa": 200, "moderada": 300, "alta": 400})

    def test_review_classifies_dmg_example_encounters(self):
        # Exemplo 2 do DMG: 2 Nothics (450) + 9 Stirges (25) = 1.125 → Moderado (budget 1.125).
        resultado = avaliar_encontro(1125, 3, 5)
        self.assertEqual(resultado["dificuldade"], "moderada")
        self.assertEqual(resultado["xp_restante_no_budget"], 0)
        # Exemplo 2: 1 Wight (700) + 1 Warhorse Skeleton (100) + 6 Skeletons (50) = 1.100.
        resultado = avaliar_encontro(1100, 3, 5)
        self.assertEqual(resultado["dificuldade"], "moderada")
        self.assertEqual(resultado["xp_restante_no_budget"], 25)
        # Exemplo 1: 6 Twig Blights (25) = 150 com budget Baixa de 200.
        resultado = avaliar_encontro(150, 1, 4)
        self.assertEqual(resultado["dificuldade"], "baixa")
        self.assertEqual(resultado["xp_restante_no_budget"], 50)

    def test_review_above_high_budget_is_a_derived_label(self):
        resultado = avaliar_encontro(50000, 15, 6)
        self.assertEqual(resultado["dificuldade"], "acima_da_alta")
        self.assertIn("apenas as dificuldades Baixa, Moderada e Alta", resultado["nota"])

    def test_review_from_bestiary_names(self):
        # Goblins do SRD 5.2.1 (50 XP cada, ND 1/4) contra grupo de nível 1.
        resultado = avaliar_encontro_de_monstros(["Goblin"] * 2, 1, 4)
        self.assertEqual(resultado["xp_total"], 100)
        self.assertEqual(resultado["dificuldade"], "baixa")

    def test_initial_attitude_table(self):
        self.assertEqual(atitude_inicial(4)["atitude"], "hostil")
        self.assertEqual(atitude_inicial(5)["atitude"], "indiferente")
        self.assertEqual(atitude_inicial(8)["atitude"], "indiferente")
        self.assertEqual(atitude_inicial(9)["atitude"], "amigavel")
        self.assertEqual(atitude_inicial(20)["atitude"], "amigavel")

    def test_personality_and_relationship_tables(self):
        self.assertEqual(personalidade_monstro(1)["personalidade"], "covarde; rende-se facilmente")
        self.assertEqual(personalidade_monstro(8)["personalidade"], "disciplinado; difícil de abalar")
        self.assertIn("rivalidade amarga", relacoes_monstros(1)["relacao"])
        self.assertIn("intimida os outros", relacoes_monstros(6)["relacao"])

    def test_invalid_rolls_and_budgets_are_rejected(self):
        with self.assertRaises(ValueError):
            atitude_inicial(21)
        with self.assertRaises(ValueError):
            personalidade_monstro(0)
        with self.assertRaises(ValueError):
            relacoes_monstros(7)
        with self.assertRaises(ValueError):
            orcamento_xp(21, 4, "baixa")
        with self.assertRaises(ValueError):
            orcamento_xp(1, 0, "baixa")
        with self.assertRaises(ValueError):
            orcamento_xp(1, 4, "impossivel")

    def test_encounter_rules_are_registered_in_the_engine(self):
        budget = self.engine.evaluate(
            {"type": "encounter", "operation": "budget", "party_level": 1, "party_size": 4, "difficulty": "low"}
        )
        self.assertEqual(budget.matched_rules, ["encounter.building"])
        self.assertEqual(budget.outcome["budget"], 200)
        self.assertEqual(budget.outcome["rule_source"], "Dungeon Master's Guide 2024 — Combat Encounters")
        review = self.engine.evaluate(
            {"type": "encounter", "operation": "review", "xp_total": 1125, "party_level": 3, "party_size": 5}
        )
        self.assertEqual(review.outcome["dificuldade"], "moderada")
        attitude = self.engine.evaluate({"type": "encounter", "operation": "atitude", "roll": 3})
        self.assertEqual(attitude.outcome["atitude"], "hostil")
        personality = self.engine.evaluate({"type": "encounter", "operation": "personalidade", "roll": 5})
        self.assertIn("fanático", personality.outcome["personalidade"])


if __name__ == "__main__":
    unittest.main()
