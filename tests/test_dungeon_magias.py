"""Magias e truques do Bardo no encontro de cripta.

A ficha recebe a conjuração validada pelo criador; a conjuração passa pelo
Orquestrador (preparo, espaço e círculo) e só Curar Ferimentos tem efeito
resolvido no combate. As demais magias são recusadas sem gastar espaço.
"""

import unittest

from dungeon_game.encontro import Encontro, calcular_ca, criar_ficha_bardo
from orchestrator import OrquestradorAcoes
from rule_engine import build_default_engine

INIMIGOS = [("goblin-1", "goblin", (13, 3)), ("esqueleto-1", "esqueleto", (13, 10))]


def novo_encontro(seed_base: int = 100) -> Encontro:
    orquestrador = OrquestradorAcoes(build_default_engine())
    ficha = criar_ficha_bardo()
    ficha["ca"] = calcular_ca(orquestrador, ficha)
    return Encontro(orquestrador, "cripta_inicial", ficha, INIMIGOS, seed_base=seed_base)


def no_turno_do_bardo(encontro: Encontro) -> None:
    while encontro.turno_de != encontro.ficha["id"]:
        encontro.encerrar_turno()


class TestConjuracaoDaFicha(unittest.TestCase):
    def test_ficha_recebe_conjuracao_validada_pelo_criador(self):
        conjuracao = criar_ficha_bardo()["conjuracao"]
        self.assertEqual(conjuracao["truques"], ["Luz", "Ilusão Menor"])
        self.assertEqual(
            conjuracao["magias_preparadas"], ["Curar Ferimentos", "Detectar Magia", "Enfeitiçar Pessoa", "Comando"]
        )
        self.assertEqual(conjuracao["espacos_totais"], {"1": 2})
        self.assertEqual(conjuracao["espacos_restantes"], {"1": 2})


class TestListaDeMagias(unittest.TestCase):
    def test_apenas_curar_ferimentos_esta_disponivel_no_combate(self):
        disponiveis = {m["nome"] for m in novo_encontro().magias_do_personagem() if m["disponivel"]}
        self.assertEqual(disponiveis, {"Curar Ferimentos"})

    def test_magias_indisponiveis_trazem_motivo(self):
        magias = {m["nome"]: m for m in novo_encontro().magias_do_personagem()}
        self.assertIsNotNone(magias["Comando"]["motivo"])
        self.assertIsNotNone(magias["Luz"]["motivo"])
        self.assertEqual(magias["Luz"]["circulo"], 0)
        self.assertEqual(magias["Curar Ferimentos"]["circulo"], 1)


class TestConjurar(unittest.TestCase):
    def test_comando_e_recusada_sem_gastar_espaco(self):
        encontro = novo_encontro()
        no_turno_do_bardo(encontro)
        resultado = encontro.conjurar("Comando")
        self.assertEqual(resultado["status"], "bloqueado")
        self.assertEqual(encontro.ficha["conjuracao"]["espacos_restantes"], {"1": 2})

    def test_magia_nao_escolhida_e_recusada(self):
        encontro = novo_encontro()
        no_turno_do_bardo(encontro)
        resultado = encontro.conjurar("Bola de Fogo")
        self.assertEqual(resultado["status"], "bloqueado")
        self.assertEqual(encontro.ficha["conjuracao"]["espacos_restantes"], {"1": 2})

    def test_curar_ferimentos_gasta_espaco_e_cura_com_rolagem_2d8_mais_carisma(self):
        encontro = novo_encontro(seed_base=7)
        no_turno_do_bardo(encontro)
        encontro.ficha["pv_atuais"] = 5
        modificador = encontro.ficha["modificadores"]["carisma"]
        resultado = encontro.conjurar("Curar Ferimentos")
        self.assertEqual(resultado["status"], "resolvido")
        self.assertEqual(encontro.ficha["conjuracao"]["espacos_restantes"], {"1": 1})
        self.assertTrue(2 + modificador <= resultado["rolagem"] <= 16 + modificador)
        self.assertEqual(encontro.ficha["pv_atuais"], 5 + resultado["curado"])
        self.assertLessEqual(encontro.ficha["pv_atuais"], encontro.ficha["pv_maximo"])
        self.assertEqual(encontro.log[-1]["evento"], "magia")

    def test_cura_nao_ultrapassa_pv_maximo(self):
        encontro = novo_encontro(seed_base=7)
        no_turno_do_bardo(encontro)
        encontro.ficha["pv_atuais"] = encontro.ficha["pv_maximo"] - 1
        resultado = encontro.conjurar("Curar Ferimentos")
        self.assertEqual(resultado["status"], "resolvido")
        self.assertEqual(encontro.ficha["pv_atuais"], encontro.ficha["pv_maximo"])
        self.assertEqual(resultado["curado"], 1)

    def test_sem_espaco_restante_bloqueia_sem_curar(self):
        encontro = novo_encontro(seed_base=7)
        no_turno_do_bardo(encontro)
        encontro.ficha["pv_atuais"] = 5
        encontro.ficha["conjuracao"]["espacos_restantes"] = {"1": 0}
        resultado = encontro.conjurar("Curar Ferimentos")
        self.assertEqual(resultado["status"], "bloqueado")
        self.assertEqual(encontro.ficha["pv_atuais"], 5)

    def test_alvo_que_nao_e_o_proprio_bardo_e_recusado(self):
        encontro = novo_encontro()
        no_turno_do_bardo(encontro)
        resultado = encontro.conjurar("Curar Ferimentos", alvo_id="goblin-1")
        self.assertEqual(resultado["status"], "bloqueado")
        self.assertEqual(encontro.ficha["conjuracao"]["espacos_restantes"], {"1": 2})


if __name__ == "__main__":
    unittest.main()
