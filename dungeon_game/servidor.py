"""API e página do encontro de cripta. Estado em memória (persistência: Etapa 5).

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
from .encontro import CASA_PES, Encontro, calcular_ca, criar_ficha_bardo

WEB_DIR = Path(__file__).parent / "web"
INIMIGOS_PADRAO = [("goblin-1", "goblin", (13, 3)), ("esqueleto-1", "esqueleto", (13, 10))]
TIPOS_CONTENT = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}

_orquestrador = OrquestradorAcoes(build_default_engine())
ENCONTROS: dict[str, Encontro] = {}


class ErroAPI(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


def criar_encontro(seed_base: int = 100) -> str:
    ficha = criar_ficha_bardo()
    ficha["ca"] = calcular_ca(_orquestrador, ficha)
    encontro = Encontro(_orquestrador, "cripta_inicial", ficha, INIMIGOS_PADRAO, seed_base=seed_base)
    identificador = uuid.uuid4().hex[:10]
    ENCONTROS[identificador] = encontro
    return identificador


def _encontro(identificador: str) -> Encontro:
    encontro = ENCONTROS.get(identificador)
    if encontro is None:
        raise ErroAPI(404, "Encontro não encontrado")
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
            alvos = encontro.alvos_ao_alcance(jogador_id, 5)
    magias = encontro.magias_do_personagem()
    if encontro.acao_principal_usada:
        magias = [
            {**magia, "disponivel": False, "motivo": "Ação principal já usada neste turno"}
            if magia["disponivel"]
            else magia
            for magia in magias
        ]
    nomes = {jogador_id: ficha["nome"], **{cid: i["nome"] for cid, i in encontro.inimigos.items()}}
    return {
        "encontro_id": identificador,
        "status": encontro.status.value,
        "rodada": encontro.session.round_number,
        "turno_de": encontro.turno_de,
        "de_jogador": de_jogador,
        "movimento_usado_pes": encontro.movimento_usado_pes,
        "movimento_restante_pes": encontro.movimento_restante_pes,
        "acao_principal_usada": encontro.acao_principal_usada,
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
            "nivel": ficha["nivel"],
            "pv_atuais": ficha["pv_atuais"],
            "pv_maximo": ficha["pv_maximo"],
            "ca": ficha["ca"],
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
        "alvos_magia": encontro.alvos_magia() if de_jogador and not encontro.acao_principal_usada else [],
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
        return f"Ataque em {alvo}: " + (f"acerto, {evento['dano']} de dano" if evento.get("acertou") else "erro")
    if tipo == "magia":
        ator = nomes.get(evento["ator"], evento["ator"])
        if evento["magia"] == "Curar Ferimentos":
            return f"{ator} conjura {evento['magia']}: cura {evento['curado']} PV"
        alvo = nomes.get(evento.get("alvo"), evento.get("alvo"))
        if evento["magia"] == "Comando":
            return f"{ator} usa Comando em {alvo}" + (
                f": {evento['comando']}" if "comando" in evento else ", resistido"
            )
        return f"{ator} usa {evento['magia']} em {alvo}: " + (
            f"{evento['dano']} de dano" if evento.get("dano") else "resistido"
        )
    if tipo == "ataque_inimigo":
        ator = nomes.get(evento.get("ator"), evento.get("ator"))
        return f"{ator} ataca: " + (f"acerto, {evento['dano']} de dano" if evento.get("acertou") else "erro")
    return str(tipo)


def acao(encontro: Encontro, nome: str, corpo: dict[str, Any]) -> dict[str, Any]:
    try:
        if nome == "mover":
            resultado = encontro.mover((int(corpo["x"]), int(corpo["y"])))
        elif nome == "atacar":
            resultado = encontro.atacar_jogador(str(corpo["alvo"]))
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
    if metodo == "GET" and caminho in {"/", "/encontro"}:
        return _arquivo("index.html")
    if metodo == "GET" and caminho.startswith("/static/"):
        return _arquivo(caminho.removeprefix("/static/"))
    if caminho == "/api/encontros" and metodo == "POST":
        identificador = criar_encontro()
        return _resposta(201, estado(ENCONTROS[identificador], identificador))
    partes = caminho.strip("/").split("/")
    if len(partes) >= 3 and partes[:2] == ["api", "encontros"]:
        encontro = _encontro(partes[2])
        if len(partes) == 3 and metodo == "GET":
            return _resposta(200, estado(encontro, partes[2]))
        if len(partes) == 4 and metodo == "POST":
            resultado = acao(encontro, partes[3], _ler_json(environ))
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
    for arquivo in ("app.css", "app.js"):
        versao = int((WEB_DIR / arquivo).stat().st_mtime)
        texto = texto.replace(f"/static/{arquivo}", f"/static/{arquivo}?v={versao}")
    return texto.encode("utf-8")


def app(environ: dict[str, Any], start_response: Callable[..., Any]) -> Iterable[bytes]:
    metodo = environ.get("REQUEST_METHOD", "GET").upper()
    caminho = environ.get("PATH_INFO", "/")
    try:
        status, corpo, tipo = despachar(metodo, caminho, environ)
    except ErroAPI as erro:
        status, corpo, tipo = _resposta(erro.status, {"erro": erro.mensagem})
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
