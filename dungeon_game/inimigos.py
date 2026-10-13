"""Perfis de inimigos do dungeon, lidos do bestiário oficial.

Nenhum valor de combate (CA, PV, atributos, bônus de ataque ou dano) é copiado
para cá: cada perfil aponta para uma entrada do bestiário e para uma das suas
ações. Um perfil só define *qual* ação o inimigo usa e a sua apresentação.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from rule_engine.bestiary import consultar_monstro


@dataclass(frozen=True, slots=True)
class PerfilInimigo:
    id: str
    nome_exibicao: str
    monstro: str  # nome canônico no bestiário
    acao: str  # nome da ação no bloco do bestiário


PERFIS: dict[str, PerfilInimigo] = {
    "goblin": PerfilInimigo("goblin", "Goblin", "Goblin", "Scimitar"),
    "goblin_arqueiro": PerfilInimigo("goblin_arqueiro", "Goblin Arqueiro", "Goblin", "Shortbow"),
    "esqueleto": PerfilInimigo("esqueleto", "Esqueleto", "Skeleton", "Shortsword"),
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


def carregar_inimigo(perfil_id: str) -> dict[str, Any]:
    """Monta o inimigo a partir do bestiário; falha se a referência não existir."""
    perfil = PERFIS.get(perfil_id)
    if perfil is None:
        raise PerfilInvalido(f"perfil desconhecido: {perfil_id}")
    bloco = consultar_monstro(perfil.monstro)
    if bloco is None:
        raise PerfilInvalido(f"monstro ausente do bestiário: {perfil.monstro}")
    acao = next((a for a in bloco["acoes"] if a["nome"] == perfil.acao), None)
    if acao is None:
        raise PerfilInvalido(f"ação {perfil.acao!r} ausente em {perfil.monstro}")
    return {
        "perfil": perfil.id,
        "nome": perfil.nome_exibicao,
        "monstro": bloco["nome"],
        "ca": bloco["ca"],
        "pv": bloco["pv"],
        "nd": bloco["nd"],
        "deslocamento_pes": bloco["deslocamento_pes"],
        "atributos": dict(bloco["atributos"]),
        "acao": {
            "nome": acao["nome"],
            "bonus_ataque": acao["bonus_ataque"],
            "dano_dados": acao["dano_dados"],
            "tipo_dano": acao["tipo_dano"],
            "alcance_pes": _alcance_pes(acao["desc"]),
        },
    }


def listar_perfis() -> list[str]:
    return sorted(PERFIS)
