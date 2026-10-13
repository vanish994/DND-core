"""Magias e truques do Bardo no encontro de cripta.

A ficha recebe a conjuração validada pelo criador. Cada conjuração passa pelo
Orquestrador (preparo, espaço e círculo) e o efeito é resolvido pelo motor:
Curar Ferimentos (cura), Zombaria Perversa (salvaguarda e dano) e Comando
(salvaguarda e comando no próximo turno). Magias sem efeito resolvido são
recusadas sem gastar espaço.
"""

import unittest
from unittest import mock

from dungeon_game import encontro as modulo
from dungeon_game.encontro import Encontro, calcular_ca, criar_ficha_bardo
from orchestrator import OrquestradorAcoes
from rule_engine import build_default_engine

INIMIGOS = [("goblin-1", "goblin", (13, 3)), ("esqueleto-1", "esqueleto", (13, 10))]


def novo_encontro(seed_base: int = 100, zombaria: bool = False) -> Encontro:
    orquestrador = OrquestradorAcoes(build_default_engine())
    ficha = criar_ficha_bardo()
    ficha["ca"] = calcular_ca(orquestrador, ficha)
    if zombaria:
        # A escolha de truques é do criador; aqui o Bardo recebe Zombaria Perversa para testar o efeito.
        ficha["conjuracao"]["truques"].append("Zombaria Perversa")
    return Encontro(orquestrador, "cripta_inicial", ficha, INIMIGOS, seed_base=seed_base)


def no_turno_do_bardo(encontro: Encontro) -> None:
    while encontro.turno_de != encontro.ficha["id"]:
        encontro.encerrar_turno()


def turno_do_goblin(encontro: Encontro) -> None:
    """Encerra o turno do Bardo e executa o turno do Goblin (antes do Esqueleto)."""
    encontro.encerrar_turno()
    while encontro.turno_de == "goblin-1":
        encontro.encerrar_turno()


def semente_que_falha_na_salvaguarda_de_sabedoria(encontro: Encontro, cid: str, cd: int) -> int:
    """Procura uma semente em que o inimigo falha a salvaguarda de Sabedoria (sem consumir o encontro)."""
    for semente in range(1, 500):
        encontro._proxima_semente = lambda s=semente: s  # noqa: B023
        if encontro._salvaguarda_sabedoria(cid, cd)["result"] == "failure":
            return semente
    raise AssertionError("nenhuma semente falha a salvaguarda")


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
    def test_magias_com_efeito_no_combate_estao_disponiveis(self):
        disponiveis = {m["nome"] for m in novo_encontro().magias_do_personagem() if m["disponivel"]}
        self.assertEqual(disponiveis, {"Curar Ferimentos", "Comando"})

    def test_magias_sem_efeito_trazem_motivo(self):
        magias = {m["nome"]: m for m in novo_encontro().magias_do_personagem()}
        self.assertIsNotNone(magias["Luz"]["motivo"])
        self.assertIsNotNone(magias["Enfeitiçar Pessoa"]["motivo"])
        self.assertEqual(magias["Luz"]["circulo"], 0)
        self.assertEqual(magias["Curar Ferimentos"]["alvo"], "si_mesmo")
        self.assertEqual(magias["Comando"]["alvo"], "inimigo")

    def test_zombaria_perversa_aparece_quando_escolhida(self):
        magias = {m["nome"]: m for m in novo_encontro(zombaria=True).magias_do_personagem()}
        self.assertTrue(magias["Zombaria Perversa"]["disponivel"])
        self.assertEqual(magias["Zombaria Perversa"]["alvo"], "inimigo")

    def test_alvos_de_magia_respeitam_alcance_de_18_metros(self):
        encontro = novo_encontro()
        self.assertEqual(set(encontro.alvos_magia()), {"goblin-1", "esqueleto-1"})  # 55 pés e menos de 60
        encontro.posicoes["esqueleto-1"] = encontro.posicoes["esqueleto-1"].__class__(23, 13)
        self.assertNotIn("esqueleto-1", encontro.alvos_magia())


