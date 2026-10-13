"""Perfis de inimigos do dungeon: valores vêm do bestiário, sem cópia local."""

import unittest

from dungeon_game.inimigos import PERFIS, PerfilInimigo, PerfilInvalido, carregar_inimigo, listar_perfis
from rule_engine.bestiary import consultar_monstro


class PerfisInimigosTests(unittest.TestCase):
    def test_perfis_carregam_do_bestiario(self):
        self.assertEqual(listar_perfis(), ["esqueleto", "goblin", "goblin_arqueiro"])
        for perfil_id in listar_perfis():
            inimigo = carregar_inimigo(perfil_id)
            bloco = consultar_monstro(PERFIS[perfil_id].monstro)
            self.assertEqual(inimigo["ca"], bloco["ca"])
            self.assertEqual(inimigo["pv"], bloco["pv"])
            self.assertEqual(inimigo["atributos"], bloco["atributos"])

    def test_goblin_arqueiro_reusa_o_goblin_e_muda_so_a_acao(self):
        goblin = carregar_inimigo("goblin")
        arqueiro = carregar_inimigo("goblin_arqueiro")
        self.assertEqual(goblin["monstro"], arqueiro["monstro"])
        self.assertEqual((goblin["ca"], goblin["pv"]), (arqueiro["ca"], arqueiro["pv"]))
        self.assertEqual(goblin["acao"]["alcance_pes"], {"normal": 5, "maximo": 5})
        self.assertEqual(arqueiro["acao"]["alcance_pes"], {"normal": 80, "maximo": 320})

    def test_esqueleto_usa_nome_do_bestiario_em_ingles(self):
        esqueleto = carregar_inimigo("esqueleto")
        self.assertEqual(esqueleto["monstro"], "Skeleton")
        self.assertEqual(esqueleto["nome"], "Esqueleto")

    def test_perfil_desconhecido_falha(self):
        with self.assertRaises(PerfilInvalido):
            carregar_inimigo("dragao")

    def test_acao_inexistente_no_bloco_falha(self):
        PERFIS["teste_invalido"] = PerfilInimigo("teste_invalido", "X", "Goblin", "Inexistente")
        try:
            with self.assertRaises(PerfilInvalido):
                carregar_inimigo("teste_invalido")
        finally:
            del PERFIS["teste_invalido"]


if __name__ == "__main__":
    unittest.main()
