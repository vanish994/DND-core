"""Encontro de cripta com o Bardo contra Goblin e Esqueleto.

Regras passam pelo Orquestrador; estes testes conferem o encaminhamento, a
geometria do mapa e a consistência entre o estado final e o log do combate.
"""

import unittest

from dungeon_game.combat_board import BoardPosition
from dungeon_game.combat_session import EncounterStatus
from dungeon_game.encontro import (
    Encontro,
    calcular_ca,
    criar_ficha_artifice,
    criar_ficha_barbaro,
    criar_ficha_bardo,
    criar_ficha_bruxo,
    criar_ficha_clerigo,
    criar_ficha_druida,
    criar_ficha_feiticeiro,
    criar_ficha_guardiao,
    criar_ficha_guerreiro,
    criar_ficha_ladino,
    criar_ficha_mago,
    criar_ficha_monge,
    criar_ficha_paladino,
    criar_ficha_personagem,
    listar_classes,
    listar_especies_jogaveis,
)
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
        self.assertEqual(encontro.movimento_usado_pes, 15)
        self.assertEqual(encontro.movimento_restante_pes, 15)

    def test_movimentos_sucessivos_compartilham_o_deslocamento_do_turno(self):
        encontro = novo_encontro()
        while encontro.turno_de != "bardo-1":
            encontro.encerrar_turno()

        self.assertEqual(encontro.mover((5, 7)), {"status": "resolvido", "custo_pes": 15})
        self.assertEqual(encontro.mover((8, 7)), {"status": "resolvido", "custo_pes": 15})
        self.assertEqual(encontro.movimento_usado_pes, 30)
        self.assertEqual(encontro.movimento_restante_pes, 0)
        self.assertEqual(
            encontro.mover((9, 7)), {"status": "bloqueado", "motivo": "deslocamento_esgotado"}
        )

    def test_ataque_fora_do_alcance_e_recusado(self):
        encontro = novo_encontro()
        while encontro.turno_de != "bardo-1":
            encontro.encerrar_turno()
        self.assertEqual(encontro.atacar_jogador("goblin-1")["motivo"], "alvo_fora_do_alcance")
        self.assertFalse(encontro.acao_principal_usada)

    def test_acao_principal_so_pode_ser_usada_uma_vez_e_nao_gasta_movimento(self):
        encontro = novo_encontro()
        while encontro.turno_de != "bardo-1":
            encontro.encerrar_turno()
        encontro.posicoes["goblin-1"] = BoardPosition(5, 7)

        self.assertEqual(encontro.mover((4, 7)), {"status": "resolvido", "custo_pes": 10})
        encontro._proxima_semente = lambda: 25  # 1 natural: o ataque erra, mas a ação é gasta.
        ataque = encontro.atacar_jogador("goblin-1")
        self.assertEqual(ataque, {"status": "resolvido", "acertou": False})
        self.assertTrue(encontro.acao_principal_usada)
        pv_goblin = encontro.inimigos["goblin-1"]["pv_atuais"]
        self.assertEqual(
            encontro.atacar_jogador("goblin-1"), {"status": "bloqueado", "motivo": "acao_principal_usada"}
        )
        self.assertEqual(encontro.inimigos["goblin-1"]["pv_atuais"], pv_goblin)

        # O personagem ainda pode terminar de se mover depois de atacar.
        self.assertEqual(encontro.mover((2, 7)), {"status": "resolvido", "custo_pes": 10})
        self.assertEqual(encontro.movimento_usado_pes, 20)
        self.assertEqual(encontro.movimento_restante_pes, 10)

    def test_conjuracao_gasta_acao_e_acoes_invalidas_nao_a_gastam(self):
        encontro = novo_encontro()
        while encontro.turno_de != "bardo-1":
            encontro.encerrar_turno()
        espacos_antes = encontro.ficha["conjuracao"]["espacos_restantes"]["1"]

        bloqueada = encontro.conjurar("Luz")
        self.assertEqual(bloqueada["status"], "bloqueado")
        self.assertFalse(encontro.acao_principal_usada)

        conjuracao = encontro.conjurar("Curar Ferimentos")
        self.assertEqual(conjuracao["status"], "resolvido")
        self.assertTrue(encontro.acao_principal_usada)
        espacos_apos = encontro.ficha["conjuracao"]["espacos_restantes"]["1"]
        self.assertEqual(espacos_apos, espacos_antes - 1)
        self.assertEqual(
            encontro.conjurar("Curar Ferimentos"),
            {"status": "bloqueado", "motivo": "acao_principal_usada"},
        )
        self.assertEqual(encontro.ficha["conjuracao"]["espacos_restantes"]["1"], espacos_apos)

    def test_encerrar_turno_restaura_movimento_e_acao_principal(self):
        encontro = novo_encontro()
        while encontro.turno_de != "bardo-1":
            encontro.encerrar_turno()
        encontro.mover((3, 7))
        encontro.conjurar("Curar Ferimentos")
        self.assertGreater(encontro.movimento_usado_pes, 0)
        self.assertTrue(encontro.acao_principal_usada)

        encontro.encerrar_turno()
        while encontro.status is EncounterStatus.ACTIVE and encontro.turno_de != "bardo-1":
            encontro.encerrar_turno()

        self.assertEqual(encontro.movimento_usado_pes, 0)
        self.assertEqual(encontro.movimento_restante_pes, encontro.deslocamento_pes)
        self.assertFalse(encontro.acao_principal_usada)

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


