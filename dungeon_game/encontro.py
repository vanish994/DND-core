"""Encontro de cripta: um Bardo contra inimigos do bestiário, por turnos.

Regras não são resolvidas aqui. Iniciativa, ataque, dano, PV e CA passam pelo
Orquestrador; a geometria (grade, alcance, caminho) vem do tabuleiro. Este
módulo guarda o estado do encontro e decide a ordem das chamadas.

Simplificações conscientes desta etapa:
- água é caminhável com custo normal (o tabuleiro não modela custo 2 ainda);
- a IA dos inimigos é: atacar se estiver ao alcance, senão aproximar-se;
- posições são mantidas aqui; o CombatSession cuida só de ordem e derrota.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from character_creator.service import CharacterCreatorService
from orchestrator import Acao, OrquestradorAcoes
from orchestrator.preparo import cd_de_magia
from rule_engine.bestiary import consultar_monstro
from rule_engine.catalog import CATALOGO_ARMADURAS
from rule_engine.spells import mecanica_de_magia
from rule_engine.survival import EstadoVital

from .combat_board import BoardPosition, CombatBoard
from .combat_session import Combatant, CombatSession, EncounterStatus
from .combate_inimigo import atacar as atacar_inimigo
from .inimigos import carregar_inimigo
from .rule_adapter import DungeonRuleAdapter

MAPAS_DIR = Path(__file__).parent / "mapas"
SIMBOLOS_BLOQUEADOS = {"#", "+", "o"}
CASA_PES = 5
ATRIBUTO_CONJURACAO = "carisma"

# Magias com efeito resolvido no encontro. Curar Ferimentos: 2d8 + modificador de
# conjuração (PHB 2024; a mecânica do motor também marca soma_modificador_conjuracao).
EFEITOS_EM_COMBATE = {"Curar Ferimentos", "Zombaria Perversa", "Comando"}

# Alvo de cada magia: si mesmo (toque) ou inimigo ao alcance.
ALVO_MAGIA = {"Curar Ferimentos": "si_mesmo", "Zombaria Perversa": "inimigo", "Comando": "inimigo"}
SALVAGUARDA_EM_COMBATE = {"Zombaria Perversa", "Comando"}  # usam CD de magia (salvaguarda do alvo)
ALCANCE_MAGIA_PES = 60  # 18 m, alcance de Zombaria Perversa e Comando

# Comandos de Comando (PHB 2024). Cada um vale só para o próximo turno do alvo.
COMANDOS = ("aproximar", "largar", "fugir", "abaixar", "parar")

MOTIVOS_SEM_EFEITO = {
    "Golpe Certeiro": "magia sem resolução específica no motor",
    "Luz": "sem efeito em combate",
    "Ilusão Menor": "sem efeito em combate",
    "Detectar Magia": "sem efeito em combate",
    "Enfeitiçar Pessoa": "efeito ainda não resolvido pelo motor (salvaguarda e condição)",
}


def carregar_mapa(mapa_id: str) -> dict[str, Any]:
    return json.loads((MAPAS_DIR / f"{mapa_id}.json").read_text(encoding="utf-8"))


def tabuleiro_do_mapa(mapa: dict[str, Any]) -> CombatBoard:
    grade = mapa["grade"]
    bloqueadas = frozenset(
        BoardPosition(x, y)
        for y, linha in enumerate(grade)
        for x, simbolo in enumerate(linha)
        if simbolo in SIMBOLOS_BLOQUEADOS
    )
    return DungeonRuleAdapter.create_combat_board(len(grade[0]), len(grade), blocked=bloqueadas, tile_feet=CASA_PES)


def criar_ficha_bardo(nome: str = "Vanish", *, id_ficha: str = "bardo-1") -> dict[str, Any]:
    """Ficha de Bardo nível 1 validada pelo criador, com CA calculada pelo motor.

    O criador ainda não calcula CA nem escolhe armadura; a armadura (Couro) é
    aplicada pelo motor sobre a Destreza da ficha.
    """
    payload = {
        "name": nome,
        "class": "bardo",
        "species": "anao",
        "background": "fazendeiro",
        "ravenloft": False,
        "ability_method": "standard_array",
        "ability_scores": {
            "forca": 8,
            "destreza": 14,
            "constituicao": 13,
            "inteligencia": 10,
            "sabedoria": 12,
            "carisma": 15,
        },
        "background_increases": {"constituicao": 2, "sabedoria": 1},
        "background_equipment": "A",
        "class_skills": ["atuacao", "intuicao", "persuasao"],
        "spells": {
            "cantrips": ["Luz", "Ilusão Menor"],
            "selected": ["Curar Ferimentos", "Detectar Magia", "Enfeitiçar Pessoa", "Comando"],
            "spellbook": [],
        },
        "narrative": {"pronouns": "ele/dele", "appearance": "Capuz escuro e lâmina fina."},
    }
    previa = CharacterCreatorService().preview(payload)
    if not previa.get("ready"):
        raise ValueError(f"Ficha de Bardo incompleta: {previa.get('missing')}")
    ficha = dict(previa["character"])
    ficha["id"] = id_ficha
    ficha["conjuracao"] = _conjuracao_validada(previa)
    # O criador grava o deslocamento em metros (9 m = 30 pés); o tabuleiro usa casas de 5 pés.
    ficha["deslocamento_pes"] = round(float(ficha["deslocamento"]) * 3.28084 / CASA_PES) * CASA_PES
    ficha["pv_atuais"] = ficha["pv_maximo"]
    ficha["pv_temporarios"] = 0
    return ficha


def _conjuracao_validada(previa: dict[str, Any]) -> dict[str, Any]:
    """Converte as escolhas de magia já validadas pelo criador na conjuração da ficha.

    O criador valida truques, magias e espaços, mas não os grava na ficha; esta
    função faz essa ponte sem acrescentar nenhuma magia.
    """
    detalhes = previa["validation"]["spell_choices"]["details"]
    espacos = int(detalhes["slots"][0])
    return {
        "truques": list(detalhes["cantrips"]),
        "magias_preparadas": list(detalhes["selected"]),
        "espacos_totais": {"1": espacos},
        "espacos_restantes": {"1": espacos},
    }


def calcular_ca(orquestrador: OrquestradorAcoes, ficha: dict[str, Any]) -> int:
    fatos = {
        "type": "armor_class",
        "armor": "leve",
        # O motor soma 10 + bônus + Destreza; o bônus é a CA base da armadura menos 10.
        "armor_bonus": CATALOGO_ARMADURAS["Couro"]["ca"] - 10,
        "dexterity_modifier": ficha["modificadores"]["destreza"],
        "shield": False,
        "armor_proficient": True,
    }
    resultado = orquestrador.executar(Acao.de_ferramenta("resolver_regra", {"fatos": fatos}), [])
    if resultado.dados.get("resultado") != "calculada":
        raise ValueError(f"CA não calculada: {resultado.dados.get('motivo')}")
    return int(resultado.dados["ca"])


class Encontro:
    def __init__(
        self,
        orquestrador: OrquestradorAcoes,
        mapa_id: str,
        ficha: dict[str, Any],
        perfis_inimigos: list[tuple[str, str, tuple[int, int]]],
        *,
        seed_base: int = 1,
    ) -> None:
        """``perfis_inimigos``: lista de (id_do_combatente, perfil, (x, y)).

        A ficha precisa ter ``ca`` (use :func:`calcular_ca`).
        """
        self.orquestrador = orquestrador
        self.mapa_id = mapa_id
        self.mapa = carregar_mapa(mapa_id)
        self.board = tabuleiro_do_mapa(self.mapa)
        self.ficha = ficha
        self.deslocamento_pes = int(ficha.get("deslocamento_pes", 30))
        self.movimento_usado_pes = 0
        self.acao_principal_usada = False
        self._seed = seed_base
        self.log: list[dict[str, Any]] = []

        self.posicoes: dict[str, BoardPosition] = {ficha["id"]: BoardPosition(*self._entrada_jogador())}
        self.inimigos: dict[str, dict[str, Any]] = {}
        for cid, perfil, (x, y) in perfis_inimigos:
            stats = carregar_inimigo(perfil)
            self.inimigos[cid] = {
                "perfil": perfil,
                "nome": stats["nome"],
                "monstro": stats["monstro"],
                "ca": stats["ca"],
                "pv_maximo": stats["pv"],
                "pv_atuais": stats["pv"],
                "pv_temporarios": 0,
                "alcance_maximo": stats["acao"]["alcance_pes"]["maximo"],
                "deslocamento_pes": stats["deslocamento_pes"],
            }
            self.posicoes[cid] = BoardPosition(x, y)
        self.inimigos_derrotados: set[str] = set()

        ordem = self._rolar_iniciativas()
        self.session = CombatSession(
            self.board,
            [
                Combatant(id=cid, position=self.posicoes[cid], initiative=total, is_player=cid == ficha["id"])
                for cid, total in ordem
            ],
        )

    def to_state(self) -> dict[str, Any]:
        """Exporta somente o estado mutável necessário para retomar o encontro."""
        efeitos_mutaveis = ("desvantagem_proximo_ataque", "comando_pendente", "caido")
        return {
            "versao": 1,
            "mapa_id": self.mapa_id,
            "ficha": self.ficha,
            "deslocamento_pes": self.deslocamento_pes,
            "movimento_usado_pes": self.movimento_usado_pes,
            "acao_principal_usada": self.acao_principal_usada,
            "semente": self._seed,
            "log": self.log,
            "posicoes": {cid: [pos.x, pos.y] for cid, pos in self.posicoes.items()},
            "inimigos": {
                cid: {
                    "perfil": inimigo["perfil"],
                    "pv_atuais": inimigo["pv_atuais"],
                    "pv_temporarios": inimigo["pv_temporarios"],
                    "efeitos": {chave: inimigo[chave] for chave in efeitos_mutaveis if chave in inimigo},
                }
                for cid, inimigo in self.inimigos.items()
            },
            "inimigos_derrotados": sorted(self.inimigos_derrotados),
            "combatentes": [
                {"id": c.id, "iniciativa": c.initiative, "is_player": c.is_player}
                for c in self.session.combatants
            ],
            "sessao": {
                "derrotados": sorted(self.session._defeated),
                "rodada": self.session.round_number,
                "indice_turno": self.session._turn_index,
                "status": self.session.status.value,
            },
        }

    @classmethod
    def from_state(cls, orquestrador: OrquestradorAcoes, state: dict[str, Any]) -> Encontro:
        """Reconstrói um encontro usando mapas e blocos de estatísticas canônicos."""
        if state.get("versao") != 1:
            raise ValueError("versão de snapshot não suportada")

        encontro = cls.__new__(cls)
        encontro.orquestrador = orquestrador
        encontro.mapa_id = str(state["mapa_id"])
        encontro.mapa = carregar_mapa(encontro.mapa_id)
        encontro.board = tabuleiro_do_mapa(encontro.mapa)
        encontro.ficha = dict(state["ficha"])
        encontro.deslocamento_pes = int(state["deslocamento_pes"])
        encontro.movimento_usado_pes = int(state["movimento_usado_pes"])
        encontro.acao_principal_usada = bool(state["acao_principal_usada"])
        encontro._seed = int(state["semente"])
        encontro.log = list(state["log"])

        encontro.posicoes = {
            cid: BoardPosition(int(posicao[0]), int(posicao[1]))
            for cid, posicao in state["posicoes"].items()
        }
        encontro.inimigos = {}
        for cid, salvo in state["inimigos"].items():
            stats = carregar_inimigo(str(salvo["perfil"]))
            inimigo = {
                "perfil": stats["perfil"],
                "nome": stats["nome"],
                "monstro": stats["monstro"],
                "ca": stats["ca"],
                "pv_maximo": stats["pv"],
                "pv_atuais": int(salvo["pv_atuais"]),
                "pv_temporarios": int(salvo["pv_temporarios"]),
                "alcance_maximo": stats["acao"]["alcance_pes"]["maximo"],
                "deslocamento_pes": stats["deslocamento_pes"],
            }
            for chave in ("desvantagem_proximo_ataque", "comando_pendente", "caido"):
                if chave in salvo.get("efeitos", {}):
                    inimigo[chave] = salvo["efeitos"][chave]
            encontro.inimigos[cid] = inimigo

        encontro.inimigos_derrotados = set(state["inimigos_derrotados"])
        combatentes = [
            Combatant(
                id=str(item["id"]),
                position=encontro.posicoes[str(item["id"])],
                initiative=int(item["iniciativa"]),
                is_player=bool(item["is_player"]),
            )
            for item in state["combatentes"]
        ]
        encontro.session = CombatSession(encontro.board, combatentes)
        sessao = state["sessao"]
        encontro.session._defeated = set(sessao["derrotados"])
        encontro.session.round_number = int(sessao["rodada"])
        encontro.session._turn_index = int(sessao["indice_turno"])
        encontro.session.status = EncounterStatus(sessao["status"])
        if not 0 <= encontro.session._turn_index < len(encontro.session.combatants):
            raise ValueError("índice de turno inválido no snapshot")
        return encontro

    # ------------------------------------------------------------------
    def _entrada_jogador(self) -> tuple[int, int]:
        entradas = self.mapa["entradas"]["jogador"]
        return entradas[0]["x"], entradas[0]["y"]

    def _proxima_semente(self) -> int:
        self._seed += 1
        return self._seed

    def _executar(self, fatos: dict[str, Any], personagens: list[dict[str, Any]]):
        return self.orquestrador.executar(
            Acao.de_ferramenta("resolver_regra", {"fatos": fatos}), personagens=personagens
        )

    def _rolar_iniciativas(self) -> list[tuple[str, int]]:
        ordem: list[tuple[str, int]] = []
        resultado = self._executar(
            {"type": "initiative", "character_id": self.ficha["id"], "seed": self._proxima_semente()}, [self.ficha]
        )
        ordem.append((self.ficha["id"], int(resultado.dados["total"])))
        for cid, inimigo in self.inimigos.items():
            resultado = self._executar(
                {"type": "initiative", "atacante_monstro": inimigo["monstro"], "seed": self._proxima_semente()}, []
            )
            ordem.append((cid, int(resultado.dados["total"])))
        self.log.append({"evento": "iniciativa", "ordem": ordem})
        return ordem

    # ------------------------------------------------------------------
    @property
    def turno_de(self) -> str | None:
        atual = self.session.current_combatant
        return atual.id if atual else None

    @property
    def status(self) -> EncounterStatus:
        return self.session.status

    def _ocupadas(self, excetuando: str | None = None) -> set[BoardPosition]:
        return {pos for cid, pos in self.posicoes.items() if cid != excetuando and cid not in self._derrotados()}

    def _derrotados(self) -> set[str]:
        derrotados = set(self.inimigos_derrotados)
        if self.ficha["pv_atuais"] <= 0:
            derrotados.add(self.ficha["id"])
        return derrotados

    def distancia_pes(self, a: str, b: str) -> int:
        return self.board.distance_feet(self.posicoes[a], self.posicoes[b])

    def alvos_ao_alcance(self, ator: str, alcance: int) -> list[str]:
        return [cid for cid in self._alvos_vivos(ator) if self.distancia_pes(ator, cid) <= alcance]

    def _alvos_vivos(self, ator: str) -> list[str]:
        if ator == self.ficha["id"]:
            return [cid for cid in self.inimigos if cid not in self.inimigos_derrotados]
        return [self.ficha["id"]] if self.ficha["pv_atuais"] > 0 else []

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Magias e truques
    # ------------------------------------------------------------------
    def magias_do_personagem(self) -> list[dict[str, Any]]:
        """Magias e truques da ficha, cada um com a razão de estar ou não disponível."""
        conjuracao = self.ficha.get("conjuracao") or {}
        espacos = (conjuracao.get("espacos_restantes") or {}).get("1", 0)
        itens = [self._item_magia(nome, 0, espacos) for nome in conjuracao.get("truques", [])]
        itens += [self._item_magia(nome, 1, espacos) for nome in conjuracao.get("magias_preparadas", [])]
        return itens

    def _item_magia(self, nome: str, circulo: int, espacos: int) -> dict[str, Any]:
        if nome not in EFEITOS_EM_COMBATE:
            motivo = MOTIVOS_SEM_EFEITO.get(nome, "sem efeito em combate")
            return {"nome": nome, "circulo": circulo, "disponivel": False, "motivo": motivo, "alvo": None}
        motivo = "sem espaço de 1º círculo" if circulo > 0 and espacos <= 0 else None
        return {
            "nome": nome,
            "circulo": circulo,
            "disponivel": motivo is None,
            "motivo": motivo,
            "alvo": ALVO_MAGIA[nome],
        }

    def alvos_magia(self) -> list[str]:
        """Inimigos vivos ao alcance de magia (18 m)."""
        return self.alvos_ao_alcance(self.ficha["id"], ALCANCE_MAGIA_PES)

    def conjurar(self, magia: str, alvo_id: str | None = None, comando: str | None = None) -> dict[str, Any]:
        """Conjura uma magia do personagem. Só as de efeito resolvido pelo motor são aceitas."""
        ator = self._exigir_turno_do_jogador()
        if self.acao_principal_usada:
            return {"status": "bloqueado", "motivo": "acao_principal_usada"}
        if magia not in EFEITOS_EM_COMBATE:
            motivo = MOTIVOS_SEM_EFEITO.get(magia, "magia_nao_disponivel_no_combate")
            return {"status": "bloqueado", "motivo": motivo}
        conjuracao_ficha = self.ficha.get("conjuracao") or {}
        escolhidas = list(conjuracao_ficha.get("truques", [])) + list(conjuracao_ficha.get("magias_preparadas", []))
        if magia not in escolhidas:
            return {"status": "bloqueado", "motivo": "magia_nao_escolhida_na_ficha"}
        if self.ficha["pv_atuais"] <= 0:
            return {"status": "bloqueado", "motivo": "personagem_inconsciente"}
        if ALVO_MAGIA[magia] == "si_mesmo":
            if alvo_id not in (None, ator):
                return {"status": "bloqueado", "motivo": "alvo_invalido_toque_em_si_mesmo"}
        else:
            if alvo_id not in self.inimigos or alvo_id in self.inimigos_derrotados:
                return {"status": "bloqueado", "motivo": "alvo_invalido"}
            if self.distancia_pes(ator, alvo_id) > ALCANCE_MAGIA_PES:
                return {"status": "bloqueado", "motivo": "alvo_fora_do_alcance"}
        if magia == "Comando" and comando not in COMANDOS:
            return {"status": "bloqueado", "motivo": "comando_invalido"}

        # CD antes de gastar espaço: sem CD o efeito não pode ser resolvido.
        cd = cd_de_magia(self.orquestrador.engine, self.ficha) if magia in SALVAGUARDA_EM_COMBATE else None
        if magia in SALVAGUARDA_EM_COMBATE and cd is None:
            return {"status": "bloqueado", "motivo": "cd_magia_ausente"}

        # 1) Conjuração: preparo, espaço e círculo são conferidos e o espaço é gasto no orquestrador.
        conjuracao = self._executar(
            {"type": "spell_cast", "magia": magia, "character_id": ator, "seed": self._proxima_semente()},
            [self.ficha],
        )
        if conjuracao.dados.get("resultado") != "conjurada":
            return {"status": "bloqueado", "motivo": conjuracao.motivo or conjuracao.dados.get("motivo")}
        self.acao_principal_usada = True

        # 2) Efeito, sempre pelo motor.
        if magia == "Curar Ferimentos":
            return self._curar(ator)
        if magia == "Zombaria Perversa":
            return self._zombaria_perversa(alvo_id, cd)
        return self._comando(alvo_id, comando, cd)

    def _curar(self, ator: str) -> dict[str, Any]:
        # 2d8 + modificador de Carisma (PHB 2024).
        modificador = int(self.ficha["modificadores"][ATRIBUTO_CONJURACAO])
        rolagem = self._executar(
            {
                "type": "damage",
                "damage_expression": f"2d8+{modificador}",
                "damage_type": "cura",
                "critical": False,
                "seed": self._proxima_semente(),
            },
            [self.ficha],
        ).dados["total"]
        estado = EstadoVital(
            pv_maximos=int(self.ficha["pv_maximo"]),
            pv_atuais=int(self.ficha["pv_atuais"]),
            pv_temporarios=int(self.ficha.get("pv_temporarios", 0)),
        )
        pv_antes = estado.pv_atuais
        self._executar({"type": "healing", "estado": estado, "amount": int(rolagem)}, [])
        self.ficha["pv_atuais"] = estado.pv_atuais
        curado = estado.pv_atuais - pv_antes
        self.log.append({"evento": "magia", "ator": ator, "magia": "Curar Ferimentos", "curado": curado})
        return {
            "status": "resolvido",
            "magia": "Curar Ferimentos",
            "rolagem": int(rolagem),
            "curado": curado,
            "pv_atuais": estado.pv_atuais,
            "espacos_restantes": self.ficha["conjuracao"]["espacos_restantes"],
        }

    def _salvaguarda_sabedoria(self, cid: str, cd: int) -> dict[str, Any]:
        """Salvaguarda de Sabedoria do inimigo, resolvida pelo motor com o bloco do bestiário."""
        bloco = consultar_monstro(self.inimigos[cid]["monstro"])
        registro = {
            "id": cid,
            "modificadores": dict(bloco["modificadores"]),
            "bonus_proficiencia": bloco["bonus_proficiencia"],
            "proficiencias_salvaguarda": list(bloco["salvaguardas"].keys()),
        }
        return self._executar(
            {
                "type": "saving_throw",
                "atributo": "sabedoria",
                "character_id": cid,
                "dc": cd,
                "seed": self._proxima_semente(),
            },
            [registro],
        ).dados

    def _zombaria_perversa(self, cid: str, cd: int) -> dict[str, Any]:
        salvaguarda = self._salvaguarda_sabedoria(cid, cd)
        if salvaguarda.get("result") != "failure":
            self.log.append(
                {"evento": "magia", "ator": self.ficha["id"], "magia": "Zombaria Perversa", "alvo": cid, "dano": 0}
            )
            return {
                "status": "resolvido",
                "magia": "Zombaria Perversa",
                "alvo": cid,
                "resultado": "resistiu",
                "dano": 0,
            }
        expressao = mecanica_de_magia("Zombaria Perversa", nivel_personagem=int(self.ficha["nivel"]))["dados_dano"]
        dano = self._executar(
            {
                "type": "damage",
                "damage_expression": expressao,
                "damage_type": "psychic",
                "critical": False,
                "seed": self._proxima_semente(),
            },
            [self.ficha],
        ).dados["total"]
        inimigo = self.inimigos[cid]
        estado = EstadoVital(
            pv_maximos=inimigo["pv_maximo"], pv_atuais=inimigo["pv_atuais"], pv_temporarios=inimigo["pv_temporarios"]
        )
        self._executar(
            {"type": "damage_application", "estado": estado, "damage": int(dano), "damage_type": "psychic"}, []
        )
        inimigo["pv_atuais"] = estado.pv_atuais
        inimigo["pv_temporarios"] = estado.pv_temporarios
        derrubado = estado.pv_atuais == 0
        if derrubado:
            self._marcar_derrotado(cid)
        # Desvantagem no próximo ataque do alvo, até o fim do próximo turno dele.
        inimigo["desvantagem_proximo_ataque"] = True
        self.log.append(
            {"evento": "magia", "ator": self.ficha["id"], "magia": "Zombaria Perversa", "alvo": cid, "dano": int(dano)}
        )
        return {
            "status": "resolvido",
            "magia": "Zombaria Perversa",
            "alvo": cid,
            "resultado": "falhou",
            "dano": int(dano),
            "alvo_pv": estado.pv_atuais,
            "derrubado": derrubado,
        }

    def _comando(self, cid: str, comando: str, cd: int) -> dict[str, Any]:
        salvaguarda = self._salvaguarda_sabedoria(cid, cd)
        if salvaguarda.get("result") != "failure":
            self.log.append({"evento": "magia", "ator": self.ficha["id"], "magia": "Comando", "alvo": cid})
            return {"status": "resolvido", "magia": "Comando", "alvo": cid, "resultado": "resistiu"}
        self.inimigos[cid]["comando_pendente"] = comando
        self.log.append(
            {"evento": "magia", "ator": self.ficha["id"], "magia": "Comando", "alvo": cid, "comando": comando}
        )
        return {"status": "resolvido", "magia": "Comando", "alvo": cid, "resultado": "falhou", "comando": comando}

    @property
    def movimento_restante_pes(self) -> int:
        return max(0, self.deslocamento_pes - self.movimento_usado_pes)

    def mover(self, destino: tuple[int, int]) -> dict[str, Any]:
        ator = self._exigir_turno_do_jogador()
        origem = self.posicoes[ator]
        alvo = BoardPosition(*destino)
        if self.movimento_restante_pes <= 0:
            return {"status": "bloqueado", "motivo": "deslocamento_esgotado"}
        alcancaveis = self.board.reachable_positions(
            origem, self.movimento_restante_pes, occupied=self._ocupadas(ator)
        )
        if alvo not in alcancaveis or alvo == origem:
            return {"status": "bloqueado", "motivo": "casa_fora_do_alcance_ou_ocupada"}
        custo = alcancaveis[alvo]
        self.posicoes[ator] = alvo
        self.movimento_usado_pes += custo
        self.log.append({"evento": "mover", "ator": ator, "para": destino, "custo_pes": custo})
        return {"status": "resolvido", "custo_pes": custo}

    def atacar_jogador(self, alvo_id: str) -> dict[str, Any]:
        ator = self._exigir_turno_do_jogador()
        if self.acao_principal_usada:
            return {"status": "bloqueado", "motivo": "acao_principal_usada"}
        if alvo_id not in self.inimigos or alvo_id in self.inimigos_derrotados:
            return {"status": "bloqueado", "motivo": "alvo_invalido"}
        alcance = 5  # Rapieira é corpo a corpo
        if self.distancia_pes(ator, alvo_id) > alcance:
            return {"status": "bloqueado", "motivo": "alvo_fora_do_alcance"}
        inimigo = self.inimigos[alvo_id]
        ataque = self._executar(
            {
                "type": "attack",
                "weapon": "Rapieira",
                "character_id": self.ficha["id"],
                "target_name": inimigo["monstro"],
                "seed": self._proxima_semente(),
            },
            [self.ficha],
        )
        resultado = ataque.dados.get("result")
        if resultado not in {"hit", "miss"}:
            return {"status": "bloqueado", "motivo": ataque.motivo or "ataque_nao_resolvido"}
        self.acao_principal_usada = True
        if resultado == "miss":
            self.log.append({"evento": "ataque_jogador", "alvo": alvo_id, "acertou": False})
            return {"status": "resolvido", "acertou": False}
        dados = ataque.dados
        expressao = f"{dados['weapon_damage']}+{dados['damage_modifier']}"
        dano = self._executar(
            {
                "type": "damage",
                "damage_expression": expressao,
                "damage_type": dados["damage_type"],
                "critical": bool(dados.get("critical")),
                "seed": self._proxima_semente(),
            },
            [self.ficha],
        ).dados["total"]
        estado = EstadoVital(
            pv_maximos=inimigo["pv_maximo"],
            pv_atuais=inimigo["pv_atuais"],
            pv_temporarios=inimigo["pv_temporarios"],
        )
        self._executar(
            {"type": "damage_application", "estado": estado, "damage": int(dano), "damage_type": dados["damage_type"]},
            [],
        )
        inimigo["pv_atuais"] = estado.pv_atuais
        inimigo["pv_temporarios"] = estado.pv_temporarios
        derrubado = estado.pv_atuais == 0
        if derrubado:
            self._marcar_derrotado(alvo_id)
        self.log.append(
            {
                "evento": "ataque_jogador",
                "alvo": alvo_id,
                "acertou": True,
                "dano": int(dano),
                "pv_alvo": estado.pv_atuais,
            }
        )
        return {"status": "resolvido", "acertou": True, "dano": int(dano), "derrubado": derrubado}

    def encerrar_turno(self) -> dict[str, Any]:
        """Encerra o turno do combatente atual; inimigos agem automaticamente."""
        ator = self.turno_de
        if ator is None:
            return {"status": "bloqueado", "motivo": "encontro_encerrado"}
        if ator != self.ficha["id"]:
            return self._turno_inimigo(ator)
        self.session.end_turn(ator)
        self.movimento_usado_pes = 0
        self.acao_principal_usada = False
        return {"status": "resolvido"}

    def _exigir_turno_do_jogador(self) -> str:
        if self.turno_de != self.ficha["id"]:
            raise ValueError("Não é o turno do personagem")
        return self.ficha["id"]

    def _marcar_derrotado(self, cid: str) -> None:
        if cid == self.ficha["id"]:
            self.session.mark_defeated(cid)
            return
        self.inimigos_derrotados.add(cid)
        self.session.mark_defeated(cid)

    def _turno_inimigo(self, cid: str) -> dict[str, Any]:
        """IA simples: ataca se estiver no alcance; senão, aproxima-se e tenta atacar.

        Comando pendente e condição Caído alteram o turno (ver ``COMANDOS``).
        """
        jogador = self.ficha["id"]
        if self.ficha["pv_atuais"] <= 0:
            return {"status": "bloqueado", "motivo": "jogador_derrotado"}
        inimigo = self.inimigos[cid]
        comando = inimigo.pop("comando_pendente", None)
        caido = inimigo.pop("caido", False)
        resultado: dict[str, Any] = {"status": "resolvido", "acao": "nenhuma"}
        passos = inimigo["deslocamento_pes"] // CASA_PES
        if caido:
            passos //= 2  # levantar-se gasta metade do deslocamento

        if comando in {"largar", "parar"}:
            resultado = {"status": "resolvido", "acao": f"comando_{comando}"}
        elif comando == "abaixar":
            inimigo["caido"] = True
            resultado = {"status": "resolvido", "acao": "comando_abaixar"}
        elif comando == "fugir":
            self._fugir(cid, passos)
            resultado = {"status": "resolvido", "acao": "comando_fugir"}
        else:
            if not self._pode_atacar(cid):
                # A casa do próprio alvo não bloqueia a rota: o caminho termina nela.
                ocupadas = self._ocupadas(cid) - {self.posicoes[jogador]}
                caminho = self.board.shortest_path(self.posicoes[cid], self.posicoes[jogador], occupied=ocupadas)
                if caminho:
                    for pos in caminho[1:-1][:passos]:
                        self.posicoes[cid] = pos
                        if self._pode_atacar(cid):
                            break
                self.log.append(
                    {"evento": "movimento_inimigo", "ator": cid, "para": (self.posicoes[cid].x, self.posicoes[cid].y)}
                )
                resultado = {"status": "resolvido", "acao": "moveu"}
            # Comando "aproximar" encerra o turno ao se mover: não ataca neste turno.
            if comando != "aproximar" and self._pode_atacar(cid) and self.ficha["pv_atuais"] > 0:
                resultado = self._atacar_com_inimigo(cid)
        if self.session.status is EncounterStatus.ACTIVE and self.turno_de == cid:
            self.session.end_turn(cid)
        # Desvantagem de Zombaria Perversa dura só até o fim deste turno.
        inimigo.pop("desvantagem_proximo_ataque", None)
        return resultado

    def _fugir(self, cid: str, passos: int) -> None:
        """Comando Fugir: move-se para a casa alcançável mais distante do personagem."""
        jogador = self.ficha["id"]
        origem = self.posicoes[cid]
        candidatos = self.board.reachable_positions(origem, passos * CASA_PES, occupied=self._ocupadas(cid))
        destino = max(
            candidatos,
            key=lambda p: (
                self.board.distance_feet(p, self.posicoes[jogador]),
                -abs(p.x - origem.x) - abs(p.y - origem.y),
            ),
            default=origem,
        )
        if self.board.distance_feet(destino, self.posicoes[jogador]) > self.board.distance_feet(
            origem, self.posicoes[jogador]
        ):
            self.posicoes[cid] = destino
        self.log.append(
            {"evento": "movimento_inimigo", "ator": cid, "para": (self.posicoes[cid].x, self.posicoes[cid].y)}
        )

    def _pode_atacar(self, cid: str) -> bool:
        """Alcance máximo da ação. Desvantagem por alcance longo ainda não é aplicada."""
        return self.distancia_pes(cid, self.ficha["id"]) <= self.inimigos[cid]["alcance_maximo"]

    def _atacar_com_inimigo(self, cid: str) -> dict[str, Any]:
        resultado = atacar_inimigo(
            self.orquestrador,
            self.inimigos[cid]["perfil"],
            self.ficha,
            seed=self._proxima_semente(),
            desvantagem=bool(self.inimigos[cid].get("desvantagem_proximo_ataque")),
        )
        if resultado.get("status") == "bloqueado":
            return {"status": "bloqueado", "motivo": resultado.get("motivo")}
        if resultado.get("acertou"):
            self.ficha["pv_atuais"] = resultado["pv_atuais"]
            self.ficha["pv_temporarios"] = resultado["pv_temporarios"]
        self.log.append(
            {
                "evento": "ataque_inimigo",
                "ator": cid,
                "acertou": resultado.get("acertou"),
                "dano": resultado.get("dano"),
            }
        )
        if self.ficha["pv_atuais"] <= 0:
            self._marcar_derrotado(self.ficha["id"])
        return {"status": "resolvido", "acao": "atacou", **resultado}
