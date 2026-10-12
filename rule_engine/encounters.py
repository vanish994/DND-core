"""Construção e avaliação de encontros do Dungeon Master's Guide 2024.

Fonte: Dungeon Master's Guide 2024, capítulo 4 ("Creating Adventures"),
seção "Combat Encounters". A tabela *XP Budget per Character* é transcrita
literalmente: cada personagem contribui com um orçamento de XP por nível e
dificuldade desejada (Baixa, Moderada ou Alta), multiplicado pelo tamanho do
grupo. Os exemplos do livro usam exatamente essa conta (50 × 4 = 200 para
encontro Baixa com quatro personagens de nível 1, por exemplo).

As categorias de dificuldade oficiais são apenas três (Baixa, Moderada e
Alta). Um encontro acima do orçamento Alto não tem categoria própria no
livro; o resolvedor devolve ``acima_da_alta`` como rótulo derivado, com a
ressalva explícita no resultado.
"""

from __future__ import annotations

from typing import Any, Mapping

FONTE_ENCONTROS = "Dungeon Master's Guide 2024 — Combat Encounters"

# XP Budget per Character (DMG 2024): nível do grupo → (baixa, moderada, alta).
XP_BUDGET_POR_PERSONAGEM: dict[int, tuple[int, int, int]] = {
    1: (50, 75, 100),
    2: (100, 150, 200),
    3: (150, 225, 400),
    4: (250, 375, 500),
    5: (500, 750, 1100),
    6: (600, 1000, 1400),
    7: (750, 1300, 1700),
    8: (1000, 1700, 2100),
    9: (1300, 2000, 2600),
    10: (1600, 2300, 3100),
    11: (1900, 2900, 4100),
    12: (2200, 3700, 4700),
    13: (2600, 4200, 5400),
    14: (2900, 4900, 6200),
    15: (3300, 5400, 7800),
    16: (3800, 6100, 9800),
    17: (4500, 7200, 11700),
    18: (5000, 8700, 14200),
    19: (5500, 10700, 17200),
    20: (6400, 13200, 22000),
}

DIFICULDADES = ("baixa", "moderada", "alta")

_ALIASES_DIFICULDADE = {
    "baixa": "baixa",
    "baixo": "baixa",
    "low": "baixa",
    "leve": "baixa",
    "moderada": "moderada",
    "moderado": "moderada",
    "moderate": "moderada",
    "media": "moderada",
    "média": "moderada",
    "alta": "alta",
    "alto": "alta",
    "high": "alta",
}


def normalizar_dificuldade(valor: Any) -> str:
    chave = str(valor or "").strip().lower()
    if chave not in _ALIASES_DIFICULDADE:
        raise ValueError(f"Dificuldade de encontro inválida: {valor}")
    return _ALIASES_DIFICULDADE[chave]


def _validar_grupo(nivel: Any, personagens: Any) -> tuple[int, int]:
    nivel_int = int(nivel)
    personagens_int = int(personagens)
    if not 1 <= nivel_int <= 20:
        raise ValueError("O nível do grupo deve estar entre 1 e 20")
    if personagens_int < 1:
        raise ValueError("O grupo precisa de pelo menos um personagem")
    return nivel_int, personagens_int


def orcamento_xp(nivel: int, personagens: int, dificuldade: str) -> int:
    """Orçamento de XP do encontro: valor por personagem × tamanho do grupo."""
    nivel_int, personagens_int = _validar_grupo(nivel, personagens)
    dificuldade_normalizada = normalizar_dificuldade(dificuldade)
    indice = DIFICULDADES.index(dificuldade_normalizada)
    return XP_BUDGET_POR_PERSONAGEM[nivel_int][indice] * personagens_int


def budgets_do_grupo(nivel: int, personagens: int) -> dict[str, int]:
    """Os três orçamentos (Baixa, Moderada e Alta) do grupo informado."""
    nivel_int, personagens_int = _validar_grupo(nivel, personagens)
    baixa, moderada, alta = XP_BUDGET_POR_PERSONAGEM[nivel_int]
    return {
        "baixa": baixa * personagens_int,
        "moderada": moderada * personagens_int,
        "alta": alta * personagens_int,
    }


def avaliar_encontro(xp_total: int, nivel: int, personagens: int) -> dict[str, Any]:
    """Compara o XP total de um encontro com os orçamentos do grupo.

    As dificuldades oficiais do DMG 2024 são Baixa, Moderada e Alta.
    ``acima_da_alta`` é um rótulo derivado (não consta no livro) para encontros
    que superam o orçamento Alto; a ressalva acompanha o resultado.
    """
    xp = int(xp_total)
    if xp < 0:
        raise ValueError("O XP total não pode ser negativo")
    budgets = budgets_do_grupo(nivel, personagens)
    if xp <= budgets["baixa"]:
        dificuldade = "baixa"
    elif xp <= budgets["moderada"]:
        dificuldade = "moderada"
    elif xp <= budgets["alta"]:
        dificuldade = "alta"
    else:
        dificuldade = "acima_da_alta"
    resultado: dict[str, Any] = {
        "xp_total": xp,
        "nivel_grupo": int(nivel),
        "personagens": int(personagens),
        "budgets": budgets,
        "dificuldade": dificuldade,
        "fonte": FONTE_ENCONTROS,
    }
    if dificuldade == "acima_da_alta":
        resultado["nota"] = (
            "O DMG 2024 define apenas as dificuldades Baixa, Moderada e Alta; "
            "acima_da_alta é um rótulo derivado para encontros acima do orçamento Alto."
        )
    else:
        resultado["xp_restante_no_budget"] = budgets[dificuldade] - xp
    return resultado


