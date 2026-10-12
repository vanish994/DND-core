"""Escolhas de espécie do Livro do Jogador 2024.

Fonte: Livro do Jogador 2024 (edição brasileira), capítulo 4 — traços de
Draconato (p. 188-194). Nenhuma linhagem, tipo de dano ou forma de sopro é
inventada aqui: os valores abaixo são transcritos da tabela do livro.
"""

from __future__ import annotations

from typing import Any, Mapping

# Herança Dracônica — tabela do traço "Herança Dracônica" do Draconato.
# A escolha define o tipo de dano do Ataque de Sopro e da Resistência a Dano.
HERANCA_DRACONICA: dict[str, dict[str, str]] = {
    "azul": {"nome": "Azul", "dano": "elétrico"},
    "branco": {"nome": "Branco", "dano": "gélido"},
    "bronze": {"nome": "Bronze", "dano": "elétrico"},
    "cobre": {"nome": "Cobre", "dano": "ácido"},
    "latao": {"nome": "Latão", "dano": "ígneo"},
    "negro": {"nome": "Negro", "dano": "ácido"},
    "ouro": {"nome": "Ouro", "dano": "ígneo"},
    "prata": {"nome": "Prata", "dano": "gélido"},
    "verde": {"nome": "Verde", "dano": "venenoso"},
    "vermelho": {"nome": "Vermelho", "dano": "ígneo"},
}

# Dano do Ataque de Sopro por nível de personagem (1d10, 2d10, 3d10 e 4d10).
DADO_SOPRO_POR_NIVEL = ((5, "2d10"), (11, "3d10"), (17, "4d10"))
DADO_SOPRO_BASE = "1d10"

# Formas do sopro e salvaguarda, conforme o texto do traço.
FORMAS_SOPRO = ("Cone de 4,5 metros", "Linha de 9 metros por 1,5 metro")

ESCOLHAS_ESPECIE: dict[str, dict[str, Any]] = {
    "draconato": {
        "campo": "heranca_draconica",
        "rotulo": "Herança Dracônica",
        "nota": "Define o tipo de dano do Ataque de Sopro e da Resistência a Dano.",
        "opcoes": HERANCA_DRACONICA,
    },
}


def escolha_de_especie(especie: Any) -> dict[str, Any] | None:
    """Devolve a escolha obrigatória da espécie, quando ela existe."""
    return ESCOLHAS_ESPECIE.get(str(especie or "").strip().lower())


def normalizar_escolha(especie: Any, valor: Any) -> str:
    """Valida a escolha de espécie e devolve a chave normalizada."""
    escolha = escolha_de_especie(especie)
    chave = str(valor or "").strip().lower().replace("-", "_")
    if escolha is None:
        raise ValueError(f"A espécie {especie} não exige escolha adicional")
    if chave not in escolha["opcoes"]:
        raise ValueError(f"{escolha['rotulo']} inválida: {valor}")
    return chave


def dado_sopro(nivel: int) -> str:
    """Dano do Ataque de Sopro por nível, conforme a progressão do traço."""
    dado = DADO_SOPRO_BASE
    for marca, valor in DADO_SOPRO_POR_NIVEL:
        if int(nivel) >= marca:
            dado = valor
    return dado


def bloco_heranca_draconica(
    chave: str,
    nivel: int,
    modificador_constituicao: int,
    bonus_proficiencia: int,
) -> dict[str, Any]:
    """Bloco derivado do Draconato para exibição e para o contexto do MJ."""
    heranca = HERANCA_DRACONICA[chave]
    return {
        "fonte": "Livro do Jogador 2024 — Herança Dracônica",
        "chave": chave,
        "nome": heranca["nome"],
        "linhagem": f"Dragão {heranca['nome']}",
        "tipo_dano": heranca["dano"],
        "resistencia": f"dano {heranca['dano']}",
        "sopro": {
            "dado": dado_sopro(nivel),
            "tipo_dano": heranca["dano"],
            "formas": list(FORMAS_SOPRO),
            "salvaguarda": "Destreza",
            "cd": 8 + int(modificador_constituicao) + int(bonus_proficiencia),
            "usos": int(bonus_proficiencia),
            "recarga": "descanso longo",
        },
    }


