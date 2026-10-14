"""API e página do encontro de cripta, com persistência de snapshots configurável.

Toda decisão de regra fica no Encontro/Orquestrador. A API só traduz pedidos
HTTP em chamadas ao encontro e devolve o estado para a interface.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Callable, Iterable

from orchestrator import OrquestradorAcoes
from rule_engine import build_default_engine

from .combat_session import EncounterStatus
from .encontro import (
    CASA_PES,
    SALAS_PADRAO,
    Encontro,
    calcular_ca,
    criar_ficha_personagem,
    inimigos_padrao_do_mapa,
    listar_classes,
    listar_especies_jogaveis,
    listar_mapas,
)
from .inimigos import carregar_inimigo, listar_perfis
from .session_store import SessionStoreError, criar_session_store

WEB_DIR = Path(__file__).parent / "web"
INIMIGOS_PADRAO = list(SALAS_PADRAO["cripta_inicial"]["inimigos"])
TIPOS_CONTENT = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".png": "image/png",
}

_orquestrador = OrquestradorAcoes(build_default_engine())
SESSION_STORE = criar_session_store()


class ErroAPI(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


def criar_encontro(
    seed_base: int = 100,
    *,
    mapa_id: str = "cripta_inicial",
    classe: str = "bardo",
    especie: str | None = None,
) -> str:
    try:
        ficha = criar_ficha_personagem(classe=classe, especie=especie)
        ficha["ca"] = calcular_ca(_orquestrador, ficha)
    except ValueError as erro:
        raise ErroAPI(400, f"Classe ou espécie inválida: {erro}") from erro
    try:
        inimigos = inimigos_padrao_do_mapa(mapa_id)
        encontro = Encontro(_orquestrador, mapa_id, ficha, inimigos, seed_base=seed_base)
    except ValueError as erro:
        raise ErroAPI(400, f"Mapa inválido: {erro}") from erro
    identificador = uuid.uuid4().hex
    SESSION_STORE.save(identificador, encontro.to_state())
    return identificador


def _encontro(identificador: str) -> Encontro:
    state = SESSION_STORE.load(identificador)
    if state is None:
        raise ErroAPI(404, "Encontro não encontrado")
    try:
        encontro = Encontro.from_state(_orquestrador, state)
    except (KeyError, TypeError, ValueError) as erro:
        raise SessionStoreError("O snapshot do encontro está inválido") from erro
    return encontro


def _avancar_ate_jogador(encontro: Encontro) -> None:
    """Executa os turnos dos inimigos até voltar ao jogador ou o combate acabar."""
    limite = 20
    while encontro.status is EncounterStatus.ACTIVE and encontro.turno_de != encontro.ficha["id"] and limite:
        encontro.encerrar_turno()
        limite -= 1


def estado(encontro: Encontro, identificador: str) -> dict[str, Any]:
    ficha = encontro.ficha
    jogador_id = ficha["id"]
    de_jogador = encontro.status is EncounterStatus.ACTIVE and encontro.turno_de == jogador_id
    alcancaveis: list[list[int]] = []
    alvos: list[str] = []
    if de_jogador:
        origem = encontro.posicoes[jogador_id]
        mapa = encontro.board.reachable_positions(
            origem, encontro.movimento_restante_pes, occupied=encontro._ocupadas(jogador_id)
        )
        alcancaveis = sorted([p.x, p.y] for p in mapa if p != origem)
        if not encontro.acao_principal_usada:
            alvos = encontro.alvos_ataque_jogador()
        elif bool((encontro.recursos_artes_marciais() or {}).get("ataque_desarmado_bonus")) and encontro.acao_bonus_disponivel:
            alvos = encontro.alvos_ataque_jogador(apenas_corpo_a_corpo=True)
    magias = encontro.magias_do_personagem()
    if encontro.acao_principal_usada:
        magias = [
            {**magia, "disponivel": False, "motivo": "Ação principal já usada neste turno"}
            if magia["disponivel"] and magia.get("acao") != "bonus"
            else magia
            for magia in magias
        ]
    nomes = {jogador_id: ficha["nome"], **{cid: i["nome"] for cid, i in encontro.inimigos.items()}}
    return {
        "encontro_id": identificador,
        "status": encontro.status.value,
        "andar": encontro.andar,
        "sala": encontro.sala_numero,
        "proxima_sala": encontro.proxima_sala,
        "recompensa": encontro.recompensa,
        "subida_nivel": encontro.subida_nivel,
        "descanso_curto": encontro.recursos_descanso_curto(),
        "rodada": encontro.session.round_number,
        "turno_de": encontro.turno_de,
        "de_jogador": de_jogador,
        "movimento_usado_pes": encontro.movimento_usado_pes,
        "movimento_restante_pes": encontro.movimento_restante_pes,
        "acao_principal_usada": encontro.acao_principal_usada,
        "acao_bonus_usada": encontro.acao_bonus_usada,
        "acao_bonus_disponivel": encontro.acao_bonus_disponivel,
        "arma_principal": encontro.arma_principal,
        "arma_distancia": encontro.arma_distancia,
        "artes_marciais": encontro.recursos_artes_marciais(),
        "recuperar_folego": encontro.recursos_recuperar_folego(),
        "furia": encontro.recursos_furia(),
        "ladino": encontro.recursos_ladino(),
        "recuperacao_arcana": encontro.recursos_recuperacao_arcana(),
        "maos_consagradas": encontro.recursos_maos_consagradas(),
        "inimigo_favorito": encontro.recursos_inimigo_favorito(),
        "feiticaria_inata": encontro.recursos_feiticaria_inata(),
        "sopro_draconico": encontro.recursos_sopro_draconico(),
        "mapa": {
            "id": encontro.mapa["id"],
            "nome": encontro.mapa["nome"],
            "largura": encontro.board.width,
            "altura": encontro.board.height,
            "casa_pes": CASA_PES,
            "grade": encontro.mapa["grade"],
            "legenda": encontro.mapa["legenda"],
        },
        "personagem": {
            "id": jogador_id,
            "nome": ficha["nome"],
            "classe": ficha["classe"],
            "especie": ficha.get("especie"),
            "especie_nome": ficha.get("especie_nome"),
            "tracos_especie": list(ficha.get("tracos_especie") or ()),
            "usos_sopro_draconico": int(ficha.get("usos_sopro_draconico", 0)),
            "usos_ancestralidade_gigante": int(ficha.get("usos_ancestralidade_gigante", 0)),
            "vigor_implacavel_disponivel": bool(ficha.get("vigor_implacavel_disponivel", False)),
            "subclasse": ficha.get("subclasse"),
            "subclasse_nome": ficha.get("subclasse_nome"),
            "caracteristica_subclasse": ficha.get("caracteristica_subclasse_nome"),
            "nivel": ficha["nivel"],
            "pv_atuais": ficha["pv_atuais"],
            "pv_maximo": ficha["pv_maximo"],
            "pv_temporarios": int(ficha.get("pv_temporarios", 0)),
            "ca": ficha["ca"],
            "xp": int(ficha.get("xp", 0)),
            "ouro_po": int(ficha.get("ouro_po", 0)),
            "dados_vida_disponiveis": int(ficha.get("dados_vida_disponiveis", ficha.get("nivel", 1))),
            "dados_vida_maximos": int(ficha.get("dados_vida_maximos", ficha.get("nivel", 1))),
            "arma_padrao": encontro.arma_principal,
            "arma_distancia": encontro.arma_distancia,
            "maestrias_arma": list(ficha.get("maestrias_arma") or ()),
            "condicoes": encontro._condicoes_combatente(jogador_id)
            + (["maldicao_da_mumia"] if ficha.get("maldicao_da_mumia") else []),
            "reducao_forca": int(ficha.get("reducao_forca_sombra", 0)),
            "deslocamento_pes": encontro.deslocamento_pes,
            "posicao": [encontro.posicoes[jogador_id].x, encontro.posicoes[jogador_id].y],
        },
        "unidades": [
            {
                "id": cid,
                "nome": inimigo["nome"],
                "perfil": inimigo["perfil"],
                "pv_atuais": inimigo["pv_atuais"],
                "pv_maximo": inimigo["pv_maximo"],
                "ca": inimigo["ca"],
                "derrotado": cid in encontro.inimigos_derrotados,
                "condicoes": encontro._condicoes_combatente(cid),
                "posicao": [encontro.posicoes[cid].x, encontro.posicoes[cid].y],
            }
            for cid, inimigo in encontro.inimigos.items()
        ],
        "iniciativa": [
            {"id": c.id, "nome": nomes.get(c.id, c.id), "total": c.initiative} for c in encontro.session.combatants
        ],
        "alcancaveis": alcancaveis,
        "alvos": alvos,
        "magias": magias,
        "alvos_magia": encontro.alvos_magia()
        if de_jogador and (not encontro.acao_principal_usada or not encontro.acao_bonus_usada)
        else [],
        "log": [_resumo(evento, nomes) for evento in encontro.log[-12:]],
    }


def _resumo(evento: dict[str, Any], nomes: dict[str, str]) -> str:
    tipo = evento.get("evento")
    if tipo == "iniciativa":
        return "Iniciativa rolada"
    if tipo == "mover":
        return f"{nomes.get(evento['ator'], evento['ator'])} se moveu"
    if tipo == "movimento_inimigo":
        return f"{nomes.get(evento['ator'], evento['ator'])} se aproximou"
    if tipo == "ataque_jogador":
        alvo = nomes.get(evento.get("alvo"), evento.get("alvo"))
        if evento.get("arma") == "Ataque de Sopro":
            prefixo = "Ataque de Sopro"
        elif evento.get("acao_bonus"):
            prefixo = "Golpe Desarmado (bônus)"
        else:
            prefixo = "Ataque"
        tipo_acerto = "acerto crítico" if evento.get("critico") else "acerto"
        detalhe_dano = f"{tipo_acerto}, {evento.get('dano')} de dano"
        if evento.get("ataque_furtivo"):
            detalhe_dano += " (furtivo)"
        if evento.get("dano_furia"):
            detalhe_dano += " (fúria)"
        if evento.get("dano_marca_do_predador"):
            detalhe_dano += " (marca)"
        if evento.get("maestria_aplicada"):
            detalhe_dano += f" [maestria: {evento['maestria_aplicada']}]"
        if evento.get("alvo_trespassar"):
            alvo_t = nomes.get(evento["alvo_trespassar"], evento["alvo_trespassar"])
            detalhe_dano += f" (+{evento.get('dano_trespassar', 0)} em {alvo_t})"
        if evento.get("defesa_aplicada") == "vulnerabilidade":
            detalhe_dano += " (vulnerável)"
        elif evento.get("defesa_aplicada") == "resistencia":
            detalhe_dano += " (resistido)"
        elif evento.get("defesa_aplicada") == "imunidade":
            detalhe_dano += " (imune)"
        if evento.get("fortitude_morto_vivo"):
            detalhe_dano += " (Fortitude de Morto-Vivo → 1 PV)"
        if not evento.get("acertou"):
            if evento.get("maestria_aplicada") == "garantido" and evento.get("dano"):
                return f"{prefixo} em {alvo}: erro (maestria garantido: {evento['dano']} de dano)"
            return f"{prefixo} em {alvo}: erro"
        return f"{prefixo} em {alvo}: {detalhe_dano}"
    if tipo == "magia":
        ator = nomes.get(evento["ator"], evento["ator"])
        if evento["magia"] in {"Curar Ferimentos", "Palavra Curativa"}:
            sufixo_maldicao = " (bloqueado pela Maldição da Múmia)" if evento.get("bloqueado_por_maldicao") else ""
            return f"{ator} conjura {evento['magia']}: cura {evento['curado']} PV{sufixo_maldicao}"
        if evento["magia"] == "Vitalidade Vazia":
            return f"{ator} conjura Vitalidade Vazia (+{evento.get('pv_temporarios', 0)} PV temp)"
        if evento["magia"] == "Armadura de Agathys":
            return f"{ator} conjura Armadura de Agathys (+{evento.get('pv_temporarios', 5)} PV temp)"
        if evento["magia"] == "Marca do Predador":
            alvo = nomes.get(evento.get("alvo"), evento.get("alvo"))
            return f"{ator} conjura Marca do Predador em {alvo} (+{evento.get('dado_dano_extra', '1d6')} dano)"
        if evento["magia"] == "Escudo da Fé":
            return f"{ator} conjura Escudo da Fé (+{evento.get('bonus_ca', 2)} CA → CA {evento.get('ca')})"
        if evento["magia"] == "Armadura Arcana":
            return f"{ator} conjura Armadura Arcana (CA {evento.get('ca')})"
        alvo = nomes.get(evento.get("alvo"), evento.get("alvo"))
        if evento["magia"] == "Comando":
            return f"{ator} usa Comando em {alvo}" + (
                f": {evento['comando']}" if "comando" in evento else ", resistido"
            )
        sufixo_defesa = ""
        if evento.get("defesa_aplicada") == "vulnerabilidade":
            sufixo_defesa = " (vulnerável)"
        elif evento.get("defesa_aplicada") == "resistencia":
            sufixo_defesa = " (resistido)"
        elif evento.get("defesa_aplicada") == "imunidade":
            sufixo_defesa = " (imune)"
        if evento.get("fortitude_morto_vivo"):
            sufixo_defesa += " (Fortitude de Morto-Vivo → 1 PV)"
        if evento["magia"] == "Mísseis Mágicos":
            return f"{ator} conjura Mísseis Mágicos em {alvo}: {evento.get('dano')} de dano{sufixo_defesa}"
        if "acertou" in evento:
            return f"{ator} usa {evento['magia']} em {alvo}: " + (
                f"acerto, {evento.get('dano')} de dano{sufixo_defesa}" if evento.get("acertou") else "erro"
            )
        return f"{ator} usa {evento['magia']} em {alvo}: " + (
            f"{evento['dano']} de dano{sufixo_defesa}" if ("dano" in evento and evento.get("defesa_aplicada")) or evento.get("dano") else "resistido"
        )
    if tipo == "ataque_inimigo":
        ator = nomes.get(evento.get("ator"), evento.get("ator"))
        detalhe_inimigo = f"acerto, {evento.get('dano')} de dano"
        if evento.get("defesa_aplicada") == "resistencia":
            detalhe_inimigo += " (resistido)"
        if evento.get("dano_investida"):
            detalhe_inimigo += f" [Investida +{evento['dano_investida']}]"
        if evento.get("dreno_forca"):
            detalhe_inimigo += f" (-{evento['dreno_forca']} FOR)"
        if evento.get("reducao_pv_maximo"):
            detalhe_inimigo += f" (-{evento['reducao_pv_maximo']} PV máx)"
        if evento.get("condicao_aplicada") == "paralisado":
            detalhe_inimigo += " [paralisado!]"
        elif evento.get("condicao_aplicada") == "caido":
            detalhe_inimigo += " [derrubado!]"
        elif evento.get("condicao_aplicada") == "maldicao_da_mumia":
            detalhe_inimigo += " [Maldição da Múmia!]"
        return f"{ator} ataca: " + (detalhe_inimigo if evento.get("acertou") else "erro")
    if tipo == "recuperar_folego":
        ator = nomes.get(evento.get("ator"), evento.get("ator"))
        return f"{ator} usa Recuperar o Fôlego: cura {evento.get('curado', 0)} PV"
    if tipo == "furia":
        ator = nomes.get(evento.get("ator"), evento.get("ator"))
        return f"{ator} entra em Fúria (+2 dano e resistência física)"
    if tipo == "mirar":
        ator = nomes.get(evento.get("ator"), evento.get("ator"))
        return f"{ator} usa Mirar (vantagem no próximo ataque)"
    if tipo == "recuperacao_arcana":
        ator = nomes.get(evento.get("ator"), evento.get("ator"))
        return f"{ator} usa Recuperação Arcana (+1 espaço de 1º círculo)"
    if tipo == "maos_consagradas":
        ator = nomes.get(evento.get("ator"), evento.get("ator"))
        return f"{ator} usa Mãos Consagradas: cura {evento.get('curado', 0)} PV"
    if tipo == "feiticaria_inata":
        ator = nomes.get(evento.get("ator"), evento.get("ator"))
        return f"{ator} ativa Feitiçaria Inata (+{evento.get('bonus_cd', 1)} CD e vantagem em ataques mágicos)"
    if tipo == "vigor_implacavel":
        ator = nomes.get(evento.get("ator"), evento.get("ator"))
        return f"{ator} ativa Vigor Implacável e permanece de pé com 1 PV!"
    if tipo == "descanso_curto":
        ator = nomes.get(evento.get("ator"), evento.get("ator"))
        return f"{ator} faz Descanso Curto: +{evento.get('curado', 0)} PV ({evento.get('dados_vida_gastos', 0)} DV)"
    if tipo == "subiu_nivel":
        ator = nomes.get(evento.get("ator"), evento.get("ator"))
        return f"{ator} alcançou o Nível {evento.get('nivel')} (+{evento.get('pv_ganhos', 0)} PV máx)!"
    if tipo == "recompensa":
        return f"Recompensa: +{evento.get('xp', 0)} XP, +{evento.get('ouro_po', 0)} PO"
    if tipo == "avancar_sala":
        return f"Avançou para a sala {evento.get('sala', '')}"
    return str(tipo)


def acao(encontro: Encontro, nome: str, corpo: dict[str, Any]) -> dict[str, Any]:
    try:
        if nome == "mover":
            resultado = encontro.mover((int(corpo["x"]), int(corpo["y"])))
        elif nome == "atacar":
            acao_bonus = bool(corpo.get("acao_bonus", False))
            arma = corpo.get("arma")
            resultado = encontro.atacar_jogador(
                str(corpo["alvo"]),
                acao_bonus=acao_bonus,
                arma=None if arma is None else str(arma),
            )
        elif nome == "recuperar_folego":
            resultado = encontro.recuperar_folego()
        elif nome == "furia":
            resultado = encontro.ativar_furia()
        elif nome == "mirar":
            resultado = encontro.mirar()
        elif nome == "recuperacao_arcana":
            resultado = encontro.recuperacao_arcana()
        elif nome == "maos_consagradas":
            pontos = corpo.get("pontos")
            resultado = encontro.maos_consagradas(None if pontos is None else int(pontos))
        elif nome == "feiticaria_inata":
            resultado = encontro.ativar_feiticaria_inata()
        elif nome == "conjurar":
            alvo = corpo.get("alvo")
            comando = corpo.get("comando")
            resultado = encontro.conjurar(
                str(corpo["magia"]),
                None if alvo is None else str(alvo),
                None if comando is None else str(comando),
            )
        elif nome == "encerrar":
            encontro.encerrar_turno()
            _avancar_ate_jogador(encontro)
            resultado = {"status": "resolvido"}
        elif nome == "descansar":
            dados_vida = corpo.get("dados_vida", 1)
            resultado = encontro.descansar_curto(1 if dados_vida is None else int(dados_vida))
        elif nome == "avancar":
            resultado = encontro.avancar_sala()
            if resultado.get("status") == "resolvido":
                _avancar_ate_jogador(encontro)
        else:
            raise ErroAPI(404, "Ação desconhecida")
    except (KeyError, TypeError, ValueError) as erro:
        raise ErroAPI(400, f"Pedido inválido: {erro}") from erro
    if resultado.get("status") == "bloqueado":
        raise ErroAPI(409, resultado.get("motivo", "ação recusada"))
    return resultado


def _ler_json(environ: dict[str, Any]) -> dict[str, Any]:
    tamanho = int(environ.get("CONTENT_LENGTH") or 0)
    if tamanho == 0:
        return {}
    try:
        return json.loads(environ["wsgi.input"].read(tamanho).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as erro:
        raise ErroAPI(400, "JSON inválido") from erro


def _resposta(status: int, corpo: Any, tipo: str = "application/json; charset=utf-8") -> tuple[int, bytes, str]:
    dados = corpo if isinstance(corpo, bytes) else json.dumps(corpo, ensure_ascii=False).encode("utf-8")
    return status, dados, tipo


def despachar(metodo: str, caminho: str, environ: dict[str, Any]) -> tuple[int, bytes, str]:
    if metodo == "GET" and caminho == "/health":
        SESSION_STORE.ping()
        return _resposta(200, {"status": "ok"})
    if metodo == "GET" and caminho in {"/", "/encontro"}:
        return _arquivo("index.html")
    if metodo == "GET" and caminho.startswith("/static/"):
        return _arquivo(caminho.removeprefix("/static/"))
    if metodo == "GET" and caminho == "/api/mapas":
        return _resposta(200, {"mapas": listar_mapas()})
    if metodo == "GET" and caminho == "/api/inimigos":
        return _resposta(200, {"inimigos": [carregar_inimigo(p) for p in listar_perfis()]})
    if metodo == "GET" and caminho == "/api/classes":
        return _resposta(200, {"classes": listar_classes(), "padrao": "bardo"})
    if metodo == "GET" and caminho == "/api/especies":
        return _resposta(200, {"especies": listar_especies_jogaveis(), "padrao": "anao"})
    if caminho == "/api/encontros" and metodo == "POST":
        corpo = _ler_json(environ)
        mapa_id = str(corpo.get("mapa_id") or "cripta_inicial")
        classe = str(corpo.get("classe") or "bardo")
        especie_raw = corpo.get("especie")
        especie = None if not especie_raw else str(especie_raw)
        identificador = criar_encontro(mapa_id=mapa_id, classe=classe, especie=especie)
        encontro = _encontro(identificador)
        return _resposta(201, estado(encontro, identificador))
    partes = caminho.strip("/").split("/")
    if len(partes) >= 3 and partes[:2] == ["api", "encontros"]:
        encontro = _encontro(partes[2])
        if len(partes) == 3 and metodo == "GET":
            return _resposta(200, estado(encontro, partes[2]))
        if len(partes) == 4 and metodo == "POST":
            resultado = acao(encontro, partes[3], _ler_json(environ))
            SESSION_STORE.save(partes[2], encontro.to_state())
            return _resposta(200, {"resultado": resultado, "estado": estado(encontro, partes[2])})
    raise ErroAPI(404, "Rota não encontrada")


def _arquivo(nome: str) -> tuple[int, bytes, str]:
    caminho = (WEB_DIR / nome).resolve()
    if WEB_DIR.resolve() not in caminho.parents or not caminho.is_file():
        raise ErroAPI(404, "Arquivo não encontrado")
    dados = caminho.read_bytes()
    if caminho.suffix == ".html":
        dados = _html_com_versoes(dados)
    return _resposta(200, dados, TIPOS_CONTENT.get(caminho.suffix, "application/octet-stream"))


def _html_com_versoes(html: bytes) -> bytes:
    """Acrescenta ?v=<data de modificação> aos CSS/JS, para que uma mudança nunca use arquivo antigo do cache."""
    texto = html.decode("utf-8")
    for arquivo in ("app.css", "d20.css", "app.js"):
        caminho = WEB_DIR / arquivo
        if caminho.is_file():
            versao = int(caminho.stat().st_mtime)
            texto = texto.replace(f"/static/{arquivo}", f"/static/{arquivo}?v={versao}")
    return texto.encode("utf-8")


def app(environ: dict[str, Any], start_response: Callable[..., Any]) -> Iterable[bytes]:
    metodo = environ.get("REQUEST_METHOD", "GET").upper()
    caminho = environ.get("PATH_INFO", "/")
    try:
        status, corpo, tipo = despachar(metodo, caminho, environ)
    except ErroAPI as erro:
        status, corpo, tipo = _resposta(erro.status, {"erro": erro.mensagem})
    except SessionStoreError:
        status, corpo, tipo = _resposta(503, {"erro": "persistencia_indisponivel"})
    # Sem cache: o celular sempre recebe a versão atual de HTML, CSS e JS.
    cabecalhos = [
        ("Content-Type", tipo),
        ("Content-Length", str(len(corpo))),
        ("Cache-Control", "no-cache, no-store, must-revalidate"),
    ]
    start_response(f"{status} {'OK' if status < 400 else 'ERRO'}", cabecalhos)
    return [corpo]


def main() -> None:
    import os
    from wsgiref.simple_server import make_server

    porta = int(os.environ.get("PORT", "8100"))
    with make_server("0.0.0.0", porta, app) as servidor:
        print(f"Encontro de cripta em http://0.0.0.0:{porta}/encontro")
        servidor.serve_forever()


if __name__ == "__main__":
    main()
