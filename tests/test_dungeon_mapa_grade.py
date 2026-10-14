"""Mapas de grade próprios do dungeon: formato, legenda e entradas válidas."""

import json
import unittest
from pathlib import Path

from dungeon_game.combat_board import BoardPosition
from dungeon_game.encontro import carregar_mapa, listar_mapas, tabuleiro_do_mapa

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

    def test_catalogo_lista_e_valida_todos_os_mapas_e_rotas_entre_entradas(self):
        catalogo = listar_mapas()
        self.assertEqual(
            [m["id"] for m in catalogo],
            [
                "cripta_inicial",
                "santuario_circular",
                "catacumba_dos_mortos",
                "camara_profana",
                "sarcofago_do_rei_mumia",
            ],
        )
        self.assertEqual(catalogo[0]["proxima_sala"], "santuario_circular")
        self.assertEqual(catalogo[1]["proxima_sala"], "catacumba_dos_mortos")
        self.assertEqual(catalogo[2]["proxima_sala"], "camara_profana")
        self.assertEqual(catalogo[3]["proxima_sala"], "sarcofago_do_rei_mumia")
        self.assertIsNone(catalogo[4]["proxima_sala"])
        self.assertEqual((catalogo[1]["largura"], catalogo[1]["altura"]), (42, 26))
        self.assertEqual((catalogo[2]["largura"], catalogo[2]["altura"]), (26, 16))
        self.assertEqual((catalogo[3]["largura"], catalogo[3]["altura"]), (28, 16))
        self.assertEqual((catalogo[4]["largura"], catalogo[4]["altura"]), (30, 18))

        for item in catalogo:
            mapa = carregar_mapa(item["id"])
            board = tabuleiro_do_mapa(mapa)
            origem_raw = mapa["entradas"]["jogador"][0]
            origem = BoardPosition(origem_raw["x"], origem_raw["y"])
            self.assertTrue(board.is_walkable(origem), item["id"])
            for ponto in mapa["entradas"]["inimigos"]:
                destino = BoardPosition(ponto["x"], ponto["y"])
                self.assertTrue(board.is_walkable(destino), (item["id"], ponto))
                self.assertIsNotNone(board.shortest_path(origem, destino), (item["id"], ponto))

    def test_carregar_mapa_inexistente_ou_invalido_falha(self):
        with self.assertRaises(ValueError):
            carregar_mapa("mapa_inexistente")
        with self.assertRaises(ValueError):
            carregar_mapa("../servidor")


if __name__ == "__main__":
    unittest.main()