def resumo_escolha(especie: Any, valor: Any) -> str:
    """Texto curto da escolha para o contexto do MJ."""
    escolha = escolha_de_especie(especie)
    if escolha is None or not valor:
        return "nenhuma"
    opcao = escolha["opcoes"].get(str(valor))
    return opcao["nome"] if opcao else str(valor)


# ---------------------------------------------------------------------------
# Traços completos das dez espécies do Livro do Jogador 2024 (capítulo 4,
# "Descrições das Espécies"). Cada entrada espelha o bloco "Traços de <Espécie>"
# do livro; valores derivados (dados por nível, CD, usos) são calculados pelo
# resolvedor, nunca inventados aqui.
# ---------------------------------------------------------------------------

_ALIASES_ESPECIE = {
    "aasimar": "aasimar",
    "anao": "anao",
    "dwarf": "anao",
    "draconato": "draconato",
    "dragonborn": "draconato",
    "elfo": "elfo",
    "elf": "elfo",
    "gnomo": "gnomo",
    "gnome": "gnomo",
    "golias": "golias",
    "goliath": "golias",
    "humano": "humano",
    "human": "humano",
    "orc": "orc",
    "halfling": "halfling",
    "pequenino": "halfling",
    "tiefling": "tiefling",
    "tiferino": "tiefling",
}


def normalizar_especie(especie: Any) -> str:
    chave = str(especie or "").strip().lower().replace("-", "_").replace(" ", "_")
    if chave not in _ALIASES_ESPECIE:
        raise ValueError(f"Espécie desconhecida: {especie}")
    return _ALIASES_ESPECIE[chave]


# Linhagem Élfica (PHB 2024 — Traços de Elfo).
LINHAGENS_ELFICAS: dict[str, dict[str, Any]] = {
    "alto_elfo": {
        "nome": "Alto Elfo",
        "nivel_1": {
            "truques": ["Prestidigitação Arcana"],
            "nota": "este truque pode ser trocado por um truque da lista de Mago ao completar um Descanso Longo",
        },
        "nivel_3": {"magias": ["Detectar Magia"]},
        "nivel_5": {"magias": ["Passo Nebuloso"]},
    },
    "drow": {
        "nome": "Drow",
        "visao_no_escuro_m": 36,
        "nivel_1": {"truques": ["Luzes Dançantes"]},
        "nivel_3": {"magias": ["Fogo das Fadas"]},
        "nivel_5": {"magias": ["Escuridão"]},
    },
    "silvestre": {
        "nome": "Elfo Silvestre",
        "deslocamento_m": 10.5,
        "nivel_1": {"truques": ["Arte Druídica"]},
        "nivel_3": {"magias": ["Passos Largos"]},
        "nivel_5": {"magias": ["Passos Sem Rastro"]},
    },
}

# Linhagem Gnômica (PHB 2024 — Traços de Gnomo).
LINHAGENS_GNOMICAS: dict[str, dict[str, Any]] = {
    "rochas": {
        "nome": "Gnomo das Rochas",
        "nivel_1": {
            "truques": ["Prestidigitação Arcana", "Reparar"],
            "nota": "pode fabricar um dispositivo mecânico minúsculo (CA 5, 1 PV) com 10 minutos de Prestidigitação Arcana; até 3 dispositivos, durando 8 horas cada",
        },
    },
    "bosque": {
        "nome": "Gnomo do Bosque",
        "nivel_1": {
            "truques": ["Ilusão Menor"],
            "magias_preparadas": ["Falar com Animais"],
            "usos_sem_espaco_igual_bonus_proficiencia": True,
            "nota": "Falar com Animais pode ser conjurada sem espaço de magia um número de vezes igual ao Bônus de Proficiência, restauradas em Descanso Longo",
        },
    },
}

