"""API do encontro de cripta: estado, ações recusadas e arquivos estáticos."""

import io
import json
import tempfile
import unittest
from pathlib import Path

from dungeon_game import servidor
from dungeon_game.session_store import MemorySessionStore, SQLiteSessionStore, SessionStoreError


def chamar(metodo: str, caminho: str, corpo: dict | None = None) -> tuple[int, dict | bytes]:
    dados = json.dumps(corpo).encode("utf-8") if corpo is not None else b""
    ambiente = {
        "REQUEST_METHOD": metodo,
        "PATH_INFO": caminho,
        "CONTENT_LENGTH": str(len(dados)),
        "wsgi.input": io.BytesIO(dados),
    }
    capturado = {}

    def iniciar(status, cabecalhos):
        capturado["status"] = int(status.split()[0])

    corpo_bytes = b"".join(servidor.app(ambiente, iniciar))
    if capturado["status"] == 200 and caminho.startswith("/static") or caminho in {"/", "/encontro"}:
        return capturado["status"], corpo_bytes
    return capturado["status"], json.loads(corpo_bytes)


def usar_store_memoria(teste: unittest.TestCase) -> None:
    store_anterior = servidor.SESSION_STORE
    teste.addCleanup(setattr, servidor, "SESSION_STORE", store_anterior)
    servidor.SESSION_STORE = MemorySessionStore()