class TaticasEsqueletoEProgressaoTests(unittest.TestCase):
    def test_esqueleto_ataca_a_distancia_com_arco_curto_sem_precisar_encostar(self):
        encontro = novo_encontro(seed_base=100)
        # Avança até o turno do esqueleto-1 (posição inicial 13, 10; Bardo em 2, 7 -> 55 pés).
        while encontro.turno_de != "esqueleto-1":
            encontro.encerrar_turno()
        pos_inicial = encontro.posicoes["esqueleto-1"]
        resultado = encontro.encerrar_turno()
        self.assertEqual(resultado["acao"], "Shortbow")
        self.assertTrue(resultado["a_distancia"])
        self.assertEqual(encontro.posicoes["esqueleto-1"], pos_inicial)

    def test_esqueleto_usa_espada_curta_quando_adjacente(self):
        encontro = novo_encontro(seed_base=100)
        while encontro.turno_de != "esqueleto-1":
            encontro.encerrar_turno()
        encontro.posicoes["esqueleto-1"] = BoardPosition(3, 7)  # 5 pés de (2, 7)
        resultado = encontro.encerrar_turno()
        self.assertEqual(resultado["acao"], "Shortsword")
        self.assertFalse(resultado["a_distancia"])

    def test_vitoria_consolida_xp_do_bestiario_e_ouro_e_permite_avancar_para_sala_2(self):
        encontro = novo_encontro(seed_base=100)
        while encontro.turno_de != "bardo-1":
            encontro.encerrar_turno()

        # Recusa avançar antes de concluir o encontro.
        self.assertEqual(encontro.avancar_sala(), {"status": "bloqueado", "motivo": "encontro_nao_concluido"})

        # Simula derrota do primeiro inimigo e derrota o último com ataque corpo a corpo.
        encontro.inimigos["goblin-1"]["pv_atuais"] = 0
        encontro._marcar_derrotado("goblin-1")
        self.assertEqual(encontro.status, EncounterStatus.ACTIVE)
        self.assertIsNone(encontro.recompensa)

        encontro.posicoes["esqueleto-1"] = BoardPosition(3, 7)
        encontro.inimigos["esqueleto-1"]["pv_atuais"] = 1
        encontro._proxima_semente = lambda: 1  # semente 1 acerta
        ataque = encontro.atacar_jogador("esqueleto-1")
        self.assertTrue(ataque["derrubado"])
        self.assertEqual(encontro.status, EncounterStatus.COMPLETED)

        # Goblin (50 XP) + Skeleton (50 XP) = 100 XP no bestiário oficial; 15 PO na cripta inicial.
        self.assertEqual(encontro.recompensa, {"xp": 100, "ouro_po": 15})
        self.assertEqual(encontro.ficha["xp"], 100)
        self.assertEqual(encontro.ficha["ouro_po"], 15)
        self.assertEqual(encontro.proxima_sala, "santuario_circular")

        # Avança para a Sala 2 (Santuário Circular), preservando PV, espaços, XP e ouro da ficha.
        encontro.ficha["pv_atuais"] = 8
        transicao = encontro.avancar_sala()
        self.assertEqual(
            transicao,
            {"status": "resolvido", "mapa_id": "santuario_circular", "andar": 1, "sala": 2},
        )
        self.assertEqual(encontro.status, EncounterStatus.ACTIVE)
        self.assertEqual(encontro.ficha["pv_atuais"], 8)
        self.assertEqual(encontro.ficha["xp"], 100)
        self.assertEqual(encontro.ficha["ouro_po"], 15)
        self.assertEqual((encontro.board.width, encontro.board.height), (42, 26))
        self.assertEqual(set(encontro.inimigos), {"goblin-1", "esqueleto-1", "goblin-arqueiro-1"})
        self.assertEqual(encontro.proxima_sala, "catacumba_dos_mortos")

        # Snapshot da Sala 2 preserva o estado completo.
        restaurado = Encontro.from_state(encontro.orquestrador, encontro.to_state())
        self.assertEqual(restaurado.mapa_id, "santuario_circular")
        self.assertEqual(restaurado.sala_numero, 2)
        self.assertEqual(restaurado.ficha["xp"], 100)
        self.assertEqual(restaurado.ficha["ouro_po"], 15)

        # Conclui a Sala 2 (XP: Goblin 50 + Esqueleto 50 + Goblin Arqueiro 50 = 150 XP, +30 PO) e avança à Sala 3.
        for cid in list(encontro.inimigos):
            encontro.inimigos[cid]["pv_atuais"] = 0
            encontro._marcar_derrotado(cid)
        self.assertEqual(encontro.status, EncounterStatus.COMPLETED)
        self.assertEqual(encontro.recompensa, {"xp": 150, "ouro_po": 30})
        self.assertEqual(encontro.ficha["xp"], 250)
        self.assertEqual(encontro.ficha["ouro_po"], 45)

        transicao_3 = encontro.avancar_sala()
        self.assertEqual(
            transicao_3,
            {"status": "resolvido", "mapa_id": "catacumba_dos_mortos", "andar": 1, "sala": 3},
        )
        self.assertEqual(set(encontro.inimigos), {"zumbi-1", "cultista-1", "carnical-1"})
        self.assertEqual(encontro.proxima_sala, "camara_profana")

        # Conclui a Sala 3 (XP: Zumbi 50 + Cultista 25 + Carniçal 200 = 275 XP, +45 PO) e avança à Sala 4 (Chefe).
        # Com 525 XP (>= 300 XP), o personagem sobe automaticamente para o Nível 2 pelo Rule Engine!
        pv_max_antes = encontro.ficha["pv_maximo"]
        for cid in list(encontro.inimigos):
            encontro.inimigos[cid]["pv_atuais"] = 0
            encontro._marcar_derrotado(cid)
        self.assertEqual(encontro.recompensa, {"xp": 275, "ouro_po": 45})
        self.assertEqual(encontro.ficha["xp"], 525)
        self.assertEqual(encontro.ficha["ouro_po"], 90)
        self.assertEqual(encontro.ficha["nivel"], 2)
        self.assertIsNotNone(encontro.subida_nivel)
        self.assertEqual(encontro.subida_nivel["nivel"], 2)
        self.assertGreater(encontro.ficha["pv_maximo"], pv_max_antes)
        self.assertEqual(encontro.ficha["dados_vida_maximos"], 2)
        self.assertEqual(encontro.ficha["conjuracao"]["espacos_totais"]["1"], 3)

        # Faz um Descanso Curto antes da Sala 4 para gastar 1 Dado de Vida e recuperar PV.
        encontro.ficha["pv_atuais"] = 5
        descanso = encontro.descansar_curto(dados_vida=1)
        self.assertEqual(descanso["status"], "resolvido")
        self.assertEqual(descanso["dados_vida_gastos"], 1)
        self.assertGreater(encontro.ficha["pv_atuais"], 5)
        self.assertEqual(
            encontro.descansar_curto(dados_vida=1),
            {"status": "bloqueado", "motivo": "descanso_curto_ja_realizado"},
        )

        transicao_4 = encontro.avancar_sala()
        self.assertEqual(
            transicao_4,
            {"status": "resolvido", "mapa_id": "camara_profana", "andar": 1, "sala": 4},
        )
        self.assertEqual(set(encontro.inimigos), {"sombra-1", "armadura-animada-1", "aparicao-1"})
        self.assertEqual(encontro.proxima_sala, "sarcofago_do_rei_mumia")
        self.assertFalse(encontro.descanso_curto_usado)

        # Conclui a Sala 4 (+1000 XP -> 1525 XP >= 900 XP) -> sobe para o Nível 3 com Subclasse!
        ca_antes = encontro.ficha["ca"]
        for cid in list(encontro.inimigos):
            encontro.inimigos[cid]["pv_atuais"] = 0
            encontro._marcar_derrotado(cid)
        self.assertEqual(encontro.ficha["nivel"], 3)
        self.assertEqual(encontro.ficha["subclasse"], "colegio_da_bravura")
        self.assertEqual(encontro.ficha["subclasse_nome"], "Colégio da Bravura")
        self.assertEqual(encontro.ficha["ca"], ca_antes + 1)
        self.assertEqual(encontro.subida_nivel["subclasse"], "colegio_da_bravura")

        transicao_5 = encontro.avancar_sala()
        self.assertEqual(
            transicao_5,
            {"status": "resolvido", "mapa_id": "sarcofago_do_rei_mumia", "andar": 1, "sala": 5},
        )
        self.assertEqual(set(encontro.inimigos), {"espectro-1", "esqueleto-minotauro-1", "mumia-1"})
        self.assertIsNone(encontro.proxima_sala)


class MongeEncontroTests(unittest.TestCase):
    def test_ficha_monge_usa_defesa_sem_armadura_e_artes_marciais_do_motor(self):
        orquestrador = OrquestradorAcoes(build_default_engine())
        classes = [c["id"] for c in listar_classes()]
        self.assertEqual(
            classes,
            [
                "bardo",
                "monge",
                "guerreiro",
                "barbaro",
                "ladino",
                "clerigo",
                "mago",
                "paladino",
                "druida",
                "artifice",
                "guardiao",
                "feiticeiro",
                "bruxo",
            ],
        )

        ficha = criar_ficha_monge()
        ficha["ca"] = calcular_ca(orquestrador, ficha)
        self.assertEqual(ficha["classe"], "monge")
        self.assertEqual(ficha["arma_padrao"], "Cajado")
        # 10 + Destreza (+3) + Sabedoria (+2) = 15
        self.assertEqual(ficha["ca"], 15)

        encontro = Encontro(orquestrador, "cripta_inicial", ficha, INIMIGOS, seed_base=100)
        while encontro.turno_de != "monge-1":
            encontro.encerrar_turno()

        self.assertTrue(encontro.acao_bonus_disponivel)
        self.assertEqual(encontro.arma_principal, "Cajado")

        # Coloca esqueleto adjacente: ataque com Cajado aplica vulnerabilidade a dano contundente.
        encontro.posicoes["esqueleto-1"] = BoardPosition(3, 7)
        encontro.inimigos["esqueleto-1"]["pv_maximo"] = 30
        encontro.inimigos["esqueleto-1"]["pv_atuais"] = 30
        encontro._proxima_semente = lambda: 1  # semente 1 garante acerto
        ataque_principal = encontro.atacar_jogador("esqueleto-1")
        self.assertEqual(ataque_principal["status"], "resolvido")
        self.assertEqual(ataque_principal["arma"], "Cajado")
        self.assertFalse(ataque_principal["acao_bonus"])
        self.assertTrue(ataque_principal["acertou"])
        self.assertEqual(ataque_principal["defesa_aplicada"], "vulnerabilidade")
        self.assertEqual(ataque_principal["dano"] % 2, 0)
        self.assertTrue(encontro.acao_principal_usada)
        self.assertFalse(encontro.acao_bonus_usada)

        # Ainda no mesmo turno, o Monge pode executar o Golpe Desarmado bônus (Artes Marciais).
        ataque_bonus = encontro.atacar_jogador("esqueleto-1", acao_bonus=True)
        self.assertEqual(ataque_bonus["status"], "resolvido")
        self.assertEqual(ataque_bonus["arma"], "Ataque Desarmado")
        self.assertTrue(ataque_bonus["acao_bonus"])
        self.assertTrue(ataque_bonus["acertou"])
        self.assertEqual(ataque_bonus["defesa_aplicada"], "vulnerabilidade")
        self.assertTrue(encontro.acao_bonus_usada)
        self.assertFalse(encontro.acao_bonus_disponivel)

        # Segunda tentativa de ação bônus no mesmo turno é bloqueada.
        self.assertEqual(
            encontro.atacar_jogador("esqueleto-1", acao_bonus=True),
            {"status": "bloqueado", "motivo": "acao_bonus_usada"},
        )

    def test_bardo_nao_tem_golpe_desarmado_bonus(self):
        encontro = novo_encontro(seed_base=100)
        while encontro.turno_de != "bardo-1":
            encontro.encerrar_turno()
        self.assertFalse(encontro.acao_bonus_disponivel)
        self.assertEqual(
            encontro.atacar_jogador("goblin-1", acao_bonus=True),
            {"status": "bloqueado", "motivo": "acao_bonus_indisponivel"},
        )


class GuerreiroEncontroTests(unittest.TestCase):
    def test_guerreiro_tem_ca_19_ataca_a_distancia_e_corpo_a_corpo_e_usa_recuperar_folego(self):
        orquestrador = OrquestradorAcoes(build_default_engine())
        ficha = criar_ficha_guerreiro()
        ficha["ca"] = calcular_ca(orquestrador, ficha)
        self.assertEqual(ficha["classe"], "guerreiro")
        # Cota de Malha (16) + Escudo (+2) + Estilo de Luta Defensivo (+1) = 19
        self.assertEqual(ficha["ca"], 19)
        self.assertEqual(ficha["pv_maximo"], 14)

        encontro = Encontro(orquestrador, "cripta_inicial", ficha, INIMIGOS, seed_base=100)
        while encontro.turno_de != "guerreiro-1":
            encontro.encerrar_turno()

        self.assertEqual(encontro.arma_principal, "Espada Longa")
        self.assertEqual(encontro.arma_distancia, "Arco Curto")
        self.assertEqual(encontro.ficha["maestrias_arma"], ["Espada Longa", "Arco Curto", "Machado de Batalha"])
        self.assertEqual(encontro.recursos_recuperar_folego()["usos_restantes"], 2)

        # À distância (> 5 pés), ataca com Arco Curto validando linha de visão e alcance pelo motor.
        encontro._proxima_semente = lambda: 1
        ataque_arco = encontro.atacar_jogador("goblin-1")
        self.assertEqual(ataque_arco["status"], "resolvido")
        self.assertEqual(ataque_arco["arma"], "Arco Curto")
        self.assertTrue(ataque_arco["a_distancia"])
        self.assertTrue(ataque_arco["acertou"])

        # No mesmo turno, usa Recuperar o Fôlego como ação bônus para curar 1d10 + nível.
        encontro.ficha["pv_atuais"] = 5
        folego = encontro.recuperar_folego()
        self.assertEqual(folego["status"], "resolvido")
        self.assertEqual(folego["recurso"], "recuperar_folego")
        self.assertGreater(folego["curado"], 0)
        self.assertEqual(encontro.ficha["pv_atuais"], 5 + folego["curado"])
        self.assertEqual(folego["usos_restantes"], 1)
        self.assertTrue(encontro.acao_bonus_usada)

        # Não pode usar segunda ação bônus no mesmo turno.
        self.assertEqual(encontro.recuperar_folego(), {"status": "bloqueado", "motivo": "acao_bonus_usada"})