# Ancestralidade Gigante (PHB 2024 — Traços de Golias). Escolha de nível 1.
ANCESTRALIDADES_GIGANTES: dict[str, dict[str, Any]] = {
    "arrepio_do_gelo": {
        "nome": "Arrepio do Gelo (Gigante do Gelo)",
        "efeito": "ao atingir um alvo e causar dano, inflige também 1d6 de dano Gélido e reduz o Deslocamento do alvo em 3 metros até o início do seu próximo turno",
    },
    "queimadura_de_fogo": {
        "nome": "Queimadura de Fogo (Gigante de Fogo)",
        "efeito": "ao atingir um alvo e causar dano, inflige também 1d10 de dano Ígneo",
    },
    "resistencia_da_pedra": {
        "nome": "Resistência da Pedra (Gigante da Pedra)",
        "efeito": "Reação ao sofrer dano: joga 1d12, soma o modificador de Constituição e reduz o dano desse total",
    },
    "salto_da_nuvem": {
        "nome": "Salto da Nuvem (Gigante das Nuvens)",
        "efeito": "Ação Bônus: teleporte mágico de até 9 metros para um espaço desocupado à vista",
    },
    "tombo_da_colina": {
        "nome": "Tombo da Colina (Gigante da Colina)",
        "efeito": "ao atingir uma criatura Grande ou menor e causar dano, impõe a condição Caído",
    },
    "trovao_da_tempestade": {
        "nome": "Trovão da Tempestade (Gigante da Tempestade)",
        "efeito": "Reação ao sofrer dano de uma criatura a até 18 metros: causa 1d8 de dano Trovejante a ela",
    },
}

# Legados Ínferos (PHB 2024 — Traços de Tiferino).
LEGADOS_INFEROS: dict[str, dict[str, Any]] = {
    "abissal": {
        "nome": "Abissal",
        "resistencias_dano": ["venenoso"],
        "nivel_1": {"truques": ["Rajada de Veneno"]},
        "nivel_3": {"magias": ["Raio Nauseante"]},
        "nivel_5": {"magias": ["Paralisar Pessoa"]},
    },
    "ctonico": {
        "nome": "Ctônico",
        "resistencias_dano": ["necrótico"],
        "nivel_1": {"truques": ["Toque Necrótico"]},
        "nivel_3": {"magias": ["Vitalidade Vazia"]},
        "nivel_5": {"magias": ["Raio do Enfraquecimento"]},
    },
    "infernal": {
        "nome": "Infernal",
        "resistencias_dano": ["ígneo"],
        "nivel_1": {"truques": ["Raio de Fogo"]},
        "nivel_3": {"magias": ["Repreensão Diabólica"]},
        "nivel_5": {"magias": ["Escuridão"]},
    },
}


def _traco(nome: str, efeito: str, **extras: Any) -> dict[str, Any]:
    return {"nome": nome, "efeito": efeito, **extras}


