"""Perfis de inimigos do dungeon, lidos do bestiário oficial.

Nenhum valor de combate (CA, PV, atributos, bônus de ataque ou dano) é copiado
para cá: cada perfil aponta para uma entrada do bestiário e para uma das suas
ações. Um perfil só define *qual* ação o inimigo usa e a sua apresentação.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from rule_engine.bestiary import consultar_monstro


@dataclass(frozen=True, slots=True)
class PerfilInimigo:
    id: str
    nome_exibicao: str
    monstro: str  # nome canônico no bestiário
    acao: str  # nome da ação principal/corpo a corpo no bloco do bestiário
    acao_distancia: str | None = None  # nome da ação à distância no bloco do bestiário


PERFIS: dict[str, PerfilInimigo] = {
    "goblin": PerfilInimigo("goblin", "Goblin", "Goblin", "Scimitar"),
    "goblin_arqueiro": PerfilInimigo("goblin_arqueiro", "Goblin Arqueiro", "Goblin", "Shortbow"),
    "esqueleto": PerfilInimigo("esqueleto", "Esqueleto", "Skeleton", "Shortsword", acao_distancia="Shortbow"),
    "zumbi": PerfilInimigo("zumbi", "Zumbi", "Zombie", "Slam"),
    "cultista": PerfilInimigo("cultista", "Cultista", "Cultist", "Scimitar"),
    "bandido": PerfilInimigo("bandido", "Bandido", "Bandit", "Scimitar", acao_distancia="Light Crossbow"),
    "orc": PerfilInimigo("orc", "Orc", "Orc", "Greataxe", acao_distancia="Javelin"),
    "sombra": PerfilInimigo("sombra", "Sombra", "Shadow", "Strength Drain"),
    "carnical": PerfilInimigo("carnical", "Carniçal", "Ghoul", "Bite"),
    "armadura_animada": PerfilInimigo("armadura_animada", "Armadura Animada", "Animated Armor", "Slam"),
    "aparicao": PerfilInimigo("aparicao", "Aparição", "Wight", "Longsword", acao_distancia="Longbow"),
    "espectro": PerfilInimigo("espectro", "Espectro", "Specter", "Life Drain"),
    "esqueleto_minotauro": PerfilInimigo(
        "esqueleto_minotauro", "Esqueleto Minotauro", "Minotaur Skeleton", "Greataxe"
    ),
    "mumia": PerfilInimigo("mumia", "Múmia Ancestral", "Mummy", "Rotting Fist"),
}


class PerfilInvalido(ValueError):
    """Perfil aponta para monstro ou ação que o bestiário não tem."""


def _alcance_pes(descricao: str) -> dict[str, int]:
    """Extrai o alcance do texto oficial: 'reach 5 ft.' ou 'range 80/320 ft.'."""
    m = re.search(r"range (\d+)/(\d+) ft", descricao)
    if m:
        return {"normal": int(m.group(1)), "maximo": int(m.group(2))}
    m = re.search(r"reach (\d+) ft", descricao)
    if m:
        return {"normal": int(m.group(1)), "maximo": int(m.group(1))}
    raise PerfilInvalido(f"alcance não reconhecido em: {descricao!r}")


def _eh_ataque_a_distancia(descricao: str) -> bool:
    return bool(re.search(r"range \d+/\d+ ft", descricao))


def _montar_acao(bloco: Mapping[str, Any], nome_acao: str) -> dict[str, Any]:
    acao = next((a for a in bloco["acoes"] if a["nome"] == nome_acao), None)
    if acao is None:
        raise PerfilInvalido(f"ação {nome_acao!r} ausente em {bloco['nome']}")
    return {
        "nome": acao["nome"],
        "bonus_ataque": acao["bonus_ataque"],
        "dano_dados": acao["dano_dados"],
        "tipo_dano": acao["tipo_dano"],
        "alcance_pes": _alcance_pes(acao["desc"]),
        "a_distancia": _eh_ataque_a_distancia(acao["desc"]),
    }


def carregar_inimigo(perfil_id: str) -> dict[str, Any]:
    """Monta o inimigo a partir do bestiário; falha se a referência não existir."""
    perfil = PERFIS.get(perfil_id)
    if perfil is None:
        raise PerfilInvalido(f"perfil desconhecido: {perfil_id}")
    bloco = consultar_monstro(perfil.monstro)
    if bloco is None:
        raise PerfilInvalido(f"monstro ausente do bestiário: {perfil.monstro}")
    acao_principal = _montar_acao(bloco, perfil.acao)
    acao_distancia = (
        _montar_acao(bloco, perfil.acao_distancia)
        if perfil.acao_distancia
        else (acao_principal if acao_principal["a_distancia"] else None)
    )
    acoes = {acao_principal["nome"]: acao_principal}
    if acao_distancia is not None:
        acoes[acao_distancia["nome"]] = acao_distancia
    return {
        "perfil": perfil.id,
        "nome": perfil.nome_exibicao,
        "monstro": bloco["nome"],
        "ca": bloco["ca"],
        "pv": bloco["pv"],
        "nd": bloco["nd"],
        "xp": bloco["xp"],
        "deslocamento_pes": bloco["deslocamento_pes"],
        "atributos": dict(bloco["atributos"]),
        "acao": acao_principal,
        "acao_distancia": acao_distancia,
        "acoes": acoes,
        "vulnerabilidades_dano": list(bloco.get("vulnerabilidades_dano") or ()),
        "resistencias_dano": list(bloco.get("resistencias_dano") or ()),
        "imunidades_dano": list(bloco.get("imunidades_dano") or ()),
        "imunidades_condicao": list(bloco.get("imunidades_condicao") or ()),
    }


def escolher_acao_inimigo(inimigo: Mapping[str, Any], distancia_pes: int) -> dict[str, Any]:
    """Escolhe deterministicamente entre ataque corpo a corpo e à distância conforme a distância."""
    acao_principal = dict(inimigo["acao"])
    acao_distancia = inimigo.get("acao_distancia")
    if not acao_principal.get("a_distancia") and distancia_pes <= acao_principal["alcance_pes"]["maximo"]:
        return acao_principal
    if acao_distancia is not None:
        return dict(acao_distancia)
    return acao_principal


def listar_perfis() -> list[str]:
    return sorted(PERFIS)