class BarbaroEncontroTests(unittest.TestCase):
    def test_barbaro_tem_defesa_sem_armadura_ativa_furia_soma_dano_e_resiste_dano_fisico(self):
        orquestrador = OrquestradorAcoes(build_default_engine())
        ficha = criar_ficha_barbaro()
        ficha["ca"] = calcular_ca(orquestrador, ficha)
        self.assertEqual(ficha["classe"], "barbaro")
        # 10 + Destreza (+2) + Constituição (+2) = 14
        self.assertEqual(ficha["ca"], 14)
        self.assertEqual(ficha["pv_maximo"], 16)

        encontro = Encontro(orquestrador, "cripta_inicial", ficha, INIMIGOS, seed_base=100)
        while encontro.turno_de != "barbaro-1":
            encontro.encerrar_turno()

        self.assertEqual(encontro.arma_principal, "Machado Grande")
        self.assertEqual(encontro.recursos_furia()["usos_restantes"], 2)
        self.assertFalse(encontro.recursos_furia()["ativa"])

        # Ativa Fúria como ação bônus.
        furia = encontro.ativar_furia()
        self.assertEqual(furia["status"], "resolvido")
        self.assertTrue(furia["ativa"])
        self.assertEqual(furia["dano_adicional"], 2)
        self.assertEqual(furia["usos_restantes"], 1)
        self.assertTrue(encontro.acao_bonus_usada)
        self.assertEqual(encontro.ficha["resistencias_dano"], ["contundente", "cortante", "perfurante"])

        # Ataque corpo a corpo com Machado Grande soma +2 de dano de Fúria.
        encontro.posicoes["goblin-1"] = BoardPosition(3, 7)
        encontro.inimigos["goblin-1"]["pv_maximo"] = 30
        encontro.inimigos["goblin-1"]["pv_atuais"] = 30
        encontro._proxima_semente = lambda: 1
        ataque = encontro.atacar_jogador("goblin-1")
        self.assertEqual(ataque["status"], "resolvido")
        self.assertEqual(ataque["arma"], "Machado Grande")
        self.assertTrue(ataque["acertou"])
        self.assertEqual(ataque["dano_furia"], 2)
        # Com seed=1 ("1:dano"): 1d12=5 + Força(+3) + Fúria(+2) = 10
        self.assertEqual(ataque["dano"], 10)

        # Quando um inimigo acerta o Bárbaro em Fúria, o dano físico é reduzido pela metade (damage_defenses).
        from dungeon_game.combate_inimigo import atacar as atacar_inimigo

        encontro.ficha["pv_atuais"] = 16
        ataque_monstro = atacar_inimigo(
            orquestrador,
            "goblin",
            encontro.ficha,
            seed=1,
            distancia_pes=5,
        )
        self.assertEqual(ataque_monstro["status"], "resolved")
        self.assertEqual(ataque_monstro["ataque"]["result"], "hit")
        self.assertEqual(ataque_monstro["defesa_aplicada"], "resistencia")
        self.assertLess(ataque_monstro["dano"], ataque_monstro["dano_bruto"])


class LadinoEncontroTests(unittest.TestCase):
    def test_ladino_usa_mirar_e_aplica_ataque_furtivo_uma_vez_por_turno(self):
        orquestrador = OrquestradorAcoes(build_default_engine())
        ficha = criar_ficha_ladino()
        ficha["ca"] = calcular_ca(orquestrador, ficha)
        self.assertEqual(ficha["classe"], "ladino")
        # Armadura de Couro (11) + Destreza (+3) = 14
        self.assertEqual(ficha["ca"], 14)
        self.assertEqual(ficha["pv_maximo"], 10)

        encontro = Encontro(orquestrador, "cripta_inicial", ficha, INIMIGOS, seed_base=100)
        while encontro.turno_de != "ladino-1":
            encontro.encerrar_turno()

        self.assertEqual(encontro.arma_principal, "Rapieira")
        self.assertEqual(encontro.arma_distancia, "Arco Curto")
        self.assertTrue(encontro.recursos_ladino()["mirar_disponivel"])

        # Usa Mirar (ação bônus sem se mover): ganha vantagem no próximo ataque e zera o deslocamento restante.
        mirar = encontro.mirar()
        self.assertEqual(mirar["status"], "resolvido")
        self.assertTrue(mirar["vantagem_proximo_ataque"])
        self.assertEqual(encontro.movimento_restante_pes, 0)
        self.assertTrue(encontro.acao_bonus_usada)

        # Ataque à distância com Arco Curto consome a vantagem de Mirar e aplica +1d6 de Ataque Furtivo.
        encontro.inimigos["goblin-1"]["pv_maximo"] = 30
        encontro.inimigos["goblin-1"]["pv_atuais"] = 30
        encontro._proxima_semente = lambda: 1
        ataque = encontro.atacar_jogador("goblin-1")
        self.assertEqual(ataque["status"], "resolvido")
        self.assertEqual(ataque["arma"], "Arco Curto")
        self.assertTrue(ataque["a_distancia"])
        self.assertTrue(ataque["acertou"])
        self.assertTrue(ataque["ataque_furtivo"])
        self.assertTrue(encontro.ataque_furtivo_usado)


class ClerigoEncontroTests(unittest.TestCase):
    def test_clerigo_conjura_escudo_da_fe_como_acao_bonus_e_cura_com_sabedoria(self):
        orquestrador = OrquestradorAcoes(build_default_engine())
        ficha = criar_ficha_clerigo()
        ficha["ca"] = calcular_ca(orquestrador, ficha)
        self.assertEqual(ficha["classe"], "clerigo")
        # Cota de Malha Parcial (13) + Destreza (0) + Escudo (+2) = 15
        self.assertEqual(ficha["ca"], 15)
        self.assertEqual(ficha["pv_maximo"], 12)

        encontro = Encontro(orquestrador, "cripta_inicial", ficha, INIMIGOS, seed_base=100)
        while encontro.turno_de != "clerigo-1":
            encontro.encerrar_turno()

        self.assertEqual(encontro.arma_principal, "Maça")

        # Conjura Escudo da Fé (ação bônus): aumenta CA de 15 para 17 sem gastar ação principal.
        escudo = encontro.conjurar("Escudo da Fé")
        self.assertEqual(escudo["status"], "resolvido")
        self.assertEqual(escudo["bonus_ca"], 2)
        self.assertEqual(encontro.ficha["ca"], 17)
        self.assertTrue(encontro.acao_bonus_usada)
        self.assertFalse(encontro.acao_principal_usada)

        # Ainda no mesmo turno, conjura Curar Ferimentos (ação principal) somando Sabedoria (+3).
        encontro.ficha["pv_atuais"] = 3
        encontro._proxima_semente = lambda: 1
        cura = encontro.conjurar("Curar Ferimentos")
        self.assertEqual(cura["status"], "resolvido")
        self.assertGreaterEqual(cura["rolagem"], 2 + encontro.ficha["modificadores"]["sabedoria"])
        self.assertEqual(encontro.ficha["pv_atuais"], min(12, 3 + cura["rolagem"]))
        self.assertTrue(encontro.acao_principal_usada)


class MagoEncontroTests(unittest.TestCase):
    def test_mago_conjura_armadura_arcana_raio_de_fogo_misseis_magicos_e_usa_recuperacao_arcana(self):
        orquestrador = OrquestradorAcoes(build_default_engine())
        ficha = criar_ficha_mago()
        ficha["ca"] = calcular_ca(orquestrador, ficha)
        self.assertEqual(ficha["classe"], "mago")
        # Sem armadura: 10 + Destreza (+2) = 12
        self.assertEqual(ficha["ca"], 12)
        self.assertEqual(ficha["pv_maximo"], 8)

        encontro = Encontro(orquestrador, "cripta_inicial", ficha, INIMIGOS, seed_base=100)
        while encontro.turno_de != "mago-1":
            encontro.encerrar_turno()

        # Conjura Armadura Arcana: CA sobe para 13 + Destreza (+2) = 15.
        armadura = encontro.conjurar("Armadura Arcana")
        self.assertEqual(armadura["status"], "resolvido")
        self.assertEqual(encontro.ficha["ca"], 15)
        self.assertEqual(encontro.ficha["conjuracao"]["espacos_restantes"]["1"], 1)

        # Usa Recuperação Arcana (ação bônus) para recuperar o espaço de 1º círculo gasto.
        rec = encontro.recuperacao_arcana()
        self.assertEqual(rec["status"], "resolvido")
        self.assertEqual(rec["circulos_recuperados"], 1)
        self.assertEqual(encontro.ficha["conjuracao"]["espacos_restantes"]["1"], 2)
        self.assertEqual(rec["usos_restantes"], 0)

        # Na rodada seguinte: conjura Mísseis Mágicos (3 dardos de 1d4+1 automáticos).
        encontro.acao_principal_usada = False
        encontro.acao_bonus_usada = False
        encontro.inimigos["goblin-1"]["pv_maximo"] = 30
        encontro.inimigos["goblin-1"]["pv_atuais"] = 30
        encontro._proxima_semente = lambda: 1
        misseis = encontro.conjurar("Mísseis Mágicos", "goblin-1")
        self.assertEqual(misseis["status"], "resolvido")
        self.assertEqual(misseis["dardos"], 3)
        self.assertGreaterEqual(misseis["dano"], 6)
        self.assertEqual(encontro.inimigos["goblin-1"]["pv_atuais"], 30 - misseis["dano"])

        # Na rodada seguinte: conjura truque Raio de Fogo (ataque mágico à distância, 1d10 ígneo).
        encontro.acao_principal_usada = False
        encontro._proxima_semente = lambda: 1
        raio = encontro.conjurar("Raio de Fogo", "goblin-1")
        self.assertEqual(raio["status"], "resolvido")
        self.assertTrue(raio["acertou"])
        self.assertGreaterEqual(raio["dano"], 1)