def avaliar_encontro_de_monstros(nomes: list[str], nivel: int, personagens: int) -> dict[str, Any]:
    """Avalia um encontro a partir dos nomes de monstros do bestiário oficial.

    O XP é o somatório dos blocos do SRD 5.2.1 (uma entrada por criatura),
    sem multiplicadores — a mesma base do ``xp_encontro`` do bestiário.
    """
    from .bestiary import xp_encontro

    lista = list(nomes)
    if not lista:
        raise ValueError("Informe ao menos um monstro no encontro")
    return avaliar_encontro(xp_encontro(lista), nivel, personagens)


# Initial Attitude (DMG 2024): rolagem de d20 e a atitude inicial da criatura
# (4 ou menos Hostil; 5–8 Indiferente; 9 ou mais Amigável).


def atitude_inicial(rolagem: int) -> dict[str, Any]:
    """Atitude inicial de uma criatura pelo d20 (4 ou menos Hostil; 5–8 Indiferente; 9+ Amigável)."""
    d20 = int(rolagem)
    if not 1 <= d20 <= 20:
        raise ValueError("A rolagem de atitude inicial deve estar entre 1 e 20")
    if d20 <= 4:
        atitude = "hostil"
    elif d20 <= 8:
        atitude = "indiferente"
    else:
        atitude = "amigavel"
    return {
        "rolagem": d20,
        "atitude": atitude,
        "faixas": {"hostil": "4 ou menos", "indiferente": "5–8", "amigavel": "9 ou mais"},
        "fonte": FONTE_ENCONTROS,
    }


# Monster Personality (DMG 2024), tabela 1d8.
PERSONALIDADES_MONSTRO: dict[int, str] = {
    1: "covarde; rende-se facilmente",
    2: "ganancioso; quer tesouro",
    3: "presunçoso; exibe bravura mas foge do perigo",
    4: "desorganizado; mal treinado e facilmente abalado",
    5: "fanático; pronto para morrer lutando",
    6: "corajoso; mantém-se firme contra o perigo",
    7: "jovial; provoca os inimigos",
    8: "disciplinado; difícil de abalar",
}


def personalidade_monstro(rolagem: int) -> dict[str, Any]:
    """Sorteia a personalidade de um monstro pela tabela 1d8 do DMG 2024."""
    d8 = int(rolagem)
    if not 1 <= d8 <= 8:
        raise ValueError("A rolagem de personalidade deve estar entre 1 e 8")
    return {"rolagem": d8, "personalidade": PERSONALIDADES_MONSTRO[d8], "fonte": FONTE_ENCONTROS}


# Monster Relationships (DMG 2024), tabela 1d6.
RELACOES_MONSTROS: dict[int, str] = {
    1: "dois monstros têm uma rivalidade amarga; cada um quer ver o outro sofrer",
    2: "um monstro, atorregado pelos outros, fica atrás e foge na primeira oportunidade",
    3: "um monstro é reverenciado ou até adorado pelos outros, que morreriam por ele",
    4: "um monstro é admirado pelo grupo; seus aliados tentam impressioná-lo ou ajudá-lo",
    5: "um monstro só pensa em si mesmo e não no resto do grupo",
    6: "um monstro intimida os outros; os obriga a entrar em perigo, mas eles querem vê-lo derrotado",
}


def relacoes_monstros(rolagem: int) -> dict[str, Any]:
    """Sorteia a relação entre monstros de um grupo pela tabela 1d6 do DMG 2024."""
    d6 = int(rolagem)
    if not 1 <= d6 <= 6:
        raise ValueError("A rolagem de relação deve estar entre 1 e 6")
    return {"rolagem": d6, "relacao": RELACOES_MONSTROS[d6], "fonte": FONTE_ENCONTROS}


def resolver_encontro(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Resolvedor de encontros: orçamento, avaliação, atitude e tabelas do DMG."""
    operacao = str(fatos.get("operation", fatos.get("operacao", "budget"))).strip().lower()
    if operacao in {"budget", "orcamento"}:
        dificuldade = fatos.get("difficulty", fatos.get("dificuldade", "moderada"))
        return {
            "operacao": "budget",
            "dificuldade": normalizar_dificuldade(dificuldade),
            "budget": orcamento_xp(
                fatos["party_level"], fatos.get("party_size", fatos.get("personagens", 1)), dificuldade
            ),
            "budgets": budgets_do_grupo(fatos["party_level"], fatos.get("party_size", fatos.get("personagens", 1))),
            "fonte": FONTE_ENCONTROS,
        }
    if operacao in {"review", "avaliar", "avaliacao"}:
        nivel = fatos["party_level"]
        personagens = fatos.get("party_size", fatos.get("personagens", 1))
        if fatos.get("monsters", fatos.get("monstros")) is not None:
            return {
                "operacao": "review",
                **avaliar_encontro_de_monstros(list(fatos.get("monsters", fatos.get("monstros"))), nivel, personagens),
            }
        return {"operacao": "review", **avaliar_encontro(int(fatos["xp_total"]), nivel, personagens)}
    if operacao in {"attitude", "atitude"}:
        return {"operacao": "attitude", **atitude_inicial(fatos["roll"])}
    if operacao in {"personality", "personalidade"}:
        return {"operacao": "personality", **personalidade_monstro(fatos["roll"])}
    if operacao in {"relationships", "relacoes"}:
        return {"operacao": "relationships", **relacoes_monstros(fatos["roll"])}
    raise ValueError(f"Operação de encontro inválida: {operacao}")
