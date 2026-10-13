"""API do encontro de cripta: estado, ações recusadas e arquivos estáticos."""

import io
import json
import unittest

from dungeon_game import servidor


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


class ApiEncontroTests(unittest.TestCase):
    def setUp(self):
        servidor.ENCONTROS.clear()

    def criar(self) -> tuple[str, dict]:
        status, estado = chamar("POST", "/api/encontros", {})
        self.assertEqual(status, 201)
        return estado["encontro_id"], estado

    def test_criar_devolve_estado_com_ca_do_motor_e_iniciativa(self):
        _, estado = self.criar()
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


class EstaticosTests(unittest.TestCase):
    def test_pagina_do_encontro_e_servida(self):
        status, corpo = chamar("GET", "/encontro")
        self.assertEqual(status, 200)
        self.assertIn(b"Ordem de Iniciativa", corpo)
        self.assertIn(b"Encerrar Turno", corpo)

    def test_arquivo_fora_da_pasta_web_e_recusado(self):
        status, _ = chamar("GET", "/static/../servidor.py")
        self.assertEqual(status, 404)


class ApiMagiaTests(unittest.TestCase):
    def setUp(self):
        servidor.ENCONTROS.clear()

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