class PaladinoEncontroTests(unittest.TestCase):
    def test_paladino_usa_maos_consagradas_e_escudo_da_fe_e_ataca_com_espada_longa(self):
        orquestrador = OrquestradorAcoes(build_default_engine())
        ficha = criar_ficha_paladino()
        ficha["ca"] = calcular_ca(orquestrador, ficha)
        self.assertEqual(ficha["classe"], "paladino")
        # Cota de Malha (16) + Escudo (+2) = 18
        self.assertEqual(ficha["ca"], 18)
        self.assertEqual(ficha["pv_maximo"], 14)

        encontro = Encontro(orquestrador, "cripta_inicial", ficha, INIMIGOS, seed_base=100)
        while encontro.turno_de != "paladino-1":
            encontro.encerrar_turno()

        self.assertEqual(encontro.arma_principal, "Espada Longa")
        self.assertEqual(encontro.recursos_maos_consagradas()["pool_restante"], 5)

        # Sofre dano e usa Mãos Consagradas (ação bônus) para curar 4 PV.
        encontro.ficha["pv_atuais"] = 8
        cura = encontro.maos_consagradas(4)
        self.assertEqual(cura["status"], "resolvido")
        self.assertEqual(cura["curado"], 4)
        self.assertEqual(encontro.ficha["pv_atuais"], 12)
        self.assertEqual(encontro.ficha["pool_maos_consagradas"], 1)
        self.assertTrue(encontro.acao_bonus_usada)
        self.assertFalse(encontro.acao_principal_usada)

        # Ainda pode atacar com Espada Longa na ação principal.
        encontro.posicoes["goblin-1"] = BoardPosition(3, 7)
        encontro.inimigos["goblin-1"]["pv_maximo"] = 30
        encontro.inimigos["goblin-1"]["pv_atuais"] = 30
        encontro._proxima_semente = lambda: 1
        ataque = encontro.atacar_jogador("goblin-1")
        self.assertEqual(ataque["status"], "resolvido")
        self.assertTrue(ataque["acertou"])
        self.assertTrue(encontro.acao_principal_usada)

        # Na rodada seguinte: conjura Escudo da Fé (ação bônus) elevando CA para 20.
        encontro.acao_principal_usada = False
        encontro.acao_bonus_usada = False
        escudo = encontro.conjurar("Escudo da Fé")
        self.assertEqual(escudo["status"], "resolvido")
        self.assertEqual(encontro.ficha["ca"], 20)


class DruidaEncontroTests(unittest.TestCase):
    def test_druida_conjura_chicote_de_espinhos_puxando_alvo_e_palavra_curativa_bonus(self):
        orquestrador = OrquestradorAcoes(build_default_engine())
        ficha = criar_ficha_druida()
        ficha["ca"] = calcular_ca(orquestrador, ficha)
        self.assertEqual(ficha["classe"], "druida")
        # Armadura de Couro (11) + Destreza (+2) + Escudo (+2) = 15
        self.assertEqual(ficha["ca"], 15)
        self.assertEqual(ficha["pv_maximo"], 10)

        encontro = Encontro(orquestrador, "cripta_inicial", ficha, INIMIGOS, seed_base=100)
        while encontro.turno_de != "druida-1":
            encontro.encerrar_turno()

        self.assertEqual(encontro.arma_principal, "Cajado")

        # Coloca goblin-1 a 20 pés (4 casas) na mesma linha horizontal livre: (6, 7).
        encontro.posicoes["goblin-1"] = BoardPosition(6, 7)
        encontro.inimigos["goblin-1"]["pv_maximo"] = 30
        encontro.inimigos["goblin-1"]["pv_atuais"] = 30
        encontro._proxima_semente = lambda: 1
        chicote = encontro.conjurar("Chicote de Espinhos", "goblin-1")
        self.assertEqual(chicote["status"], "resolvido")
        self.assertTrue(chicote["acertou"])
        # Puxou o alvo em até 2 casas (10 pés) na direção do Druida em (2, 7) -> (4, 7).
        self.assertEqual(encontro.posicoes["goblin-1"], BoardPosition(4, 7))
        self.assertTrue(encontro.acao_principal_usada)
        self.assertFalse(encontro.acao_bonus_usada)

        # No mesmo turno, usa Palavra Curativa (ação bônus, 2d4 + Sabedoria).
        encontro.ficha["pv_atuais"] = 3
        encontro._proxima_semente = lambda: 1
        palavra = encontro.conjurar("Palavra Curativa")
        self.assertEqual(palavra["status"], "resolvido")
        self.assertGreaterEqual(palavra["rolagem"], 2 + encontro.ficha["modificadores"]["sabedoria"])
        self.assertEqual(encontro.ficha["pv_atuais"], min(10, 3 + palavra["rolagem"]))
        self.assertTrue(encontro.acao_bonus_usada)

        # Na rodada seguinte: conjura Rajada de Veneno (1d12 venenoso).
        encontro.acao_principal_usada = False
        encontro.acao_bonus_usada = False
        encontro._proxima_semente = lambda: 1
        rajada = encontro.conjurar("Rajada de Veneno", "goblin-1")
        self.assertEqual(rajada["status"], "resolvido")
        self.assertTrue(rajada["acertou"])
        self.assertGreaterEqual(rajada["dano"], 1)


class ArtificeEncontroTests(unittest.TestCase):
    def test_artifice_conjura_vitalidade_vazia_toque_chocante_e_ataca_com_besta_leve(self):
        orquestrador = OrquestradorAcoes(build_default_engine())
        ficha = criar_ficha_artifice()
        ficha["ca"] = calcular_ca(orquestrador, ficha)
        self.assertEqual(ficha["classe"], "artifice")
        # Cota de Malha Parcial (13) + Destreza (+2) + Escudo (+2) = 17
        self.assertEqual(ficha["ca"], 17)
        self.assertEqual(ficha["pv_maximo"], 10)

        encontro = Encontro(orquestrador, "cripta_inicial", ficha, INIMIGOS, seed_base=100)
        while encontro.turno_de != "artifice-1":
            encontro.encerrar_turno()

        self.assertEqual(encontro.arma_principal, "Maça")
        self.assertEqual(encontro.arma_distancia, "Besta Leve")
        self.assertEqual(encontro.ficha.get("foco_conjuracao"), "ferramentas_de_artifice")

        # Conjura Vitalidade Vazia (2d4+4 PV temporários).
        encontro._proxima_semente = lambda: 1
        vitalidade = encontro.conjurar("Vitalidade Vazia")
        self.assertEqual(vitalidade["status"], "resolvido")
        self.assertGreaterEqual(vitalidade["pv_temporarios"], 6)
        self.assertEqual(encontro.ficha["pv_temporarios"], vitalidade["pv_temporarios"])

        # Na rodada seguinte: conjura Toque Chocante (1d8 elétrico, alcance toque 5 pés).
        encontro.acao_principal_usada = False
        encontro.posicoes["goblin-1"] = BoardPosition(3, 7)
        encontro.inimigos["goblin-1"]["pv_maximo"] = 30
        encontro.inimigos["goblin-1"]["pv_atuais"] = 30
        encontro._proxima_semente = lambda: 1
        toque = encontro.conjurar("Toque Chocante", "goblin-1")
        self.assertEqual(toque["status"], "resolvido")
        self.assertTrue(toque["acertou"])
        self.assertGreaterEqual(toque["dano"], 1)

        # Na rodada seguinte: ataca à distância com Besta Leve (1d8+2 perfurante).
        encontro.acao_principal_usada = False
        encontro.posicoes["goblin-1"] = BoardPosition(6, 7)
        encontro._proxima_semente = lambda: 1
        disparo = encontro.atacar_jogador("goblin-1")
        self.assertEqual(disparo["status"], "resolvido")
        self.assertEqual(disparo["arma"], "Besta Leve")
        self.assertTrue(disparo["a_distancia"])
        self.assertTrue(disparo["acertou"])


