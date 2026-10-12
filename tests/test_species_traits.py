"""Traços completos das espécies do Livro do Jogador 2024."""

import unittest

from rule_engine import (
    TRACOS_ESPECIE,
    build_default_engine,
    listar_especies,
    normalizar_especie,
    resolver_tracos_especie,
    tracos_de_especie,
)


class SpeciesTraitsTests(unittest.TestCase):
    def setUp(self):
        self.engine = build_default_engine()

    def test_catalog_covers_all_ten_phb_species(self):
        self.assertEqual(
            listar_especies(),
            ["aasimar", "anao", "draconato", "elfo", "gnomo", "golias", "halfling", "humano", "orc", "tiefling"],
        )
        self.assertEqual(len(TRACOS_ESPECIE), 10)

    def test_catalog_values_match_the_book(self):
        self.assertEqual(tracos_de_especie("aasimar")["deslocamento_m"], 9)
        self.assertEqual(tracos_de_especie("golias")["deslocamento_m"], 10.5)
        # Pequenino: 9 metros no PHB 2024 (não mais os 7,5 m da edição anterior).
        self.assertEqual(tracos_de_especie("pequenino")["deslocamento_m"], 9)
        self.assertEqual(tracos_de_especie("humano")["tamanhos"], ["medio", "pequeno"])
        self.assertEqual(tracos_de_especie("tiferino")["nome"], "Tiferino")

    def test_species_aliases_are_normalized(self):
        self.assertEqual(normalizar_especie("Pequenino"), "halfling")
        self.assertEqual(normalizar_especie("Tiferino"), "tiefling")
        self.assertEqual(normalizar_especie("Dwarf"), "anao")
        with self.assertRaises(ValueError):
            normalizar_especie("sereiano")

    def test_dwarf_traits_are_derived(self):
        resultado = resolver_tracos_especie({"especie": "anao", "nivel": 5})
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["resistencias_dano"], ["venenoso"])
        self.assertEqual(resultado["vantagens_salvaguarda"], ["envenenado"])
        self.assertEqual(resultado["visao_no_escuro_m"], 36)
        self.assertEqual(resultado["pv_bonus_por_nivel"], 1)
        self.assertEqual(resultado["pv_bonus_total"], 5)
        self.assertIn("fonte", resultado)

    def test_high_elf_lineage_grants_spells_by_level(self):
        nivel_1 = resolver_tracos_especie({"especie": "elfo", "linhagem": "alto_elfo", "nivel": 1})
        self.assertEqual(nivel_1["magias"]["truques"], ["Prestidigitação Arcana"])
        self.assertEqual(nivel_1["magias"]["magias"], [])
        nivel_5 = resolver_tracos_especie(
            {"especie": "elfo", "linhagem": "alto_elfo", "nivel": 5, "bonus_proficiencia": 3}
        )
        self.assertEqual([m["magia"] for m in nivel_5["magias"]["magias"]], ["Detectar Magia", "Passo Nebuloso"])
        self.assertEqual(nivel_5["magias"]["conjura_sem_espaco_por_descanso_longo"], 1)

    def test_drow_lineage_upgrades_darkvision_and_speed(self):
        drow = resolver_tracos_especie({"especie": "elfo", "linhagem": "drow", "nivel": 3})
        self.assertEqual(drow["visao_no_escuro_m"], 36)
        self.assertEqual(drow["magias"]["truques"], ["Luzes Dançantes"])
        silvestre = resolver_tracos_especie({"especie": "elfo", "linhagem": "silvestre", "nivel": 1})
        self.assertEqual(silvestre["deslocamento_m"], 10.5)

    def test_elf_fey_ancestry_advantage(self):
        elfo = resolver_tracos_especie({"especie": "elfo", "linhagem": "drow", "nivel": 1})
        self.assertEqual(elfo["vantagens_salvaguarda"], ["enfeiticado"])

    def test_wood_gnome_spell_uses_scale_with_proficiency(self):
        gnomo = resolver_tracos_especie({"especie": "gnomo", "linhagem": "bosque", "nivel": 5, "bonus_proficiencia": 3})
        self.assertEqual(gnomo["magias"]["truques"], ["Ilusão Menor"])
        self.assertEqual(gnomo["magias"]["magias"][0]["magia"], "Falar com Animais")
        self.assertEqual(gnomo["magias"]["conjura_sem_espaco_por_descanso_longo"], 3)

    def test_tiefling_legacy_sets_resistance_and_spells(self):
        infernal = resolver_tracos_especie({"especie": "tiefling", "legado": "infernal", "nivel": 5})
        self.assertEqual(infernal["resistencias_dano"], ["ígneo"])
        self.assertEqual(infernal["magias"]["truques"], ["Raio de Fogo"])
        self.assertEqual([m["magia"] for m in infernal["magias"]["magias"]], ["Repreensão Diabólica", "Escuridão"])
        self.assertEqual(infernal["legado_infero"]["nome"], "Infernal")

    def test_dragonborn_heritage_drives_resistance_and_breath(self):
        resultado = resolver_tracos_especie(
            {"especie": "draconato", "heranca_draconica": "vermelho", "nivel": 11, "modificador_constituicao": 3}
        )
        self.assertEqual(resultado["resistencias_dano"], ["ígneo"])
        sopro = resultado["heranca_draconica"]["sopro"]
        self.assertEqual(sopro["dado"], "3d10")
        self.assertEqual(sopro["cd"], 8 + 3 + 4)
        self.assertEqual(sopro["usos"], 4)

    def test_goliath_ancestry_and_level_gated_traits(self):
        nivel_1 = resolver_tracos_especie({"especie": "golias", "ancestralidade": "tombo_da_colina", "nivel": 1})
        nomes = [t["nome"] for t in nivel_1["tracos"]]
        self.assertNotIn("Forma Grande", nomes)
        nivel_5 = resolver_tracos_especie({"especie": "golias", "ancestralidade": "tombo_da_colina", "nivel": 5})
        nomes = [t["nome"] for t in nivel_5["tracos"]]
        self.assertIn("Forma Grande", nomes)
        self.assertIn("Caído", nivel_5["ancestralidade_gigante"]["efeito"])

    def test_orc_and_aasimar_resources_and_level_gating(self):
        orc = resolver_tracos_especie({"especie": "orc", "nivel": 3, "bonus_proficiencia": 2})
        self.assertEqual(orc["visao_no_escuro_m"], 36)
        aasimar_1 = resolver_tracos_especie({"especie": "aasimar", "nivel": 1})
        nomes = [t["nome"] for t in aasimar_1["tracos"]]
        self.assertNotIn("Revelação Celestial", nomes)
        aasimar_3 = resolver_tracos_especie({"especie": "aasimar", "nivel": 3})
        self.assertIn("Revelação Celestial", [t["nome"] for t in aasimar_3["tracos"]])
        self.assertEqual(aasimar_3["resistencias_dano"], ["necrótico", "radiante"])

    def test_pending_choices_are_explicit(self):
        resultado = resolver_tracos_especie({"especie": "elfo", "nivel": 1})
        self.assertEqual(resultado["escolhas_pendentes"], ["linhagem_elfica"])
        self.assertNotIn("magias", resultado)
        with self.assertRaises(ValueError):
            resolver_tracos_especie({"especie": "elfo", "linhagem": "inventada", "nivel": 1})
        with self.assertRaises(ValueError):
            resolver_tracos_especie({"especie": "golias", "ancestralidade": "gigante_do_espaço", "nivel": 1})

    def test_species_traits_rule_is_registered(self):
        result = self.engine.evaluate({"type": "species_traits", "especie": "anao", "nivel": 2})
        self.assertEqual(result.matched_rules, ["species.traits"])
        self.assertEqual(result.outcome["resistencias_dano"], ["venenoso"])
        self.assertEqual(result.outcome["rule_source"], "D&D 2024 — Origens dos Personagens: espécies")

    def test_character_species_speeds_follow_2024(self):
        from rule_engine.character import ESPECIES

        self.assertEqual(ESPECIES["halfling"]["deslocamento"], 9)
        self.assertEqual(ESPECIES["humano"]["tamanho"], "pequeno_ou_medio")


if __name__ == "__main__":
    unittest.main()
