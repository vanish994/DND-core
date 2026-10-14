"""Turno de ataque de um inimigo do dungeon contra uma ficha.

Não resolve regra alguma: monta os fatos a partir do perfil do bestiário e
encaminha cada etapa ao Orquestrador (ataque, dano, aplicação ao PV). A CA e o
PV atual vêm da ficha/estado do jogador, nunca do pedido.

O PV novo é devolvido em ``pv_atuais``; quem grava esse valor é o jogo
(persistência ainda não existe, ver Etapa 5).
"""

from __future__ import annotations

from typing import Any, Mapping

from orchestrator import Acao, OrquestradorAcoes
from rule_engine.survival import EstadoVital

from .inimigos import PerfilInvalido, carregar_inimigo, escolher_acao_inimigo

ACERTOS = {"hit"}


def _executar(orquestrador: OrquestradorAcoes, fatos: Mapping[str, Any], personagens: list[dict[str, Any]]):
    return orquestrador.executar(Acao.de_ferramenta("resolver_regra", {"fatos": dict(fatos)}), personagens=personagens)


def validar_geometria_ataque(
    orquestrador: OrquestradorAcoes,
    acao: Mapping[str, Any],
    *,
    distancia_pes: int,
    linha_de_visao_bloqueada: bool = False,
    cobertura: str = "nenhuma",
) -> dict[str, Any]:
    """Valida distância, alcance normal/máximo, linha de visão e cobertura pelo motor."""
    alcance = acao["alcance_pes"]
    geometria = _executar(
        orquestrador,
        {
            "type": "attack_geometry",
            "distance": int(distancia_pes),
            "range": int(alcance["normal"]),
            "maximum_range": int(alcance["maximo"]),
            "ranged_attack": bool(acao.get("a_distancia", alcance["maximo"] > alcance["normal"])),
            "line_of_sight_blocked": bool(linha_de_visao_bloqueada),
            "cover": cobertura,
        },
        [],
    )
    return dict(geometria.dados)


def atacar(
    orquestrador: OrquestradorAcoes,
    perfil_id: str,
    alvo: Mapping[str, Any],
    *,
    seed: int | None = None,
    desvantagem: bool = False,
    acao_nome: str | None = None,
    distancia_pes: int | None = None,
    linha_de_visao_bloqueada: bool = False,
    cobertura: str = "nenhuma",
) -> dict[str, Any]:
    """Resolve um ataque do inimigo contra ``alvo`` (ficha com ``id``, ``ca``, ``pv_maximo``).

    ``alvo`` pode trazer ``pv_atuais`` e ``pv_temporarios``; se ausente, o PV
    atual é considerado igual ao máximo. Quando ``distancia_pes`` (ou restrições
    de visão/cobertura) é informada, a geometria do ataque é validada pelo motor
    antes de rolar o ataque.
    """
    inimigo = carregar_inimigo(perfil_id)
    if acao_nome is not None:
        acao = inimigo["acoes"].get(acao_nome)
        if acao is None:
            raise PerfilInvalido(f"ação {acao_nome!r} ausente no perfil {perfil_id}")
    elif distancia_pes is not None:
        acao = escolher_acao_inimigo(inimigo, distancia_pes)
    else:
        acao = inimigo["acao"]

    desvantagem_por_alcance = False
    bonus_ca_por_cobertura = 0
    if distancia_pes is not None or linha_de_visao_bloqueada or cobertura != "nenhuma":
        geometria = validar_geometria_ataque(
            orquestrador,
            acao,
            distancia_pes=distancia_pes if distancia_pes is not None else acao["alcance_pes"]["normal"],
            linha_de_visao_bloqueada=linha_de_visao_bloqueada,
            cobertura=cobertura,
        )
        if geometria.get("resultado") != "permitido":
            return {
                "status": "bloqueado",
                "motivo": geometria.get("motivo", "geometria_bloqueada"),
                "perfil": perfil_id,
                "acao": acao["nome"],
            }
        desvantagem_por_alcance = bool(geometria.get("desvantagem_por_alcance", False))
        bonus_ca_por_cobertura = int(geometria.get("bonus_ca_por_cobertura", 0))

    alvo_efetivo = dict(alvo)
    if (
        bonus_ca_por_cobertura
        and isinstance(alvo_efetivo.get("ca"), int)
        and not isinstance(alvo_efetivo.get("ca"), bool)
    ):
        alvo_efetivo["ca"] = int(alvo_efetivo["ca"]) + bonus_ca_por_cobertura

    fatos: dict[str, Any] = {
        "type": "attack",
        "atacante_monstro": inimigo["monstro"],
        "acao_monstro": acao["nome"],
        "alvo_id": alvo.get("id"),
    }
    if seed is not None:
        fatos["seed"] = seed
    if desvantagem or desvantagem_por_alcance:
        # O motor de ataque lê "disadvantage"; outras chaves são ignoradas.
        fatos["disadvantage"] = True
    ataque = _executar(orquestrador, fatos, [alvo_efetivo])
    if ataque.status == "bloqueado":
        return {"status": ataque.status, "motivo": ataque.motivo, "perfil": perfil_id}

    base = {
        "status": ataque.status,
        "perfil": perfil_id,
        "acao": acao["nome"],
        "a_distancia": bool(acao.get("a_distancia", False)),
        "desvantagem_por_alcance": desvantagem_por_alcance,
        "bonus_ca_por_cobertura": bonus_ca_por_cobertura,
        "ataque": dict(ataque.dados),
    }
    if ataque.dados.get("result") not in ACERTOS:
        return {**base, "acertou": False}

    critico = bool(ataque.dados.get("critical", False))
    dano_fatos: dict[str, Any] = {
        "type": "damage",
        "damage_expression": acao["dano_dados"],
        "damage_type": str(acao["tipo_dano"]).lower(),
        "critical": critico,
        "character_id": alvo.get("id"),
    }
    if seed is not None:
        dano_fatos["seed"] = seed
    dano = _executar(orquestrador, dano_fatos, [dict(alvo)])
    if dano.status == "bloqueado":
        return {**base, "acertou": True, "motivo_dano": dano.motivo}
    dano_bruto = int(dano.dados["total"])
    total = dano_bruto
    defesa_aplicada = "normal"
    if any(alvo.get(k) for k in ("resistencias_dano", "imunidades_dano", "vulnerabilidades_dano")):
        defesas = _executar(
            orquestrador,
            {
                "type": "damage_defenses",
                "damage": total,
                "damage_type": str(acao["tipo_dano"]).lower(),
                "defesas": dict(alvo),
            },
            [],
        ).dados
        total = int(defesas.get("dano", total))
        defesa_aplicada = str(defesas.get("aplicacao", "normal"))

    estado = EstadoVital(
        pv_maximos=int(alvo["pv_maximo"]),
        pv_atuais=int(alvo.get("pv_atuais", alvo["pv_maximo"])),
        pv_temporarios=int(alvo.get("pv_temporarios", 0)),
    )
    aplicacao = _executar(
        orquestrador,
        {
            "type": "damage_application",
            "estado": estado,
            "damage": total,
            "damage_type": str(acao["tipo_dano"]).lower(),
            "critical": critico,
        },
        [],
    )
    return {
        **base,
        "acertou": True,
        "dano": total,
        "dano_bruto": dano_bruto,
        "defesa_aplicada": defesa_aplicada,
        "critico": critico,
        "pv_atuais": estado.pv_atuais,
        "pv_temporarios": estado.pv_temporarios,
        "derrubado": estado.pv_atuais == 0,
        "aplicacao": dict(aplicacao.dados),
    }