class NovosMonstrosEncontroTests(unittest.TestCase):
    def test_imunidades_srd_em_magias_e_tatica_chefe_aparicao(self):
        orquestrador = OrquestradorAcoes(build_default_engine())
        ficha_bardo = criar_ficha_bardo()
        ficha_bardo["ca"] = calcular_ca(orquestrador, ficha_bardo)
        ficha_bardo["conjuracao"]["truques"].append("Zombaria Perversa")
        inimigos = [
            ("armadura-1", "armadura_animada", (13, 3)),
            ("aparicao-1", "aparicao", (13, 10)),
        ]
        encontro = Encontro(orquestrador, "cripta_inicial", ficha_bardo, inimigos, seed_base=100)
        while encontro.turno_de != "bardo-1":
            encontro.encerrar_turno()
        encontro.ficha["pv_atuais"] = encontro.ficha["pv_maximo"]
        encontro.posicoes["armadura-1"] = BoardPosition(6, 7)
        encontro.posicoes["aparicao-1"] = BoardPosition(8, 7)

        # Armadura Animada é imune a dano psíquico no SRD 5.2.1 -> Zombaria Perversa causa 0 de dano.
        encontro._salvaguarda_sabedoria = lambda cid, cd: {"result": "failure"}
        zombaria = encontro.conjurar("Zombaria Perversa", "armadura-1")
        self.assertEqual(zombaria["status"], "resolvido")
        self.assertEqual(zombaria["defesa_aplicada"], "imunidade")
        self.assertEqual(zombaria["dano"], 0)
        self.assertEqual(encontro.inimigos["armadura-1"]["pv_atuais"], 33)

        # Aparição (Wight) à distância usa Longbow; quando adjacente (5 pés), usa Longsword.
        acao_longe, geo_longe = encontro._avaliar_ataque_inimigo("aparicao-1")
        self.assertEqual(acao_longe["nome"], "Longbow")
        self.assertEqual(geo_longe["resultado"], "permitido")

        encontro.posicoes["aparicao-1"] = BoardPosition(3, 7)
        acao_perto, geo_perto = encontro._avaliar_ataque_inimigo("aparicao-1")
        self.assertEqual(acao_perto["nome"], "Longsword")
        self.assertEqual(geo_perto["resultado"], "permitido")

        # Carniçal (Ghoul) é imune a dano de veneno no SRD 5.2.1 -> Rajada de Veneno causa 0 de dano.
        ficha_druida = criar_ficha_druida()
        ficha_druida["ca"] = calcular_ca(orquestrador, ficha_druida)
        encontro_druida = Encontro(
            orquestrador,
            "cripta_inicial",
            ficha_druida,
            [("carnical-1", "carnical", (13, 3))],
            seed_base=100,
        )
        while encontro_druida.turno_de != "druida-1":
            encontro_druida.encerrar_turno()
        encontro_druida.ficha["pv_atuais"] = encontro_druida.ficha["pv_maximo"]
        encontro_druida.posicoes["carnical-1"] = BoardPosition(5, 7)
        encontro_druida._proxima_semente = lambda: 1
        veneno = encontro_druida.conjurar("Rajada de Veneno", "carnical-1")
        self.assertEqual(veneno["status"], "resolvido")
        self.assertTrue(veneno["acertou"])
        self.assertEqual(veneno["defesa_aplicada"], "imunidade")
        self.assertEqual(veneno["dano"], 0)
        self.assertEqual(encontro_druida.inimigos["carnical-1"]["pv_atuais"], 22)


class GuardiaoEncontroTests(unittest.TestCase):
    def test_guardiao_usa_inimigo_favorito_marca_do_predador_e_causa_1d6_extra(self):
        orquestrador = OrquestradorAcoes(build_default_engine())
        ficha = criar_ficha_guardiao()
        ficha["ca"] = calcular_ca(orquestrador, ficha)
        self.assertEqual(ficha["classe"], "guardiao")
        # Cota de Malha Parcial (13) + Destreza (+2 máx.) = 15
        self.assertEqual(ficha["ca"], 15)
        self.assertEqual(ficha["arma_padrao"], "Espada Curta")
        self.assertEqual(ficha["arma_distancia"], "Arco Longo")

        encontro = Encontro(orquestrador, "cripta_inicial", ficha, INIMIGOS, seed_base=100)
        self.assertEqual(encontro.ficha["usos_maximos_inimigo_favorito"], 2)
        while encontro.turno_de != "guardiao-1":
            encontro.encerrar_turno()
        encontro.ficha["pv_atuais"] = encontro.ficha["pv_maximo"]
        encontro.posicoes["goblin-1"] = BoardPosition(6, 7)
        encontro.inimigos["goblin-1"]["pv_maximo"] = 30
        encontro.inimigos["goblin-1"]["pv_atuais"] = 30

        # Conjura Marca do Predador (ação bônus) usando Inimigo Favorito (sem gastar espaço de magia).
        marca = encontro.conjurar("Marca do Predador", "goblin-1")
        self.assertEqual(marca["status"], "resolvido")
        self.assertEqual(marca["usos_inimigo_favorito"], 1)
        self.assertEqual(encontro.ficha["conjuracao"]["espacos_restantes"]["1"], 2)
        self.assertTrue(encontro.acao_bonus_usada)
        self.assertFalse(encontro.acao_principal_usada)
        self.assertEqual(encontro.ficha["alvo_marca_do_predador"], "goblin-1")

        # No mesmo turno, dispara Arco Longo contra o alvo marcado -> soma +1d6 de dano de Energia.
        encontro._proxima_semente = lambda: 1
        disparo = encontro.atacar_jogador("goblin-1")
        self.assertEqual(disparo["status"], "resolvido")
        self.assertEqual(disparo["arma"], "Arco Longo")
        self.assertTrue(disparo["a_distancia"])
        self.assertTrue(disparo["acertou"])
        self.assertGreaterEqual(disparo["dano_marca_do_predador"], 1)
        self.assertGreater(disparo["dano"], disparo["dano_marca_do_predador"])


class FeiticeiroEncontroTests(unittest.TestCase):
    def test_feiticeiro_ativa_feiticaria_inata_e_conjura_com_vantagem_e_cd_ampliada(self):
        orquestrador = OrquestradorAcoes(build_default_engine())
        ficha = criar_ficha_feiticeiro()
        ficha["ca"] = calcular_ca(orquestrador, ficha)
        self.assertEqual(ficha["classe"], "feiticeiro")
        # 10 + Destreza (+2) = 12
        self.assertEqual(ficha["ca"], 12)

        encontro = Encontro(orquestrador, "cripta_inicial", ficha, INIMIGOS, seed_base=100)
        self.assertEqual(encontro.ficha["usos_maximos_feiticaria_inata"], 2)
        while encontro.turno_de != "feiticeiro-1":
            encontro.encerrar_turno()
        encontro.ficha["pv_atuais"] = encontro.ficha["pv_maximo"]
        encontro.posicoes["goblin-1"] = BoardPosition(6, 7)
        encontro.inimigos["goblin-1"]["pv_maximo"] = 30
        encontro.inimigos["goblin-1"]["pv_atuais"] = 30

        # Ativa Feitiçaria Inata (ação bônus) via Rule Engine.
        inata = encontro.ativar_feiticaria_inata()
        self.assertEqual(inata["status"], "resolvido")
        self.assertEqual(inata["recurso"], "feiticaria_inata")
        self.assertEqual(inata["bonus_cd"], 1)
        self.assertTrue(inata["vantagem_ataque_magia"])
        self.assertEqual(inata["usos_restantes"], 1)
        self.assertTrue(encontro.ficha["feiticaria_inata_ativa"])
        self.assertEqual(encontro.ficha["bonus_cd_magia"], 1)
        self.assertTrue(encontro.ficha["vantagem_ataque_magia"])
        self.assertTrue(encontro.acao_bonus_usada)
        self.assertFalse(encontro.acao_principal_usada)

        # Ainda no mesmo turno, conjura Raio de Fogo com ação principal.
        encontro._proxima_semente = lambda: 1
        raio = encontro.conjurar("Raio de Fogo", "goblin-1")
        self.assertEqual(raio["status"], "resolvido")
        self.assertTrue(raio["acertou"])
        self.assertGreaterEqual(raio["dano"], 1)


class BruxoEncontroTests(unittest.TestCase):
    def test_bruxo_usa_armadura_de_sombras_armadura_de_agathys_raio_mistico_e_recupera_pacto_no_descanso(self):
        orquestrador = OrquestradorAcoes(build_default_engine())
        ficha = criar_ficha_bruxo()
        ficha["ca"] = calcular_ca(orquestrador, ficha)
        self.assertEqual(ficha["classe"], "bruxo")
        # Armadura de Sombras (Invocação Mística): 13 + Destreza (+2) = 15
        self.assertEqual(ficha["ca"], 15)
        self.assertEqual(ficha["invocacao_mistica"], "armadura_de_sombras")

        encontro = Encontro(orquestrador, "cripta_inicial", ficha, INIMIGOS, seed_base=100)
        while encontro.turno_de != "bruxo-1":
            encontro.encerrar_turno()
        encontro.ficha["pv_atuais"] = encontro.ficha["pv_maximo"]

        # Conjura Armadura de Agathys (1º círculo) -> 5 PV temporários e retaliação de gelo.
        agathys = encontro.conjurar("Armadura de Agathys")
        self.assertEqual(agathys["status"], "resolvido")
        self.assertEqual(agathys["pv_temporarios"], 5)
        self.assertEqual(encontro.ficha["pv_temporarios"], 5)
        self.assertEqual(encontro.ficha["armadura_de_agathys_dano"], 5)
        self.assertEqual(encontro.ficha["conjuracao"]["espacos_restantes"]["1"], 0)

        # Quando inimigo adjacente acerta ataque corpo a corpo, sofre 5 de dano de frio de Agathys.
        encontro.posicoes["goblin-1"] = BoardPosition(3, 7)
        encontro.inimigos["goblin-1"]["pv_maximo"] = 20
        encontro.inimigos["goblin-1"]["pv_atuais"] = 20
        encontro._proxima_semente = lambda: 2  # garante acerto do goblin
        ataque_goblin = encontro._atacar_com_inimigo("goblin-1")
        self.assertIsNotNone(ataque_goblin)
        if ataque_goblin["acertou"]:
            self.assertEqual(ataque_goblin["dano_retaliacao_agathys"], 5)
            self.assertEqual(encontro.inimigos["goblin-1"]["pv_atuais"], 15)

        # Na rodada seguinte, conjura o truque Raio Místico (1d10 Energia).
        encontro.acao_principal_usada = False
        encontro.posicoes["goblin-1"] = BoardPosition(6, 7)
        encontro._proxima_semente = lambda: 1
        raio = encontro.conjurar("Raio Místico", "goblin-1")
        self.assertEqual(raio["status"], "resolvido")
        self.assertTrue(raio["acertou"])
        self.assertGreaterEqual(raio["dano"], 1)

        # Ao concluir a sala e fazer Descanso Curto, recupera o espaço de Magia de Pacto.
        for cid in ("goblin-1", "esqueleto-1"):
            encontro.inimigos[cid]["pv_atuais"] = 0
            encontro._marcar_derrotado(cid)
        self.assertEqual(encontro.status, EncounterStatus.COMPLETED)
        descanso = encontro.descansar_curto(dados_vida=0)
        self.assertEqual(descanso["status"], "resolvido")
        self.assertIn("magia_de_pacto", descanso["recursos_recuperados"])
        self.assertEqual(encontro.ficha["conjuracao"]["espacos_restantes"]["1"], 1)


