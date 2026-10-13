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

from .inimigos import carregar_inimigo

ACERTOS = {"hit"}


def _executar(orquestrador: OrquestradorAcoes, fatos: Mapping[str, Any], personagens: list[dict[str, Any]]):
    return orquestrador.executar(Acao.de_ferramenta("resolver_regra", {"fatos": dict(fatos)}), personagens=personagens)


def atacar(
    orquestrador: OrquestradorAcoes,
    perfil_id: str,
    alvo: Mapping[str, Any],
    *,
    seed: int | None = None,
) -> dict[str, Any]:
    """Resolve um ataque do inimigo contra ``alvo`` (ficha com ``id``, ``ca``, ``pv_maximo``).

    ``alvo`` pode trazer ``pv_atuais`` e ``pv_temporarios``; se ausente, o PV
    atual é considerado igual ao máximo.
    """
    inimigo = carregar_inimigo(perfil_id)
    acao = inimigo["acao"]
    fatos: dict[str, Any] = {
        "type": "attack",
        "atacante_monstro": inimigo["monstro"],
        "acao_monstro": acao["nome"],
        "alvo_id": alvo.get("id"),
    }
    if seed is not None:
        fatos["seed"] = seed
    ataque = _executar(orquestrador, fatos, [dict(alvo)])
    if ataque.status == "bloqueado":
        return {"status": ataque.status, "motivo": ataque.motivo, "perfil": perfil_id}

    base = {"status": ataque.status, "perfil": perfil_id, "acao": acao["nome"], "ataque": dict(ataque.dados)}
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
    total = int(dano.dados["total"])

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
        "critico": critico,
        "pv_atuais": estado.pv_atuais,
        "pv_temporarios": estado.pv_temporarios,
        "derrubado": estado.pv_atuais == 0,
        "aplicacao": dict(aplicacao.dados),
    }
