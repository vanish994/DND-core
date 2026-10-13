"""Mapas de grade próprios do dungeon: formato, legenda e entradas válidas."""

import json
import unittest
from pathlib import Path

MAPAS = Path(__file__).resolve().parents[1] / "dungeon_game" / "mapas"


class MapaGradeTests(unittest.TestCase):
    def setUp(self):
        self.mapa = json.loads((MAPAS / "cripta_inicial.json").read_text(encoding="utf-8"))
        self.grade = self.mapa["grade"]

    def test_grade_retangular_e_simbolos_conhecidos(self):
        larguras = {len(linha) for linha in self.grade}
        self.assertEqual(len(larguras), 1)
        simbolos = {c for linha in self.grade for c in linha}
        self.assertTrue(simbolos <= set(self.mapa["legenda"]), simbolos - set(self.mapa["legenda"]))

    def test_entradas_caem_em_casa_livre(self):
        livres = {"chao", "agua"}
        for ponto in self.mapa["entradas"]["jogador"] + self.mapa["entradas"]["inimigos"]:
            simbolo = self.grade[ponto["y"]][ponto["x"]]
            self.assertIn(self.mapa["legenda"][simbolo]["tipo"], livres, ponto)

    def test_borda_fechada_exceto_porta(self):
        topo, base = self.grade[0], self.grade[-1]
        self.assertEqual(set(topo), {"#"})
        self.assertEqual(set(base), {"#"})
        esquerda = [linha[0] for linha in self.grade]
        self.assertEqual(esquerda.count("+"), 1)


if __name__ == "__main__":
    unittest.main()
