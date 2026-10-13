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
from rule_engine.catalog import CATALOGO_ARMADURAS
from rule_engine.survival import EstadoVital

from .combat_board import BoardPosition, CombatBoard
from .combat_session import Combatant, CombatSession, EncounterStatus
from .combate_inimigo import atacar as atacar_inimigo
from .inimigos import carregar_inimigo
from .rule_adapter import DungeonRuleAdapter

MAPAS_DIR = Path(__file__).parent / "mapas"
SIMBOLOS_BLOQUEADOS = {"#", "+", "o"}
CASA_PES = 5


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
    # O criador grava o deslocamento em metros (9 m = 30 pés); o tabuleiro usa casas de 5 pés.
    ficha["deslocamento_pes"] = round(float(ficha["deslocamento"]) * 3.28084 / CASA_PES) * CASA_PES
    ficha["pv_atuais"] = ficha["pv_maximo"]
    ficha["pv_temporarios"] = 0
    return ficha


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
        self.mapa = carregar_mapa(mapa_id)
        self.board = tabuleiro_do_mapa(self.mapa)
        self.ficha = ficha
        self.deslocamento_pes = int(ficha.get("deslocamento_pes", 30))
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
    def mover(self, destino: tuple[int, int]) -> dict[str, Any]:
        ator = self._exigir_turno_do_jogador()
        origem = self.posicoes[ator]
        alvo = BoardPosition(*destino)
        alcancaveis = self.board.reachable_positions(origem, self.deslocamento_pes, occupied=self._ocupadas(ator))
        if alvo not in alcancaveis or alvo == origem:
            return {"status": "bloqueado", "motivo": "casa_fora_do_alcance_ou_ocupada"}
        self.posicoes[ator] = alvo
        self.log.append({"evento": "mover", "ator": ator, "para": destino, "custo_pes": alcancaveis[alvo]})
        return {"status": "resolvido", "custo_pes": alcancaveis[alvo]}

    def atacar_jogador(self, alvo_id: str) -> dict[str, Any]:
        ator = self._exigir_turno_do_jogador()
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
        if ataque.dados.get("result") != "hit":
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
        """IA simples: ataca se estiver no alcance; senão, aproxima-se e tenta atacar."""
        jogador = self.ficha["id"]
        if self.ficha["pv_atuais"] <= 0:
            return {"status": "bloqueado", "motivo": "jogador_derrotado"}
        resultado: dict[str, Any] = {"status": "resolvido", "acao": "nenhuma"}
        if not self._pode_atacar(cid):
            passos = self.inimigos[cid]["deslocamento_pes"] // CASA_PES
            caminho = self.board.shortest_path(self.posicoes[cid], self.posicoes[jogador], occupied=self._ocupadas(cid))
            if caminho:
                for pos in caminho[1:-1][:passos]:
                    self.posicoes[cid] = pos
                    if self._pode_atacar(cid):
                        break
            self.log.append(
                {"evento": "movimento_inimigo", "ator": cid, "para": (self.posicoes[cid].x, self.posicoes[cid].y)}
            )
            resultado = {"status": "resolvido", "acao": "moveu"}
        if self._pode_atacar(cid) and self.ficha["pv_atuais"] > 0:
            resultado = self._atacar_com_inimigo(cid)
        if self.session.status is EncounterStatus.ACTIVE and self.turno_de == cid:
            self.session.end_turn(cid)
        return resultado

    def _pode_atacar(self, cid: str) -> bool:
        """Alcance máximo da ação. Desvantagem por alcance longo ainda não é aplicada."""
        return self.distancia_pes(cid, self.ficha["id"]) <= self.inimigos[cid]["alcance_maximo"]

    def _atacar_com_inimigo(self, cid: str) -> dict[str, Any]:
        resultado = atacar_inimigo(
            self.orquestrador, self.inimigos[cid]["perfil"], self.ficha, seed=self._proxima_semente()
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