class SubclassesNivel3EncontroTests(unittest.TestCase):
    def test_subclasses_de_nivel_3_aplicam_efeitos_do_motor_em_combate(self):
        orquestrador = OrquestradorAcoes(build_default_engine())

        # 1. Monge Nível 3 (Combatente da Mão Espalmada): Golpe Desarmado bônus derruba o alvo (Caído).
        ficha_m = criar_ficha_monge()
        ficha_m["nivel"] = 3
        ficha_m["ca"] = calcular_ca(orquestrador, ficha_m)
        enc_m = Encontro(orquestrador, "sarcofago_do_rei_mumia", ficha_m, INIMIGOS, seed_base=100)
        self.assertEqual(enc_m.ficha["subclasse"], "combatente_da_mao_espalmada")
        while enc_m.turno_de != "monge-1":
            enc_m.encerrar_turno()
        enc_m.posicoes["goblin-1"] = BoardPosition(3, 9)
        enc_m.inimigos["goblin-1"]["pv_maximo"] = 40
        enc_m.inimigos["goblin-1"]["pv_atuais"] = 40
        enc_m._proxima_semente = lambda: 1
        golpe = enc_m.atacar_jogador("goblin-1", acao_bonus=True)
        self.assertTrue(golpe["acertou"])
        self.assertIn("caido", enc_m._condicoes_combatente("goblin-1"))

        # 2. Bruxo Nível 3 (Patrono Ínfero — Bênção do Obscuro): ganha CAR + nível (6) PV temporários ao abater.
        ficha_b = criar_ficha_bruxo()
        ficha_b["nivel"] = 3
        ficha_b["ca"] = calcular_ca(orquestrador, ficha_b)
        enc_b = Encontro(orquestrador, "sarcofago_do_rei_mumia", ficha_b, INIMIGOS, seed_base=100)
        self.assertEqual(enc_b.ficha["subclasse"], "patrono_infero")
        enc_b.inimigos["goblin-1"]["pv_atuais"] = 0
        enc_b._marcar_derrotado("goblin-1")
        self.assertEqual(enc_b.ficha["pv_temporarios"], 6)

        # 3. Feiticeiro Nível 3 (Feitiçaria Dracônica — Resiliência Dracônica): CA 15 (13 + DES) e +3 PV máximos.
        ficha_f = criar_ficha_feiticeiro()
        pv_base_f = ficha_f["pv_maximo"]
        ficha_f["nivel"] = 3
        ficha_f["ca"] = calcular_ca(orquestrador, ficha_f)
        enc_f = Encontro(orquestrador, "sarcofago_do_rei_mumia", ficha_f, INIMIGOS, seed_base=100)
        self.assertEqual(enc_f.ficha["subclasse"], "feiticaria_draconica")
        self.assertEqual(enc_f.ficha["ca"], 15)
        self.assertEqual(enc_f.ficha["pv_maximo"], pv_base_f + 3)

        # 4. Guardião Nível 3 (Caçador — Matador de Colossos): +1d8 contra alvo já ferido.
        ficha_g = criar_ficha_guardiao()
        ficha_g["nivel"] = 3
        ficha_g["ca"] = calcular_ca(orquestrador, ficha_g)
        enc_g = Encontro(orquestrador, "sarcofago_do_rei_mumia", ficha_g, INIMIGOS, seed_base=100)
        self.assertEqual(enc_g.ficha["subclasse"], "cacador")
        while enc_g.turno_de != "guardiao-1":
            enc_g.encerrar_turno()
        enc_g.posicoes["goblin-1"] = BoardPosition(6, 9)
        enc_g.inimigos["goblin-1"]["pv_maximo"] = 40
        enc_g.inimigos["goblin-1"]["pv_atuais"] = 30  # já ferido
        enc_g._proxima_semente = lambda: 1
        disparo = enc_g.atacar_jogador("goblin-1")
        self.assertTrue(disparo["acertou"])
        self.assertGreaterEqual(disparo["dano_marca_do_predador"], 1)


class MaestriaArmaTabuleiroTests(unittest.TestCase):
    def test_maestrias_em_armas_aplicam_efeitos_taticos_no_tabuleiro(self):
        orquestrador = OrquestradorAcoes(build_default_engine())

        # 1. Ladino com Rapieira (Afligir/Vex): concede vantagem no próximo ataque e ativa Ataque Furtivo no turno seguinte.
        ficha_l = criar_ficha_ladino()
        ficha_l["ca"] = calcular_ca(orquestrador, ficha_l)
        enc_l = Encontro(orquestrador, "cripta_inicial", ficha_l, INIMIGOS, seed_base=100)
        while enc_l.turno_de != "ladino-1":
            enc_l.encerrar_turno()
        enc_l.posicoes["goblin-1"] = BoardPosition(3, 7)
        enc_l.inimigos["goblin-1"]["pv_maximo"] = 50
        enc_l.inimigos["goblin-1"]["pv_atuais"] = 50
        enc_l._proxima_semente = lambda: 1
        atq_1 = enc_l.atacar_jogador("goblin-1")
        self.assertTrue(atq_1["acertou"])
        self.assertEqual(atq_1["maestria_aplicada"], "afligir")
        self.assertTrue(enc_l.ficha.get("vantagem_proximo_ataque"))
        # Ao encerrar o turno do Ladino, a vantagem de Afligir persiste para o próximo turno.
        enc_l.encerrar_turno()
        self.assertTrue(enc_l.ficha.get("vantagem_proximo_ataque"))

        # 2. Guerreiro com Espada Longa (Drenar/Sap), Machado de Batalha (Derrubar/Topple) e Espada Grande (Garantido/Graze).
        ficha_g = criar_ficha_guerreiro()
        ficha_g["ca"] = calcular_ca(orquestrador, ficha_g)
        enc_g = Encontro(orquestrador, "cripta_inicial", ficha_g, INIMIGOS, seed_base=100)
        while enc_g.turno_de != "guerreiro-1":
            enc_g.encerrar_turno()
        enc_g.posicoes["goblin-1"] = BoardPosition(3, 7)
        enc_g.inimigos["goblin-1"]["pv_maximo"] = 60
        enc_g.inimigos["goblin-1"]["pv_atuais"] = 60
        enc_g._proxima_semente = lambda: 1
        drenar = enc_g.atacar_jogador("goblin-1", arma="Espada Longa")
        self.assertTrue(drenar["acertou"])
        self.assertEqual(drenar["maestria_aplicada"], "drenar")
        self.assertTrue(enc_g.inimigos["goblin-1"].get("desvantagem_proximo_ataque"))

        enc_g.acao_principal_usada = False
        enc_g._salvaguarda_atributo = lambda cid, atr, cd: {"result": "failure"}
        derrubar = enc_g.atacar_jogador("goblin-1", arma="Machado de Batalha")
        self.assertTrue(derrubar["acertou"])
        self.assertEqual(derrubar["maestria_aplicada"], "derrubar")
        self.assertIn("caido", enc_g._condicoes_combatente("goblin-1"))

        # Garantido (Graze) em Espada Grande: mesmo errando o ataque, causa modificador de Força (+3) de dano.
        enc_g.ficha["maestrias_arma"] = ["Espada Grande"]
        enc_g.acao_principal_usada = False
        enc_g._remover_condicao_inimigo("goblin-1", "caido")
        enc_g.inimigos["goblin-1"]["ca"] = 25
        enc_g.inimigos["goblin-1"]["pv_atuais"] = 40
        enc_g._proxima_semente = lambda: 4  # erra CA 25 (não é 20 natural)
        garantido = enc_g.atacar_jogador("goblin-1", arma="Espada Grande")
        self.assertFalse(garantido["acertou"])
        self.assertEqual(garantido["maestria_aplicada"], "garantido")
        self.assertEqual(garantido["dano"], 3)
        self.assertEqual(enc_g.inimigos["goblin-1"]["pv_atuais"], 37)

        # 3. Paladino com Martelo de Guerra (Empurrar/Push): afasta o alvo em 2 casas (10 pés).
        ficha_p = criar_ficha_paladino()
        ficha_p["ca"] = calcular_ca(orquestrador, ficha_p)
        enc_p = Encontro(orquestrador, "cripta_inicial", ficha_p, INIMIGOS, seed_base=100)
        while enc_p.turno_de != "paladino-1":
            enc_p.encerrar_turno()
        enc_p.posicoes["goblin-1"] = BoardPosition(3, 7)
        enc_p.inimigos["goblin-1"]["pv_maximo"] = 40
        enc_p.inimigos["goblin-1"]["pv_atuais"] = 40
        enc_p._proxima_semente = lambda: 1
        empurrar = enc_p.atacar_jogador("goblin-1", arma="Martelo de Guerra")
        self.assertTrue(empurrar["acertou"])
        self.assertEqual(empurrar["maestria_aplicada"], "empurrar")
        self.assertEqual(enc_p.posicoes["goblin-1"], BoardPosition(5, 7))

        # 4. Guardião com Arco Longo (Lentidão/Slow): reduz deslocamento do alvo em 10 pés.
        ficha_gua = criar_ficha_guardiao()
        ficha_gua["ca"] = calcular_ca(orquestrador, ficha_gua)
        enc_gua = Encontro(orquestrador, "cripta_inicial", ficha_gua, INIMIGOS, seed_base=100)
        while enc_gua.turno_de != "guardiao-1":
            enc_gua.encerrar_turno()
        enc_gua.posicoes["goblin-1"] = BoardPosition(6, 7)
        enc_gua.inimigos["goblin-1"]["pv_maximo"] = 40
        enc_gua.inimigos["goblin-1"]["pv_atuais"] = 40
        enc_gua._proxima_semente = lambda: 1
        lentidao = enc_gua.atacar_jogador("goblin-1")
        self.assertTrue(lentidao["acertou"])
        self.assertEqual(lentidao["maestria_aplicada"], "lentidao")
        self.assertEqual(enc_gua.inimigos["goblin-1"].get("reducao_deslocamento_pes"), 10)

        # 5. Bárbaro com Machado Grande (Trespassar/Cleave): atinge segundo inimigo adjacente a ambos.
        ficha_bar = criar_ficha_barbaro()
        ficha_bar["ca"] = calcular_ca(orquestrador, ficha_bar)
        enc_bar = Encontro(orquestrador, "cripta_inicial", ficha_bar, INIMIGOS, seed_base=100)
        while enc_bar.turno_de != "barbaro-1":
            enc_bar.encerrar_turno()
        enc_bar.posicoes["goblin-1"] = BoardPosition(3, 7)
        enc_bar.posicoes["esqueleto-1"] = BoardPosition(3, 6)
        enc_bar.inimigos["goblin-1"]["pv_maximo"] = 40
        enc_bar.inimigos["goblin-1"]["pv_atuais"] = 40
        enc_bar.inimigos["esqueleto-1"]["pv_maximo"] = 40
        enc_bar.inimigos["esqueleto-1"]["pv_atuais"] = 40
        enc_bar._proxima_semente = lambda: 1
        tresp = enc_bar.atacar_jogador("goblin-1")
        self.assertTrue(tresp["acertou"])
        self.assertEqual(tresp["maestria_aplicada"], "trespassar")
        self.assertEqual(tresp["alvo_trespassar"], "esqueleto-1")
        self.assertGreaterEqual(tresp["dano_trespassar"], 1)
        self.assertLess(enc_bar.inimigos["esqueleto-1"]["pv_atuais"], 40)


