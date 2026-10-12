"""Defesas de dano e normalização de tipos.

Transcrito do Livro do Jogador 2024 (Resistência, Vulnerabilidade e Imunidade)
e do SRD 5.2 para os blocos de monstro. O backend e o MJ compartilham esta
fonte única para que nenhum dos dois reimplemente a regra.
"""

from __future__ import annotations

import unicodedata
from typing import Iterable

# Tipos do catálogo PT-BR e do SRD mapeados para uma chave comparável.
ALIASES_TIPO_DANO = {
    "contundente": "bludgeoning",
    "bludgeoning": "bludgeoning",
    "perfurante": "piercing",
    "piercing": "piercing",
    "cortante": "slashing",
    "slashing": "slashing",
    "acido": "acid",
    "acid": "acid",
    "frio": "cold",
    "cold": "cold",
    "fogo": "fire",
    "fire": "fire",
    "igneo": "fire",
    "forca": "force",
    "force": "force",
    "eletrico": "lightning",
    "raio": "lightning",
    "lightning": "lightning",
    "necrotico": "necrotic",
    "necrotic": "necrotic",
    "veneno": "poison",
    "venenoso": "poison",
    "poison": "poison",
    "psiquico": "psychic",
    "psychic": "psychic",
    "radiante": "radiant",
    "radiant": "radiant",
    "trovejante": "thunder",
    "thunder": "thunder",
}

# Palavras que o catálogo em PT-BR e a Herança Dracônica usam para o mesmo tipo.
# Sem elas, o "ígneo" do Draconato não casaria com o "fire" do bloco do monstro.
ALIASES_TIPO_DANO.update({"gelido": "cold", "gélido": "cold"})


def normalizar_tipo_dano(tipo: str) -> str:
    """Mapeia tipos do catálogo PT-BR e do SRD em uma chave comparável."""
    texto = unicodedata.normalize("NFKD", str(tipo or "").casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c)).strip()
    return ALIASES_TIPO_DANO.get(texto, texto)


# Blocos oficiais podem declarar um efeito para "todos" os tipos de dano.
CURINGAS_TODOS_OS_TIPOS = frozenset({"todos", "todas", "all", "qualquer"})


def possui_defesa(tipos_declarados: Iterable[str], tipo_dano: str) -> bool:
    """Verifica se o tipo de dano cai em uma defesa declarada (com curinga "todos")."""
    normalizados = {normalizar_tipo_dano(x) for x in tipos_declarados}
    return normalizar_tipo_dano(tipo_dano) in normalizados or bool(normalizados & CURINGAS_TODOS_OS_TIPOS)


def aplicar_defesas_monstro(dano: int, tipo_dano: str, defesas: dict) -> dict:
    """Aplica imunidade, resistência e vulnerabilidade conforme o bloco oficial.

    Ordem de aplicação do Livro do Jogador 2024 (glossário "Resistência e
    Vulnerabilidade"): ajustes primeiro, depois Resistência (metade, para
    baixo) e, por último, Vulnerabilidade (dobro). Resistência e
    Vulnerabilidade ao mesmo tipo não se cancelam — as duas são aplicadas em
    sequência; situações do mesmo efeito não acumulam.

    Funciona tanto para blocos de monstro do bestiário quanto para fichas que
    declarem as mesmas chaves; o backend usa em ambos os casos.
    """
    tipo = normalizar_tipo_dano(tipo_dano)
    resistencias = defesas.get("resistencias_dano") or []
    imunidades = defesas.get("imunidades_dano") or []
    vulnerabilidades = defesas.get("vulnerabilidades_dano") or []
    bruto = max(0, int(dano))
    if possui_defesa(imunidades, tipo):
        return {"dano": 0, "dano_bruto": bruto, "tipo_dano": tipo, "aplicacao": "imunidade", "fator": 0}
    resistente = possui_defesa(resistencias, tipo)
    vulneravel = possui_defesa(vulnerabilidades, tipo)
    if not resistente and not vulneravel:
        return {"dano": bruto, "dano_bruto": bruto, "tipo_dano": tipo, "aplicacao": "normal", "fator": 1}
    dano_final = bruto
    if resistente:
        dano_final //= 2
    if vulneravel:
        dano_final *= 2
    if resistente and vulneravel:
        aplicacao = "resistencia_e_vulnerabilidade"
    elif resistente:
        aplicacao = "resistencia"
    else:
        aplicacao = "vulnerabilidade"
    return {
        "dano": dano_final,
        "dano_bruto": bruto,
        "tipo_dano": tipo,
        "aplicacao": aplicacao,
        "fator": dano_final / bruto if bruto else 1,
    }