TRACOS_ESPECIE: dict[str, dict[str, Any]] = {
    "aasimar": {
        "nome": "Aasimar",
        "tipo_criatura": "humanoide",
        "tamanhos": ["medio", "pequeno"],
        "deslocamento_m": 9,
        "escolhas": {"revelacao_celestial": ("Asas Celestiais", "Manto Necrótico", "Transfiguração Radiante")},
        "resistencias_dano": ["necrótico", "radiante"],
        "tracos": [
            _traco("Resistência Celestial", "Resistência a dano Necrótico e Radiante."),
            _traco("Visão no Escuro", "Visão no Escuro com alcance de 18 metros.", visao_no_escuro_m=18),
            _traco(
                "Mãos Curativas",
                "Ação Usar Magia: toca uma criatura e joga um número de d4s igual ao Bônus de Proficiência, "
                "restaurando PV igual ao total. 1 vez por Descanso Longo.",
                recurso={"usos": "bonus_proficiencia", "recarga": "descanso_longo"},
            ),
            _traco("Portador da Luz", "Conhece o truque Luz. Carisma é o atributo de conjuração.", truques=["Luz"]),
            _traco(
                "Revelação Celestial",
                "No nível 3, Ação Bônus de transformação por 1 minuto (Asas Celestiais, Manto Necrótico ou "
                "Transfiguração Radiante). Enquanto dura, inflige dano adicional igual ao Bônus de Proficiência "
                "uma vez por turno (Necrótico no Manto; Radiante nas Asas e na Transfiguração). "
                "1 vez por Descanso Longo.",
                nivel_minimo=3,
                recurso={"usos": 1, "recarga": "descanso_longo"},
            ),
        ],
    },
    "anao": {
        "nome": "Anão",
        "tipo_criatura": "humanoide",
        "tamanhos": ["medio"],
        "deslocamento_m": 9,
        "resistencias_dano": ["venenoso"],
        "tracos": [
            _traco("Visão no Escuro", "Visão no Escuro com alcance de 36 metros.", visao_no_escuro_m=36),
            _traco(
                "Resistência a Toxinas",
                "Resistência a dano Venenoso e Vantagem em salvaguardas para evitar ou encerrar Envenenado.",
                vantagens_salvaguarda=["envenenado"],
            ),
            _traco(
                "Tenacidade Anã",
                "PV máximos aumentam em 1, e novamente em 1 em cada nível de personagem.",
                pv_bonus_por_nivel=1,
            ),
            _traco(
                "Conhecimento de Pedras",
                "Ação Bônus: adquire Sismiconsciência com alcance de 18 metros por 10 minutos, estando em ou "
                "tocando pedra. Usos iguais ao Bônus de Proficiência, restaurados em Descanso Longo.",
                recurso={"usos": "bonus_proficiencia", "recarga": "descanso_longo"},
            ),
        ],
    },
    "draconato": {
        "nome": "Draconato",
        "tipo_criatura": "humanoide",
        "tamanhos": ["medio"],
        "deslocamento_m": 9,
        "escolhas": {"heranca_draconica": tuple(HERANCA_DRACONICA)},
        "tracos": [
            _traco("Herança Dracônica", "A linhagem define o tipo de dano do Ataque de Sopro e da Resistência a Dano."),
            _traco(
                "Ataque de Sopro",
                "Na ação Atacar, substitui um ataque por uma emissão em Cone de 4,5 metros ou Linha de 9 por "
                "1,5 metros. Salvaguarda de Destreza (CD 8 + Constituição + Bônus de Proficiência); falha sofre "
                "1d10 do tipo da herança, sucesso metade. Dano aumenta para 2d10/3d10/4d10 nos níveis 5/11/17. "
                "Usos iguais ao Bônus de Proficiência, restaurados em Descanso Longo.",
                recurso={"usos": "bonus_proficiencia", "recarga": "descanso_longo"},
            ),
            _traco("Resistência a Dano", "Resistência ao tipo de dano da Herança Dracônica."),
            _traco("Visão no Escuro", "Visão no Escuro com alcance de 18 metros.", visao_no_escuro_m=18),
            _traco(
                "Voo Dracônico",
                "No nível 5, Ação Bônus cria asas espectrais por 10 minutos: Deslocamento de Voo igual ao "
                "Deslocamento. 1 vez por Descanso Longo.",
                nivel_minimo=5,
                recurso={"usos": 1, "recarga": "descanso_longo"},
            ),
        ],
    },
    "elfo": {
        "nome": "Elfo",
        "tipo_criatura": "humanoide",
        "tamanhos": ["medio"],
        "deslocamento_m": 9,
        "escolhas": {"linhagem_elfica": tuple(LINHAGENS_ELFICAS)},
        "tracos": [
            _traco("Visão no Escuro", "Visão no Escuro com alcance de 18 metros.", visao_no_escuro_m=18),
            _traco(
                "Linhagem Élfica",
                "Linhagem concede truques no nível 1 e magias nos níveis 3 e 5 (sempre preparadas; 1 conjuração "
                "sem espaço por Descanso Longo). Inteligência, Sabedoria ou Carisma é o atributo de conjuração.",
            ),
            _traco(
                "Ancestralidade Feérica",
                "Vantagem em salvaguardas para evitar ou encerrar Enfeitiçado.",
                vantagens_salvaguarda=["enfeiticado"],
            ),
            _traco("Sentidos Aguçados", "Proficiência em Intuição, Percepção ou Sobrevivência.", pericias_escolha=3),
            _traco(
                "Transe",
                "Completa um Descanso Longo em 4 horas meditando; magia não pode forçá-lo a dormir.",
            ),
        ],
    },
    "gnomo": {
        "nome": "Gnomo",
        "tipo_criatura": "humanoide",
        "tamanhos": ["pequeno"],
        "deslocamento_m": 9,
        "escolhas": {"linhagem_gnomica": tuple(LINHAGENS_GNOMICAS)},
        "tracos": [
            _traco("Visão no Escuro", "Visão no Escuro com alcance de 18 metros.", visao_no_escuro_m=18),
            _traco(
                "Astúcia de Gnomo",
                "Vantagem em salvaguardas de Inteligência, Sabedoria e Carisma.",
                vantagens_salvaguarda=["inteligencia", "sabedoria", "carisma"],
            ),
            _traco(
                "Linhagem Gnômica",
                "Gnomo das Rochas (truques Prestidigitação Arcana e Reparar, dispositivo mecânico) ou "
                "Gnomo do Bosque (Ilusão Menor e Falar com Animais preparada).",
            ),
        ],
    },
    "golias": {
        "nome": "Golias",
        "tipo_criatura": "humanoide",
        "tamanhos": ["medio"],
        "deslocamento_m": 10.5,
        "escolhas": {"ancestralidade_gigante": tuple(ANCESTRALIDADES_GIGANTES)},
        "tracos": [
            _traco(
                "Ancestralidade Gigante",
                "Um benefício sobrenatural da ancestralidade gigante; usos iguais ao Bônus de Proficiência, "
                "restaurados em Descanso Longo.",
                recurso={"usos": "bonus_proficiencia", "recarga": "descanso_longo"},
            ),
            _traco(
                "Forma Grande",
                "No nível 5, Ação Bônus para tornar-se Grande por 10 minutos: Vantagem em testes de Força e "
                "Deslocamento +3 metros. 1 vez por Descanso Longo.",
                nivel_minimo=5,
                recurso={"usos": 1, "recarga": "descanso_longo"},
            ),
            _traco(
                "Porte Poderoso",
                "Vantagem em testes de atributo para encerrar Imobilizado; conta como um tamanho maior para "
                "capacidade de carga.",
            ),
        ],
    },
    "humano": {
        "nome": "Humano",
        "tipo_criatura": "humanoide",
        "tamanhos": ["medio", "pequeno"],
        "deslocamento_m": 9,
        "tracos": [
            _traco("Eficiente", "Adquire Inspiração Heroica ao completar um Descanso Longo."),
            _traco("Hábil", "Proficiência em uma perícia à escolha.", pericias_escolha=1),
            _traco("Versátil", "Adquire um talento de Origem à escolha (Habilidoso é recomendado)."),
        ],
    },
    "orc": {
        "nome": "Orc",
        "tipo_criatura": "humanoide",
        "tamanhos": ["medio"],
        "deslocamento_m": 9,
        "tracos": [
            _traco(
                "Pico de Adrenalina",
                "Ação Bônus para executar Correr e ganhar PV Temporários iguais ao Bônus de Proficiência. "
                "Usos iguais ao Bônus de Proficiência, restaurados em Descanso Curto ou Longo.",
                recurso={"usos": "bonus_proficiencia", "recarga": "descanso_curto_ou_longo"},
            ),
            _traco("Visão no Escuro", "Visão no Escuro com alcance de 36 metros.", visao_no_escuro_m=36),
            _traco(
                "Vigor Implacável",
                "Ao ser reduzido a 0 PV sem morte instantânea, fica com 1 PV. 1 vez por Descanso Longo.",
                recurso={"usos": 1, "recarga": "descanso_longo"},
            ),
        ],
    },
    "halfling": {
        "nome": "Pequenino",
        "tipo_criatura": "humanoide",
        "tamanhos": ["pequeno"],
        "deslocamento_m": 9,
        "tracos": [
            _traco(
                "Corajoso",
                "Vantagem em salvaguardas para evitar ou encerrar Amedrontado.",
                vantagens_salvaguarda=["amedrontado"],
            ),
            _traco(
                "Agilidade Pequenina",
                "Move-se pelo espaço de criaturas maiores, sem parar nele.",
            ),
            _traco("Sorte", "Ao tirar 1 no d20 de um Teste de D20, pode jogar novamente e deve usar o novo resultado."),
            _traco(
                "Furtividade Natural",
                "Pode executar Esconder mesmo encoberto apenas por uma criatura ao menos um tamanho maior.",
            ),
        ],
    },
    "tiefling": {
        "nome": "Tiferino",
        "tipo_criatura": "humanoide",
        "tamanhos": ["medio", "pequeno"],
        "deslocamento_m": 9,
        "escolhas": {"legado_infero": tuple(LEGADOS_INFEROS)},
        "tracos": [
            _traco("Visão no Escuro", "Visão no Escuro com alcance de 18 metros.", visao_no_escuro_m=18),
            _traco(
                "Legado Ínfero",
                "Legado (Abissal, Ctônico ou Infernal) confere resistência, um truque no nível 1 e magias nos "
                "níveis 3 e 5 (sempre preparadas; 1 conjuração sem espaço por Descanso Longo). Inteligência, "
                "Sabedoria ou Carisma é o atributo de conjuração.",
            ),
            _traco("Presença Sobrenatural", "Conhece o truque Taumaturgia.", truques=["Taumaturgia"]),
        ],
    },
}