class HabilidadesEspeciaisMonstrosTests(unittest.TestCase):
    def test_habilidades_especiais_srd_dos_monstros_no_tabuleiro(self):
        orquestrador = OrquestradorAcoes(build_default_engine())

        # 1. Carniçal (Ghoul — Toque Paralisante): paralisa humano em falha de CON CD 10, mas Elfo é imune.
        ficha_g = criar_ficha_guerreiro()
        ficha_g["ca"] = 10
        ficha_g["pv_maximo"] = 50
        ficha_g["pv_atuais"] = 50
        enc_c = Encontro(
            orquestrador,
            "cripta_inicial",
            ficha_g,
            [("carnical-1", "carnical", (3, 7))],
            seed_base=100,
        )
        enc_c.posicoes["guerreiro-1"] = BoardPosition(2, 7)
        enc_c.posicoes["carnical-1"] = BoardPosition(3, 7)
        enc_c._proxima_semente = lambda: 1
        enc_c._salvaguarda_jogador = lambda atr, cd: {"result": "failure"}
        atq_c = enc_c._atacar_com_inimigo("carnical-1")
        self.assertTrue(atq_c["acertou"])
        self.assertEqual(atq_c["efeito_especial"], "toque_paralisante")
        self.assertEqual(atq_c["condicao_aplicada"], "paralisado")
        self.assertIn("paralisado", enc_c._condicoes_combatente("guerreiro-1"))

        # Guardião Elfo é imune à paralisia do Carniçal.
        ficha_elfo = criar_ficha_guardiao()
        ficha_elfo["ca"] = 10
        ficha_elfo["pv_maximo"] = 50
        ficha_elfo["pv_atuais"] = 50
        enc_elfo = Encontro(
            orquestrador,
            "cripta_inicial",
            ficha_elfo,
            [("carnical-1", "carnical", (3, 7))],
            seed_base=100,
        )
        enc_elfo.posicoes["guardiao-1"] = BoardPosition(2, 7)
        enc_elfo.posicoes["carnical-1"] = BoardPosition(3, 7)
        enc_elfo._proxima_semente = lambda: 1
        atq_elfo = enc_elfo._atacar_com_inimigo("carnical-1")
        self.assertTrue(atq_elfo["acertou"])
        self.assertNotIn("paralisado", enc_elfo._condicoes_combatente("guardiao-1"))

        # 2. Sombra (Shadow — Dreno de Força 1d4) e restauração no Descanso Curto.
        ficha_s = criar_ficha_guerreiro()
        ficha_s["ca"] = 10
        ficha_s["pv_maximo"] = 50
        ficha_s["pv_atuais"] = 50
        forca_inicial = ficha_s["atributos"]["forca"]
        enc_s = Encontro(
            orquestrador,
            "cripta_inicial",
            ficha_s,
            [("sombra-1", "sombra", (3, 7))],
            seed_base=100,
        )
        enc_s.posicoes["guerreiro-1"] = BoardPosition(2, 7)
        enc_s.posicoes["sombra-1"] = BoardPosition(3, 7)
        enc_s._proxima_semente = lambda: 1
        atq_s = enc_s._atacar_com_inimigo("sombra-1")
        self.assertTrue(atq_s["acertou"])
        self.assertEqual(atq_s["efeito_especial"], "dreno_forca")
        self.assertGreaterEqual(atq_s["dreno_forca"], 1)
        self.assertEqual(enc_s.ficha["atributos"]["forca"], forca_inicial - atq_s["dreno_forca"])
        # Ao concluir a sala e fazer Descanso Curto, a Força drenada é restaurada.
        enc_s.inimigos["sombra-1"]["pv_atuais"] = 0
        enc_s._marcar_derrotado("sombra-1")
        desc = enc_s.descansar_curto(dados_vida=1)
        self.assertEqual(desc["status"], "resolvido")
        self.assertEqual(enc_s.ficha["atributos"]["forca"], forca_inicial)

        # 3. Espectro (Specter — Dreno de Vida): reduz PV máximo igual ao dano necrótico em falha de CON CD 10.
        ficha_e = criar_ficha_guerreiro()
        ficha_e["ca"] = 10
        ficha_e["pv_maximo"] = 40
        ficha_e["pv_atuais"] = 40
        enc_e = Encontro(
            orquestrador,
            "cripta_inicial",
            ficha_e,
            [("espectro-1", "espectro", (3, 7))],
            seed_base=100,
        )
        enc_e.posicoes["guerreiro-1"] = BoardPosition(2, 7)
        enc_e.posicoes["espectro-1"] = BoardPosition(3, 7)
        enc_e._proxima_semente = lambda: 1
        enc_e._salvaguarda_jogador = lambda atr, cd: {"result": "failure"}
        atq_e = enc_e._atacar_com_inimigo("espectro-1")
        self.assertTrue(atq_e["acertou"])
        self.assertEqual(atq_e["efeito_especial"], "dreno_vida")
        self.assertEqual(atq_e["reducao_pv_maximo"], atq_e["dano"])
        self.assertEqual(enc_e.ficha["pv_maximo"], 40 - atq_e["dano"])

        # 4. Esqueleto Minotauro (Charge / Investida): +2d8 perfurante, empurra 10 pés e derruba em falha de FOR CD 14.
        ficha_m = criar_ficha_guerreiro()
        ficha_m["ca"] = 10
        ficha_m["pv_maximo"] = 60
        ficha_m["pv_atuais"] = 60
        enc_m = Encontro(
            orquestrador,
            "cripta_inicial",
            ficha_m,
            [("minotauro-1", "esqueleto_minotauro", (7, 7))],
            seed_base=100,
        )
        enc_m.posicoes["guerreiro-1"] = BoardPosition(5, 7)
        enc_m.posicoes["minotauro-1"] = BoardPosition(6, 7)
        enc_m.inimigos["minotauro-1"]["passos_movidos_pes_turno"] = 15  # moveu >= 10 pés
        enc_m._proxima_semente = lambda: 1
        enc_m._salvaguarda_jogador = lambda atr, cd: {"result": "failure"}
        atq_m = enc_m._atacar_com_inimigo("minotauro-1")
        self.assertTrue(atq_m["acertou"])
        self.assertEqual(atq_m["efeito_especial"], "investida")
        self.assertGreaterEqual(atq_m["dano_investida"], 2)
        self.assertEqual(atq_m["condicao_aplicada"], "caido")
        self.assertIn("caido", enc_m._condicoes_combatente("guerreiro-1"))
        self.assertEqual(enc_m.posicoes["guerreiro-1"], BoardPosition(3, 7))

        # 5. Múmia Ancestral (Rotting Fist — Maldição da Múmia): +3d6 necrótico e bloqueia cura em falha de CON CD 12.
        ficha_mu = criar_ficha_guerreiro()
        ficha_mu["ca"] = 10
        ficha_mu["pv_maximo"] = 60
        ficha_mu["pv_atuais"] = 60
        enc_mu = Encontro(
            orquestrador,
            "cripta_inicial",
            ficha_mu,
            [("mumia-1", "mumia", (3, 7))],
            seed_base=100,
        )
        while enc_mu.turno_de != "guerreiro-1":
            enc_mu.encerrar_turno()
        enc_mu.ficha["pv_atuais"] = 60
        enc_mu.posicoes["guerreiro-1"] = BoardPosition(2, 7)
        enc_mu.posicoes["mumia-1"] = BoardPosition(3, 7)
        enc_mu._proxima_semente = lambda: 1
        enc_mu._salvaguarda_jogador = lambda atr, cd: {"result": "failure"}
        atq_mu = enc_mu._atacar_com_inimigo("mumia-1")
        self.assertTrue(atq_mu["acertou"])
        self.assertEqual(atq_mu["efeito_especial"], "maldicao_da_mumia")
        self.assertGreaterEqual(atq_mu["dano_necrotico_extra"], 3)
        self.assertTrue(enc_mu.ficha.get("maldicao_da_mumia"))
        folego = enc_mu.recuperar_folego()
        self.assertEqual(folego["status"], "resolvido")
        self.assertTrue(folego.get("bloqueado_por_maldicao"))
        self.assertEqual(folego["curado"], 0)

        # 6. Zumbi (Undead Fortitude): sobrevive com 1 PV se passar na salvaguarda de CON (CD 5 + dano).
        ficha_z = criar_ficha_guerreiro()
        ficha_z["ca"] = calcular_ca(orquestrador, ficha_z)
        enc_z = Encontro(
            orquestrador,
            "cripta_inicial",
            ficha_z,
            [("zumbi-1", "zumbi", (3, 7))],
            seed_base=100,
        )
        while enc_z.turno_de != "guerreiro-1":
            enc_z.encerrar_turno()
        enc_z.posicoes["zumbi-1"] = BoardPosition(3, 7)
        enc_z.inimigos["zumbi-1"]["pv_atuais"] = 3
        enc_z._proxima_semente = lambda: 1
        enc_z._salvaguarda_atributo = lambda cid, atr, cd: {"result": "success"}
        golpe_z = enc_z.atacar_jogador("zumbi-1", arma="Espada Longa")
        self.assertTrue(golpe_z["acertou"])
        self.assertTrue(golpe_z.get("fortitude_morto_vivo"))
        self.assertFalse(golpe_z["derrubado"])
        self.assertEqual(enc_z.inimigos["zumbi-1"]["pv_atuais"], 1)