class TestConjurarRecusas(unittest.TestCase):
    def test_magia_sem_efeito_e_recusada_sem_gastar_espaco(self):
        encontro = novo_encontro()
        no_turno_do_bardo(encontro)
        self.assertEqual(encontro.conjurar("Luz")["status"], "bloqueado")
        self.assertEqual(encontro.ficha["conjuracao"]["espacos_restantes"], {"1": 2})

    def test_magia_nao_escolhida_e_recusada(self):
        encontro = novo_encontro()
        no_turno_do_bardo(encontro)
        self.assertEqual(encontro.conjurar("Bola de Fogo")["status"], "bloqueado")

    def test_comando_sem_comando_escolhido_e_recusado_sem_gastar(self):
        encontro = novo_encontro()
        no_turno_do_bardo(encontro)
        resultado = encontro.conjurar("Comando", "goblin-1")
        self.assertEqual(resultado["motivo"], "comando_invalido")
        self.assertEqual(encontro.ficha["conjuracao"]["espacos_restantes"], {"1": 2})

    def test_comando_fora_de_alcance_e_recusado(self):
        encontro = novo_encontro()
        no_turno_do_bardo(encontro)
        encontro.posicoes["esqueleto-1"] = encontro.posicoes["esqueleto-1"].__class__(23, 13)
        resultado = encontro.conjurar("Comando", "esqueleto-1", "parar")
        self.assertEqual(resultado["motivo"], "alvo_fora_do_alcance")
        self.assertFalse(encontro.acao_principal_usada)
        self.assertEqual(encontro.ficha["conjuracao"]["espacos_restantes"], {"1": 2})

    def test_curar_ferimentos_com_alvo_outro_e_recusada(self):
        encontro = novo_encontro()
        no_turno_do_bardo(encontro)
        resultado = encontro.conjurar("Curar Ferimentos", alvo_id="goblin-1")
        self.assertEqual(resultado["status"], "bloqueado")
        self.assertEqual(encontro.ficha["conjuracao"]["espacos_restantes"], {"1": 2})


class TestCurarFerimentos(unittest.TestCase):
    def test_gasta_espaco_e_cura_com_2d8_mais_carisma(self):
        encontro = novo_encontro(seed_base=7)
        no_turno_do_bardo(encontro)
        encontro.ficha["pv_atuais"] = 5
        modificador = encontro.ficha["modificadores"]["carisma"]
        resultado = encontro.conjurar("Curar Ferimentos")
        self.assertEqual(resultado["status"], "resolvido")
        self.assertEqual(encontro.ficha["conjuracao"]["espacos_restantes"], {"1": 1})
        self.assertTrue(2 + modificador <= resultado["rolagem"] <= 16 + modificador)
        self.assertEqual(encontro.ficha["pv_atuais"], 5 + resultado["curado"])
        self.assertEqual(encontro.log[-1]["evento"], "magia")

    def test_cura_nao_ultrapassa_pv_maximo(self):
        encontro = novo_encontro(seed_base=7)
        no_turno_do_bardo(encontro)
        encontro.ficha["pv_atuais"] = encontro.ficha["pv_maximo"] - 1
        resultado = encontro.conjurar("Curar Ferimentos")
        self.assertEqual(encontro.ficha["pv_atuais"], encontro.ficha["pv_maximo"])
        self.assertEqual(resultado["curado"], 1)

    def test_sem_espaco_restante_bloqueia_sem_curar(self):
        encontro = novo_encontro(seed_base=7)
        no_turno_do_bardo(encontro)
        encontro.ficha["pv_atuais"] = 5
        encontro.ficha["conjuracao"]["espacos_restantes"] = {"1": 0}
        self.assertEqual(encontro.conjurar("Curar Ferimentos")["status"], "bloqueado")
        self.assertEqual(encontro.ficha["pv_atuais"], 5)


class TestZombariaPerversa(unittest.TestCase):
    def test_falha_causa_dano_e_desvantagem_no_proximo_ataque(self):
        encontro = novo_encontro()
        no_turno_do_bardo(encontro)
        cd = modulo.cd_de_magia(encontro.orquestrador.engine, encontro.ficha)
        semente = semente_que_falha_na_salvaguarda_de_sabedoria(encontro, "goblin-1", cd)
        encontro = novo_encontro(zombaria=True)
        no_turno_do_bardo(encontro)
        encontro._proxima_semente = lambda: semente
        pv_antes = encontro.inimigos["goblin-1"]["pv_atuais"]
        resultado = encontro.conjurar("Zombaria Perversa", "goblin-1")
        self.assertEqual(resultado["resultado"], "falhou")
        self.assertGreaterEqual(resultado["dano"], 1)
        self.assertEqual(encontro.inimigos["goblin-1"]["pv_atuais"], max(0, pv_antes - resultado["dano"]))
        self.assertTrue(encontro.inimigos["goblin-1"]["desvantagem_proximo_ataque"])

    def test_sucesso_na_salvaguarda_nao_causa_efeito(self):
        encontro = novo_encontro(zombaria=True)
        no_turno_do_bardo(encontro)
        encontro._proxima_semente = lambda: 1  # semente 1: salvaguarda de Sabedoria bem-sucedida
        pv_antes = encontro.inimigos["goblin-1"]["pv_atuais"]
        resultado = encontro.conjurar("Zombaria Perversa", "goblin-1")
        self.assertEqual(resultado["resultado"], "resistiu")
        self.assertEqual(encontro.inimigos["goblin-1"]["pv_atuais"], pv_antes)
        self.assertNotIn("desvantagem_proximo_ataque", encontro.inimigos["goblin-1"])

    def test_desvantagem_chega_ao_ataque_do_inimigo_e_some_no_fim_do_turno(self):
        encontro = novo_encontro(zombaria=True)
        no_turno_do_bardo(encontro)
        encontro.inimigos["goblin-1"]["desvantagem_proximo_ataque"] = True
        turno_do_goblin(encontro)
        self.assertNotIn("desvantagem_proximo_ataque", encontro.inimigos["goblin-1"])


