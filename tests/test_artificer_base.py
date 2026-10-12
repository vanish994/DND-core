"""Regression tests for the Artificer 5.5e base class."""
import unittest

from rule_engine.artificer_base import ARTIFICER_PREPARED_SPELLS, resolve_artificer_feature
from rule_engine.character import criar_personagem, ficha_personagem
from rule_engine.class_features import resolver_caracteristica
from rule_engine.class_progression import caracteristicas_no_nivel
from rule_engine.spellcasting import progresso_artifice


class ArtificerProgressionTests(unittest.TestCase):
    def test_fixed_prepared_spell_table_for_all_levels(self):
        self.assertEqual(
            [progresso_artifice(level, 16)["magias_preparadas"] for level in range(1, 21)],
            [ARTIFICER_PREPARED_SPELLS[level] for level in range(1, 21)],
        )

    def test_cantrip_thresholds_and_slots(self):
        self.assertEqual(progresso_artifice(1, 16)["truques"], 2)
        self.assertEqual(progresso_artifice(9, 16)["truques"], 2)
        self.assertEqual(progresso_artifice(10, 16)["truques"], 3)
        self.assertEqual(progresso_artifice(14, 16)["truques"], 4)
        self.assertEqual(progresso_artifice(20, 16)["espacos_totais"], {
            "1": 4, "2": 3, "3": 3, "4": 3, "5": 2
        })

    def test_english_feature_aliases_obey_level_gates(self):
        early_tinker = resolver_caracteristica({
            "classe": "artifice", "recurso": "Magic Item Tinker", "nivel": 1,
        })
        self.assertEqual(early_tinker["resultado"], "bloqueado")
        self.assertEqual(early_tinker["nivel_minimo"], 6)
        early_adept = resolver_caracteristica({
            "classe": "artifice", "recurso": "Magic Item Adept", "nivel": 1,
        })
        self.assertEqual(early_adept["nivel_minimo"], 10)
        early_master = resolver_caracteristica({
            "classe": "artifice", "recurso": "Magic Item Master", "nivel": 1,
        })
        self.assertEqual(early_master["nivel_minimo"], 18)
        early_boon = resolver_caracteristica({
            "classe": "artifice", "recurso": "Epic Boon", "nivel": 18,
        })
        self.assertEqual(early_boon["nivel_minimo"], 19)

    def test_level_6_10_14_18_and_epic_boon_are_in_progression(self):
        self.assertIn("Ajustador de Item Mágico", caracteristicas_no_nivel("artifice", 6))
        self.assertIn("Adepto de Item Mágico", caracteristicas_no_nivel("artifice", 10))
        self.assertIn("Artífice Avançado", caracteristicas_no_nivel("artifice", 14))
        self.assertIn("Mestre de Item Mágico", caracteristicas_no_nivel("artifice", 18))
        self.assertIn("Dádiva Épica", caracteristicas_no_nivel("artifice", 19))
        self.assertIn("Alma do Artífice", caracteristicas_no_nivel("artifice", 20))

    def test_tinkers_magic_creates_gear_with_tools_and_uses(self):
        result = resolver_caracteristica({
            "classe": "artifice", "recurso": "Magia de Artífice", "nivel": 1,
            "inteligencia": 16, "acao": "criar", "item": "Estrepes",
            "ferramentas_tinkering_em_maos": True, "usos_gastos": 1,
        })
        self.assertEqual(result["resultado"], "criado")
        self.assertEqual(result["usos_maximos"], 3)
        self.assertEqual(result["usos_restantes"], 1)
        self.assertEqual(result["desaparece"], "proximo_descanso_longo")

    def test_replicate_item_requires_artisan_tools_and_distinct_plans(self):
        missing_tools = resolver_caracteristica({
            "classe": "artifice", "recurso": "Replicar Item Mágico", "nivel": 2,
            "acao": "criar", "planos": ["plano_a"],
        })
        self.assertEqual(missing_tools["resultado"], "requer_dados")
        duplicate = resolver_caracteristica({
            "classe": "artifice", "recurso": "Replicar Item Mágico", "nivel": 2,
            "acao": "criar", "planos": ["plano_a", "plano_a"],
            "ferramentas_artesao_em_maos": True,
        })
        self.assertEqual(duplicate["motivo"], "cada_item_deve_usar_plano_diferente")

    def test_starting_equipment_is_a_choice_and_uses_selected_artisan_tool(self):
        character = criar_personagem({
            "name": "Artífice de Teste", "species": "humano", "class": "artifice",
            "level": 1,
            "ability_scores": {"forca": 8, "destreza": 14, "constituicao": 13,
                               "inteligencia": 15, "sabedoria": 12, "carisma": 10},
            "class_skill_proficiencies": ["arcanismo", "investigacao"],
            "artisan_tool_proficiency": "Ferramentas de Ferreiro",
            "class_equipment": "A",
        })
        sheet = ficha_personagem(character)
        self.assertEqual(sheet["equipamento_classe"]["escolha"], "A")
        self.assertIn("Ferramentas de Ferreiro", sheet["equipamento_classe"]["itens"])
        self.assertEqual(sheet["equipamento_classe"]["ouro"], 16)
        self.assertFalse(sheet["equipamento_classe_pendente"])

    def test_drain_item_uses_rarity_and_is_bonus_action(self):
        result = resolver_caracteristica({
            "classe": "artifice", "recurso": "Ajustador de Item Mágico", "nivel": 6,
            "acao": "drenar", "item_replicado": True, "distancia_m": 1,
            "raridade": "raro",
        })
        self.assertEqual(result["resultado"], "drenado")
        self.assertEqual(result["nivel_espaco_recuperado"], 2)
        self.assertEqual(result["acao"], "acao_bonus")


if __name__ == "__main__":
    unittest.main()
