"""Catálogo de mapas do dungeon: metadados de colisão e atribuição de licença."""

import json
import unittest
from pathlib import Path

CATALOGO = Path(__file__).resolve().parents[1] / "dungeon_game" / "mapas" / "catalogo_vtt.json"


class CatalogoMapasTests(unittest.TestCase):
    def setUp(self):
        self.dados = json.loads(CATALOGO.read_text(encoding="utf-8"))
        self.mapas = {mapa["id"]: mapa for mapa in self.dados["mapas"]}

    def test_tres_mapas_da_primeira_fase(self):
        self.assertEqual(set(self.mapas), {"simple-beach", "pirate-cove", "the-litch-and-his-tomb"})

    def test_paredes_ficam_dentro_da_grade(self):
        # Tolerância de meia casa: o Dungeondraft arredonda vértices nas bordas.
        margem = 0.5
        for mapa in self.mapas.values():
            largura, altura = mapa["grade"]["largura"], mapa["grade"]["altura"]
            for trecho in mapa["paredes"]:
                for ponto in trecho:
                    self.assertTrue(-margem <= ponto["x"] <= largura + margem, mapa["id"])
                    self.assertTrue(-margem <= ponto["y"] <= altura + margem, mapa["id"])

    def test_tumba_tem_colisao_e_portas(self):
        tumba = self.mapas["the-litch-and-his-tomb"]
        self.assertEqual(len(tumba["paredes"]), 35)
        self.assertEqual(len(tumba["portas"]), 5)

    def test_licenca_e_atribuicao_em_todos(self):
        for mapa in self.mapas.values():
            self.assertEqual(mapa["fonte"]["licenca"], "CC-BY-SA-4.0")
            self.assertEqual(mapa["fonte"]["autor"], "mbround18")
            self.assertFalse(mapa["imagem_no_repositorio"])


if __name__ == "__main__":
    unittest.main()