class TestComando(unittest.TestCase):
    def _com_comando_falhado(self, comando: str) -> Encontro:
        encontro = novo_encontro()
        no_turno_do_bardo(encontro)
        cd = modulo.cd_de_magia(encontro.orquestrador.engine, encontro.ficha)
        semente = semente_que_falha_na_salvaguarda_de_sabedoria(encontro, "goblin-1", cd)
        encontro._proxima_semente = lambda: semente
        resultado = encontro.conjurar("Comando", "goblin-1", comando)
        self.assertEqual(resultado["resultado"], "falhou")
        self.assertEqual(encontro.ficha["conjuracao"]["espacos_restantes"], {"1": 1})
        return encontro

    def test_parar_e_largar_impedem_movimento_e_ataque(self):
        for comando in ("parar", "largar"):
            with self.subTest(comando=comando):
                encontro = self._com_comando_falhado(comando)
                posicao = (encontro.posicoes["goblin-1"].x, encontro.posicoes["goblin-1"].y)
                turno_do_goblin(encontro)
                self.assertEqual((encontro.posicoes["goblin-1"].x, encontro.posicoes["goblin-1"].y), posicao)
                self.assertFalse(any(e.get("evento") == "ataque_inimigo" for e in encontro.log))

    def test_abaixar_deixa_inimigo_caido_e_encerra_turno(self):
        encontro = self._com_comando_falhado("abaixar")
        posicao = (encontro.posicoes["goblin-1"].x, encontro.posicoes["goblin-1"].y)
        turno_do_goblin(encontro)
        self.assertTrue(encontro.inimigos["goblin-1"].get("caido"))
        self.assertEqual((encontro.posicoes["goblin-1"].x, encontro.posicoes["goblin-1"].y), posicao)

    def test_aproximar_move_mas_nao_ataca(self):
        encontro = self._com_comando_falhado("aproximar")
        distancia_antes = encontro.distancia_pes("goblin-1", "bardo-1")
        turno_do_goblin(encontro)
        self.assertLess(encontro.distancia_pes("goblin-1", "bardo-1"), distancia_antes)
        self.assertFalse(any(e.get("evento") == "ataque_inimigo" for e in encontro.log))

    def test_fugir_nao_aproxima_e_nao_ataca(self):
        encontro = self._com_comando_falhado("fugir")
        distancia_antes = encontro.distancia_pes("goblin-1", "bardo-1")
        turno_do_goblin(encontro)
        self.assertGreaterEqual(encontro.distancia_pes("goblin-1", "bardo-1"), distancia_antes)
        self.assertFalse(any(e.get("evento") == "ataque_inimigo" for e in encontro.log))

    def test_comando_resistido_nao_tem_efeito(self):
        encontro = novo_encontro()
        no_turno_do_bardo(encontro)
        encontro._proxima_semente = lambda: 1
        resultado = encontro.conjurar("Comando", "goblin-1", "parar")
        self.assertEqual(resultado["resultado"], "resistiu")
        self.assertNotIn("comando_pendente", encontro.inimigos["goblin-1"])


class TestMovimentoDoInimigo(unittest.TestCase):
    def test_inimigo_fora_de_alcance_se_aproxima_no_proprio_turno(self):
        encontro = novo_encontro()
        no_turno_do_bardo(encontro)
        distancia_antes = encontro.distancia_pes("goblin-1", "bardo-1")
        turno_do_goblin(encontro)
        self.assertLess(encontro.distancia_pes("goblin-1", "bardo-1"), distancia_antes)
        self.assertTrue(any(e.get("evento") == "movimento_inimigo" for e in encontro.log))


class TestAtaqueComDesvantagem(unittest.TestCase):
    def test_atacar_inimigo_recebe_desvantagem(self):
        encontro = novo_encontro(zombaria=True)
        no_turno_do_bardo(encontro)
        encontro.inimigos["goblin-1"]["desvantagem_proximo_ataque"] = True
        with mock.patch.object(modulo, "atacar_inimigo", return_value={"status": "resolvido"}) as ataque:
            encontro._atacar_com_inimigo("goblin-1")
        self.assertTrue(ataque.call_args.kwargs["desvantagem"])


if __name__ == "__main__":
    unittest.main()