class EspeciesJogaveisTests(unittest.TestCase):
    def test_todas_as_10_especies_jogaveis_e_tracos_mecanicos_phb_2024(self):
        orquestrador = OrquestradorAcoes(build_default_engine())
        catalogo = listar_especies_jogaveis()
        ids = sorted(item["id"] for item in catalogo)
        self.assertEqual(
            ids,
            [
                "aasimar",
                "anao",
                "draconato",
                "elfo",
                "gnomo",
                "golias",
                "halfling",
                "humano",
                "orc",
                "tiefling",
            ],
        )

        # 1. Anão: +1 PV por nível (Tenacidade Anã) e resistência a dano venenoso.
        f_base = criar_ficha_guerreiro()
        f_anao = criar_ficha_personagem(classe="guerreiro", especie="anao")
        self.assertEqual(f_anao["especie"], "anao")
        self.assertEqual(f_anao["pv_maximo"], f_base["pv_maximo"] + 1)
        self.assertIn("venenoso", f_anao["resistencias_dano"])

        # 2. Draconato: resistência a ígneo e Ataque de Sopro (1d10 ígneo em alcance de 15 pés).
        f_draco = criar_ficha_personagem(classe="guerreiro", especie="draconato")
        f_draco["ca"] = calcular_ca(orquestrador, f_draco)
        self.assertIn("ígneo", f_draco["resistencias_dano"])
        self.assertEqual(f_draco["usos_sopro_draconico"], 2)
        enc_draco = Encontro(
            orquestrador,
            "cripta_inicial",
            f_draco,
            [("goblin-1", "goblin", (4, 7))],
            seed_base=100,
        )
        while enc_draco.turno_de != "guerreiro-1":
            enc_draco.encerrar_turno()
        enc_draco.posicoes["guerreiro-1"] = BoardPosition(2, 7)
        enc_draco.posicoes["goblin-1"] = BoardPosition(4, 7)  # 10 pés
        enc_draco.inimigos["goblin-1"]["pv_maximo"] = 25
        enc_draco.inimigos["goblin-1"]["pv_atuais"] = 25
        sopro = enc_draco.atacar_jogador("goblin-1", arma="Ataque de Sopro")
        self.assertEqual(sopro["status"], "resolvido")
        self.assertEqual(sopro["arma"], "Ataque de Sopro")
        self.assertGreaterEqual(sopro["dano"], 1)
        self.assertEqual(sopro["usos_restantes"], 1)

        # 3. Orc: Pico de Adrenalina (PV temporários ao iniciar) e Vigor Implacável (fica com 1 PV ao cair a 0 PV).
        f_orc = criar_ficha_personagem(classe="barbaro", especie="orc")
        f_orc["ca"] = 10
        f_orc["pv_maximo"] = 8
        f_orc["pv_atuais"] = 2
        f_orc["pv_temporarios"] = 0
        enc_orc = Encontro(
            orquestrador,
            "cripta_inicial",
            f_orc,
            [("esqueleto-1", "esqueleto", (3, 7))],
            seed_base=100,
        )
        self.assertGreaterEqual(enc_orc.ficha["pv_temporarios"], 2)
        enc_orc.ficha["pv_temporarios"] = 0
        enc_orc.ficha["pv_atuais"] = 2
        enc_orc.posicoes["barbaro-1"] = BoardPosition(2, 7)
        enc_orc.posicoes["esqueleto-1"] = BoardPosition(3, 7)
        enc_orc._proxima_semente = lambda: 1
        golpe_orc = enc_orc._atacar_com_inimigo("esqueleto-1")
        self.assertTrue(golpe_orc["acertou"])
        self.assertTrue(golpe_orc.get("vigor_implacavel"))
        self.assertEqual(enc_orc.ficha["pv_atuais"], 1)
        self.assertFalse(enc_orc.ficha["vigor_implacavel_disponivel"])

        # 4. Golias: 35 pés de deslocamento e Queimadura de Fogo (+1d10 ígneo no acerto).
        f_golias = criar_ficha_personagem(classe="guerreiro", especie="golias")
        f_golias["ca"] = calcular_ca(orquestrador, f_golias)
        self.assertEqual(f_golias["deslocamento_pes"], 35)
        self.assertEqual(f_golias["usos_ancestralidade_gigante"], 2)
        enc_gol = Encontro(
            orquestrador,
            "cripta_inicial",
            f_golias,
            [("goblin-1", "goblin", (3, 7))],
            seed_base=100,
        )
        while enc_gol.turno_de != "guerreiro-1":
            enc_gol.encerrar_turno()
        enc_gol.posicoes["guerreiro-1"] = BoardPosition(2, 7)
        enc_gol.posicoes["goblin-1"] = BoardPosition(3, 7)
        enc_gol.inimigos["goblin-1"]["pv_maximo"] = 40
        enc_gol.inimigos["goblin-1"]["pv_atuais"] = 40
        enc_gol._proxima_semente = lambda: 1
        atq_gol = enc_gol.atacar_jogador("goblin-1", arma="Espada Longa")
        self.assertTrue(atq_gol["acertou"])
        self.assertEqual(enc_gol.ficha["usos_ancestralidade_gigante"], 1)

        # 5. Aasimar, Elfo, Gnomo, Halfling, Humano e Tiefling.
        f_aasimar = criar_ficha_personagem(classe="paladino", especie="aasimar")
        self.assertIn("radiante", f_aasimar["resistencias_dano"])
        self.assertIn("necrótico", f_aasimar["resistencias_dano"])

        f_elfo = criar_ficha_personagem(classe="guerreiro", especie="elfo")
        self.assertIn("Raio de Fogo", f_elfo["conjuracao"]["truques"])

        f_gnomo = criar_ficha_personagem(classe="mago", especie="gnomo")
        self.assertIn("sabedoria", f_gnomo["vantagens_salvaguarda"])

        f_half = criar_ficha_personagem(classe="ladino", especie="halfling")
        self.assertTrue(f_half["sorte_halfling"])

        f_hum = criar_ficha_personagem(classe="bardo", especie="humano")
        self.assertTrue(f_hum["inspiracao_heroica"])

        f_tief = criar_ficha_personagem(classe="bruxo", especie="tiefling")
        self.assertIn("ígneo", f_tief["resistencias_dano"])
        self.assertIn("Raio de Fogo", f_tief["conjuracao"]["truques"])


if __name__ == "__main__":
    unittest.main()
