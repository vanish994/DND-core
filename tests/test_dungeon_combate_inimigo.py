"""Ataque de inimigo do dungeon encaminhado pelo Orquestrador.

As seeds foram escolhidas por varredura no próprio motor: 1 acerta (dano 5),
4 erra, 13 é crítico. O resultado é reprodutível porque a rolagem vem da seed.
"""

import unittest

from dungeon_game.combate_inimigo import atacar
from orchestrator import Acao, OrquestradorAcoes
from rule_engine import build_default_engine


def bardo(**extra):
    ficha = {"id": "bardo1", "nome": "Vanish", "ca": 13, "pv_maximo": 12, "pv_atuais": 12}
    ficha.update(extra)
    return ficha


class AtaqueDeInimigoTests(unittest.TestCase):
    def setUp(self):
        self.orquestrador = OrquestradorAcoes(build_default_engine())

    def test_acerto_reduz_pv_pelo_dano_oficial(self):
        resultado = atacar(self.orquestrador, "goblin", bardo(), seed=1)
        self.assertEqual(resultado["status"], "resolved")
        self.assertTrue(resultado["acertou"])
        self.assertFalse(resultado["critico"])
        self.assertEqual(resultado["dano"], 5)
        self.assertEqual(resultado["pv_atuais"], 7)
        self.assertFalse(resultado["derrubado"])

    def test_erro_nao_causa_dano(self):
        resultado = atacar(self.orquestrador, "goblin", bardo(), seed=4)
        self.assertFalse(resultado["acertou"])
        self.assertNotIn("dano", resultado)

    def test_critico_dobra_os_dados(self):
        resultado = atacar(self.orquestrador, "goblin", bardo(), seed=13)
        self.assertTrue(resultado["critico"])
        self.assertEqual(resultado["dano"], 7)
        self.assertEqual(resultado["pv_atuais"], 5)

    def test_zerar_pv_marca_derrubado(self):
        resultado = atacar(self.orquestrador, "goblin", bardo(ca=1, pv_maximo=3, pv_atuais=3), seed=1)
        self.assertEqual(resultado["pv_atuais"], 0)
        self.assertTrue(resultado["derrubado"])

    def test_pv_temporario_absorve_antes_do_pv(self):
        resultado = atacar(self.orquestrador, "goblin", bardo(pv_temporarios=5), seed=1)
        self.assertEqual(resultado["pv_temporarios"], 0)
        self.assertEqual(resultado["pv_atuais"], 12)

    def test_ca_ausente_bloqueia_sem_rolagem(self):
        ficha = bardo()
        del ficha["ca"]
        resultado = atacar(self.orquestrador, "goblin", ficha, seed=1)
        self.assertEqual(resultado["status"], "bloqueado")
        self.assertEqual(resultado["motivo"], "ca_do_alvo_ausente_na_ficha")

    def test_ca_nao_inteira_bloqueia(self):
        resultado = atacar(self.orquestrador, "goblin", bardo(ca="13"), seed=1)
        self.assertEqual(resultado["motivo"], "ca_do_alvo_ausente_na_ficha")

    def test_ca_vinda_do_pedido_nao_substitui_a_ficha(self):
        # O orquestrador usa a CA da ficha; um target_ac enviado pelo chamador é sobrescrito.
        fatos = {
            "type": "attack",
            "atacante_monstro": "Goblin",
            "acao_monstro": "Scimitar",
            "alvo_id": "bardo1",
            "target_ac": 1,
            "seed": 4,
        }
        resultado = self.orquestrador.executar(Acao.de_ferramenta("resolver_regra", {"fatos": fatos}), [bardo()])
        self.assertEqual(resultado.dados["target_ac"], 13)

    def test_esqueleto_usa_arco_a_distancia_e_aplica_desvantagem_no_alcance_longo(self):
        normal = atacar(self.orquestrador, "esqueleto", bardo(), seed=1, distancia_pes=50)
        self.assertEqual(normal["acao"], "Shortbow")
        self.assertTrue(normal["a_distancia"])
        self.assertFalse(normal["desvantagem_por_alcance"])

        longo = atacar(self.orquestrador, "esqueleto", bardo(), seed=1, distancia_pes=120)
        self.assertEqual(longo["acao"], "Shortbow")
        self.assertTrue(longo["desvantagem_por_alcance"])
        self.assertEqual(len(longo["ataque"]["rolls"]), 2)

    def test_esqueleto_bloqueia_fora_do_alcance_ou_sem_linha_de_visao_e_aplica_cobertura(self):
        fora = atacar(self.orquestrador, "esqueleto", bardo(), seed=1, distancia_pes=325)
        self.assertEqual(fora["status"], "bloqueado")
        self.assertEqual(fora["motivo"], "fora_de_alcance")

        sem_visao = atacar(
            self.orquestrador, "esqueleto", bardo(), seed=1, distancia_pes=40, linha_de_visao_bloqueada=True
        )
        self.assertEqual(sem_visao["status"], "bloqueado")
        self.assertEqual(sem_visao["motivo"], "linha_de_visao")

        com_cobertura = atacar(
            self.orquestrador, "esqueleto", bardo(ca=13), seed=4, distancia_pes=40, cobertura="meia"
        )
        self.assertEqual(com_cobertura["bonus_ca_por_cobertura"], 2)
        self.assertEqual(com_cobertura["ataque"]["target_ac"], 15)


class AtaqueDeMonstroNoOrquestradorTests(unittest.TestCase):
    def setUp(self):
        self.orquestrador = OrquestradorAcoes(build_default_engine())

    def executar(self, **fatos):
        base = {"type": "attack", "atacante_monstro": "Goblin", "acao_monstro": "Scimitar", "alvo_id": "bardo1"}
        base.update(fatos)
        return self.orquestrador.executar(Acao.de_ferramenta("resolver_regra", {"fatos": base}), [bardo()])

    def test_monstro_desconhecido_bloqueia(self):
        self.assertEqual(self.executar(atacante_monstro="Dragão Inventado").motivo, "monstro_desconhecido_no_bestiario")

    def test_acao_que_nao_e_ataque_bloqueia(self):
        resultado = self.executar(acao_monstro="Inexistente")
        self.assertEqual(resultado.motivo, "acao_de_ataque_ausente_no_monstro")

    def test_alvo_ausente_bloqueia(self):
        resultado = self.executar(alvo_id="ninguem")
        self.assertEqual(resultado.motivo, "alvo_ausente_ou_nao_identificado")


if __name__ == "__main__":
    unittest.main()
