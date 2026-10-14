"""Perfis de inimigos do dungeon: valores vêm do bestiário, sem cópia local."""

import unittest

from dungeon_game.inimigos import (
    PERFIS,
    PerfilInimigo,
    PerfilInvalido,
    carregar_inimigo,
    escolher_acao_inimigo,
    listar_perfis,
)
from rule_engine.bestiary import consultar_monstro


class PerfisInimigosTests(unittest.TestCase):
    def test_perfis_carregam_do_bestiario(self):
        self.assertEqual(
            listar_perfis(),
            [
                "aparicao",
                "armadura_animada",
                "bandido",
                "carnical",
                "cultista",
                "espectro",
                "esqueleto",
                "esqueleto_minotauro",
                "goblin",
                "goblin_arqueiro",
                "mumia",
                "orc",
                "sombra",
                "zumbi",
            ],
        )
        for perfil_id in listar_perfis():
            inimigo = carregar_inimigo(perfil_id)
            bloco = consultar_monstro(PERFIS[perfil_id].monstro)
            self.assertEqual(inimigo["ca"], bloco["ca"])
            self.assertEqual(inimigo["pv"], bloco["pv"])
            self.assertEqual(inimigo["atributos"], bloco["atributos"])
            self.assertEqual(inimigo["vulnerabilidades_dano"], list(bloco.get("vulnerabilidades_dano") or ()))
            self.assertEqual(inimigo["resistencias_dano"], list(bloco.get("resistencias_dano") or ()))
            self.assertEqual(inimigo["imunidades_dano"], list(bloco.get("imunidades_dano") or ()))
            self.assertEqual(inimigo["imunidades_condicao"], list(bloco.get("imunidades_condicao") or ()))

    def test_novos_perfis_srd_respeitam_acoes_e_defesas_canonicas(self):
        zumbi = carregar_inimigo("zumbi")
        self.assertEqual(zumbi["monstro"], "Zombie")
        self.assertEqual((zumbi["ca"], zumbi["pv"], zumbi["deslocamento_pes"]), (8, 22, 20))
        self.assertEqual(zumbi["acao"]["nome"], "Slam")
        self.assertIn("poisoned", zumbi["imunidades_condicao"])

        carnical = carregar_inimigo("carnical")
        self.assertEqual(carnical["monstro"], "Ghoul")
        self.assertEqual((carnical["ca"], carnical["pv"]), (12, 22))
        self.assertEqual(carnical["acao"]["nome"], "Bite")
        self.assertIn("poison", carnical["imunidades_dano"])

        cultista = carregar_inimigo("cultista")
        self.assertEqual(cultista["monstro"], "Cultist")
        self.assertEqual((cultista["ca"], cultista["pv"]), (12, 9))
        self.assertEqual(cultista["acao"]["nome"], "Scimitar")

        bandido = carregar_inimigo("bandido")
        self.assertEqual(bandido["monstro"], "Bandit")
        self.assertEqual(escolher_acao_inimigo(bandido, 5)["nome"], "Scimitar")
        self.assertEqual(escolher_acao_inimigo(bandido, 30)["nome"], "Light Crossbow")
        self.assertEqual(bandido["acao_distancia"]["alcance_pes"], {"normal": 80, "maximo": 320})

        orc = carregar_inimigo("orc")
        self.assertEqual(orc["monstro"], "Orc")
        self.assertEqual((orc["ca"], orc["pv"]), (13, 15))
        self.assertEqual(escolher_acao_inimigo(orc, 5)["nome"], "Greataxe")
        self.assertEqual(escolher_acao_inimigo(orc, 20)["nome"], "Javelin")
        self.assertEqual(orc["acao_distancia"]["alcance_pes"], {"normal": 30, "maximo": 120})

        sombra = carregar_inimigo("sombra")
        self.assertEqual(sombra["monstro"], "Shadow")
        self.assertEqual((sombra["ca"], sombra["pv"], sombra["deslocamento_pes"]), (12, 16, 40))
        self.assertEqual(sombra["acao"]["nome"], "Strength Drain")
        self.assertIn("radiant", sombra["vulnerabilidades_dano"])
        self.assertIn("necrotic", sombra["imunidades_dano"])

        armadura = carregar_inimigo("armadura_animada")
        self.assertEqual(armadura["monstro"], "Animated Armor")
        self.assertEqual((armadura["ca"], armadura["pv"], armadura["deslocamento_pes"]), (18, 33, 25))
        self.assertEqual(armadura["acao"]["nome"], "Slam")
        self.assertEqual(set(armadura["imunidades_dano"]), {"poison", "psychic"})

        aparicao = carregar_inimigo("aparicao")
        self.assertEqual(aparicao["monstro"], "Wight")
        self.assertEqual((aparicao["ca"], aparicao["pv"]), (14, 45))
        self.assertEqual(escolher_acao_inimigo(aparicao, 5)["nome"], "Longsword")
        self.assertEqual(escolher_acao_inimigo(aparicao, 60)["nome"], "Longbow")
        self.assertEqual(aparicao["acao_distancia"]["alcance_pes"], {"normal": 150, "maximo": 600})

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
        self.assertEqual(esqueleto["acao"]["nome"], "Shortsword")
        self.assertEqual(esqueleto["acao_distancia"]["nome"], "Shortbow")
        self.assertEqual(esqueleto["acao_distancia"]["alcance_pes"], {"normal": 80, "maximo": 320})
        self.assertTrue(esqueleto["acao_distancia"]["a_distancia"])
        self.assertEqual(escolher_acao_inimigo(esqueleto, 5)["nome"], "Shortsword")
        self.assertEqual(escolher_acao_inimigo(esqueleto, 30)["nome"], "Shortbow")

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