FONTE_ESPECIES = "Livro do Jogador 2024 — Origens dos Personagens: Descrições das Espécies"


def listar_especies() -> list[str]:
    """Nomes internos das espécies do catálogo, em ordem estável."""
    return sorted(TRACOS_ESPECIE)


def tracos_de_especie(especie: Any) -> dict[str, Any]:
    """Bloco completo de traços da espécie, ou erro para nome desconhecido."""
    return TRACOS_ESPECIE[normalizar_especie(especie)]


def _magias_da_escolha(opcao: dict[str, Any], nivel: int, bonus_proficiencia: int) -> dict[str, Any]:
    """Magias e truques concedidos por uma escolha (linhagem/legado) até o nível."""
    truques: list[str] = []
    magias: list[dict[str, Any]] = []
    usos_sem_espaco = 1
    for marco in ("nivel_1", "nivel_3", "nivel_5"):
        dados = opcao.get(marco) or {}
        truques.extend(dados.get("truques", ()))
        for magia in dados.get("magias", ()):
            magias.append({"magia": magia, "marco": int(marco.split("_")[1])})
        if dados.get("magias_preparadas"):
            for magia in dados["magias_preparadas"]:
                magias.append({"magia": magia, "marco": 1, "sempre_preparada": True})
        if dados.get("usos_sem_espaco_igual_bonus_proficiencia"):
            usos_sem_espaco = bonus_proficiencia
    liberadas = [m for m in magias if nivel >= m["marco"]]
    return {
        "truques": truques,
        "magias": liberadas,
        "magias_preparadas": True,
        "conjura_sem_espaco_por_descanso_longo": usos_sem_espaco,
    }


