"""Listas de magias por classe do PHB 2024 (capítulo 3)."""

import unittest

from rule_engine import (
    CLASSES_CONJURADORAS,
    LISTAS_POR_CLASSE,
    MAGIAS,
    build_default_engine,
    listar_magias_da_classe,
    magia_na_lista,
)
from rule_engine.spell_lists import META_POR_NOME
from rule_engine.spells import _normalizar_nome_magia


class SpellListCatalogTests(unittest.TestCase):
    def test_oito_classes_conjuradoras(self):
        self.assertEqual(
            CLASSES_CONJURADORAS,
            ("bardo", "bruxo", "clerigo", "druida", "feiticeiro", "guardiao", "mago", "paladino"),
        )
        self.assertEqual(set(LISTAS_POR_CLASSE), set(CLASSES_CONJURADORAS))

    def test_guardiao_e_paladino_nao_tem_truques_vao_ate_o_quinto_circulo(self):
        for classe in ("guardiao", "paladino"):
            self.assertNotIn(0, LISTAS_POR_CLASSE[classe])
            self.assertEqual(sorted(LISTAS_POR_CLASSE[classe]), [1, 2, 3, 4, 5])

    def test_conjuradores_completos_tem_truques_e_ate_nono_circulo(self):
        for classe in ("bardo", "bruxo", "clerigo", "druida", "feiticeiro", "mago"):
            self.assertIn(0, LISTAS_POR_CLASSE[classe])
            self.assertEqual(sorted(LISTAS_POR_CLASSE[classe]), list(range(10)))

    def test_todas_as_magias_das_listas_estao_no_catalogo(self):
        faltando = []
        for classe, circulos in LISTAS_POR_CLASSE.items():
            for circulo, nomes in circulos.items():
                for nome in nomes:
                    if _normalizar_nome_magia(nome) not in {_normalizar_nome_magia(m["nome"]) for m in MAGIAS.values()}:
                        faltando.append(f"{classe}:{circulo}:{nome}")
        self.assertEqual(faltando, [])

    def test_circulo_da_lista_confera_com_o_catalogo(self):
        divergentes = []
        for classe, circulos in LISTAS_POR_CLASSE.items():
            for circulo, nomes in circulos.items():
                for nome in nomes:
                    chave = _normalizar_nome_magia(nome)
                    if chave in META_POR_NOME and META_POR_NOME[chave]["circulo"] != circulo:
                        divergentes.append(nome)
        self.assertEqual(divergentes, [])

    def test_marcadores_vem_das_listas(self):
        # As chaves de META_POR_NOME são nomes normalizados (sem acento).
        self.assertTrue(META_POR_NOME["detectar magia"]["ritual"])
        self.assertTrue(META_POR_NOME["detectar magia"]["concentracao"])
        self.assertEqual(META_POR_NOME["remeter"]["escola"], "adivinhação")
        self.assertTrue(META_POR_NOME["luzes dancantes"]["concentracao"])
        self.assertFalse(META_POR_NOME["bola de fogo"]["concentracao"])


class SpellListQueryTests(unittest.TestCase):
    def test_listar_por_classe_e_circulo(self):
        primeiro = listar_magias_da_classe("guardiao", 1)
        self.assertIn("Marca do Predador", primeiro)
        self.assertIn("Alarme", primeiro)
        self.assertEqual(listar_magias_da_classe("guardiao", 6), [])

    def test_listar_todas_as_magias_da_classe(self):
        mago = listar_magias_da_classe("mago")
        self.assertEqual(len(mago), sum(len(v) for v in LISTAS_POR_CLASSE["mago"].values()))
        self.assertIn("Desejo", mago)
        self.assertIn("Bola de Fogo", mago)

    def test_magia_na_lista_ignora_acentos_e_caixa(self):
        self.assertTrue(magia_na_lista("bola de fogo", "MAGO", 3))
        self.assertTrue(magia_na_lista("Mãos Mágicas", "bardo", 0))
        self.assertFalse(magia_na_lista("Bola de Fogo", "guardiao"))

    def test_classe_desconhecida_levanta_erro(self):
        with self.assertRaises(ValueError):
            listar_magias_da_classe("guerreiro")

    def test_desejo_nas_listas_de_mago_e_feiticeiro(self):
        self.assertTrue(magia_na_lista("Desejo", "mago", 9))
        self.assertTrue(magia_na_lista("Desejo", "feiticeiro", 9))
        self.assertFalse(magia_na_lista("Desejo", "bardo", 9))

    def test_rota_do_engine_por_classe(self):
        engine = build_default_engine()
        result = engine.evaluate({"type": "spell_catalog", "operation": "by_class", "classe": "paladino", "circulo": 1})
        self.assertEqual(result.outcome["resultado"], "listado")
        self.assertIn("Benção", result.outcome["magias"])
        self.assertEqual(result.outcome["circulo"], 1)


if __name__ == "__main__":
    unittest.main()
