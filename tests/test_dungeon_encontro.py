"""Encontro de cripta com o Bardo contra Goblin e Esqueleto.

Regras passam pelo Orquestrador; estes testes conferem o encaminhamento, a
geometria do mapa e a consistência entre o estado final e o log do combate.
"""

import unittest

from dungeon_game.combat_board import BoardPosition
from dungeon_game.combat_session import EncounterStatus
from dungeon_game.encontro import Encontro, calcular_ca, criar_ficha_bardo
from orchestrator import OrquestradorAcoes
from rule_engine import build_default_engine

INIMIGOS = [("goblin-1", "goblin", (13, 3)), ("esqueleto-1", "esqueleto", (13, 10))]


def novo_encontro(seed_base: int = 100) -> Encontro:
    orquestrador = OrquestradorAcoes(build_default_engine())
    ficha = criar_ficha_bardo()
    ficha["ca"] = calcular_ca(orquestrador, ficha)
    return Encontro(orquestrador, "cripta_inicial", ficha, INIMIGOS, seed_base=seed_base)


def jogar_politica_simples(encontro: Encontro, limite: int = 60) -> None:
    """Jogador se aproxima do inimigo mais próximo e ataque quando estiver ao alcance."""
    jogador = encontro.ficha["id"]
    for _ in range(limite):
        if encontro.status is not EncounterStatus.ACTIVE:
            return
        if encontro.turno_de == jogador:
            vivos = [c for c in encontro.inimigos if c not in encontro.inimigos_derrotados]
            if not vivos:
                return
            alvo = min(vivos, key=lambda c: encontro.distancia_pes(jogador, c))
            if encontro.distancia_pes(jogador, alvo) <= 5:
                encontro.atacar_jogador(alvo)
            else:
                alcancaveis = encontro.board.reachable_positions(
                    encontro.posicoes[jogador], encontro.deslocamento_pes, occupied=encontro._ocupadas(jogador)
                )
                melhor = min(alcancaveis, key=lambda p: encontro.board.distance_feet(p, encontro.posicoes[alvo]))
                encontro.mover((melhor.x, melhor.y))
        encontro.encerrar_turno()


class FichaEMapaTests(unittest.TestCase):
    def test_ficha_do_bardo_vem_do_criador_e_tem_ca_do_motor(self):
        encontro = novo_encontro()
        ficha = encontro.ficha
        self.assertEqual(ficha["classe"], "bardo")
        self.assertEqual(ficha["ca"], 13)  # Couro (11) + Destreza +2
        self.assertEqual(ficha["deslocamento_pes"], 30)  # 9 m no criador
        self.assertEqual(ficha["pv_atuais"], ficha["pv_maximo"])

    def test_tabuleiro_bloqueia_paredes_porta_e_pilares(self):
        board = novo_encontro().board
        self.assertEqual((board.width, board.height), (24, 14))
        for pos in [(0, 0), (0, 7), (4, 3)]:  # canto, porta, pilar
            self.assertFalse(board.is_walkable(BoardPosition(*pos)), pos)
        self.assertTrue(board.is_walkable(BoardPosition(2, 7)))  # entrada do jogador

    def test_iniciativa_ordena_os_tres_combatentes(self):
        encontro = novo_encontro()
        totais = [c.initiative for c in encontro.session.combatants]
        self.assertEqual(totais, sorted(totais, reverse=True))
        self.assertEqual({c.id for c in encontro.session.combatants}, {"bardo-1", "goblin-1", "esqueleto-1"})


class MovimentoEAlcanceTests(unittest.TestCase):
    def test_movimento_alem_do_deslocamento_e_recusado(self):
        encontro = novo_encontro()
        while encontro.turno_de != "bardo-1":
            encontro.encerrar_turno()
        resultado = encontro.mover((20, 7))  # 18 casas, bem além de 6
        self.assertEqual(resultado["motivo"], "casa_fora_do_alcance_ou_ocupada")

    def test_movimento_em_casa_parede_e_recusado(self):
        encontro = novo_encontro()
        while encontro.turno_de != "bardo-1":
            encontro.encerrar_turno()
        self.assertEqual(encontro.mover((0, 0))["status"], "bloqueado")

    def test_movimento_valido_gasta_pes_do_alcance(self):
        encontro = novo_encontro()
        while encontro.turno_de != "bardo-1":
            encontro.encerrar_turno()
        resultado = encontro.mover((5, 7))  # 3 casas
        self.assertEqual(resultado, {"status": "resolvido", "custo_pes": 15})

    def test_ataque_fora_do_alcance_e_recusado(self):
        encontro = novo_encontro()
        while encontro.turno_de != "bardo-1":
            encontro.encerrar_turno()
        self.assertEqual(encontro.atacar_jogador("goblin-1")["motivo"], "alvo_fora_do_alcance")

    def test_acao_fora_do_turno_nao_e_permitida(self):
        encontro = novo_encontro()
        while encontro.turno_de == "bardo-1":
            encontro.encerrar_turno()
        with self.assertRaises(ValueError):
            encontro.mover((3, 7))


class CombateCompletoTests(unittest.TestCase):
    def test_combate_termina_em_vitoria_ou_derrota(self):
        encontro = novo_encontro()
        jogar_politica_simples(encontro)
        self.assertIn(encontro.status, {EncounterStatus.COMPLETED, EncounterStatus.DEFEATED})

    def test_estado_final_bate_com_o_log(self):
        encontro = novo_encontro()
        jogar_politica_simples(encontro)
        ataques_inimigos = [e for e in encontro.log if e["evento"] == "ataque_inimigo" and e.get("acertou")]
        dano_sofrido = sum(e["dano"] for e in ataques_inimigos)
        self.assertEqual(encontro.ficha["pv_atuais"], max(0, encontro.ficha["pv_maximo"] - dano_sofrido))
        for cid, inimigo in encontro.inimigos.items():
            dano_causado = sum(
                e["dano"]
                for e in encontro.log
                if e["evento"] == "ataque_jogador" and e.get("alvo") == cid and e.get("acertou")
            )
            self.assertEqual(inimigo["pv_atuais"], max(0, inimigo["pv_maximo"] - dano_causado), cid)

    def test_vitoria_exige_todos_os_inimigos_derrubados(self):
        encontro = novo_encontro()
        jogar_politica_simples(encontro)
        if encontro.status is EncounterStatus.COMPLETED:
            self.assertTrue(all(i["pv_atuais"] == 0 for i in encontro.inimigos.values()))
            self.assertGreater(encontro.ficha["pv_atuais"], 0)
        else:
            self.assertEqual(encontro.ficha["pv_atuais"], 0)

    def test_combate_e_reproduzivel_com_a_mesma_seed(self):
        primeiro = novo_encontro(seed_base=100)
        segundo = novo_encontro(seed_base=100)
        jogar_politica_simples(primeiro)
        jogar_politica_simples(segundo)
        self.assertEqual(primeiro.log, segundo.log)


if __name__ == "__main__":
    unittest.main()