def resolver_tracos_especie(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve os traços de espécie em fatos mecânicos determinísticos.

    Entrada: ``especie``, ``nivel`` (padrão 1) e as escolhas da espécie
    (``heranca_draconica``, ``linhagem``/``linhagem_elfica``, ``linhagem_gnomica``,
    ``ancestralidade``, ``legado``) além de ``bonus_proficiencia`` quando o
    chamador já o calculou. Saída auditável com ``fonte`` do livro, traços
    disponíveis até o nível e fatos derivados (resistências, vantagens de
    salvaguarda, visão no escuro, deslocamento, PV por nível, magias).
    """
    chave = normalizar_especie(fatos.get("especie", fatos.get("especie_nome")))
    bloco = TRACOS_ESPECIE[chave]
    nivel = int(fatos.get("nivel", 1) or 1)
    if not 1 <= nivel <= 20:
        raise ValueError("O nível deve estar entre 1 e 20")
    bonus_proficiencia = fatos.get("bonus_proficiencia")
    if bonus_proficiencia is None:
        from .core import bonus_proficiencia as calcular_bonus

        bonus_proficiencia = calcular_bonus(nivel)
    bonus_proficiencia = int(bonus_proficiencia)

    tracos_disponiveis = [t for t in bloco["tracos"] if nivel >= int(t.get("nivel_minimo", 1))]
    pv_por_nivel = sum(int(t.get("pv_bonus_por_nivel", 0)) for t in tracos_disponiveis)
    resultado: dict[str, Any] = {
        "resultado": "resolvido",
        "especie": chave,
        "nome": bloco["nome"],
        "tipo_criatura": bloco["tipo_criatura"],
        "tamanhos": list(bloco["tamanhos"]),
        "nivel": nivel,
        "bonus_proficiencia": bonus_proficiencia,
        "deslocamento_m": bloco["deslocamento_m"],
        "resistencias_dano": list(bloco.get("resistencias_dano", ())),
        "vantagens_salvaguarda": sorted({v for t in tracos_disponiveis for v in t.get("vantagens_salvaguarda", ())}),
        "visao_no_escuro_m": max(
            [t["visao_no_escuro_m"] for t in tracos_disponiveis if "visao_no_escuro_m" in t] or [0]
        )
        or None,
        "pv_bonus_por_nivel": pv_por_nivel,
        "pv_bonus_total": pv_por_nivel * nivel,
        "tracos": tracos_disponiveis,
        "fonte": FONTE_ESPECIES,
    }

    # Escolhas da espécie: magias/efeitos derivados e pendências explícitas.
    escolhas_pendentes = []
    magias: dict[str, Any] = {}
    if chave == "draconato":
        heranca = fatos.get("heranca_draconica", fatos.get("heranca"))
        if heranca:
            chave_heranca = str(heranca).strip().lower().replace("-", "_").replace(" ", "_")
            if chave_heranca not in HERANCA_DRACONICA:
                raise ValueError(f"Herança Dracônica inválida: {heranca}")
            resultado["heranca_draconica"] = bloco_heranca_draconica(
                chave_heranca,
                nivel,
                int(fatos.get("modificador_constituicao", 0)),
                bonus_proficiencia,
            )
            resultado["resistencias_dano"] = [resultado["heranca_draconica"]["tipo_dano"]]
        else:
            escolhas_pendentes.append("heranca_draconica")
    elif chave == "elfo":
        linhagem = fatos.get("linhagem", fatos.get("linhagem_elfica"))
        if linhagem:
            chave_lin = str(linhagem).strip().lower().replace("-", "_").replace(" ", "_")
            if chave_lin not in LINHAGENS_ELFICAS:
                raise ValueError(f"Linhagem élfica inválida: {linhagem}")
            opcao = LINHAGENS_ELFICAS[chave_lin]
            magias = _magias_da_escolha(opcao, nivel, bonus_proficiencia)
            if "visao_no_escuro_m" in opcao:
                resultado["visao_no_escuro_m"] = max(resultado["visao_no_escuro_m"] or 0, opcao["visao_no_escuro_m"])
            if "deslocamento_m" in opcao:
                resultado["deslocamento_m"] = opcao["deslocamento_m"]
            resultado["linhagem"] = {"chave": linhagem, "nome": opcao["nome"]}
        else:
            escolhas_pendentes.append("linhagem_elfica")
    elif chave == "gnomo":
        linhagem = fatos.get("linhagem", fatos.get("linhagem_gnomica"))
        if linhagem:
            chave_lin = str(linhagem).strip().lower().replace("-", "_").replace(" ", "_")
            if chave_lin not in LINHAGENS_GNOMICAS:
                raise ValueError(f"Linhagem gnômica inválida: {linhagem}")
            opcao = LINHAGENS_GNOMICAS[chave_lin]
            magias = _magias_da_escolha(opcao, nivel, bonus_proficiencia)
            resultado["linhagem"] = {"chave": linhagem, "nome": opcao["nome"]}
        else:
            escolhas_pendentes.append("linhagem_gnomica")
    elif chave == "golias":
        ancestralidade = fatos.get("ancestralidade", fatos.get("ancestralidade_gigante"))
        if ancestralidade:
            chave_anc = str(ancestralidade).strip().lower().replace("-", "_").replace(" ", "_")
            if chave_anc not in ANCESTRALIDADES_GIGANTES:
                raise ValueError(f"Ancestralidade gigante inválida: {ancestralidade}")
            resultado["ancestralidade_gigante"] = {"chave": chave_anc, **ANCESTRALIDADES_GIGANTES[chave_anc]}
        else:
            escolhas_pendentes.append("ancestralidade_gigante")
    elif chave == "tiefling":
        legado = fatos.get("legado", fatos.get("legado_infero"))
        if legado:
            chave_legado = str(legado).strip().lower().replace("-", "_").replace(" ", "_")
            if chave_legado not in LEGADOS_INFEROS:
                raise ValueError(f"Legado ínfero inválido: {legado}")
            opcao = LEGADOS_INFEROS[chave_legado]
            magias = _magias_da_escolha(opcao, nivel, bonus_proficiencia)
            resultado["legado_infero"] = {"chave": chave_legado, "nome": opcao["nome"]}
            resultado["resistencias_dano"] = list(opcao["resistencias_dano"])
        else:
            escolhas_pendentes.append("legado_infero")

    if magias:
        resultado["magias"] = magias
    if escolhas_pendentes:
        resultado["escolhas_pendentes"] = escolhas_pendentes
    return resultado