class ApiEncontroTests(unittest.TestCase):
    def setUp(self):
        usar_store_memoria(self)

    def criar(self) -> tuple[str, dict]:
        status, estado = chamar("POST", "/api/encontros", {})
        self.assertEqual(status, 201)
        return estado["encontro_id"], estado

    def test_criar_devolve_estado_com_ca_do_motor_e_iniciativa(self):
        _, estado = self.criar()
        self.assertEqual(len(estado["encontro_id"]), 32)
        self.assertEqual(estado["personagem"]["ca"], 13)
        self.assertEqual(estado["personagem"]["deslocamento_pes"], 30)
        self.assertEqual(estado["movimento_usado_pes"], 0)
        self.assertEqual(estado["movimento_restante_pes"], 30)
        self.assertFalse(estado["acao_principal_usada"])
        self.assertEqual(len(estado["iniciativa"]), 3)
        self.assertEqual(estado["mapa"]["largura"], 24)
        self.assertEqual(len(estado["mapa"]["grade"]), 14)

    def test_estado_traz_perfil_para_o_sprite(self):
        _, estado = self.criar()
        self.assertEqual({u["perfil"] for u in estado["unidades"]}, {"goblin", "esqueleto"})

    def test_alcancaveis_so_quando_e_o_turno_do_jogador(self):
        _, estado = self.criar()
        if estado["turno_de"] == estado["personagem"]["id"]:
            self.assertTrue(estado["de_jogador"])
            self.assertGreater(len(estado["alcancaveis"]), 0)
            self.assertNotIn(estado["personagem"]["posicao"], estado["alcancaveis"])
        else:
            self.assertFalse(estado["de_jogador"])
            self.assertEqual(estado["alcancaveis"], [])

    def test_movimento_invalido_devolve_409(self):
        encontro_id, estado = self.criar()
        if estado["turno_de"] != estado["personagem"]["id"]:
            chamar("POST", f"/api/encontros/{encontro_id}/encerrar", {})
        status, corpo = chamar("POST", f"/api/encontros/{encontro_id}/mover", {"x": 0, "y": 0})
        self.assertEqual(status, 409)
        self.assertIn("erro", corpo)

    def test_movimento_valido_atualiza_posicao(self):
        encontro_id, estado = self.criar()
        if estado["turno_de"] != estado["personagem"]["id"]:
            _, corpo = chamar("POST", f"/api/encontros/{encontro_id}/encerrar", {})
            estado = corpo["estado"]
        destino = estado["alcancaveis"][0]
        status, corpo = chamar("POST", f"/api/encontros/{encontro_id}/mover", {"x": destino[0], "y": destino[1]})
        self.assertEqual(status, 200)
        self.assertEqual(corpo["estado"]["personagem"]["posicao"], destino)

    def test_movimento_acumula_em_chamadas_sucessivas_e_bloqueia_excesso(self):
        encontro_id, estado = self.criar()
        if not estado["de_jogador"]:
            _, corpo = chamar("POST", f"/api/encontros/{encontro_id}/encerrar", {})
            estado = corpo["estado"]

        status, corpo = chamar("POST", f"/api/encontros/{encontro_id}/mover", {"x": 5, "y": 7})
        self.assertEqual(status, 200)
        self.assertEqual(corpo["estado"]["movimento_usado_pes"], 15)
        self.assertEqual(corpo["estado"]["movimento_restante_pes"], 15)

        status, corpo = chamar("POST", f"/api/encontros/{encontro_id}/mover", {"x": 8, "y": 7})
        self.assertEqual(status, 200)
        self.assertEqual(corpo["estado"]["movimento_usado_pes"], 30)
        self.assertEqual(corpo["estado"]["movimento_restante_pes"], 0)

        status, corpo = chamar("POST", f"/api/encontros/{encontro_id}/mover", {"x": 9, "y": 7})
        self.assertEqual(status, 409)
        self.assertEqual(corpo["erro"], "deslocamento_esgotado")
        status, estado = chamar("GET", f"/api/encontros/{encontro_id}")
        self.assertEqual(status, 200)
        self.assertEqual(estado["personagem"]["posicao"], [8, 7])

    def test_encerrar_turno_leva_os_inimigos_ate_o_jogador(self):
        encontro_id, estado = self.criar()
        if estado["turno_de"] == estado["personagem"]["id"]:
            _, corpo = chamar("POST", f"/api/encontros/{encontro_id}/encerrar", {})
            estado = corpo["estado"]
            self.assertTrue(estado["de_jogador"] or estado["status"] != "active")

    def test_sessao_sqlite_sobrevive_a_recriacao_do_store(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho_banco = Path(diretorio) / "encontros.sqlite3"
            servidor.SESSION_STORE = SQLiteSessionStore(caminho_banco)
            encontro_id, estado = self.criar()
            while not estado["de_jogador"]:
                status, corpo = chamar("POST", f"/api/encontros/{encontro_id}/encerrar", {})
                self.assertEqual(status, 200)
                estado = corpo["estado"]

            destino = estado["alcancaveis"][0]
            status, corpo = chamar(
                "POST", f"/api/encontros/{encontro_id}/mover", {"x": destino[0], "y": destino[1]}
            )
            self.assertEqual(status, 200)
            estado_esperado = corpo["estado"]

            servidor.SESSION_STORE = SQLiteSessionStore(caminho_banco)
            status, retomado = chamar("GET", f"/api/encontros/{encontro_id}")
            self.assertEqual(status, 200)
            self.assertEqual(retomado["personagem"]["posicao"], estado_esperado["personagem"]["posicao"])
            self.assertEqual(retomado["movimento_usado_pes"], estado_esperado["movimento_usado_pes"])
            self.assertEqual(retomado["turno_de"], estado_esperado["turno_de"])

    def test_health_check_retorna_ok_quando_o_store_responde(self):
        status, corpo = chamar("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(corpo, {"status": "ok"})

    def test_health_check_oculta_detalhes_quando_o_store_falha(self):
        class StoreIndisponivel:
            def ping(self):
                raise SessionStoreError("DATABASE_URL=credencial-secreta")

        servidor.SESSION_STORE = StoreIndisponivel()
        status, corpo = chamar("GET", "/health")
        self.assertEqual(status, 503)
        self.assertEqual(corpo, {"erro": "persistencia_indisponivel"})
        self.assertNotIn("credencial-secreta", str(corpo))

    def test_encontro_inexistente_devolve_404(self):
        status, corpo = chamar("GET", "/api/encontros/nao-existe")
        self.assertEqual(status, 404)

    def test_acao_desconhecida_devolve_404(self):
        encontro_id, _ = self.criar()
        status, _ = chamar("POST", f"/api/encontros/{encontro_id}/magia", {})
        self.assertEqual(status, 404)

    def test_json_invalido_devolve_400(self):
        encontro_id, _ = self.criar()
        ambiente = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": f"/api/encontros/{encontro_id}/mover",
            "CONTENT_LENGTH": "3",
            "wsgi.input": io.BytesIO(b"{x"),
        }
        capturado = {}
        corpo = b"".join(servidor.app(ambiente, lambda status, cabecalhos: capturado.update(status=int(status[:3]))))
        self.assertEqual(capturado["status"], 400)
        self.assertIn("JSON", json.loads(corpo)["erro"])

    def test_listar_mapas_e_selecionar_mapa_na_criacao(self):
        status, catalogo = chamar("GET", "/api/mapas")
        self.assertEqual(status, 200)
        ids = [m["id"] for m in catalogo["mapas"]]
        self.assertEqual(
            ids,
            [
                "cripta_inicial",
                "santuario_circular",
                "catacumba_dos_mortos",
                "camara_profana",
                "sarcofago_do_rei_mumia",
            ],
        )

        status_ini, catalogo_ini = chamar("GET", "/api/inimigos")
        self.assertEqual(status_ini, 200)
        self.assertEqual(
            [i["perfil"] for i in catalogo_ini["inimigos"]],
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

        status, estado = chamar("POST", "/api/encontros", {"mapa_id": "santuario_circular"})
        self.assertEqual(status, 201)
        self.assertEqual(estado["mapa"]["largura"], 42)
        self.assertEqual(estado["mapa"]["altura"], 26)
        self.assertEqual(estado["sala"], 2)

        status_3, estado_3 = chamar("POST", "/api/encontros", {"mapa_id": "catacumba_dos_mortos"})
        self.assertEqual(status_3, 201)
        self.assertEqual(estado_3["sala"], 3)
        self.assertEqual({u["perfil"] for u in estado_3["unidades"]}, {"zumbi", "cultista", "carnical"})

        status_4, estado_4 = chamar("POST", "/api/encontros", {"mapa_id": "camara_profana"})
        self.assertEqual(status_4, 201)
        self.assertEqual(estado_4["sala"], 4)
        self.assertEqual({u["perfil"] for u in estado_4["unidades"]}, {"sombra", "armadura_animada", "aparicao"})

        status_5, estado_5 = chamar("POST", "/api/encontros", {"mapa_id": "sarcofago_do_rei_mumia"})
        self.assertEqual(status_5, 201)
        self.assertEqual(estado_5["sala"], 5)
        self.assertEqual(
            {u["perfil"] for u in estado_5["unidades"]},
            {"espectro", "esqueleto_minotauro", "mumia"},
        )

        status, erro = chamar("POST", "/api/encontros", {"mapa_id": "inexistente"})
        self.assertEqual(status, 400)
        self.assertIn("erro", erro)

    def test_avancar_sala_via_api_exige_vitoria_e_transita_para_santuario(self):
        encontro_id, _ = self.criar()
        status, recusado = chamar("POST", f"/api/encontros/{encontro_id}/avancar", {})
        self.assertEqual(status, 409)
        self.assertEqual(recusado["erro"], "encontro_nao_concluido")

        # Conclui o encontro na store e avança via endpoint HTTP.
        encontro = servidor._encontro(encontro_id)
        for cid in list(encontro.inimigos):
            encontro.inimigos[cid]["pv_atuais"] = 0
            encontro._marcar_derrotado(cid)
        servidor.SESSION_STORE.save(encontro_id, encontro.to_state())

        status, concluido = chamar("GET", f"/api/encontros/{encontro_id}")
        self.assertEqual(status, 200)
        self.assertEqual(concluido["status"], "completed")
        self.assertEqual(concluido["recompensa"], {"xp": 100, "ouro_po": 15})
        self.assertEqual(concluido["personagem"]["xp"], 100)
        self.assertEqual(concluido["personagem"]["ouro_po"], 15)
        self.assertEqual(concluido["proxima_sala"], "santuario_circular")

        # Reduz PV para validar Descanso Curto via API antes de avançar de sala.
        encontro = servidor._encontro(encontro_id)
        encontro.ficha["pv_atuais"] = 4
        servidor.SESSION_STORE.save(encontro_id, encontro.to_state())

        status_desc, resp_desc = chamar("POST", f"/api/encontros/{encontro_id}/descansar", {"dados_vida": 1})
        self.assertEqual(status_desc, 200)
        self.assertEqual(resp_desc["resultado"]["status"], "resolvido")
        self.assertGreater(resp_desc["estado"]["personagem"]["pv_atuais"], 4)
        self.assertEqual(resp_desc["estado"]["personagem"]["dados_vida_disponiveis"], 0)
        self.assertFalse(resp_desc["estado"]["descanso_curto"]["disponivel"])

        status_dup, resp_dup = chamar("POST", f"/api/encontros/{encontro_id}/descansar", {"dados_vida": 1})
        self.assertEqual(status_dup, 409)
        self.assertEqual(resp_dup["erro"], "descanso_curto_ja_realizado")

        status, avancado = chamar("POST", f"/api/encontros/{encontro_id}/avancar", {})
        self.assertEqual(status, 200)
        self.assertEqual(avancado["resultado"]["mapa_id"], "santuario_circular")
        self.assertEqual(avancado["estado"]["status"], "active")
        self.assertEqual(avancado["estado"]["sala"], 2)
        self.assertEqual(avancado["estado"]["personagem"]["xp"], 100)
        self.assertEqual(avancado["estado"]["personagem"]["ouro_po"], 15)

    def test_listar_classes_e_criar_encontro_com_monge_e_guerreiro(self):
        status, catalogo = chamar("GET", "/api/classes")
        self.assertEqual(status, 200)
        self.assertEqual(
            [c["id"] for c in catalogo["classes"]],
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

        status, estado = chamar("POST", "/api/encontros", {"classe": "monge"})
        self.assertEqual(status, 201)
        self.assertEqual(estado["personagem"]["classe"], "monge")
        self.assertEqual(estado["personagem"]["ca"], 15)
        self.assertEqual(estado["arma_principal"], "Cajado")
        self.assertTrue(estado["acao_bonus_disponivel"])
        self.assertEqual(estado["magias"], [])

        status, estado_g = chamar("POST", "/api/encontros", {"classe": "guerreiro"})
        self.assertEqual(status, 201)
        self.assertEqual(estado_g["personagem"]["classe"], "guerreiro")
        self.assertEqual(estado_g["personagem"]["ca"], 19)
        self.assertEqual(estado_g["arma_principal"], "Espada Longa")
        self.assertEqual(estado_g["arma_distancia"], "Arco Curto")
        self.assertEqual(estado_g["recuperar_folego"]["usos_restantes"], 2)
        encontro_g_id = estado_g["encontro_id"]
        while not estado_g["de_jogador"]:
            status, corpo = chamar("POST", f"/api/encontros/{encontro_g_id}/encerrar", {})
            self.assertEqual(status, 200)
            estado_g = corpo["estado"]

        status, folego = chamar("POST", f"/api/encontros/{encontro_g_id}/recuperar_folego", {})
        self.assertEqual(status, 200)
        self.assertEqual(folego["resultado"]["recurso"], "recuperar_folego")
        self.assertEqual(folego["estado"]["recuperar_folego"]["usos_restantes"], 1)
        self.assertTrue(folego["estado"]["acao_bonus_usada"])

        status, estado_b = chamar("POST", "/api/encontros", {"classe": "barbaro"})
        self.assertEqual(status, 201)
        self.assertEqual(estado_b["personagem"]["classe"], "barbaro")
        self.assertEqual(estado_b["personagem"]["ca"], 14)
        self.assertEqual(estado_b["arma_principal"], "Machado Grande")
        self.assertEqual(estado_b["furia"]["usos_restantes"], 2)
        encontro_b_id = estado_b["encontro_id"]
        while not estado_b["de_jogador"]:
            status, corpo = chamar("POST", f"/api/encontros/{encontro_b_id}/encerrar", {})
            self.assertEqual(status, 200)
            estado_b = corpo["estado"]

        status, furia = chamar("POST", f"/api/encontros/{encontro_b_id}/furia", {})
        self.assertEqual(status, 200)
        self.assertEqual(furia["resultado"]["recurso"], "furia")
        self.assertTrue(furia["estado"]["furia"]["ativa"])
        self.assertEqual(furia["estado"]["furia"]["usos_restantes"], 1)

        status, estado_l = chamar("POST", "/api/encontros", {"classe": "ladino"})
        self.assertEqual(status, 201)
        self.assertEqual(estado_l["personagem"]["classe"], "ladino")
        self.assertEqual(estado_l["personagem"]["ca"], 14)
        self.assertEqual(estado_l["arma_principal"], "Rapieira")
        self.assertEqual(estado_l["arma_distancia"], "Arco Curto")
        encontro_l_id = estado_l["encontro_id"]
        while not estado_l["de_jogador"]:
            status, corpo = chamar("POST", f"/api/encontros/{encontro_l_id}/encerrar", {})
            self.assertEqual(status, 200)
            estado_l = corpo["estado"]

        status, mirar = chamar("POST", f"/api/encontros/{encontro_l_id}/mirar", {})
        self.assertEqual(status, 200)
        self.assertEqual(mirar["resultado"]["recurso"], "mirar")
        self.assertTrue(mirar["estado"]["ladino"]["mirar_ativo"])
        self.assertEqual(mirar["estado"]["movimento_restante_pes"], 0)

        status, estado_c = chamar("POST", "/api/encontros", {"classe": "clerigo"})
        self.assertEqual(status, 201)
        self.assertEqual(estado_c["personagem"]["classe"], "clerigo")
        self.assertEqual(estado_c["personagem"]["ca"], 15)
        self.assertEqual(estado_c["arma_principal"], "Maça")
        encontro_c_id = estado_c["encontro_id"]
        while not estado_c["de_jogador"]:
            status, corpo = chamar("POST", f"/api/encontros/{encontro_c_id}/encerrar", {})
            self.assertEqual(status, 200)
            estado_c = corpo["estado"]

        status, escudo = chamar("POST", f"/api/encontros/{encontro_c_id}/conjurar", {"magia": "Escudo da Fé"})
        self.assertEqual(status, 200)
        self.assertEqual(escudo["estado"]["personagem"]["ca"], 17)
        self.assertTrue(escudo["estado"]["acao_bonus_usada"])
        self.assertFalse(escudo["estado"]["acao_principal_usada"])

        status, estado_m = chamar("POST", "/api/encontros", {"classe": "mago"})
        self.assertEqual(status, 201)
        self.assertEqual(estado_m["personagem"]["classe"], "mago")
        self.assertEqual(estado_m["personagem"]["ca"], 12)
        self.assertEqual(estado_m["arma_principal"], "Cajado")
        encontro_m_id = estado_m["encontro_id"]
        while not estado_m["de_jogador"]:
            status, corpo = chamar("POST", f"/api/encontros/{encontro_m_id}/encerrar", {})
            self.assertEqual(status, 200)
            estado_m = corpo["estado"]

        status, armadura = chamar("POST", f"/api/encontros/{encontro_m_id}/conjurar", {"magia": "Armadura Arcana"})
        self.assertEqual(status, 200)
        self.assertEqual(armadura["estado"]["personagem"]["ca"], 15)
        self.assertTrue(armadura["estado"]["recuperacao_arcana"]["disponivel"])

        status, rec_arcana = chamar("POST", f"/api/encontros/{encontro_m_id}/recuperacao_arcana", {})
        self.assertEqual(status, 200)
        self.assertEqual(rec_arcana["resultado"]["recurso"], "recuperacao_arcana")
        self.assertEqual(rec_arcana["estado"]["recuperacao_arcana"]["usos_restantes"], 0)

        status, estado_p = chamar("POST", "/api/encontros", {"classe": "paladino"})
        self.assertEqual(status, 201)
        self.assertEqual(estado_p["personagem"]["classe"], "paladino")
        self.assertEqual(estado_p["personagem"]["ca"], 18)
        self.assertEqual(estado_p["arma_principal"], "Espada Longa")
        encontro_p_id = estado_p["encontro_id"]
        while not estado_p["de_jogador"]:
            status, corpo = chamar("POST", f"/api/encontros/{encontro_p_id}/encerrar", {})
            self.assertEqual(status, 200)
            estado_p = corpo["estado"]

        status, maos = chamar("POST", f"/api/encontros/{encontro_p_id}/maos_consagradas", {"pontos": 2})
        self.assertEqual(status, 200)
        self.assertEqual(maos["resultado"]["recurso"], "maos_consagradas")
        self.assertEqual(maos["estado"]["maos_consagradas"]["pool_restante"], 3)

        status, estado_d = chamar("POST", "/api/encontros", {"classe": "druida"})
        self.assertEqual(status, 201)
        self.assertEqual(estado_d["personagem"]["classe"], "druida")
        self.assertEqual(estado_d["personagem"]["ca"], 15)
        self.assertEqual(estado_d["arma_principal"], "Cajado")
        encontro_d_id = estado_d["encontro_id"]
        while not estado_d["de_jogador"]:
            status, corpo = chamar("POST", f"/api/encontros/{encontro_d_id}/encerrar", {})
            self.assertEqual(status, 200)
            estado_d = corpo["estado"]

        status, palavra = chamar("POST", f"/api/encontros/{encontro_d_id}/conjurar", {"magia": "Palavra Curativa"})
        self.assertEqual(status, 200)
        self.assertEqual(palavra["resultado"]["magia"], "Palavra Curativa")
        self.assertTrue(palavra["estado"]["acao_bonus_usada"])
        self.assertFalse(palavra["estado"]["acao_principal_usada"])

        status, estado_a = chamar("POST", "/api/encontros", {"classe": "artifice"})
        self.assertEqual(status, 201)
        self.assertEqual(estado_a["personagem"]["classe"], "artifice")
        self.assertEqual(estado_a["personagem"]["ca"], 17)
        self.assertEqual(estado_a["arma_principal"], "Maça")
        self.assertEqual(estado_a["arma_distancia"], "Besta Leve")
        encontro_a_id = estado_a["encontro_id"]
        while not estado_a["de_jogador"]:
            status, corpo = chamar("POST", f"/api/encontros/{encontro_a_id}/encerrar", {})
            self.assertEqual(status, 200)
            estado_a = corpo["estado"]

        status, vitalidade = chamar("POST", f"/api/encontros/{encontro_a_id}/conjurar", {"magia": "Vitalidade Vazia"})
        self.assertEqual(status, 200)
        self.assertEqual(vitalidade["resultado"]["magia"], "Vitalidade Vazia")
        self.assertGreaterEqual(vitalidade["estado"]["personagem"]["pv_temporarios"], 6)

        status, estado_gua = chamar("POST", "/api/encontros", {"classe": "guardiao"})
        self.assertEqual(status, 201)
        self.assertEqual(estado_gua["personagem"]["classe"], "guardiao")
        self.assertEqual(estado_gua["personagem"]["ca"], 15)
        self.assertEqual(estado_gua["arma_principal"], "Espada Curta")
        self.assertEqual(estado_gua["arma_distancia"], "Arco Longo")
        self.assertEqual(estado_gua["inimigo_favorito"]["usos_restantes"], 2)

        status, estado_f = chamar("POST", "/api/encontros", {"classe": "feiticeiro"})
        self.assertEqual(status, 201)
        self.assertEqual(estado_f["personagem"]["classe"], "feiticeiro")
        self.assertEqual(estado_f["personagem"]["ca"], 12)
        self.assertEqual(estado_f["feiticaria_inata"]["usos_restantes"], 2)
        encontro_f_id = estado_f["encontro_id"]
        while not estado_f["de_jogador"]:
            status, corpo = chamar("POST", f"/api/encontros/{encontro_f_id}/encerrar", {})
            self.assertEqual(status, 200)
            estado_f = corpo["estado"]

        status, inata = chamar("POST", f"/api/encontros/{encontro_f_id}/feiticaria_inata", {})
        self.assertEqual(status, 200)
        self.assertEqual(inata["resultado"]["recurso"], "feiticaria_inata")
        self.assertTrue(inata["estado"]["feiticaria_inata"]["ativa"])
        self.assertEqual(inata["estado"]["feiticaria_inata"]["usos_restantes"], 1)

        status, estado_bru = chamar("POST", "/api/encontros", {"classe": "bruxo"})
        self.assertEqual(status, 201)
        self.assertEqual(estado_bru["personagem"]["classe"], "bruxo")
        self.assertEqual(estado_bru["personagem"]["ca"], 15)
        encontro_bru_id = estado_bru["encontro_id"]
        while not estado_bru["de_jogador"]:
            status, corpo = chamar("POST", f"/api/encontros/{encontro_bru_id}/encerrar", {})
            self.assertEqual(status, 200)
            estado_bru = corpo["estado"]

        status, agathys = chamar("POST", f"/api/encontros/{encontro_bru_id}/conjurar", {"magia": "Armadura de Agathys"})
        self.assertEqual(status, 200)
        self.assertEqual(agathys["resultado"]["magia"], "Armadura de Agathys")
        self.assertEqual(agathys["estado"]["personagem"]["pv_temporarios"], 5)

        status, erro = chamar("POST", "/api/encontros", {"classe": "inexistente"})
        self.assertEqual(status, 400)
        self.assertIn("erro", erro)


class EstaticosTests(unittest.TestCase):
    def test_pagina_do_encontro_e_servida(self):
        status, corpo = chamar("GET", "/encontro")
        self.assertEqual(status, 200)
        self.assertIn(b"Ordem de Iniciativa", corpo)
        self.assertIn(b"Encerrar Turno", corpo)
        self.assertIn(b'id="painel-toggle"', corpo)
        self.assertIn(b'id="tela-cheia"', corpo)
        self.assertIn(b'id="painel"', corpo)
        self.assertIn(b'id="seletor-classe"', corpo)
        self.assertIn(b'data-acao="golpe_bonus"', corpo)
        self.assertIn(b'data-acao="recuperar_folego"', corpo)
        self.assertIn(b'data-acao="furia"', corpo)
        self.assertIn(b'data-acao="mirar"', corpo)
        self.assertIn(b'data-acao="recuperacao_arcana"', corpo)
        self.assertIn(b'data-acao="maos_consagradas"', corpo)
        self.assertIn(b'data-acao="magias"', corpo)
        self.assertIn(b'id="turnLabel"', corpo)
        self.assertIn(b'id="minimap"', corpo)
        self.assertIn(b'class="combat-log"', corpo)
        self.assertIn(b'id="retrato"', corpo)
        self.assertIn(b'class="character-panel"', corpo)

    def test_area_de_combate_ocupa_a_viewport_inteira(self):
        status, css = chamar("GET", "/static/app.css")
        self.assertEqual(status, 200)
        regra_mapa = css.split(b".area-mapa {", 1)[1].split(b"}", 1)[0]
        self.assertIn(b"inset: 0;", regra_mapa)

    def test_sprite_sheet_do_bardo_e_servida_com_tipo_e_dimensoes_corretos(self):
        status, corpo, tipo = servidor.despachar("GET", "/static/assets/bardo.png", {})
        self.assertEqual(status, 200)
        self.assertEqual(tipo, "image/png")
        self.assertTrue(corpo.startswith(b"\x89PNG\r\n\x1a\n"))
        dimensoes = (int.from_bytes(corpo[16:20], "big"), int.from_bytes(corpo[20:24], "big"))
        self.assertEqual(dimensoes, (128, 128))
        status, javascript = chamar("GET", "/static/app.js")
        self.assertEqual(status, 200)
        self.assertIn(b"/static/assets/bardo.png", javascript)

    def test_sprite_sheet_do_monge_e_servida_com_tipo_e_dimensoes_corretos(self):
        status, corpo, tipo = servidor.despachar("GET", "/static/assets/monge.png", {})
        self.assertEqual(status, 200)
        self.assertEqual(tipo, "image/png")
        self.assertTrue(corpo.startswith(b"\x89PNG\r\n\x1a\n"))
        dimensoes = (int.from_bytes(corpo[16:20], "big"), int.from_bytes(corpo[20:24], "big"))
        self.assertEqual(dimensoes, (128, 128))
        status, javascript = chamar("GET", "/static/app.js")
        self.assertEqual(status, 200)
        self.assertIn(b"/static/assets/monge.png", javascript)

    def test_sprite_sheet_do_guerreiro_e_servida_com_tipo_e_dimensoes_corretos(self):
        status, corpo, tipo = servidor.despachar("GET", "/static/assets/guerreiro.png", {})
        self.assertEqual(status, 200)
        self.assertEqual(tipo, "image/png")
        self.assertTrue(corpo.startswith(b"\x89PNG\r\n\x1a\n"))
        dimensoes = (int.from_bytes(corpo[16:20], "big"), int.from_bytes(corpo[20:24], "big"))
        self.assertEqual(dimensoes, (128, 128))
        status, javascript = chamar("GET", "/static/app.js")
        self.assertEqual(status, 200)
        self.assertIn(b"/static/assets/guerreiro.png", javascript)

    def test_sprite_sheets_do_barbaro_e_ladino_sao_servidas_com_tipo_e_dimensoes_corretos(self):
        for nome in (
            "barbaro.png",
            "ladino.png",
            "clerigo.png",
            "mago.png",
            "paladino.png",
            "druida.png",
            "artifice.png",
            "guardiao.png",
            "feiticeiro.png",
            "bruxo.png",
        ):
            status, corpo, tipo = servidor.despachar("GET", f"/static/assets/{nome}", {})
            self.assertEqual(status, 200)
            self.assertEqual(tipo, "image/png")
            self.assertTrue(corpo.startswith(b"\x89PNG\r\n\x1a\n"))
            dimensoes = (int.from_bytes(corpo[16:20], "big"), int.from_bytes(corpo[20:24], "big"))
            self.assertEqual(dimensoes, (128, 128))
        status, javascript = chamar("GET", "/static/app.js")
        self.assertEqual(status, 200)
        self.assertIn(b"/static/assets/barbaro.png", javascript)
        self.assertIn(b"/static/assets/ladino.png", javascript)
        self.assertIn(b"/static/assets/clerigo.png", javascript)
        self.assertIn(b"/static/assets/mago.png", javascript)
        self.assertIn(b"/static/assets/paladino.png", javascript)
        self.assertIn(b"/static/assets/druida.png", javascript)
        self.assertIn(b"/static/assets/artifice.png", javascript)
        self.assertIn(b"/static/assets/guardiao.png", javascript)
        self.assertIn(b"/static/assets/feiticeiro.png", javascript)
        self.assertIn(b"/static/assets/bruxo.png", javascript)

    def test_logo_e_icones_de_magias_sao_servidos_com_dimensoes_corretas(self):
        status_logo, corpo_logo, tipo_logo = servidor.despachar("GET", "/static/assets/logo.png", {})
        self.assertEqual(status_logo, 200)
        self.assertEqual(tipo_logo, "image/png")
        self.assertTrue(corpo_logo.startswith(b"\x89PNG\r\n\x1a\n"))
        dim_logo = (int.from_bytes(corpo_logo[16:20], "big"), int.from_bytes(corpo_logo[20:24], "big"))
        self.assertEqual(dim_logo, (128, 128))

        status_mag, corpo_mag, tipo_mag = servidor.despachar("GET", "/static/assets/magias.png", {})
        self.assertEqual(status_mag, 200)
        self.assertEqual(tipo_mag, "image/png")
        self.assertTrue(corpo_mag.startswith(b"\x89PNG\r\n\x1a\n"))
        dim_mag = (int.from_bytes(corpo_mag[16:20], "big"), int.from_bytes(corpo_mag[20:24], "big"))
        self.assertEqual(dim_mag, (192, 64))

        status_d20, corpo_d20, tipo_d20 = servidor.despachar("GET", "/static/assets/d20-spritesheet.png", {})
        self.assertEqual(status_d20, 200)
        self.assertEqual(tipo_d20, "image/png")
        self.assertTrue(corpo_d20.startswith(b"\x89PNG\r\n\x1a\n"))
        dim_d20 = (int.from_bytes(corpo_d20[16:20], "big"), int.from_bytes(corpo_d20[20:24], "big"))
        self.assertEqual(dim_d20, (256, 32))

        status_css, css_d20 = chamar("GET", "/static/d20.css")
        self.assertEqual(status_css, 200)
        self.assertIn(b"d20-spritesheet.png", css_d20)
        self.assertIn(b"is-rolling", css_d20)

        status_js, js_corpo = chamar("GET", "/static/app.js")
        self.assertEqual(status_js, 200)
        self.assertIn(b"playD20Animation", js_corpo)
        self.assertIn(b"bindD20Animation", js_corpo)

    def test_arquivo_fora_da_pasta_web_e_recusado(self):
        status, _ = chamar("GET", "/static/../servidor.py")
        self.assertEqual(status, 404)


class ApiMagiaTests(unittest.TestCase):
    def setUp(self):
        usar_store_memoria(self)

    def abrir_turno_do_bardo(self) -> tuple[str, dict]:
        _, estado = chamar("POST", "/api/encontros", {})
        encontro_id = estado["encontro_id"]
        while not estado["de_jogador"]:
            status, corpo = chamar("POST", f"/api/encontros/{encontro_id}/encerrar", {})
            self.assertEqual(status, 200)
            estado = corpo["estado"]
        return encontro_id, estado

    def test_estado_lista_magias_com_disponibilidade(self):
        _, estado = self.abrir_turno_do_bardo()
        nomes = {m["nome"]: m for m in estado["magias"]}
        self.assertTrue(nomes["Curar Ferimentos"]["disponivel"])
        self.assertTrue(nomes["Comando"]["disponivel"])
        self.assertIsNotNone(nomes["Enfeitiçar Pessoa"]["motivo"])

    def test_conjurar_magia_sem_efeito_retorna_409_com_motivo(self):
        encontro_id, _ = self.abrir_turno_do_bardo()
        status, corpo = chamar("POST", f"/api/encontros/{encontro_id}/conjurar", {"magia": "Luz"})
        self.assertEqual(status, 409)
        self.assertEqual(corpo["erro"], "sem efeito em combate")

    def test_comando_sem_comando_escolhido_retorna_409(self):
        encontro_id, _ = self.abrir_turno_do_bardo()
        status, corpo = chamar(
            "POST", f"/api/encontros/{encontro_id}/conjurar", {"magia": "Comando", "alvo": "goblin-1"}
        )
        self.assertEqual(status, 409)
        self.assertEqual(corpo["erro"], "comando_invalido")

    def test_conjurar_curar_ferimentos_no_turno_do_bardo(self):
        encontro_id, _ = self.abrir_turno_do_bardo()
        status, corpo = chamar("POST", f"/api/encontros/{encontro_id}/conjurar", {"magia": "Curar Ferimentos"})
        self.assertEqual(status, 200)
        self.assertEqual(corpo["resultado"]["status"], "resolvido")
        personagem = corpo["estado"]["personagem"]
        self.assertEqual(personagem["pv_atuais"], corpo["resultado"]["pv_atuais"])
        self.assertLessEqual(personagem["pv_atuais"], personagem["pv_maximo"])
        self.assertTrue(corpo["estado"]["acao_principal_usada"])
        curar = next(m for m in corpo["estado"]["magias"] if m["nome"] == "Curar Ferimentos")
        self.assertFalse(curar["disponivel"])
        self.assertEqual(curar["motivo"], "Ação principal já usada neste turno")

        status, repeticao = chamar(
            "POST", f"/api/encontros/{encontro_id}/conjurar", {"magia": "Curar Ferimentos"}
        )
        self.assertEqual(status, 409)
        self.assertEqual(repeticao["erro"], "acao_principal_usada")

        status, ataque = chamar("POST", f"/api/encontros/{encontro_id}/atacar", {"alvo": "goblin-1"})
        self.assertEqual(status, 409)
        self.assertEqual(ataque["erro"], "acao_principal_usada")


if __name__ == "__main__":
    unittest.main()


class PaginaVersionadaTests(unittest.TestCase):
    def test_pagina_aponta_css_e_js_com_versao_e_sem_cache(self):
        status, corpo = chamar("GET", "/encontro")
        self.assertEqual(status, 200)
        html = corpo.decode("utf-8")
        self.assertRegex(html, r"/static/app\.js\?v=\d+")
        self.assertRegex(html, r"/static/app\.css\?v=\d+")


class MaestriaServidorTests(unittest.TestCase):
    def setUp(self):
        usar_store_memoria(self)

    def test_estado_expoe_maestrias_de_arma_para_classes_marciais(self):
        status, estado = chamar("POST", "/api/encontros", {"classe": "guerreiro", "seed": 42})
        self.assertEqual(status, 201)
        self.assertEqual(
            estado["personagem"]["maestrias_arma"],
            ["Espada Longa", "Arco Curto", "Machado de Batalha"],
        )
        while not estado["de_jogador"]:
            _, corpo = chamar("POST", f"/api/encontros/{estado['encontro_id']}/encerrar", {})
            estado = corpo["estado"]
        status_atq, corpo_atq = chamar(
            "POST",
            f"/api/encontros/{estado['encontro_id']}/atacar",
            {"alvo": "goblin-1"},
        )
        self.assertEqual(status_atq, 200)
        if corpo_atq["resultado"]["acertou"]:
            self.assertEqual(corpo_atq["resultado"]["maestria_aplicada"], "afligir")
            self.assertTrue(any("[maestria: afligir]" in item for item in corpo_atq["estado"]["log"]))


class EspeciesServidorTests(unittest.TestCase):
    def setUp(self):
        usar_store_memoria(self)

    def test_api_especies_e_criacao_de_encontro_com_especie(self):
        status, catalogo = chamar("GET", "/api/especies")
        self.assertEqual(status, 200)
        self.assertEqual(catalogo["padrao"], "anao")
        self.assertEqual(len(catalogo["especies"]), 10)
        ids = [item["id"] for item in catalogo["especies"]]
        self.assertIn("draconato", ids)
        self.assertIn("orc", ids)
        self.assertIn("golias", ids)

        status, estado_draco = chamar(
            "POST",
            "/api/encontros",
            {"classe": "guerreiro", "especie": "draconato"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(estado_draco["personagem"]["especie"], "draconato")
        self.assertEqual(estado_draco["personagem"]["especie_nome"], "Draconato")
        self.assertEqual(estado_draco["personagem"]["usos_sopro_draconico"], 2)
        self.assertEqual(estado_draco["sopro_draconico"]["usos_restantes"], 2)

        status_inv, erro_inv = chamar(
            "POST",
            "/api/encontros",
            {"classe": "guerreiro", "especie": "klingon"},
        )
        self.assertEqual(status_inv, 400)
        self.assertIn("Espécie não suportada", erro_inv["erro"])
