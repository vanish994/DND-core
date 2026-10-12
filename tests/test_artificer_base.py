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
            "ferramentas_tinkering_em_maos": True, "distancia_m": 1, "espaco_desocupado": True, "usos_gastos": 1,
        })
        self.assertEqual(result["resultado"], "criado")
        self.assertEqual(result["usos_maximos"], 3)
        self.assertEqual(result["usos_restantes"], 1)
        self.assertEqual(result["desaparece"], "proximo_descanso_longo")

    def test_replicate_catalog_is_tiered_and_returns_item_metadata(self):
        level_2 = resolve_artificer_feature("replicar_item_magico", 2, {})
        level_6 = resolve_artificer_feature("replicar_item_magico", 6, {})
        level_10 = resolve_artificer_feature("replicar_item_magico", 10, {})
        level_14 = resolve_artificer_feature("replicar_item_magico", 14, {})
        self.assertIn("alchemy_jug", [p["id"] for p in level_2["planos_disponiveis"]])
        self.assertNotIn("armor_plus_1", [p["id"] for p in level_2["planos_disponiveis"]])
        self.assertIn("armor_plus_1", [p["id"] for p in level_6["planos_disponiveis"]])
        self.assertIn("armor_of_resistance", [p["id"] for p in level_10["planos_disponiveis"]])
        self.assertIn("ring_of_the_ram", [p["id"] for p in level_14["planos_disponiveis"]])

    def test_replicate_plan_milestones_add_a_new_plan(self):
        result = resolver_caracteristica({
            "classe": "artifice", "recurso": "Replicar Item Mágico", "nivel": 6,
            "acao": "aprender_plano", "ao_subir_de_nivel": True,
            "plano_novo": "armor_plus_1",
            "planos_conhecidos": ["alchemy_jug", "bag_of_holding", "cap_of_water_breathing", "wand_of_secrets"],
        })
        self.assertEqual(result["resultado"], "plano_aprendido")
        self.assertEqual(len(result["planos_conhecidos"]), 5)

    def test_replicate_plan_replacement_only_on_level_up(self):
        result = resolver_caracteristica({
            "classe": "artifice", "recurso": "Replicar Item Mágico", "nivel": 2,
            "acao": "substituir_plano", "plano_antigo": "alchemy_jug",
            "plano_novo": "goggles_of_night",
            "planos_conhecidos": ["alchemy_jug", "bag_of_holding", "cap_of_water_breathing", "wand_of_secrets"],
        })
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "planos_so_podem_ser_substituidos_ao_subir_de_nivel")

    def test_replicate_creation_replaces_oldest_when_at_capacity(self):
        result = resolver_caracteristica({
            "classe": "artifice", "recurso": "Replicar Item Mágico", "nivel": 2,
            "acao": "criar", "ferramentas_artesao_em_maos": True, "descanso_longo_concluido": True,
            "planos_conhecidos": ["alchemy_jug", "bag_of_holding", "cap_of_water_breathing", "wand_of_secrets"],
            "planos": ["alchemy_jug", "bag_of_holding"],
            "itens_atuais": [{"plano": "cap_of_water_breathing", "nome": "Bolsa antiga"}],
        })
        self.assertEqual(result["resultado"], "criado")
        self.assertEqual(result["itens_que_desaparecem"][0]["plano"], "cap_of_water_breathing")
        self.assertEqual(len(result["itens_atuais_apos_criacao"]), 2)

    def test_replicate_item_requires_artisan_tools_and_distinct_plans(self):
        missing_tools = resolver_caracteristica({
            "classe": "artifice", "recurso": "Replicar Item Mágico", "nivel": 2,
            "acao": "criar", "planos": ["plano_a"],
        })
        self.assertEqual(missing_tools["resultado"], "requer_dados")
        duplicate = resolver_caracteristica({
            "classe": "artifice", "recurso": "Replicar Item Mágico", "nivel": 2,
            "acao": "criar", "planos": ["plano_a", "plano_a"],
            "ferramentas_artesao_em_maos": True, "descanso_longo_concluido": True,
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

    def test_artificer_attunement_limit_accepts_replicated_item_metadata(self):
        from rule_engine.economy import resolver_sintonizacao
        known = ["item_a", "item_b", "item_c"]
        metadata = {"nome": "Ferramenta Multifuncional +1", "raridade": "incomum", "sintonizacao": True}
        result = resolver_sintonizacao({
            "item": "all_purpose_tool_plus_1", "metadados_item": metadata,
            "sintonizados": known, "classe": "artifice", "nivel": 10,
        })
        self.assertEqual(result["resultado"], "sintonizado")
        self.assertEqual(result["limite"], 4)
        blocked = resolver_sintonizacao({
            "item": "wand_of_the_war_mage_plus_1",
            "metadados_item": {"nome": "Varinha do Mago de Guerra +1", "sintonizacao": True},
            "sintonizados": ["a", "b", "c", "d"], "classe": "artifice", "nivel": 10,
        })
        self.assertEqual(blocked["motivo"], "limite_de_itens_sintonizados")

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
