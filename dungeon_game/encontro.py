"""Encontro de cripta: um Bardo contra inimigos do bestiário, por turnos.

Regras não são resolvidas aqui. Iniciativa, ataque, geometria de alcance/visão,
condições, dano, PV, CA e XP passam pelo Orquestrador; a geometria de grade
(caminhos, ocupação, segmento de linha de visão) vem do tabuleiro. Este módulo
guarda o estado do encontro e decide a ordem das chamadas.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from character_creator.service import CharacterCreatorService
from orchestrator import Acao, OrquestradorAcoes, aplicar_recompensa
from orchestrator.preparo import cd_de_magia
from rule_engine.bestiary import consultar_monstro
from rule_engine.casting import atributo_de_conjuracao
from rule_engine.catalog import CATALOGO_ARMADURAS, CATALOGO_ARMAS
from rule_engine.conditions import EstadoCondicoes
from rule_engine.spells import mecanica_de_magia
from rule_engine.survival import EstadoVital

from .combat_board import BoardPosition, CombatBoard
from .combat_session import Combatant, CombatSession, EncounterStatus
from .combate_inimigo import atacar as atacar_inimigo, validar_geometria_ataque
from .inimigos import carregar_inimigo, escolher_acao_inimigo
from .rule_adapter import DungeonRuleAdapter

MAPAS_DIR = Path(__file__).parent / "mapas"
SIMBOLOS_BLOQUEADOS = {"#", "+", "o", "t"}
SIMBOLOS_BLOQUEADOS_VISAO = {"#", "+"}
CASA_PES = 5
ATRIBUTO_CONJURACAO = "carisma"
CLASSES_JOGAVEIS = (
    "bardo",
    "monge",
    "guerreiro",
    "barbaro",
    "ladino",
    "clerigo",
    "mago",
    "paladino",
    "druida",
    "artifice",
    "guardiao",
    "feiticeiro",
    "bruxo",
)

CATALOGO_CLASSES: dict[str, dict[str, str]] = {
    "bardo": {
        "id": "bardo",
        "nome": "Bardo",
        "nome_personagem_padrao": "Vanish",
        "arma_padrao": "Rapieira",
        "descricao": "Conjurador versátil com Rapieira (1d8 perfurante) e magias de suporte e controle.",
    },
    "monge": {
        "id": "monge",
        "nome": "Monge",
        "nome_personagem_padrao": "Kael",
        "arma_padrao": "Cajado",
        "descricao": "Artista marcial ágil com Defesa sem Armadura, Cajado (1d6 contundente) e Golpe Desarmado bônus.",
    },
    "guerreiro": {
        "id": "guerreiro",
        "nome": "Guerreiro",
        "nome_personagem_padrao": "Aldric",
        "arma_padrao": "Espada Longa",
        "arma_distancia": "Arco Curto",
        "descricao": "Linha de frente blindado (Cota de Malha + Escudo), com Espada Longa, Arco Curto e Recuperar o Fôlego.",
    },
    "barbaro": {
        "id": "barbaro",
        "nome": "Bárbaro",
        "nome_personagem_padrao": "Thorgar",
        "arma_padrao": "Machado Grande",
        "descricao": "Combatente feroz com Defesa sem Armadura, Machado Grande (1d12 cortante) e Fúria (+2 dano e resistência física).",
    },
    "ladino": {
        "id": "ladino",
        "nome": "Ladino",
        "nome_personagem_padrao": "Lyra",
        "arma_padrao": "Rapieira",
        "arma_distancia": "Arco Curto",
        "descricao": "Especialista furtiva com Rapieira, Arco Curto, Mirar (ação bônus) e Ataque Furtivo (+1d6 de dano com vantagem).",
    },
    "clerigo": {
        "id": "clerigo",
        "nome": "Clérigo",
        "nome_personagem_padrao": "Seraphina",
        "arma_padrao": "Maça",
        "descricao": "Conjuradora divina (Cota de Malha Parcial + Escudo), com Maça, Curar Ferimentos, Comando e Escudo da Fé (+2 CA).",
    },
    "mago": {
        "id": "mago",
        "nome": "Mago",
        "nome_personagem_padrao": "Elira",
        "arma_padrao": "Cajado",
        "descricao": "Conjuradora arcana com Raio de Fogo, Raio de Gelo, Mísseis Mágicos, Armadura Arcana e Recuperação Arcana.",
    },
    "paladino": {
        "id": "paladino",
        "nome": "Paladino",
        "nome_personagem_padrao": "Gideon",
        "arma_padrao": "Espada Longa",
        "descricao": "Campeão sagrado (Cota de Malha + Escudo), com Espada Longa, Mãos Consagradas (cura bônus), Escudo da Fé e Comando.",
    },
    "druida": {
        "id": "druida",
        "nome": "Druida",
        "nome_personagem_padrao": "Rowan",
        "arma_padrao": "Cajado",
        "descricao": "Guardião primal (Couro + Escudo), com Chicote de Espinhos, Rajada de Veneno, Palavra Curativa (bônus) e Curar Ferimentos.",
    },
    "artifice": {
        "id": "artifice",
        "nome": "Artífice",
        "nome_personagem_padrao": "Nima Cobre",
        "arma_padrao": "Maça",
        "arma_distancia": "Besta Leve",
        "descricao": "Inventora arcana (Cota de Malha Parcial + Escudo), com Maça, Besta Leve, Toque Chocante, Raio de Fogo, Curar Ferimentos e Vitalidade Vazia.",
    },
    "guardiao": {
        "id": "guardiao",
        "nome": "Guardião",
        "nome_personagem_padrao": "Sylas",
        "arma_padrao": "Espada Curta",
        "arma_distancia": "Arco Longo",
        "descricao": "Explorador primal (Cota de Malha Parcial), com Espada Curta, Arco Longo, Marca do Predador (+1d6 de dano) e Curar Ferimentos.",
    },
    "feiticeiro": {
        "id": "feiticeiro",
        "nome": "Feiticeiro",
        "nome_personagem_padrao": "Vaelis",
        "arma_padrao": "Adaga",
        "descricao": "Conjurador inato com Feitiçaria Inata (vantagem em ataques mágicos e +1 CD), Raio de Fogo, Raio de Gelo, Mísseis Mágicos e Armadura Arcana.",
    },
    "bruxo": {
        "id": "bruxo",
        "nome": "Bruxo",
        "nome_personagem_padrao": "Malakor",
        "arma_padrao": "Adaga",
        "descricao": "Conjurador de pacto com Raio Místico (1d10 energético), Raio de Bruxa (2d12 elétrico), Armadura de Agathys e recarga no Descanso Curto.",
    },
}

SUBCLASSE_PADRAO_POR_CLASSE: dict[str, dict[str, str]] = {
    "bardo": {
        "id": "colegio_da_bravura",
        "nome": "Colégio da Bravura",
        "caracteristica": "inspiracao_marcial",
        "caracteristica_nome": "Inspiração Marcial",
    },
    "monge": {
        "id": "combatente_da_mao_espalmada",
        "nome": "Combatente da Mão Espalmada",
        "caracteristica": "tecnica_da_mao_espalmada",
        "caracteristica_nome": "Técnica da Mão Espalmada",
    },
    "guerreiro": {
        "id": "campeao",
        "nome": "Campeão",
        "caracteristica": "critico_aprimorado",
        "caracteristica_nome": "Crítico Aprimorado",
    },
    "barbaro": {
        "id": "trilha_do_berserker",
        "nome": "Trilha do Berserker",
        "caracteristica": "frenesi",
        "caracteristica_nome": "Frenesi",
    },
    "ladino": {
        "id": "assassino",
        "nome": "Assassino",
        "caracteristica": "assassinar",
        "caracteristica_nome": "Assassinar",
    },
    "clerigo": {
        "id": "dominio_da_vida",
        "nome": "Domínio da Vida",
        "caracteristica": "discipulo_da_vida",
        "caracteristica_nome": "Discípulo da Vida",
    },
    "mago": {
        "id": "evocador",
        "nome": "Evocador",
        "caracteristica": "truque_potente",
        "caracteristica_nome": "Truque Potente",
    },
    "paladino": {
        "id": "juramento_da_devocao",
        "nome": "Juramento da Devoção",
        "caracteristica": "arma_sagrada",
        "caracteristica_nome": "Arma Sagrada",
    },
    "druida": {
        "id": "circulo_das_estrelas",
        "nome": "Círculo das Estrelas",
        "caracteristica": "forma_estrelada",
        "caracteristica_nome": "Forma Estrelada",
    },
    "artifice": {
        "id": "reanimador",
        "nome": "Reanimador",
        "caracteristica": "descarga_voltaica",
        "caracteristica_nome": "Descarga Voltaica",
    },
    "guardiao": {
        "id": "cacador",
        "nome": "Caçador",
        "caracteristica": "matador_de_colossos",
        "caracteristica_nome": "Matador de Colossos",
    },
    "feiticeiro": {
        "id": "feiticaria_draconica",
        "nome": "Feitiçaria Dracônica",
        "caracteristica": "resiliencia_draconica",
        "caracteristica_nome": "Resiliência Dracônica",
    },
    "bruxo": {
        "id": "patrono_infero",
        "nome": "Patrono Ínfero",
        "caracteristica": "bencao_do_obscuro",
        "caracteristica_nome": "Bênção do Obscuro",
    },
}

SALAS_PADRAO: dict[str, dict[str, Any]] = {
    "cripta_inicial": {
        "andar": 1,
        "sala": 1,
        "proxima_sala": "santuario_circular",
        "recompensa_ouro_po": 15,
        "inimigos": [
            ("goblin-1", "goblin", (25, 10)),
            ("esqueleto-1", "esqueleto", (25, 17)),
        ],
    },
    "santuario_circular": {
        "andar": 1,
        "sala": 2,
        "proxima_sala": "catacumba_dos_mortos",
        "recompensa_ouro_po": 30,
        "inimigos": [
            ("goblin-1", "goblin", (21, 10)),
            ("esqueleto-1", "esqueleto", (27, 13)),
            ("goblin-arqueiro-1", "goblin_arqueiro", (21, 16)),
        ],
    },
    "catacumba_dos_mortos": {
        "andar": 1,
        "sala": 3,
        "proxima_sala": "camara_profana",
        "recompensa_ouro_po": 45,
        "inimigos": [
            ("zumbi-1", "zumbi", (24, 9)),
            ("cultista-1", "cultista", (25, 14)),
            ("carnical-1", "carnical", (28, 18)),
        ],
    },
    "camara_profana": {
        "andar": 1,
        "sala": 4,
        "proxima_sala": "sarcofago_do_rei_mumia",
        "recompensa_ouro_po": 100,
        "inimigos": [
            ("sombra-1", "sombra", (24, 9)),
            ("armadura-animada-1", "armadura_animada", (23, 14)),
            ("aparicao-1", "aparicao", (29, 14)),
        ],
    },
    "sarcofago_do_rei_mumia": {
        "andar": 1,
        "sala": 5,
        "proxima_sala": None,
        "recompensa_ouro_po": 200,
        "inimigos": [
            ("espectro-1", "espectro", (24, 9)),
            ("esqueleto-minotauro-1", "esqueleto_minotauro", (23, 18)),
            ("mumia-1", "mumia", (31, 14)),
        ],
    },
}

# Magias com efeito resolvido no encontro. Curar Ferimentos: 2d8 + modificador de
# conjuração (PHB 2024; a mecânica do motor também marca soma_modificador_conjuracao).
EFEITOS_EM_COMBATE = {
    "Curar Ferimentos",
    "Palavra Curativa",
    "Zombaria Perversa",
    "Comando",
    "Escudo da Fé",
    "Raio de Fogo",
    "Raio de Gelo",
    "Mísseis Mágicos",
    "Armadura Arcana",
    "Chicote de Espinhos",
    "Rajada de Veneno",
    "Toque Chocante",
    "Vitalidade Vazia",
    "Marca do Predador",
    "Raio Místico",
    "Armadura de Agathys",
    "Raio de Bruxa",
}

# Alvo de cada magia: si mesmo (toque/pessoal) ou inimigo ao alcance.
ALVO_MAGIA = {
    "Curar Ferimentos": "si_mesmo",
    "Palavra Curativa": "si_mesmo",
    "Escudo da Fé": "si_mesmo",
    "Armadura Arcana": "si_mesmo",
    "Vitalidade Vazia": "si_mesmo",
    "Armadura de Agathys": "si_mesmo",
    "Zombaria Perversa": "inimigo",
    "Comando": "inimigo",
    "Raio de Fogo": "inimigo",
    "Raio de Gelo": "inimigo",
    "Mísseis Mágicos": "inimigo",
    "Chicote de Espinhos": "inimigo",
    "Rajada de Veneno": "inimigo",
    "Toque Chocante": "inimigo",
    "Marca do Predador": "inimigo",
    "Raio Místico": "inimigo",
    "Raio de Bruxa": "inimigo",
}
SALVAGUARDA_EM_COMBATE = {"Zombaria Perversa", "Comando"}  # usam CD de magia (salvaguarda do alvo)
ALCANCE_MAGIA_PES = 60  # 18 m, alcance padrão de Zombaria Perversa, Comando e Raio de Gelo
ALCANCE_MAGIA_POR_NOME_PES = {
    "Raio de Fogo": 120,
    "Mísseis Mágicos": 120,
    "Raio Místico": 120,
    "Marca do Predador": 90,
    "Raio de Gelo": 60,
    "Raio de Bruxa": 60,
    "Comando": 60,
    "Zombaria Perversa": 60,
    "Chicote de Espinhos": 30,
    "Rajada de Veneno": 30,
    "Toque Chocante": 5,
}

# Comandos de Comando (PHB 2024). Cada um vale só para o próximo turno do alvo.
COMANDOS = ("aproximar", "largar", "fugir", "abaixar", "parar")

MOTIVOS_SEM_EFEITO = {
    "Golpe Certeiro": "magia sem resolução específica no motor",
    "Luz": "sem efeito em combate",
    "Ilusão Menor": "sem efeito em combate",
    "Detectar Magia": "sem efeito em combate",
    "Orientação": "sem efeito direto em combate",
    "Resistência": "sem efeito direto em combate",
    "Bênção": "efeito ainda não resolvido no tabuleiro",
    "Mãos Flamejantes": "efeito em área ainda não resolvido no tabuleiro",
    "Fogo das Fadas": "efeito em área ainda não resolvido no tabuleiro",
    "Enfeitiçar Pessoa": "efeito ainda não resolvido pelo motor (salvaguarda e condição)",
}


def normalizar_mapa_id(mapa_id: str) -> str:
    chave = str(mapa_id or "").strip().lower().replace("-", "_")
    if not chave or "/" in chave or "\\" in chave or ".." in chave:
        raise ValueError(f"Identificador de mapa inválido: {mapa_id!r}")
    return chave


def validar_mapa(mapa: dict[str, Any]) -> dict[str, Any]:
    grade = mapa.get("grade")
    legenda = mapa.get("legenda")
    if not isinstance(grade, list) or not grade or not all(isinstance(linha, str) and linha for linha in grade):
        raise ValueError("Grade de mapa ausente ou inválida")
    if len({len(linha) for linha in grade}) != 1:
        raise ValueError("Grade de mapa precisa ser retangular")
    if not isinstance(legenda, dict) or not legenda:
        raise ValueError("Legenda de mapa ausente ou inválida")
    simbolos = {simbolo for linha in grade for simbolo in linha}
    desconhecidos = simbolos - set(legenda)
    if desconhecidos:
        raise ValueError(f"Símbolos fora da legenda: {sorted(desconhecidos)}")
    return mapa


def carregar_mapa(mapa_id: str) -> dict[str, Any]:
    chave = normalizar_mapa_id(mapa_id)
    caminho = (MAPAS_DIR / f"{chave}.json").resolve()
    if MAPAS_DIR.resolve() not in caminho.parents or not caminho.is_file():
        raise ValueError(f"Mapa não encontrado no catálogo: {mapa_id}")
    mapa = json.loads(caminho.read_text(encoding="utf-8"))
    return validar_mapa(mapa)


def listar_mapas() -> list[dict[str, Any]]:
    """Lista os mapas fixos do catálogo em ordem de andar e sala."""
    itens: list[dict[str, Any]] = []
    for caminho in sorted(MAPAS_DIR.glob("*.json")):
        chave = caminho.stem
        mapa = carregar_mapa(chave)
        padrao = SALAS_PADRAO.get(chave, {})
        grade = mapa["grade"]
        itens.append(
            {
                "id": chave,
                "codigo": mapa.get("id", chave),
                "nome": mapa.get("nome", chave),
                "ambiente": mapa.get("ambiente", "cripta"),
                "andar": int(mapa.get("andar", padrao.get("andar", 1))),
                "sala": int(mapa.get("sala", padrao.get("sala", 1))),
                "proxima_sala": mapa.get("proxima_sala", padrao.get("proxima_sala")),
                "recompensa_ouro_po": int(mapa.get("recompensa_ouro_po", padrao.get("recompensa_ouro_po", 0))),
                "largura": len(grade[0]),
                "altura": len(grade),
            }
        )
    return sorted(itens, key=lambda item: (item["andar"], item["sala"], item["id"]))


def inimigos_padrao_do_mapa(mapa_id: str) -> list[tuple[str, str, tuple[int, int]]]:
    chave = normalizar_mapa_id(mapa_id)
    if chave in SALAS_PADRAO:
        return list(SALAS_PADRAO[chave]["inimigos"])
    mapa = carregar_mapa(chave)
    entradas = mapa.get("entradas", {}).get("inimigos", [])
    perfis_ciclo = ("goblin", "esqueleto", "goblin_arqueiro")
    return [
        (f"{perfis_ciclo[i % len(perfis_ciclo)]}-{i + 1}", perfis_ciclo[i % len(perfis_ciclo)], (int(p["x"]), int(p["y"])))
        for i, p in enumerate(entradas)
    ]


def tabuleiro_do_mapa(mapa: dict[str, Any]) -> CombatBoard:
    grade = mapa["grade"]
    legenda = mapa.get("legenda") or {}
    bloqueadas = frozenset(
        BoardPosition(x, y)
        for y, linha in enumerate(grade)
        for x, simbolo in enumerate(linha)
        if bool(legenda.get(simbolo, {}).get("bloqueia_movimento", simbolo in SIMBOLOS_BLOQUEADOS))
    )
    bloqueadas_visao = frozenset(
        BoardPosition(x, y)
        for y, linha in enumerate(grade)
        for x, simbolo in enumerate(linha)
        if bool(legenda.get(simbolo, {}).get("bloqueia_visao", simbolo in SIMBOLOS_BLOQUEADOS_VISAO))
    )
    casa_pes = int(mapa.get("casa_pes", CASA_PES))
    return DungeonRuleAdapter.create_combat_board(
        len(grade[0]),
        len(grade),
        blocked=bloqueadas,
        vision_blocked=bloqueadas_visao,
        tile_feet=casa_pes,
    )


def listar_classes() -> list[dict[str, str]]:
    """Lista as classes jogáveis suportadas pelo encontro."""
    return [dict(CATALOGO_CLASSES[cid]) for cid in CLASSES_JOGAVEIS]


ESPECIES_JOGAVEIS = (
    "humano",
    "elfo",
    "anao",
    "halfling",
    "draconato",
    "gnomo",
    "golias",
    "orc",
    "tiefling",
    "aasimar",
)

CATALOGO_ESPECIES: dict[str, dict[str, Any]] = {
    "humano": {
        "id": "humano",
        "nome": "Humano",
        "escolhas_padrao": {},
        "descricao": "Eficiente (Inspiração Heroica com vantagem no 1º ataque) e Versátil (+2 PV por nível).",
    },
    "elfo": {
        "id": "elfo",
        "nome": "Elfo",
        "escolhas_padrao": {"linhagem_elfica": "alto_elfo"},
        "descricao": "Ancestralidade Feérica (imune à paralisia do Carniçal e vantagem contra Enfeitiçado) e truque Raio de Fogo.",
    },
    "anao": {
        "id": "anao",
        "nome": "Anão",
        "escolhas_padrao": {},
        "descricao": "Tenacidade Anã (+1 PV máximo por nível) e Resistência a Toxinas (resistência a dano venenoso).",
    },
    "halfling": {
        "id": "halfling",
        "nome": "Pequenino",
        "escolhas_padrao": {},
        "descricao": "Sorte (rerrola 1 natural em ataques e salvaguardas) e Corajoso (vantagem contra Amedrontado).",
    },
    "draconato": {
        "id": "draconato",
        "nome": "Draconato",
        "escolhas_padrao": {"heranca_draconica": "vermelho"},
        "descricao": "Herança Dracônica Vermelha (resistência a dano ígneo e Ataque de Sopro 1d10 ígneo).",
    },
    "gnomo": {
        "id": "gnomo",
        "nome": "Gnomo",
        "escolhas_padrao": {"linhagem_gnomica": "rochas"},
        "descricao": "Astúcia de Gnomo (vantagem nas salvaguardas de Inteligência, Sabedoria e Carisma).",
    },
    "golias": {
        "id": "golias",
        "nome": "Golias",
        "escolhas_padrao": {"ancestralidade_gigante": "queimadura_de_fogo"},
        "descricao": "Deslocamento de 35 pés (7 casas) e Ancestralidade Gigante (+1d10 de dano ígneo ao acertar).",
    },
    "orc": {
        "id": "orc",
        "nome": "Orc",
        "escolhas_padrao": {},
        "descricao": "Pico de Adrenalina (+PV temporários ao iniciar combate) e Vigor Implacável (fica com 1 PV ao cair a 0 PV).",
    },
    "tiefling": {
        "id": "tiefling",
        "nome": "Tiferino",
        "escolhas_padrao": {"legado_infero": "infernal"},
        "descricao": "Legado Infernal (resistência a dano ígneo e truque Raio de Fogo).",
    },
    "aasimar": {
        "id": "aasimar",
        "nome": "Aasimar",
        "escolhas_padrao": {},
        "descricao": "Resistência Celestial (resistência a dano necrótico e radiante) e Revelação Celestial no Nível 3.",
    },
}


def listar_especies_jogaveis() -> list[dict[str, Any]]:
    """Lista as 10 espécies jogáveis do PHB 2024 suportadas pelo encontro."""
    return [
        {k: v for k, v in CATALOGO_ESPECIES[eid].items() if k != "escolhas_padrao"}
        for eid in ESPECIES_JOGAVEIS
    ]


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
    ficha["arma_padrao"] = "Rapieira"
    ficha["conjuracao"] = _conjuracao_validada(previa)
    # O criador grava o deslocamento em metros (9 m = 30 pés); o tabuleiro usa casas de 5 pés.
    ficha["deslocamento_pes"] = round(float(ficha["deslocamento"]) * 3.28084 / CASA_PES) * CASA_PES
    ficha["pv_atuais"] = ficha["pv_maximo"]
    ficha["pv_temporarios"] = 0
    ficha["xp"] = 0
    ficha["ouro_po"] = 0
    return ficha


def criar_ficha_monge(nome: str = "Kael", *, id_ficha: str = "monge-1") -> dict[str, Any]:
    """Ficha de Monge nível 1 validada pelo criador, com Defesa sem Armadura e Artes Marciais."""
    payload = {
        "name": nome,
        "class": "monge",
        "species": "anao",
        "background": "marinheiro",
        "ravenloft": False,
        "ability_method": "standard_array",
        "ability_scores": {
            "forca": 12,
            "destreza": 15,
            "constituicao": 13,
            "inteligencia": 10,
            "sabedoria": 14,
            "carisma": 8,
        },
        "background_increases": {"destreza": 2, "sabedoria": 1},
        "background_equipment": "A",
        "class_skills": ["atletismo", "furtividade"],
        "narrative": {"pronouns": "ele/dele", "appearance": "Túnica açafrão e faixas nos punhos."},
    }
    previa = CharacterCreatorService().preview(payload)
    if not previa.get("ready"):
        raise ValueError(f"Ficha de Monge incompleta: {previa.get('missing')}")
    ficha = dict(previa["character"])
    ficha["id"] = id_ficha
    ficha["arma_padrao"] = "Cajado"
    ficha["deslocamento_pes"] = round(float(ficha["deslocamento"]) * 3.28084 / CASA_PES) * CASA_PES
    ficha["pv_atuais"] = ficha["pv_maximo"]
    ficha["pv_temporarios"] = 0
    ficha["xp"] = 0
    ficha["ouro_po"] = 0
    return ficha


def criar_ficha_guerreiro(nome: str = "Aldric", *, id_ficha: str = "guerreiro-1") -> dict[str, Any]:
    """Ficha de Guerreiro nível 1 validada pelo criador, com Espada Longa, Arco Curto e Recuperar o Fôlego."""
    payload = {
        "name": nome,
        "class": "guerreiro",
        "species": "anao",
        "background": "fazendeiro",
        "ravenloft": False,
        "ability_method": "standard_array",
        "ability_scores": {
            "forca": 15,
            "destreza": 14,
            "constituicao": 13,
            "inteligencia": 10,
            "sabedoria": 12,
            "carisma": 8,
        },
        "background_increases": {"forca": 2, "constituicao": 1},
        "background_equipment": "A",
        "class_skills": ["atletismo", "percepcao"],
        "class_choices": {"estilo_de_luta": "defensivo"},
        "spells": {"cantrips": [], "selected": [], "spellbook": []},
        "narrative": {"pronouns": "ele/dele", "appearance": "Cota de malha, escudo e espada longa."},
    }
    previa = CharacterCreatorService().preview(payload)
    if not previa.get("ready"):
        raise ValueError(f"Ficha de Guerreiro incompleta: {previa.get('missing')}")
    ficha = dict(previa["character"])
    ficha["id"] = id_ficha
    ficha["arma_padrao"] = "Espada Longa"
    ficha["arma_distancia"] = "Arco Curto"
    ficha["estilo_de_luta"] = str((previa.get("choices") or {}).get("class_choices", {}).get("estilo_de_luta", "defensivo"))
    ficha["maestrias_arma"] = ["Espada Longa", "Arco Curto", "Machado de Batalha"]
    ficha["deslocamento_pes"] = round(float(ficha["deslocamento"]) * 3.28084 / CASA_PES) * CASA_PES
    ficha["pv_atuais"] = ficha["pv_maximo"]
    ficha["pv_temporarios"] = 0
    ficha["xp"] = 0
    ficha["ouro_po"] = 0
    return ficha


def criar_ficha_barbaro(nome: str = "Thorgar", *, id_ficha: str = "barbaro-1") -> dict[str, Any]:
    """Ficha de Bárbaro nível 1 validada pelo criador, com Defesa sem Armadura e Fúria."""
    payload = {
        "name": nome,
        "class": "barbaro",
        "species": "anao",
        "background": "fazendeiro",
        "ravenloft": False,
        "ability_method": "standard_array",
        "ability_scores": {
            "forca": 15,
            "destreza": 14,
            "constituicao": 13,
            "inteligencia": 8,
            "sabedoria": 12,
            "carisma": 10,
        },
        "background_increases": {"forca": 2, "constituicao": 1},
        "background_equipment": "A",
        "class_skills": ["atletismo", "percepcao"],
        "spells": {"cantrips": [], "selected": [], "spellbook": []},
        "narrative": {"pronouns": "ele/dele", "appearance": "Machado grande e peles."},
    }
    previa = CharacterCreatorService().preview(payload)
    if not previa.get("ready"):
        raise ValueError(f"Ficha de Bárbaro incompleta: {previa.get('missing')}")
    ficha = dict(previa["character"])
    ficha["id"] = id_ficha
    ficha["arma_padrao"] = "Machado Grande"
    ficha["maestrias_arma"] = ["Machado Grande", "Machadinha"]
    ficha["deslocamento_pes"] = round(float(ficha["deslocamento"]) * 3.28084 / CASA_PES) * CASA_PES
    ficha["pv_atuais"] = ficha["pv_maximo"]
    ficha["pv_temporarios"] = 0
    ficha["xp"] = 0
    ficha["ouro_po"] = 0
    return ficha


def criar_ficha_ladino(nome: str = "Lyra", *, id_ficha: str = "ladino-1") -> dict[str, Any]:
    """Ficha de Ladino nível 1 validada pelo criador, com Rapieira, Arco Curto e Ataque Furtivo."""
    payload = {
        "name": nome,
        "class": "ladino",
        "species": "anao",
        "background": "criminoso",
        "ravenloft": False,
        "ability_method": "standard_array",
        "ability_scores": {
            "forca": 8,
            "destreza": 15,
            "constituicao": 14,
            "inteligencia": 13,
            "sabedoria": 12,
            "carisma": 10,
        },
        "background_increases": {"destreza": 2, "constituicao": 1},
        "background_equipment": "A",
        "class_skills": ["acrobacia", "intuicao", "investigacao", "percepcao"],
        "expertise": ["furtividade", "prestidigitacao"],
        "spells": {"cantrips": [], "selected": [], "spellbook": []},
        "narrative": {"pronouns": "ela/dela", "appearance": "Capuz escuro, rapieira e arco curto."},
    }
    previa = CharacterCreatorService().preview(payload)
    if not previa.get("ready"):
        raise ValueError(f"Ficha de Ladino incompleta: {previa.get('missing')}")
    ficha = dict(previa["character"])
    ficha["id"] = id_ficha
    ficha["arma_padrao"] = "Rapieira"
    ficha["arma_distancia"] = "Arco Curto"
    ficha["maestrias_arma"] = ["Rapieira", "Arco Curto"]
    ficha["deslocamento_pes"] = round(float(ficha["deslocamento"]) * 3.28084 / CASA_PES) * CASA_PES
    ficha["pv_atuais"] = ficha["pv_maximo"]
    ficha["pv_temporarios"] = 0
    ficha["xp"] = 0
    ficha["ouro_po"] = 0
    return ficha


def criar_ficha_clerigo(nome: str = "Seraphina", *, id_ficha: str = "clerigo-1") -> dict[str, Any]:
    """Ficha de Clérigo nível 1 validada pelo criador, com Maça, Escudo e conjuração divina."""
    payload = {
        "name": nome,
        "class": "clerigo",
        "species": "anao",
        "background": "fazendeiro",
        "ravenloft": False,
        "ability_method": "standard_array",
        "ability_scores": {
            "forca": 14,
            "destreza": 10,
            "constituicao": 13,
            "inteligencia": 8,
            "sabedoria": 15,
            "carisma": 12,
        },
        "background_increases": {"sabedoria": 2, "constituicao": 1},
        "background_equipment": "A",
        "class_skills": ["historia", "medicina"],
        "class_choices": {"ordem_divina": "dominio_de_vida"},
        "spells": {
            "cantrips": ["Luz", "Orientação", "Resistência"],
            "selected": ["Curar Ferimentos", "Comando", "Escudo da Fé", "Bênção"],
            "spellbook": [],
        },
        "narrative": {"pronouns": "ela/dela", "appearance": "Maça sagrada e cota de malha parcial."},
    }
    previa = CharacterCreatorService().preview(payload)
    if not previa.get("ready"):
        raise ValueError(f"Ficha de Clérigo incompleta: {previa.get('missing')}")
    ficha = dict(previa["character"])
    ficha["id"] = id_ficha
    ficha["arma_padrao"] = "Maça"
    ficha["conjuracao"] = _conjuracao_validada(previa)
    ficha["deslocamento_pes"] = round(float(ficha["deslocamento"]) * 3.28084 / CASA_PES) * CASA_PES
    ficha["pv_atuais"] = ficha["pv_maximo"]
    ficha["pv_temporarios"] = 0
    ficha["xp"] = 0
    ficha["ouro_po"] = 0
    return ficha


def criar_ficha_mago(nome: str = "Elira", *, id_ficha: str = "mago-1") -> dict[str, Any]:
    """Ficha de Mago nível 1 validada pelo criador, com Cajado, Livro de Magias e Recuperação Arcana."""
    payload = {
        "name": nome,
        "class": "mago",
        "species": "anao",
        "background": "sabio",
        "ravenloft": False,
        "ability_method": "standard_array",
        "ability_scores": {
            "forca": 8,
            "destreza": 14,
            "constituicao": 13,
            "inteligencia": 15,
            "sabedoria": 12,
            "carisma": 10,
        },
        "background_increases": {"inteligencia": 2, "constituicao": 1},
        "background_equipment": "A",
        "class_skills": ["intuicao", "investigacao"],
        "spells": {
            "cantrips": ["Raio de Fogo", "Raio de Gelo", "Luz"],
            "selected": ["Mísseis Mágicos", "Armadura Arcana", "Mãos Flamejantes", "Detectar Magia"],
            "spellbook": [
                "Mísseis Mágicos",
                "Armadura Arcana",
                "Mãos Flamejantes",
                "Detectar Magia",
                "Onda Trovejante",
                "Sono",
            ],
        },
        "narrative": {"pronouns": "ela/dela", "appearance": "Grimório arcano e cajado."},
    }
    previa = CharacterCreatorService().preview(payload)
    if not previa.get("ready"):
        raise ValueError(f"Ficha de Mago incompleta: {previa.get('missing')}")
    ficha = dict(previa["character"])
    ficha["id"] = id_ficha
    ficha["arma_padrao"] = "Cajado"
    ficha["conjuracao"] = _conjuracao_validada(previa)
    ficha["deslocamento_pes"] = round(float(ficha["deslocamento"]) * 3.28084 / CASA_PES) * CASA_PES
    ficha["pv_atuais"] = ficha["pv_maximo"]
    ficha["pv_temporarios"] = 0
    ficha["xp"] = 0
    ficha["ouro_po"] = 0
    return ficha


def criar_ficha_paladino(nome: str = "Gideon", *, id_ficha: str = "paladino-1") -> dict[str, Any]:
    """Ficha de Paladino nível 1 validada pelo criador, com Espada Longa, Mãos Consagradas e conjuração."""
    payload = {
        "name": nome,
        "class": "paladino",
        "species": "anao",
        "background": "fazendeiro",
        "ravenloft": False,
        "ability_method": "standard_array",
        "ability_scores": {
            "forca": 15,
            "destreza": 10,
            "constituicao": 13,
            "inteligencia": 8,
            "sabedoria": 12,
            "carisma": 14,
        },
        "background_increases": {"forca": 2, "constituicao": 1},
        "background_equipment": "A",
        "class_skills": ["atletismo", "religiao"],
        "weapon_mastery": ["Espada Longa", "Martelo de Guerra"],
        "spells": {
            "cantrips": [],
            "selected": ["Escudo da Fé", "Comando"],
            "spellbook": [],
        },
        "narrative": {"pronouns": "ele/dele", "appearance": "Armadura reluzente e escudo sagrado."},
    }
    previa = CharacterCreatorService().preview(payload)
    if not previa.get("ready"):
        raise ValueError(f"Ficha de Paladino incompleta: {previa.get('missing')}")
    ficha = dict(previa["character"])
    ficha["id"] = id_ficha
    ficha["arma_padrao"] = "Espada Longa"
    ficha["maestrias_arma"] = ["Espada Longa", "Martelo de Guerra"]
    ficha["conjuracao"] = _conjuracao_validada(previa)
    ficha["deslocamento_pes"] = round(float(ficha["deslocamento"]) * 3.28084 / CASA_PES) * CASA_PES
    ficha["pv_atuais"] = ficha["pv_maximo"]
    ficha["pv_temporarios"] = 0
    ficha["xp"] = 0
    ficha["ouro_po"] = 0
    return ficha


def criar_ficha_druida(nome: str = "Rowan", *, id_ficha: str = "druida-1") -> dict[str, Any]:
    """Ficha de Druida nível 1 validada pelo criador, com Cajado, Escudo e conjuração primal."""
    payload = {
        "name": nome,
        "class": "druida",
        "species": "anao",
        "background": "eremita",
        "ravenloft": False,
        "ability_method": "standard_array",
        "ability_scores": {
            "forca": 8,
            "destreza": 14,
            "constituicao": 13,
            "inteligencia": 12,
            "sabedoria": 15,
            "carisma": 10,
        },
        "background_increases": {"sabedoria": 2, "constituicao": 1},
        "background_equipment": "A",
        "class_skills": ["natureza", "percepcao"],
        "class_choices": {"ordem_primal": "combatente"},
        "spells": {
            "cantrips": ["Chicote de Espinhos", "Rajada de Veneno"],
            "selected": ["Curar Ferimentos", "Palavra Curativa", "Fogo das Fadas", "Detectar Magia"],
            "spellbook": [],
        },
        "narrative": {"pronouns": "ele/dele", "appearance": "Manto de folhas e cajado retorcido."},
    }
    previa = CharacterCreatorService().preview(payload)
    if not previa.get("ready"):
        raise ValueError(f"Ficha de Druida incompleta: {previa.get('missing')}")
    ficha = dict(previa["character"])
    ficha["id"] = id_ficha
    ficha["arma_padrao"] = "Cajado"
    ficha["conjuracao"] = _conjuracao_validada(previa)
    ficha["deslocamento_pes"] = round(float(ficha["deslocamento"]) * 3.28084 / CASA_PES) * CASA_PES
    ficha["pv_atuais"] = ficha["pv_maximo"]
    ficha["pv_temporarios"] = 0
    ficha["xp"] = 0
    ficha["ouro_po"] = 0
    return ficha


def criar_ficha_artifice(nome: str = "Nima Cobre", *, id_ficha: str = "artifice-1") -> dict[str, Any]:
    """Ficha de Artífice nível 1 validada pelo criador, com Maça, Besta Leve e Magia de Artífice."""
    payload = {
        "name": nome,
        "class": "artifice",
        "species": "anao",
        "background": "artesao",
        "ravenloft": False,
        "ability_method": "standard_array",
        "ability_scores": {
            "inteligencia": 15,
            "constituicao": 14,
            "destreza": 13,
            "sabedoria": 12,
            "forca": 10,
            "carisma": 8,
        },
        "background_increases": {"inteligencia": 2, "destreza": 1},
        "background_tool": "Ferramentas de Carpinteiro",
        "background_equipment": "A",
        "class_skills": ["arcanismo", "historia"],
        "artisan_tool_proficiency": "Ferramentas de Ferreiro",
        "spells": {
            "cantrips": ["Raio de Fogo", "Toque Chocante"],
            "selected": ["Curar Ferimentos", "Vitalidade Vazia", "Fogo das Fadas"],
            "spellbook": [],
        },
        "narrative": {"pronouns": "ela/dela", "appearance": "Óculos de latão, ferramentas e foco arcano."},
    }
    previa = CharacterCreatorService().preview(payload)
    if not previa.get("ready"):
        raise ValueError(f"Ficha de Artífice incompleta: {previa.get('missing')}")
    ficha = dict(previa["character"])
    ficha["id"] = id_ficha
    ficha["arma_padrao"] = "Maça"
    ficha["arma_distancia"] = "Besta Leve"
    ficha["conjuracao"] = _conjuracao_validada(previa)
    ficha["deslocamento_pes"] = round(float(ficha["deslocamento"]) * 3.28084 / CASA_PES) * CASA_PES
    ficha["pv_atuais"] = ficha["pv_maximo"]
    ficha["pv_temporarios"] = 0
    ficha["xp"] = 0
    ficha["ouro_po"] = 0
    return ficha


def criar_ficha_guardiao(nome: str = "Sylas", *, id_ficha: str = "guardiao-1") -> dict[str, Any]:
    """Ficha de Guardião nível 1 validada pelo criador, com Espada Curta, Arco Longo e Marca do Predador."""
    payload = {
        "name": nome,
        "class": "guardiao",
        "species": "anao",
        "background": "guia",
        "ravenloft": False,
        "ability_method": "standard_array",
        "ability_scores": {
            "forca": 10,
            "destreza": 15,
            "constituicao": 13,
            "inteligencia": 12,
            "sabedoria": 14,
            "carisma": 8,
        },
        "background_increases": {"destreza": 2, "sabedoria": 1},
        "background_equipment": "A",
        "class_skills": ["percepcao", "natureza", "intuicao"],
        "weapon_mastery": ["Espada Curta", "Arco Longo"],
        "spells": {
            "cantrips": [],
            "selected": ["Marca do Predador", "Curar Ferimentos"],
            "spellbook": [],
        },
        "narrative": {"pronouns": "ele/dele", "appearance": "Capuz de batedor, espada curta e arco longo."},
    }
    previa = CharacterCreatorService().preview(payload)
    if not previa.get("ready"):
        raise ValueError(f"Ficha de Guardião incompleta: {previa.get('missing')}")
    ficha = dict(previa["character"])
    ficha["id"] = id_ficha
    ficha["arma_padrao"] = "Espada Curta"
    ficha["arma_distancia"] = "Arco Longo"
    ficha["maestrias_arma"] = ["Espada Curta", "Arco Longo"]
    ficha["conjuracao"] = _conjuracao_validada(previa)
    ficha["deslocamento_pes"] = round(float(ficha["deslocamento"]) * 3.28084 / CASA_PES) * CASA_PES
    ficha["pv_atuais"] = ficha["pv_maximo"]
    ficha["pv_temporarios"] = 0
    ficha["xp"] = 0
    ficha["ouro_po"] = 0
    return ficha


def criar_ficha_feiticeiro(nome: str = "Vaelis", *, id_ficha: str = "feiticeiro-1") -> dict[str, Any]:
    """Ficha de Feiticeiro nível 1 validada pelo criador, com Feitiçaria Inata e magias arcanas."""
    payload = {
        "name": nome,
        "class": "feiticeiro",
        "species": "anao",
        "background": "eremita",
        "ravenloft": False,
        "ability_method": "standard_array",
        "ability_scores": {
            "forca": 8,
            "destreza": 14,
            "constituicao": 13,
            "inteligencia": 12,
            "sabedoria": 10,
            "carisma": 15,
        },
        "background_increases": {"carisma": 2, "constituicao": 1},
        "background_equipment": "A",
        "class_skills": ["arcanismo", "persuasao"],
        "spells": {
            "cantrips": ["Raio de Fogo", "Raio de Gelo", "Toque Chocante", "Luz"],
            "selected": ["Mísseis Mágicos", "Armadura Arcana"],
            "spellbook": [],
        },
        "narrative": {"pronouns": "ele/dele", "appearance": "Manto carmesim e fagulhas de magia inata."},
    }
    previa = CharacterCreatorService().preview(payload)
    if not previa.get("ready"):
        raise ValueError(f"Ficha de Feiticeiro incompleta: {previa.get('missing')}")
    ficha = dict(previa["character"])
    ficha["id"] = id_ficha
    ficha["arma_padrao"] = "Adaga"
    ficha["conjuracao"] = _conjuracao_validada(previa)
    ficha["deslocamento_pes"] = round(float(ficha["deslocamento"]) * 3.28084 / CASA_PES) * CASA_PES
    ficha["pv_atuais"] = ficha["pv_maximo"]
    ficha["pv_temporarios"] = 0
    ficha["xp"] = 0
    ficha["ouro_po"] = 0
    return ficha


def criar_ficha_bruxo(nome: str = "Malakor", *, id_ficha: str = "bruxo-1") -> dict[str, Any]:
    """Ficha de Bruxo nível 1 validada pelo criador, com Raio Místico, Magia de Pacto e Invocação."""
    payload = {
        "name": nome,
        "class": "bruxo",
        "species": "anao",
        "background": "eremita",
        "ravenloft": False,
        "ability_method": "standard_array",
        "ability_scores": {
            "forca": 8,
            "destreza": 14,
            "constituicao": 13,
            "inteligencia": 12,
            "sabedoria": 10,
            "carisma": 15,
        },
        "background_increases": {"carisma": 2, "constituicao": 1},
        "background_equipment": "A",
        "class_skills": ["arcanismo", "enganacao"],
        "class_choices": {"invocacoes_misticas": "armadura_de_sombras"},
        "spells": {
            "cantrips": ["Raio Místico", "Ilusão Menor"],
            "selected": ["Armadura de Agathys", "Raio de Bruxa"],
            "spellbook": [],
        },
        "narrative": {"pronouns": "ele/dele", "appearance": "Tomo oculto e energia mística violeta."},
    }
    previa = CharacterCreatorService().preview(payload)
    if not previa.get("ready"):
        raise ValueError(f"Ficha de Bruxo incompleta: {previa.get('missing')}")
    ficha = dict(previa["character"])
    ficha["id"] = id_ficha
    ficha["arma_padrao"] = "Adaga"
    ficha["invocacao_mistica"] = "armadura_de_sombras"
    ficha["conjuracao"] = _conjuracao_validada(previa)
    ficha["deslocamento_pes"] = round(float(ficha["deslocamento"]) * 3.28084 / CASA_PES) * CASA_PES
    ficha["pv_atuais"] = ficha["pv_maximo"]
    ficha["pv_temporarios"] = 0
    ficha["xp"] = 0
    ficha["ouro_po"] = 0
    return ficha


def aplicar_especie_em_ficha(
    orquestrador: OrquestradorAcoes,
    ficha: dict[str, Any],
    especie: str,
) -> dict[str, Any]:
    """Resolve e aplica os traços da espécie PHB 2024 à ficha pelo Rule Engine."""
    chave = str(especie or "").strip().lower()
    if chave not in CATALOGO_ESPECIES:
        raise ValueError(f"Espécie não suportada no encontro: {especie}")
    nivel = max(1, int(ficha.get("nivel", 1)))
    mod_con = int((ficha.get("modificadores") or {}).get("constituicao", 0))
    bonus_prof = int(ficha.get("bonus_proficiencia", 2))
    escolhas = dict(CATALOGO_ESPECIES[chave]["escolhas_padrao"])
    fatos_esp = {
        "type": "species_traits",
        "especie": chave,
        "nivel": nivel,
        "bonus_proficiencia": bonus_prof,
        "modificador_constituicao": mod_con,
        **escolhas,
    }
    res = orquestrador.executar(Acao.de_ferramenta("resolver_regra", {"fatos": fatos_esp}), [ficha]).dados
    if res.get("resultado") != "resolvido":
        raise ValueError(f"Traços da espécie {especie} não resolvidos pelo motor")

    ficha["especie"] = chave
    ficha["especie_nome"] = str(res["nome"])
    ficha["especie_aplicada"] = True
    ficha["tracos_especie"] = [str(t["nome"]) for t in (res.get("tracos") or [])]

    deslocamento_m = float(res.get("deslocamento_m", 9))
    ficha["deslocamento"] = deslocamento_m
    ficha["deslocamento_pes"] = round(deslocamento_m * 3.28084 / CASA_PES) * CASA_PES

    resistencias_esp = [str(r) for r in (res.get("resistencias_dano") or [])]
    ficha["resistencias_especie"] = list(resistencias_esp)
    atuais_res = [
        r for r in (ficha.get("resistencias_dano") or []) if r in {"contundente", "cortante", "perfurante"}
    ]
    ficha["resistencias_dano"] = list(dict.fromkeys([*atuais_res, *resistencias_esp]))
    ficha["vantagens_salvaguarda"] = [str(v) for v in (res.get("vantagens_salvaguarda") or [])]

    pv_por_nivel = int(res.get("pv_bonus_por_nivel", 0))
    if chave == "humano":
        pv_por_nivel = max(pv_por_nivel, 2)
    antigo_bonus_pv = int(ficha.get("pv_bonus_especie_aplicado", 0))
    novo_bonus_pv = pv_por_nivel * nivel
    delta_pv = novo_bonus_pv - antigo_bonus_pv
    if delta_pv != 0:
        ficha["pv_maximo"] = max(1, int(ficha["pv_maximo"]) + delta_pv)
        ficha["pv_atuais"] = max(1, min(int(ficha["pv_maximo"]), int(ficha["pv_atuais"]) + delta_pv))
    ficha["pv_bonus_especie_por_nivel"] = pv_por_nivel
    ficha["pv_bonus_especie_aplicado"] = novo_bonus_pv

    # Limpa chaves de outras espécies caso a espécie seja trocada
    for chave_antiga in (
        "inspiracao_heroica",
        "heranca_draconica",
        "usos_maximos_sopro_draconico",
        "usos_sopro_draconico",
        "ancestralidade_gigante",
        "usos_maximos_ancestralidade_gigante",
        "usos_ancestralidade_gigante",
        "vigor_implacavel_disponivel",
        "sorte_halfling",
        "revelacao_celestial",
    ):
        ficha.pop(chave_antiga, None)

    if chave == "humano":
        ficha["inspiracao_heroica"] = True
        ficha["vantagem_proximo_ataque"] = True
    elif chave == "draconato":
        ficha["heranca_draconica"] = "vermelho"
        ficha["usos_maximos_sopro_draconico"] = bonus_prof
        ficha["usos_sopro_draconico"] = bonus_prof
    elif chave == "golias":
        ficha["ancestralidade_gigante"] = "queimadura_de_fogo"
        ficha["usos_maximos_ancestralidade_gigante"] = bonus_prof
        ficha["usos_ancestralidade_gigante"] = bonus_prof
    elif chave == "orc":
        ficha["vigor_implacavel_disponivel"] = True
        ficha["pv_temporarios"] = max(int(ficha.get("pv_temporarios", 0)), bonus_prof)
    elif chave == "halfling":
        ficha["sorte_halfling"] = True
    elif chave in {"elfo", "tiefling"}:
        conj = ficha.setdefault(
            "conjuracao",
            {
                "truques": [],
                "magias_preparadas": [],
                "espacos_totais": {"1": 0},
                "espacos_restantes": {"1": 0},
            },
        )
        if "Raio de Fogo" not in conj["truques"]:
            conj["truques"].append("Raio de Fogo")
        if not conj.get("atributo_conjuracao") and ficha.get("classe") in {"guerreiro", "barbaro", "ladino", "monge"}:
            mods = ficha.get("modificadores") or {}
            conj["atributo_conjuracao"] = max(
                ("inteligencia", "sabedoria", "carisma"),
                key=lambda atr: int(mods.get(atr, 0)),
            )
    elif chave == "aasimar":
        ficha["revelacao_celestial"] = "transfiguracao_radiante"

    return ficha


def criar_ficha_personagem(
    classe: str = "bardo",
    nome: str | None = None,
    especie: str | None = None,
) -> dict[str, Any]:
    """Cria a ficha validada da classe escolhida para o encontro (opcionalmente com espécie PHB 2024)."""
    chave = str(classe or "bardo").strip().lower()
    if chave == "bardo":
        ficha = criar_ficha_bardo(nome=nome or CATALOGO_CLASSES["bardo"]["nome_personagem_padrao"])
    elif chave == "monge":
        ficha = criar_ficha_monge(nome=nome or CATALOGO_CLASSES["monge"]["nome_personagem_padrao"])
    elif chave == "guerreiro":
        ficha = criar_ficha_guerreiro(nome=nome or CATALOGO_CLASSES["guerreiro"]["nome_personagem_padrao"])
    elif chave == "barbaro":
        ficha = criar_ficha_barbaro(nome=nome or CATALOGO_CLASSES["barbaro"]["nome_personagem_padrao"])
    elif chave == "ladino":
        ficha = criar_ficha_ladino(nome=nome or CATALOGO_CLASSES["ladino"]["nome_personagem_padrao"])
    elif chave == "clerigo":
        ficha = criar_ficha_clerigo(nome=nome or CATALOGO_CLASSES["clerigo"]["nome_personagem_padrao"])
    elif chave == "mago":
        ficha = criar_ficha_mago(nome=nome or CATALOGO_CLASSES["mago"]["nome_personagem_padrao"])
    elif chave == "paladino":
        ficha = criar_ficha_paladino(nome=nome or CATALOGO_CLASSES["paladino"]["nome_personagem_padrao"])
    elif chave == "druida":
        ficha = criar_ficha_druida(nome=nome or CATALOGO_CLASSES["druida"]["nome_personagem_padrao"])
    elif chave == "artifice":
        ficha = criar_ficha_artifice(nome=nome or CATALOGO_CLASSES["artifice"]["nome_personagem_padrao"])
    elif chave == "guardiao":
        ficha = criar_ficha_guardiao(nome=nome or CATALOGO_CLASSES["guardiao"]["nome_personagem_padrao"])
    elif chave == "feiticeiro":
        ficha = criar_ficha_feiticeiro(nome=nome or CATALOGO_CLASSES["feiticeiro"]["nome_personagem_padrao"])
    elif chave == "bruxo":
        ficha = criar_ficha_bruxo(nome=nome or CATALOGO_CLASSES["bruxo"]["nome_personagem_padrao"])
    else:
        raise ValueError(f"Classe não suportada no encontro: {classe}")
    if especie is not None:
        from rule_engine import build_default_engine

        aplicar_especie_em_ficha(OrquestradorAcoes(build_default_engine()), ficha, especie)
    return ficha


def _conjuracao_validada(previa: dict[str, Any]) -> dict[str, Any]:
    """Converte as escolhas de magia já validadas pelo criador na conjuração da ficha.

    O criador valida truques, magias e espaços, mas não os grava na ficha; esta
    função faz essa ponte sem acrescentar nenhuma magia.
    """
    detalhes = previa["validation"]["spell_choices"]["details"]
    if "slots" in detalhes:
        slots_val = detalhes["slots"]
        espacos = int(slots_val[0]) if isinstance(slots_val, (list, tuple)) else int(slots_val)
    else:
        espacos_prog = (detalhes.get("progression") or {}).get("espacos_totais") or {}
        espacos = int(espacos_prog.get("1", 0))
    return {
        "truques": list(detalhes["cantrips"]),
        "magias_preparadas": list(detalhes["selected"]),
        "espacos_totais": {"1": espacos},
        "espacos_restantes": {"1": espacos},
    }


def calcular_ca(orquestrador: OrquestradorAcoes, ficha: dict[str, Any]) -> int:
    classe = str(ficha.get("classe", "")).strip().lower()
    efeito_sub = ficha.get("efeito_subclasse") or {}
    bonus_sub_ca = int(efeito_sub.get("bonus_ca", 0))
    bonus_escudo_da_fe = 0
    if ficha.get("escudo_da_fe_ativo"):
        mec_ef = mecanica_de_magia("Escudo da Fé", nivel_personagem=int(ficha.get("nivel", 1))) or {}
        bonus_escudo_da_fe = int(mec_ef.get("bonus_ca", 2))
    bonus_extra = bonus_escudo_da_fe + bonus_sub_ca

    if classe in {"monge", "barbaro"}:
        fatos_sem_armadura = {
            "type": "class_feature",
            "recurso": "defesa_sem_armadura",
            "character_id": ficha["id"],
        }
        resultado = orquestrador.executar(Acao.de_ferramenta("resolver_regra", {"fatos": fatos_sem_armadura}), [ficha])
        if resultado.dados.get("resultado") != "resolvido":
            raise ValueError(f"CA de {classe} não calculada: {resultado.dados.get('motivo')}")
        return int(resultado.dados["ca"]) + bonus_extra

    if classe in {"mago", "feiticeiro"}:
        if ficha.get("armadura_arcana_ativa") or efeito_sub.get("ca_base"):
            mec_aa = mecanica_de_magia("Armadura Arcana", nivel_personagem=int(ficha.get("nivel", 1))) or {}
            base_aa = int(mec_aa.get("ca_base", 13)) if ficha.get("armadura_arcana_ativa") else 10
            base_sub = int(efeito_sub.get("ca_base", 10))
            ca_base = max(base_aa, base_sub) + int(ficha["modificadores"]["destreza"])
            return ca_base + bonus_extra
        fatos_mago = {
            "type": "armor_class",
            "armor": "nenhuma",
            "dexterity_modifier": ficha["modificadores"]["destreza"],
            "shield": False,
            "armor_proficient": True,
        }
        resultado = orquestrador.executar(Acao.de_ferramenta("resolver_regra", {"fatos": fatos_mago}), [])
        if resultado.dados.get("resultado") != "calculada":
            raise ValueError(f"CA de {classe} não calculada: {resultado.dados.get('motivo')}")
        return int(resultado.dados["ca"]) + bonus_extra

    if classe in {"clerigo", "artifice"}:
        fatos_clerigo = {
            "type": "armor_class",
            "armor": "media",
            "armor_bonus": CATALOGO_ARMADURAS["Cota de Malha Parcial"]["ca"] - 10,
            "dexterity_modifier": ficha["modificadores"]["destreza"],
            "shield": True,
            "armor_proficient": True,
        }
        resultado = orquestrador.executar(Acao.de_ferramenta("resolver_regra", {"fatos": fatos_clerigo}), [])
        if resultado.dados.get("resultado") != "calculada":
            raise ValueError(f"CA de {classe} não calculada: {resultado.dados.get('motivo')}")
        return int(resultado.dados["ca"]) + bonus_extra

    if classe == "guardiao":
        fatos_guardiao = {
            "type": "armor_class",
            "armor": "media",
            "armor_bonus": CATALOGO_ARMADURAS["Cota de Malha Parcial"]["ca"] - 10,
            "dexterity_modifier": ficha["modificadores"]["destreza"],
            "shield": False,
            "armor_proficient": True,
        }
        resultado = orquestrador.executar(Acao.de_ferramenta("resolver_regra", {"fatos": fatos_guardiao}), [])
        if resultado.dados.get("resultado") != "calculada":
            raise ValueError(f"CA de Guardião não calculada: {resultado.dados.get('motivo')}")
        return int(resultado.dados["ca"]) + bonus_extra

    if classe == "bruxo" and (
        ficha.get("armadura_arcana_ativa")
        or ficha.get("armadura_de_sombras_ativa")
        or ficha.get("invocacao_mistica") == "armadura_de_sombras"
    ):
        mec_aa = mecanica_de_magia("Armadura Arcana", nivel_personagem=int(ficha.get("nivel", 1))) or {}
        ca_base = int(mec_aa.get("ca_base", 13)) + int(ficha["modificadores"]["destreza"])
        return ca_base + bonus_extra

    if classe == "druida":
        fatos_druida = {
            "type": "armor_class",
            "armor": "leve",
            "armor_bonus": CATALOGO_ARMADURAS["Couro"]["ca"] - 10,
            "dexterity_modifier": ficha["modificadores"]["destreza"],
            "shield": True,
            "armor_proficient": True,
        }
        resultado = orquestrador.executar(Acao.de_ferramenta("resolver_regra", {"fatos": fatos_druida}), [])
        if resultado.dados.get("resultado") != "calculada":
            raise ValueError(f"CA de Druida não calculada: {resultado.dados.get('motivo')}")
        return int(resultado.dados["ca"]) + bonus_extra

    if classe in {"guerreiro", "paladino"}:
        fatos_pesada = {
            "type": "armor_class",
            "armor": "pesada",
            "armor_bonus": CATALOGO_ARMADURAS["Cota de Malha"]["ca"] - 10,
            "dexterity_modifier": ficha["modificadores"]["destreza"],
            "shield": True,
            "armor_proficient": True,
        }
        resultado = orquestrador.executar(Acao.de_ferramenta("resolver_regra", {"fatos": fatos_pesada}), [])
        if resultado.dados.get("resultado") != "calculada":
            raise ValueError(f"CA de {classe} não calculada: {resultado.dados.get('motivo')}")
        ca_base = int(resultado.dados["ca"])
        estilo = ficha.get("estilo_de_luta")
        if estilo:
            res_estilo = orquestrador.executar(
                Acao.de_ferramenta(
                    "resolver_regra",
                    {
                        "fatos": {
                            "type": "class_feature",
                            "recurso": "estilo_de_luta",
                            "character_id": ficha["id"],
                            "talento": str(estilo),
                        }
                    },
                ),
                [ficha],
            )
            if res_estilo.dados.get("resultado") == "resolvido":
                ca_base += int(res_estilo.dados.get("ca", 0))
        return ca_base + bonus_extra

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
    return int(resultado.dados["ca"]) + bonus_extra


class Encontro:
    def __init__(
        self,
        orquestrador: OrquestradorAcoes,
        mapa_id: str,
        ficha: dict[str, Any],
        perfis_inimigos: list[tuple[str, str, tuple[int, int]]] | None = None,
        *,
        seed_base: int = 1,
    ) -> None:
        """``perfis_inimigos``: lista de (id_do_combatente, perfil, (x, y)).

        A ficha precisa ter ``ca`` (use :func:`calcular_ca`).
        """
        self.orquestrador = orquestrador
        self.ficha = ficha
        self.ficha.setdefault("xp", 0)
        self.ficha.setdefault("ouro_po", 0)
        self.deslocamento_pes = int(ficha.get("deslocamento_pes", 30))
        self._seed = seed_base
        self.log: list[dict[str, Any]] = []
        self._iniciar_sala(mapa_id, perfis_inimigos)

    def _iniciar_sala(
        self,
        mapa_id: str,
        perfis_inimigos: list[tuple[str, str, tuple[int, int]]] | None = None,
    ) -> None:
        chave = normalizar_mapa_id(mapa_id)
        self.mapa_id = chave
        self.mapa = carregar_mapa(chave)
        self.board = tabuleiro_do_mapa(self.mapa)
        padrao = SALAS_PADRAO.get(chave, {})
        self.andar = int(self.mapa.get("andar", padrao.get("andar", 1)))
        self.sala_numero = int(self.mapa.get("sala", padrao.get("sala", 1)))
        self.proxima_sala = self.mapa.get("proxima_sala", padrao.get("proxima_sala"))
        self.recompensa: dict[str, int] | None = None
        self.subida_nivel: dict[str, Any] | None = None
        self.descanso_curto_usado = False
        self.movimento_usado_pes = 0
        self.acao_principal_usada = False
        self.acao_bonus_usada = False
        self.ataque_furtivo_usado = False
        self.frenesi_usado = False
        self.matador_colossos_usado = False
        self.trespassar_usado = False
        nivel_ficha = max(1, int(self.ficha.get("nivel", 1)))
        self.ficha.setdefault("dados_vida_maximos", nivel_ficha)
        self.ficha.setdefault("dados_vida_disponiveis", int(self.ficha["dados_vida_maximos"]))
        classe_ficha = str(self.ficha.get("classe", "")).strip().lower()
        if classe_ficha == "guerreiro" and "usos_recuperar_folego" not in self.ficha:
            rec = self._executar(
                {
                    "type": "martial_feature",
                    "feature": "recuperar_folego",
                    "character_id": self.ficha["id"],
                    "acao": "recuperar",
                },
                [self.ficha],
            ).dados
            usos = int(rec.get("usos", 2))
            self.ficha["usos_maximos_recuperar_folego"] = usos
            self.ficha["usos_recuperar_folego"] = usos
            maestria = self._executar(
                {
                    "type": "class_feature",
                    "recurso": "maestria_em_arma",
                    "character_id": self.ficha["id"],
                    "armas": list(self.ficha.get("maestrias_arma", ["Espada Longa", "Arco Curto", "Machado de Batalha"])),
                },
                [self.ficha],
            ).dados
            if maestria.get("resultado") == "resolvido":
                self.ficha["maestrias_arma"] = list(maestria.get("armas", []))
        if classe_ficha == "barbaro" and "usos_furia" not in self.ficha:
            furia = self._executar(
                {
                    "type": "martial_feature",
                    "feature": "furia",
                    "character_id": self.ficha["id"],
                    "acao": "ativar",
                },
                [self.ficha],
            ).dados
            usos_furia = int(furia.get("usos_maximos", 2))
            self.ficha["usos_maximos_furia"] = usos_furia
            self.ficha["usos_furia"] = usos_furia
            self.ficha.setdefault("furia_ativa", False)
            maestria_b = self._executar(
                {
                    "type": "class_feature",
                    "recurso": "maestria_em_arma",
                    "character_id": self.ficha["id"],
                    "armas": list(self.ficha.get("maestrias_arma", ["Machado Grande", "Machadinha"])),
                },
                [self.ficha],
            ).dados
            if maestria_b.get("resultado") == "resolvido":
                self.ficha["maestrias_arma"] = list(maestria_b.get("armas", []))
        if classe_ficha == "ladino" and "maestrias_validadas" not in self.ficha:
            maestria_l = self._executar(
                {
                    "type": "class_feature",
                    "recurso": "maestria_em_arma",
                    "character_id": self.ficha["id"],
                    "armas": list(self.ficha.get("maestrias_arma", ["Rapieira", "Arco Curto"])),
                },
                [self.ficha],
            ).dados
            if maestria_l.get("resultado") == "resolvido":
                self.ficha["maestrias_arma"] = list(maestria_l.get("armas", []))
                self.ficha["maestrias_validadas"] = True
        if classe_ficha == "mago" and "usos_recuperacao_arcana" not in self.ficha:
            rec_arcana = self._executar(
                {
                    "type": "class_feature",
                    "recurso": "recuperacao_arcana",
                    "character_id": self.ficha["id"],
                },
                [self.ficha],
            ).dados
            usos_arcana = 1 if rec_arcana.get("resultado") == "recuperado" else 0
            self.ficha["usos_maximos_recuperacao_arcana"] = usos_arcana
            self.ficha["usos_recuperacao_arcana"] = usos_arcana
        if classe_ficha == "paladino" and "pool_maos_consagradas" not in self.ficha:
            maos = self._executar(
                {
                    "type": "class_feature",
                    "recurso": "maos_consagradas",
                    "character_id": self.ficha["id"],
                    "pontos": 0,
                },
                [self.ficha],
            ).dados
            pool_max = int(maos.get("pool_maximo", 5))
            self.ficha["pool_maximo_maos_consagradas"] = pool_max
            self.ficha["pool_maos_consagradas"] = pool_max
            maestria_p = self._executar(
                {
                    "type": "class_feature",
                    "recurso": "maestria_em_arma",
                    "character_id": self.ficha["id"],
                    "armas": list(self.ficha.get("maestrias_arma", ["Espada Longa", "Martelo de Guerra"])),
                },
                [self.ficha],
            ).dados
            if maestria_p.get("resultado") == "resolvido":
                self.ficha["maestrias_arma"] = list(maestria_p.get("armas", []))
        if classe_ficha == "artifice" and "foco_conjuracao" not in self.ficha:
            magia_art = self._executar(
                {
                    "type": "class_feature",
                    "recurso": "magia_de_artifice",
                    "character_id": self.ficha["id"],
                },
                [self.ficha],
            ).dados
            if magia_art.get("resultado") == "resolvido":
                self.ficha["foco_conjuracao"] = str(magia_art.get("foco", "ferramentas_de_artifice"))
        if classe_ficha == "guardiao":
            self.ficha.pop("alvo_marca_do_predador", None)
            if "usos_inimigo_favorito" not in self.ficha:
                inimigo_fav = self._executar(
                    {
                        "type": "class_feature",
                        "recurso": "inimigo_favorito",
                        "character_id": self.ficha["id"],
                    },
                    [self.ficha],
                ).dados
                usos_fav = int(inimigo_fav.get("usos", 2))
                self.ficha["usos_maximos_inimigo_favorito"] = usos_fav
                self.ficha["usos_inimigo_favorito"] = usos_fav
                maestria_g = self._executar(
                    {
                        "type": "class_feature",
                        "recurso": "maestria_em_arma",
                        "character_id": self.ficha["id"],
                        "armas": list(self.ficha.get("maestrias_arma", ["Espada Curta", "Arco Longo"])),
                    },
                    [self.ficha],
                ).dados
                if maestria_g.get("resultado") == "resolvido":
                    self.ficha["maestrias_arma"] = list(maestria_g.get("armas", []))
        if classe_ficha == "feiticeiro" and "usos_feiticaria_inata" not in self.ficha:
            inata = self._executar(
                {
                    "type": "class_feature",
                    "recurso": "feiticaria_inata",
                    "character_id": self.ficha["id"],
                },
                [self.ficha],
            ).dados
            usos_inata = int(inata.get("usos", 2))
            self.ficha["usos_maximos_feiticaria_inata"] = usos_inata
            self.ficha["usos_feiticaria_inata"] = usos_inata
            self.ficha.setdefault("feiticaria_inata_ativa", False)
        if classe_ficha == "bruxo" and "armadura_de_sombras_ativa" not in self.ficha:
            inv_chave = str(self.ficha.get("invocacao_mistica", "armadura_de_sombras"))
            inv_res = self._executar(
                {
                    "type": "class_feature",
                    "recurso": "invocacoes_misticas",
                    "character_id": self.ficha["id"],
                    "invocacao": inv_chave,
                    "invocacoes_escolhidas": [],
                },
                [self.ficha],
            ).dados
            if inv_res.get("efeito") == "armadura_arcana_sem_espaco":
                self.ficha["armadura_de_sombras_ativa"] = True
                self.ficha["ca"] = calcular_ca(self.orquestrador, self.ficha)
        if int(self.ficha.get("nivel", 1)) >= 3 and "efeito_subclasse" not in self.ficha:
            self._aplicar_subclasse_nivel_3()
        if (self.ficha.get("efeito_subclasse") or {}).get("vantagem"):
            self.ficha["assassinar_disponivel"] = True
        self.revelacao_celestial_usada = False
        self.deslocamento_pes = int(self.ficha.get("deslocamento_pes", 30))
        if self.ficha.get("especie_aplicada"):
            esp_chave = str(self.ficha.get("especie", "")).strip().lower()
            if esp_chave == "orc":
                self.ficha["pv_temporarios"] = max(
                    int(self.ficha.get("pv_temporarios", 0)),
                    int(self.ficha.get("bonus_proficiencia", 2)),
                )
            elif esp_chave == "humano":
                self.ficha["inspiracao_heroica"] = True
                self.ficha["vantagem_proximo_ataque"] = True
            res_esp = list(self.ficha.get("resistencias_especie") or [])
            if res_esp:
                atuais = list(self.ficha.get("resistencias_dano") or [])
                self.ficha["resistencias_dano"] = list(dict.fromkeys([*atuais, *res_esp]))

        lista_inimigos = perfis_inimigos if perfis_inimigos is not None else inimigos_padrao_do_mapa(chave)
        self.posicoes: dict[str, BoardPosition] = {self.ficha["id"]: BoardPosition(*self._entrada_jogador())}
        self.inimigos: dict[str, dict[str, Any]] = {}
        for cid, perfil, (x, y) in lista_inimigos:
            stats = carregar_inimigo(perfil)
            alcance_maximo = max(acao["alcance_pes"]["maximo"] for acao in stats["acoes"].values())
            self.inimigos[cid] = {
                "perfil": perfil,
                "nome": stats["nome"],
                "monstro": stats["monstro"],
                "ca": stats["ca"],
                "pv_maximo": stats["pv"],
                "pv_atuais": stats["pv"],
                "pv_temporarios": 0,
                "alcance_maximo": alcance_maximo,
                "deslocamento_pes": stats["deslocamento_pes"],
            }
            self.posicoes[cid] = BoardPosition(x, y)
        self.inimigos_derrotados: set[str] = set()

        ordem = self._rolar_iniciativas()
        self.session = CombatSession(
            self.board,
            [
                Combatant(id=cid, position=self.posicoes[cid], initiative=total, is_player=cid == self.ficha["id"])
                for cid, total in ordem
            ],
        )

    def to_state(self) -> dict[str, Any]:
        """Exporta somente o estado mutável necessário para retomar o encontro."""
        efeitos_mutaveis = (
            "desvantagem_proximo_ataque",
            "comando_pendente",
            "caido",
            "condicoes",
            "reducao_deslocamento_pes",
        )
        return {
            "versao": 1,
            "mapa_id": self.mapa_id,
            "andar": self.andar,
            "sala": self.sala_numero,
            "proxima_sala": self.proxima_sala,
            "recompensa": self.recompensa,
            "subida_nivel": self.subida_nivel,
            "descanso_curto_usado": self.descanso_curto_usado,
            "ficha": self.ficha,
            "deslocamento_pes": self.deslocamento_pes,
            "movimento_usado_pes": self.movimento_usado_pes,
            "acao_principal_usada": self.acao_principal_usada,
            "acao_bonus_usada": self.acao_bonus_usada,
            "ataque_furtivo_usado": self.ataque_furtivo_usado,
            "frenesi_usado": getattr(self, "frenesi_usado", False),
            "matador_colossos_usado": getattr(self, "matador_colossos_usado", False),
            "trespassar_usado": getattr(self, "trespassar_usado", False),
            "revelacao_celestial_usada": getattr(self, "revelacao_celestial_usada", False),
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
        encontro.mapa_id = normalizar_mapa_id(str(state["mapa_id"]))
        encontro.mapa = carregar_mapa(encontro.mapa_id)
        encontro.board = tabuleiro_do_mapa(encontro.mapa)
        padrao = SALAS_PADRAO.get(encontro.mapa_id, {})
        encontro.andar = int(state.get("andar", encontro.mapa.get("andar", padrao.get("andar", 1))))
        encontro.sala_numero = int(state.get("sala", encontro.mapa.get("sala", padrao.get("sala", 1))))
        encontro.proxima_sala = state.get(
            "proxima_sala", encontro.mapa.get("proxima_sala", padrao.get("proxima_sala"))
        )
        recompensa = state.get("recompensa")
        encontro.recompensa = dict(recompensa) if isinstance(recompensa, dict) else None
        subida = state.get("subida_nivel")
        encontro.subida_nivel = dict(subida) if isinstance(subida, dict) else None
        encontro.descanso_curto_usado = bool(state.get("descanso_curto_usado", False))
        encontro.ficha = dict(state["ficha"])
        encontro.ficha.setdefault("xp", 0)
        encontro.ficha.setdefault("ouro_po", 0)
        nivel_ficha = max(1, int(encontro.ficha.get("nivel", 1)))
        encontro.ficha.setdefault("dados_vida_maximos", nivel_ficha)
        encontro.ficha.setdefault("dados_vida_disponiveis", int(encontro.ficha["dados_vida_maximos"]))
        encontro.deslocamento_pes = int(state["deslocamento_pes"])
        encontro.movimento_usado_pes = int(state["movimento_usado_pes"])
        encontro.acao_principal_usada = bool(state["acao_principal_usada"])
        encontro.acao_bonus_usada = bool(state.get("acao_bonus_usada", False))
        encontro.ataque_furtivo_usado = bool(state.get("ataque_furtivo_usado", False))
        encontro.frenesi_usado = bool(state.get("frenesi_usado", False))
        encontro.matador_colossos_usado = bool(state.get("matador_colossos_usado", False))
        encontro.trespassar_usado = bool(state.get("trespassar_usado", False))
        encontro.revelacao_celestial_usada = bool(state.get("revelacao_celestial_usada", False))
        encontro._seed = int(state["semente"])
        encontro.log = list(state["log"])

        encontro.posicoes = {
            cid: BoardPosition(int(posicao[0]), int(posicao[1]))
            for cid, posicao in state["posicoes"].items()
        }
        encontro.inimigos = {}
        for cid, salvo in state["inimigos"].items():
            stats = carregar_inimigo(str(salvo["perfil"]))
            alcance_maximo = max(acao["alcance_pes"]["maximo"] for acao in stats["acoes"].values())
            inimigo = {
                "perfil": stats["perfil"],
                "nome": stats["nome"],
                "monstro": stats["monstro"],
                "ca": stats["ca"],
                "pv_maximo": stats["pv"],
                "pv_atuais": int(salvo["pv_atuais"]),
                "pv_temporarios": int(salvo["pv_temporarios"]),
                "alcance_maximo": alcance_maximo,
                "deslocamento_pes": stats["deslocamento_pes"],
            }
            for chave in (
                "desvantagem_proximo_ataque",
                "comando_pendente",
                "caido",
                "condicoes",
                "reducao_deslocamento_pes",
            ):
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

    def tem_linha_de_visao(self, origem: str, destino: str) -> bool:
        """Consulta o tabuleiro e valida a linha de visão pelo resolvedor canônico do motor."""
        bloqueada = not self.board.has_line_of_sight(self.posicoes[origem], self.posicoes[destino])
        visao = self._executar({"type": "line_of_sight", "blocked": bloqueada}, []).dados
        return visao.get("resultado") == "livre"

    def alvos_ao_alcance(self, ator: str, alcance: int, *, exigir_visao: bool = True) -> list[str]:
        return [
            cid
            for cid in self._alvos_vivos(ator)
            if self.distancia_pes(ator, cid) <= alcance and (not exigir_visao or self.tem_linha_de_visao(ator, cid))
        ]

    def _alvos_vivos(self, ator: str) -> list[str]:
        if ator == self.ficha["id"]:
            return [cid for cid in self.inimigos if cid not in self.inimigos_derrotados]
        return [self.ficha["id"]] if self.ficha["pv_atuais"] > 0 else []

    def _condicoes_combatente(self, cid: str) -> list[str]:
        if cid == self.ficha["id"]:
            condicoes = list(self.ficha.get("condicoes") or [])
            if self.ficha.get("caido") and "caido" not in condicoes:
                condicoes.append("caido")
            return condicoes
        inimigo = self.inimigos[cid]
        condicoes = list(inimigo.get("condicoes") or [])
        if inimigo.get("caido") and "caido" not in condicoes:
            condicoes.append("caido")
        return condicoes

    def _aplicar_condicao_inimigo(self, cid: str, condicao: str) -> dict[str, Any]:
        inimigo = self.inimigos[cid]
        bloco = consultar_monstro(inimigo["monstro"]) or {}
        estado = EstadoCondicoes(
            ativas=set(self._condicoes_combatente(cid)),
            imunidades=set(bloco.get("imunidades_condicao") or ()),
        )
        res = self._executar(
            {"type": "condition_state", "operation": "apply", "condition": condicao, "estado": estado}, []
        ).dados
        if estado.ativas:
            inimigo["condicoes"] = sorted(estado.ativas)
        else:
            inimigo.pop("condicoes", None)
        if "caido" in estado.ativas:
            inimigo["caido"] = True
        else:
            inimigo.pop("caido", None)
        return res

    def _remover_condicao_inimigo(self, cid: str, condicao: str) -> dict[str, Any]:
        inimigo = self.inimigos[cid]
        estado = EstadoCondicoes(ativas=set(self._condicoes_combatente(cid)))
        res = self._executar(
            {"type": "condition_state", "operation": "remove", "condition": condicao, "estado": estado}, []
        ).dados
        if estado.ativas:
            inimigo["condicoes"] = sorted(estado.ativas)
        else:
            inimigo.pop("condicoes", None)
        if "caido" in estado.ativas:
            inimigo["caido"] = True
        else:
            inimigo.pop("caido", None)
        return res

    def _aplicar_condicao_jogador(self, condicao: str) -> dict[str, Any]:
        estado = EstadoCondicoes(
            ativas=set(self._condicoes_combatente(self.ficha["id"])),
            imunidades=set(self.ficha.get("imunidades_condicao") or ()),
        )
        res = self._executar(
            {"type": "condition_state", "operation": "apply", "condition": condicao, "estado": estado}, []
        ).dados
        if estado.ativas:
            self.ficha["condicoes"] = sorted(estado.ativas)
        else:
            self.ficha.pop("condicoes", None)
        if "caido" in estado.ativas:
            self.ficha["caido"] = True
        else:
            self.ficha.pop("caido", None)
        return res

    def _remover_condicao_jogador(self, condicao: str) -> dict[str, Any]:
        estado = EstadoCondicoes(ativas=set(self._condicoes_combatente(self.ficha["id"])))
        res = self._executar(
            {"type": "condition_state", "operation": "remove", "condition": condicao, "estado": estado}, []
        ).dados
        if estado.ativas:
            self.ficha["condicoes"] = sorted(estado.ativas)
        else:
            self.ficha.pop("condicoes", None)
        if "caido" in estado.ativas:
            self.ficha["caido"] = True
        else:
            self.ficha.pop("caido", None)
        return res

    def _salvaguarda_jogador(self, atributo: str, cd: int) -> dict[str, Any]:
        """Salvaguarda do personagem no atributo indicado, resolvida pelo motor com a ficha."""
        fatos_salv: dict[str, Any] = {
            "type": "saving_throw",
            "atributo": atributo,
            "character_id": self.ficha["id"],
            "dc": cd,
            "seed": self._proxima_semente(),
        }
        vantagens = set(self.ficha.get("vantagens_salvaguarda") or ())
        if atributo in vantagens:
            fatos_salv["advantage"] = True
        dados = self._executar(fatos_salv, [self.ficha]).dados
        if self.ficha.get("sorte_halfling") and dados.get("roll") == 1:
            fatos_salv["seed"] = self._proxima_semente()
            dados = self._executar(fatos_salv, [self.ficha]).dados
        return dados

    def _verificar_fortitude_morto_vivo(
        self, cid: str, dano: int, tipo_dano: str, *, critico: bool = False
    ) -> bool:
        """Verifica se o inimigo reduzido a 0 PV ativa Fortitude de Morto-Vivo (SRD 5.2.1 Zombie)."""
        inimigo = self.inimigos[cid]
        res = self._executar(
            {
                "type": "bestiary",
                "operacao": "efeito_especial_monstro",
                "nome": inimigo["monstro"],
                "gatilho": "ao_cair_a_zero_pv",
                "dano_causado": int(dano),
                "tipo_dano": str(tipo_dano),
                "critico": bool(critico),
            },
            [],
        ).dados
        if res.get("resultado") != "resolvido" or res.get("efeito") != "fortitude_de_morto_vivo":
            return False
        salv = self._salvaguarda_atributo(
            cid,
            str(res["salvaguarda"]["atributo"]),
            int(res["salvaguarda"]["cd"]),
        )
        if salv.get("result") == "success":
            inimigo["pv_atuais"] = int(res.get("pv_em_sucesso", 1))
            return True
        return False

    def _efeito_condicoes_no_ataque(self, atacante_id: str, alvo_id: str, distancia_pes: int) -> dict[str, Any]:
        """Resolve vantagem/desvantagem por condições ativas (ex.: Caído) pelo Rule Engine."""
        return self._executar(
            {
                "type": "condition_effect",
                "action": "attack",
                "attacker_conditions": self._condicoes_combatente(atacante_id),
                "target_conditions": self._condicoes_combatente(alvo_id),
                "distancia_m": round(distancia_pes * 0.3, 2),
            },
            [],
        ).dados

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
        mecanica = mecanica_de_magia(nome, nivel_personagem=int(self.ficha.get("nivel", 1))) or {}
        acao_magia = str(mecanica.get("acao", "acao"))
        motivo: str | None = None
        usos_fav = int(self.ficha.get("usos_inimigo_favorito", 0)) if nome == "Marca do Predador" else 0
        if circulo > 0 and espacos <= 0 and usos_fav <= 0:
            motivo = "sem espaço de 1º círculo"
        elif nome == "Escudo da Fé" and self.ficha.get("escudo_da_fe_ativo"):
            motivo = "Escudo da Fé já ativo"
        elif nome == "Armadura Arcana" and (
            self.ficha.get("armadura_arcana_ativa") or self.ficha.get("armadura_de_sombras_ativa")
        ):
            motivo = "Armadura Arcana já ativa"
        elif acao_magia == "bonus" and self.acao_bonus_usada:
            motivo = "Ação bônus já usada neste turno"
        return {
            "nome": nome,
            "circulo": circulo,
            "acao": acao_magia,
            "disponivel": motivo is None,
            "motivo": motivo,
            "alvo": ALVO_MAGIA[nome],
        }

    def alvos_magia(self, magia: str | None = None) -> list[str]:
        """Inimigos vivos ao alcance de magia e com linha de visão livre."""
        if magia and magia in ALCANCE_MAGIA_POR_NOME_PES:
            alcance = ALCANCE_MAGIA_POR_NOME_PES[magia]
        elif str(self.ficha.get("classe", "")).strip().lower() in {"mago", "feiticeiro", "bruxo"}:
            alcance = 120
        elif str(self.ficha.get("classe", "")).strip().lower() == "guardiao":
            alcance = 90
        else:
            alcance = ALCANCE_MAGIA_PES
        return self.alvos_ao_alcance(self.ficha["id"], alcance, exigir_visao=True)

    def conjurar(self, magia: str, alvo_id: str | None = None, comando: str | None = None) -> dict[str, Any]:
        """Conjura uma magia do personagem. Só as de efeito resolvido pelo motor são aceitas."""
        ator = self._exigir_turno_do_jogador()
        if magia == "Marca do Caçador":
            magia = "Marca do Predador"
        elif magia == "Rajada Mística":
            magia = "Raio Místico"
        mecanica_magia = mecanica_de_magia(magia, nivel_personagem=int(self.ficha.get("nivel", 1))) or {}
        eh_acao_bonus = str(mecanica_magia.get("acao")) == "bonus"
        if eh_acao_bonus:
            if self.acao_bonus_usada:
                return {"status": "bloqueado", "motivo": "acao_bonus_usada"}
        elif self.acao_principal_usada:
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
        if magia == "Escudo da Fé" and self.ficha.get("escudo_da_fe_ativo"):
            return {"status": "bloqueado", "motivo": "escudo_da_fe_ja_ativo"}
        if magia == "Armadura Arcana" and (
            self.ficha.get("armadura_arcana_ativa") or self.ficha.get("armadura_de_sombras_ativa")
        ):
            return {"status": "bloqueado", "motivo": "armadura_arcana_ja_ativa"}
        alcance_magia = int(ALCANCE_MAGIA_POR_NOME_PES.get(magia, ALCANCE_MAGIA_PES))
        if ALVO_MAGIA[magia] == "si_mesmo":
            if alvo_id not in (None, ator):
                return {"status": "bloqueado", "motivo": "alvo_invalido_toque_em_si_mesmo"}
        else:
            if alvo_id not in self.inimigos or alvo_id in self.inimigos_derrotados:
                return {"status": "bloqueado", "motivo": "alvo_invalido"}
            if self.distancia_pes(ator, alvo_id) > alcance_magia:
                return {"status": "bloqueado", "motivo": "alvo_fora_do_alcance"}
            if not self.tem_linha_de_visao(ator, alvo_id):
                return {"status": "bloqueado", "motivo": "sem_linha_de_visao"}
        if magia == "Comando" and comando not in COMANDOS:
            return {"status": "bloqueado", "motivo": "comando_invalido"}

        # CD antes de gastar espaço: sem CD o efeito não pode ser resolvido.
        cd = cd_de_magia(self.orquestrador.engine, self.ficha) if magia in SALVAGUARDA_EM_COMBATE else None
        if magia in SALVAGUARDA_EM_COMBATE and cd is None:
            return {"status": "bloqueado", "motivo": "cd_magia_ausente"}

        # Inimigo Favorito do Guardião permite conjurar Marca do Predador sem gastar espaço de magia.
        usou_inimigo_favorito = False
        espacos_rest_1_antes = int((conjuracao_ficha.get("espacos_restantes") or {}).get("1", 0))
        espacos_tot_1_antes = int((conjuracao_ficha.get("espacos_totais") or {}).get("1", 0))
        if magia == "Marca do Predador" and int(self.ficha.get("usos_inimigo_favorito", 0)) > 0:
            res_fav = self._executar(
                {"type": "class_feature", "recurso": "inimigo_favorito", "character_id": ator},
                [self.ficha],
            ).dados
            if res_fav.get("resultado") == "ativado":
                usou_inimigo_favorito = True
                conjuracao_ficha.setdefault("espacos_restantes", {})["1"] = espacos_rest_1_antes + 1
                conjuracao_ficha.setdefault("espacos_totais", {})["1"] = max(
                    espacos_tot_1_antes, espacos_rest_1_antes + 1
                )

        # 1) Conjuração: preparo, espaço e círculo são conferidos e o espaço é gasto no orquestrador.
        conjuracao = self._executar(
            {"type": "spell_cast", "magia": magia, "character_id": ator, "seed": self._proxima_semente()},
            [self.ficha],
        )
        if usou_inimigo_favorito:
            conjuracao_ficha["espacos_totais"]["1"] = espacos_tot_1_antes
        if conjuracao.dados.get("resultado") != "conjurada":
            if usou_inimigo_favorito:
                conjuracao_ficha["espacos_restantes"]["1"] = espacos_rest_1_antes
            return {"status": "bloqueado", "motivo": conjuracao.motivo or conjuracao.dados.get("motivo")}
        if usou_inimigo_favorito:
            self.ficha["usos_inimigo_favorito"] = max(0, int(self.ficha.get("usos_inimigo_favorito", 0)) - 1)
        if eh_acao_bonus:
            self.acao_bonus_usada = True
        else:
            self.acao_principal_usada = True

        # 2) Efeito, sempre pelo motor.
        mecanica_conjurada = conjuracao.dados.get("mecanica") or {}
        if magia in {"Curar Ferimentos", "Palavra Curativa"}:
            return self._curar(ator, magia, mecanica_conjurada)
        if magia == "Vitalidade Vazia":
            return self._vitalidade_vazia(ator, mecanica_conjurada)
        if magia == "Armadura de Agathys":
            return self._armadura_de_agathys(ator, mecanica_conjurada)
        if magia == "Marca do Predador":
            return self._marca_do_predador(ator, str(alvo_id), mecanica_conjurada)
        if magia == "Escudo da Fé":
            return self._escudo_da_fe(ator, mecanica_conjurada)
        if magia == "Armadura Arcana":
            return self._armadura_arcana(ator, mecanica_conjurada)
        if magia in {
            "Raio de Fogo",
            "Raio de Gelo",
            "Chicote de Espinhos",
            "Rajada de Veneno",
            "Toque Chocante",
            "Raio Místico",
            "Raio de Bruxa",
        }:
            return self._ataque_magico(ator, magia, str(alvo_id), mecanica_conjurada)
        if magia == "Mísseis Mágicos":
            return self._misseis_magicos(ator, str(alvo_id), mecanica_conjurada)
        if magia == "Zombaria Perversa":
            return self._zombaria_perversa(str(alvo_id), int(cd))
        return self._comando(str(alvo_id), str(comando), int(cd))

    def _marca_do_predador(
        self, ator: str, cid: str, mecanica: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        mec = mecanica or {}
        dado_extra = str(mec.get("dados_dano_extra", "1d6"))
        self.ficha["alvo_marca_do_predador"] = cid
        self.ficha["dado_marca_do_predador"] = dado_extra
        self.log.append(
            {
                "evento": "magia",
                "ator": ator,
                "magia": "Marca do Predador",
                "alvo": cid,
                "dado_dano_extra": dado_extra,
            }
        )
        return {
            "status": "resolvido",
            "magia": "Marca do Predador",
            "alvo": cid,
            "dado_dano_extra": dado_extra,
            "usos_inimigo_favorito": int(self.ficha.get("usos_inimigo_favorito", 0)),
            "espacos_restantes": self.ficha["conjuracao"]["espacos_restantes"],
        }

    def _armadura_de_agathys(
        self, ator: str, mecanica: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        mec = mecanica or {}
        pv_temp = max(int(self.ficha.get("pv_temporarios", 0)), int(mec.get("pv_temporarios", 5)))
        dano_retorno = int(mec.get("dano_retorno", 5))
        self.ficha["pv_temporarios"] = pv_temp
        self.ficha["armadura_de_agathys_dano"] = dano_retorno
        self.log.append(
            {
                "evento": "magia",
                "ator": ator,
                "magia": "Armadura de Agathys",
                "pv_temporarios": pv_temp,
                "dano_retorno": dano_retorno,
            }
        )
        return {
            "status": "resolvido",
            "magia": "Armadura de Agathys",
            "pv_temporarios": pv_temp,
            "dano_retorno": dano_retorno,
            "espacos_restantes": self.ficha["conjuracao"]["espacos_restantes"],
        }

    def _vitalidade_vazia(self, ator: str, mecanica: dict[str, Any] | None = None) -> dict[str, Any]:
        mec = mecanica or {}
        base = str(mec.get("pv_temporarios_base", "2d4"))
        fixo = int(mec.get("pv_temporarios_fixo", 4)) + int(mec.get("pv_temporarios_extra", 0))
        rolagem = self._executar(
            {
                "type": "damage",
                "damage_expression": f"{base}+{fixo}",
                "damage_type": "necrotico",
                "critical": False,
                "seed": self._proxima_semente(),
            },
            [self.ficha],
        ).dados["total"]
        pv_temp = max(int(self.ficha.get("pv_temporarios", 0)), int(rolagem))
        self.ficha["pv_temporarios"] = pv_temp
        self.log.append(
            {"evento": "magia", "ator": ator, "magia": "Vitalidade Vazia", "pv_temporarios": pv_temp}
        )
        return {
            "status": "resolvido",
            "magia": "Vitalidade Vazia",
            "rolagem": int(rolagem),
            "pv_temporarios": pv_temp,
            "espacos_restantes": self.ficha["conjuracao"]["espacos_restantes"],
        }

    def _curar(self, ator: str, magia: str = "Curar Ferimentos", mecanica: dict[str, Any] | None = None) -> dict[str, Any]:
        # Dados de cura do catálogo (2d8 ou 2d4) + modificador do atributo de conjuração da classe (PHB 2024).
        dados_cura = str((mecanica or {}).get("dados_cura") or "2d8")
        atributo = atributo_de_conjuracao(self.orquestrador.engine, self.ficha) or ATRIBUTO_CONJURACAO
        efeito_sub = self.ficha.get("efeito_subclasse") or {}
        bonus_cura_sub = (
            int(efeito_sub["cura_extra_base"]) + 1
            if "cura_extra_base" in efeito_sub
            else int(efeito_sub.get("bonus_cura", 0))
        )
        modificador = int(self.ficha["modificadores"][atributo]) + bonus_cura_sub
        rolagem = self._executar(
            {
                "type": "damage",
                "damage_expression": f"{dados_cura}+{modificador}",
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
        bloqueado_maldicao = bool(self.ficha.get("maldicao_da_mumia"))
        cura_efetiva = 0 if bloqueado_maldicao else int(rolagem)
        self._executar({"type": "healing", "estado": estado, "amount": cura_efetiva}, [])
        self.ficha["pv_atuais"] = estado.pv_atuais
        curado = estado.pv_atuais - pv_antes
        self.log.append(
            {
                "evento": "magia",
                "ator": ator,
                "magia": magia,
                "curado": curado,
                **({"bloqueado_por_maldicao": True} if bloqueado_maldicao else {}),
            }
        )
        return {
            "status": "resolvido",
            "magia": magia,
            "rolagem": int(rolagem),
            "curado": curado,
            "pv_atuais": estado.pv_atuais,
            "espacos_restantes": self.ficha["conjuracao"]["espacos_restantes"],
            **({"bloqueado_por_maldicao": True} if bloqueado_maldicao else {}),
        }

    def _escudo_da_fe(self, ator: str, mecanica: dict[str, Any]) -> dict[str, Any]:
        bonus_ca = int(mecanica.get("bonus_ca", 2))
        self.ficha["escudo_da_fe_ativo"] = True
        self.ficha["ca"] = calcular_ca(self.orquestrador, self.ficha)
        self.log.append(
            {"evento": "magia", "ator": ator, "magia": "Escudo da Fé", "bonus_ca": bonus_ca, "ca": self.ficha["ca"]}
        )
        return {
            "status": "resolvido",
            "magia": "Escudo da Fé",
            "bonus_ca": bonus_ca,
            "ca": self.ficha["ca"],
            "espacos_restantes": self.ficha["conjuracao"]["espacos_restantes"],
        }

    def _armadura_arcana(self, ator: str, mecanica: dict[str, Any]) -> dict[str, Any]:
        self.ficha["armadura_arcana_ativa"] = True
        self.ficha["ca"] = calcular_ca(self.orquestrador, self.ficha)
        self.log.append(
            {
                "evento": "magia",
                "ator": ator,
                "magia": "Armadura Arcana",
                "ca_base": int(mecanica.get("ca_base", 13)),
                "ca": self.ficha["ca"],
            }
        )
        return {
            "status": "resolvido",
            "magia": "Armadura Arcana",
            "ca": self.ficha["ca"],
            "espacos_restantes": self.ficha["conjuracao"]["espacos_restantes"],
        }

    def _ataque_magico(
        self,
        ator: str,
        magia: str,
        cid: str,
        mecanica: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        inimigo = self.inimigos[cid]
        distancia = self.distancia_pes(ator, cid)
        efeito_condicao = self._efeito_condicoes_no_ataque(ator, cid, distancia)
        cobertura = self._cobertura_entre(ator, cid)
        eh_corpo_a_corpo = str((mecanica or {}).get("ataque")) == "corpo_a_corpo"
        fatos_ataque: dict[str, Any] = {
            "type": "attack",
            "magia": magia,
            "character_id": ator,
            "target_name": inimigo["monstro"],
            "seed": self._proxima_semente(),
        }
        if cobertura != "nenhuma":
            fatos_ataque["cover"] = cobertura
        if efeito_condicao.get("resultado") == "vantagem" or bool(self.ficha.get("vantagem_ataque_magia")):
            fatos_ataque["advantage"] = True
        if efeito_condicao.get("resultado") == "desvantagem":
            fatos_ataque["disadvantage"] = True
        if not eh_corpo_a_corpo and distancia == 5:
            fatos_ataque["disadvantage"] = True

        ataque = self._executar(fatos_ataque, [self.ficha])
        dados = ataque.dados
        acertou = dados.get("result") == "hit"
        if not acertou:
            self.log.append(
                {"evento": "magia", "ator": ator, "magia": magia, "alvo": cid, "acertou": False, "dano": 0}
            )
            return {
                "status": "resolvido",
                "magia": magia,
                "alvo": cid,
                "acertou": False,
                "dano": 0,
            }
        dano = int(dados.get("dano", 0))
        tipo_dano = str(dados.get("tipo_dano", "igneo"))
        defesas = dados.get("defesas_dano") or {}
        modificador_defesa = str(defesas.get("aplicacao", "normal"))
        efeito_sub = self.ficha.get("efeito_subclasse") or {}
        bonus_dano_magia = int(efeito_sub.get("bonus_dano_magia", 0)) + int(efeito_sub.get("bonus_dano_eletrico", 0))
        if bonus_dano_magia > 0 and modificador_defesa != "imunidade":
            dano += bonus_dano_magia
        estado = EstadoVital(
            pv_maximos=inimigo["pv_maximo"],
            pv_atuais=inimigo["pv_atuais"],
            pv_temporarios=inimigo["pv_temporarios"],
        )
        self._executar(
            {"type": "damage_application", "estado": estado, "damage": dano, "damage_type": tipo_dano},
            [],
        )
        inimigo["pv_atuais"] = estado.pv_atuais
        inimigo["pv_temporarios"] = estado.pv_temporarios
        derrubado = estado.pv_atuais == 0
        fortitude_ativada = False
        if derrubado and self._verificar_fortitude_morto_vivo(
            cid, int(dano), tipo_dano, critico=bool(dados.get("critical"))
        ):
            derrubado = False
            fortitude_ativada = True
        if derrubado:
            self._marcar_derrotado(cid)
        elif (mecanica or {}).get("puxa_m"):
            casas_puxao = max(1, round(float(mecanica["puxa_m"]) * 3.28084 / CASA_PES))
            ocupadas = self._ocupadas(cid) - {self.posicoes[ator]}
            caminho = self.board.shortest_path(self.posicoes[cid], self.posicoes[ator], occupied=ocupadas)
            if caminho and len(caminho) > 2:
                for pos in caminho[1:-1][:casas_puxao]:
                    self.posicoes[cid] = pos
        self.log.append(
            {
                "evento": "magia",
                "ator": ator,
                "magia": magia,
                "alvo": cid,
                "acertou": True,
                "dano": dano,
                "defesa_aplicada": modificador_defesa,
                **({"fortitude_morto_vivo": True} if fortitude_ativada else {}),
            }
        )
        return {
            "status": "resolvido",
            "magia": magia,
            "alvo": cid,
            "acertou": True,
            "dano": dano,
            "defesa_aplicada": modificador_defesa,
            "alvo_pv": inimigo["pv_atuais"],
            "derrubado": derrubado,
            **({"fortitude_morto_vivo": True} if fortitude_ativada else {}),
        }

    def _misseis_magicos(self, ator: str, cid: str, mecanica: dict[str, Any]) -> dict[str, Any]:
        dardos = int(mecanica.get("dardos", 3))
        expressao = str(mecanica.get("dano_por_dardo", "1d4+1"))
        tipo_dano = str(mecanica.get("tipo_dano", "energetico"))
        dano_bruto = 0
        for _ in range(dardos):
            dano_bruto += int(
                self._executar(
                    {
                        "type": "damage",
                        "damage_expression": expressao,
                        "damage_type": tipo_dano,
                        "critical": False,
                        "seed": self._proxima_semente(),
                    },
                    [self.ficha],
                ).dados["total"]
            )
        inimigo = self.inimigos[cid]
        bloco_alvo = consultar_monstro(inimigo["monstro"]) or {}
        defesas = self._executar(
            {
                "type": "damage_defenses",
                "damage": dano_bruto,
                "damage_type": tipo_dano,
                "defesas": bloco_alvo,
            },
            [],
        ).dados
        dano = int(defesas.get("dano", dano_bruto))
        estado = EstadoVital(
            pv_maximos=inimigo["pv_maximo"],
            pv_atuais=inimigo["pv_atuais"],
            pv_temporarios=inimigo["pv_temporarios"],
        )
        self._executar(
            {"type": "damage_application", "estado": estado, "damage": dano, "damage_type": tipo_dano},
            [],
        )
        inimigo["pv_atuais"] = estado.pv_atuais
        inimigo["pv_temporarios"] = estado.pv_temporarios
        derrubado = estado.pv_atuais == 0
        fortitude_ativada = False
        if derrubado and self._verificar_fortitude_morto_vivo(cid, int(dano), tipo_dano, critico=False):
            derrubado = False
            fortitude_ativada = True
        if derrubado:
            self._marcar_derrotado(cid)
        self.log.append(
            {
                "evento": "magia",
                "ator": ator,
                "magia": "Mísseis Mágicos",
                "alvo": cid,
                "dardos": dardos,
                "dano": dano,
                **({"fortitude_morto_vivo": True} if fortitude_ativada else {}),
            }
        )
        return {
            "status": "resolvido",
            "magia": "Mísseis Mágicos",
            "alvo": cid,
            "dardos": dardos,
            "dano": dano,
            "alvo_pv": inimigo["pv_atuais"],
            "derrubado": derrubado,
            "espacos_restantes": self.ficha["conjuracao"]["espacos_restantes"],
            **({"fortitude_morto_vivo": True} if fortitude_ativada else {}),
        }

    def _salvaguarda_atributo(self, cid: str, atributo: str, cd: int) -> dict[str, Any]:
        """Salvaguarda do inimigo no atributo indicado, resolvida pelo motor com o bloco do bestiário."""
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
                "atributo": atributo,
                "character_id": cid,
                "dc": cd,
                "seed": self._proxima_semente(),
            },
            [registro],
        ).dados

    def _salvaguarda_sabedoria(self, cid: str, cd: int) -> dict[str, Any]:
        """Salvaguarda de Sabedoria do inimigo, resolvida pelo motor com o bloco do bestiário."""
        return self._salvaguarda_atributo(cid, "sabedoria", cd)

    def _empurrar_inimigo(self, ator: str, cid: str, distancia_pes: int) -> bool:
        """Empurra o alvo em linha reta para longe do atacante até ``distancia_pes``."""
        casas = max(1, distancia_pes // CASA_PES)
        pos_ator = self.posicoes[ator]
        pos_alvo = self.posicoes[cid]
        dx = 0 if pos_alvo.x == pos_ator.x else (1 if pos_alvo.x > pos_ator.x else -1)
        dy = 0 if pos_alvo.y == pos_ator.y else (1 if pos_alvo.y > pos_ator.y else -1)
        if dx == 0 and dy == 0:
            return False
        ocupadas = self._ocupadas(cid)
        atual = pos_alvo
        moveu = False
        for _ in range(casas):
            candidata = BoardPosition(atual.x + dx, atual.y + dy)
            if not self.board.is_walkable(candidata) or candidata in ocupadas:
                break
            atual = candidata
            moveu = True
        if moveu:
            self.posicoes[cid] = atual
        return moveu

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
        dano_bruto = int(
            self._executar(
                {
                    "type": "damage",
                    "damage_expression": expressao,
                    "damage_type": "psychic",
                    "critical": False,
                    "seed": self._proxima_semente(),
                },
                [self.ficha],
            ).dados["total"]
        )
        inimigo = self.inimigos[cid]
        bloco_alvo = consultar_monstro(inimigo["monstro"]) or {}
        defesas = self._executar(
            {
                "type": "damage_defenses",
                "damage": dano_bruto,
                "damage_type": "psychic",
                "defesas": bloco_alvo,
            },
            [],
        ).dados
        dano = int(defesas.get("dano", dano_bruto))
        modificador_defesa = str(defesas.get("aplicacao", "normal"))
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
            {
                "evento": "magia",
                "ator": self.ficha["id"],
                "magia": "Zombaria Perversa",
                "alvo": cid,
                "dano": int(dano),
                "defesa_aplicada": modificador_defesa,
            }
        )
        return {
            "status": "resolvido",
            "magia": "Zombaria Perversa",
            "alvo": cid,
            "resultado": "falhou",
            "dano": int(dano),
            "defesa_aplicada": modificador_defesa,
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

    @property
    def arma_principal(self) -> str:
        arma = self.ficha.get("arma_padrao")
        if arma:
            return str(arma)
        classe = str(self.ficha.get("classe", "")).strip().lower()
        if classe in {"monge", "mago", "druida"}:
            return "Cajado"
        if classe in {"clerigo", "artifice"}:
            return "Maça"
        if classe in {"guerreiro", "paladino"}:
            return "Espada Longa"
        if classe == "barbaro":
            return "Machado Grande"
        if classe == "guardiao":
            return "Espada Curta"
        if classe in {"feiticeiro", "bruxo"}:
            return "Adaga"
        return "Rapieira"

    @property
    def arma_distancia(self) -> str | None:
        arma = self.ficha.get("arma_distancia")
        if arma:
            return str(arma)
        classe = str(self.ficha.get("classe", "")).strip().lower()
        if classe in {"guerreiro", "ladino"}:
            return "Arco Curto"
        if classe == "guardiao":
            return "Arco Longo"
        if classe == "artifice":
            return "Besta Leve"
        return None

    def alvos_ataque_jogador(self, *, apenas_corpo_a_corpo: bool = False) -> list[str]:
        """Inimigos vivos que o personagem pode atacar (5 pés, sopro dracônico ou alcance da arma à distância)."""
        ator = self.ficha["id"]
        if not apenas_corpo_a_corpo and self.arma_distancia:
            arma_cat = CATALOGO_ARMAS.get(self.arma_distancia) or {}
            alcance_normal = max(5, round(float(arma_cat.get("alcance", 24)) * 3.28084 / CASA_PES) * CASA_PES)
            return self.alvos_ao_alcance(ator, alcance_normal * 4, exigir_visao=True)
        if (
            not apenas_corpo_a_corpo
            and self.ficha.get("especie") == "draconato"
            and int(self.ficha.get("usos_sopro_draconico", 0)) > 0
        ):
            return self.alvos_ao_alcance(ator, 15, exigir_visao=True)
        return self.alvos_ao_alcance(ator, 5, exigir_visao=True)

    def recursos_sopro_draconico(self) -> dict[str, Any] | None:
        if self.ficha.get("especie") != "draconato":
            return None
        restantes = int(self.ficha.get("usos_sopro_draconico", 0))
        maximos = int(self.ficha.get("bonus_proficiencia", 2))
        alvos = self.alvos_ao_alcance(self.ficha["id"], 15, exigir_visao=True)
        return {
            "usos_restantes": restantes,
            "usos_maximos": maximos,
            "alvos": alvos,
            "disponivel": not self.acao_principal_usada and restantes > 0 and bool(alvos),
        }

    def recursos_artes_marciais(self) -> dict[str, Any] | None:
        if str(self.ficha.get("classe", "")).strip().lower() != "monge":
            return None
        res = self._executar(
            {"type": "class_feature", "recurso": "artes_marciais", "character_id": self.ficha["id"]},
            [self.ficha],
        ).dados
        return res if res.get("resultado") == "resolvido" else None

    def recursos_recuperar_folego(self) -> dict[str, Any] | None:
        if str(self.ficha.get("classe", "")).strip().lower() != "guerreiro":
            return None
        restantes = int(self.ficha.get("usos_recuperar_folego", 0))
        maximos = int(self.ficha.get("usos_maximos_recuperar_folego", 2))
        return {
            "usos_restantes": restantes,
            "usos_maximos": maximos,
            "disponivel": not self.acao_bonus_usada and restantes > 0,
        }

    def recursos_furia(self) -> dict[str, Any] | None:
        if str(self.ficha.get("classe", "")).strip().lower() != "barbaro":
            return None
        ativa = bool(self.ficha.get("furia_ativa", False))
        restantes = int(self.ficha.get("usos_furia", 0))
        maximos = int(self.ficha.get("usos_maximos_furia", 2))
        return {
            "ativa": ativa,
            "usos_restantes": restantes,
            "usos_maximos": maximos,
            "disponivel": not self.acao_bonus_usada and not ativa and restantes > 0,
        }

    def recursos_ladino(self) -> dict[str, Any] | None:
        if str(self.ficha.get("classe", "")).strip().lower() != "ladino":
            return None
        mirar_ativo = bool(self.ficha.get("vantagem_proximo_ataque", False))
        return {
            "ataque_furtivo_usado": self.ataque_furtivo_usado,
            "mirar_ativo": mirar_ativo,
            "mirar_disponivel": not self.acao_bonus_usada and self.movimento_usado_pes == 0 and not mirar_ativo,
        }

    def recursos_recuperacao_arcana(self) -> dict[str, Any] | None:
        if str(self.ficha.get("classe", "")).strip().lower() != "mago":
            return None
        restantes = int(self.ficha.get("usos_recuperacao_arcana", 0))
        maximos = int(self.ficha.get("usos_maximos_recuperacao_arcana", 1))
        conjuracao = self.ficha.get("conjuracao") or {}
        espacos_restantes = int((conjuracao.get("espacos_restantes") or {}).get("1", 0))
        espacos_totais = int((conjuracao.get("espacos_totais") or {}).get("1", 2))
        return {
            "usos_restantes": restantes,
            "usos_maximos": maximos,
            "disponivel": not self.acao_bonus_usada and restantes > 0 and espacos_restantes < espacos_totais,
        }

    def recursos_maos_consagradas(self) -> dict[str, Any] | None:
        if str(self.ficha.get("classe", "")).strip().lower() != "paladino":
            return None
        restante = int(self.ficha.get("pool_maos_consagradas", 0))
        maximo = int(self.ficha.get("pool_maximo_maos_consagradas", 5))
        return {
            "pool_restante": restante,
            "pool_maximo": maximo,
            "disponivel": not self.acao_bonus_usada and restante > 0,
        }

    def recursos_inimigo_favorito(self) -> dict[str, Any] | None:
        if str(self.ficha.get("classe", "")).strip().lower() != "guardiao":
            return None
        restantes = int(self.ficha.get("usos_inimigo_favorito", 0))
        maximos = int(self.ficha.get("usos_maximos_inimigo_favorito", 2))
        espacos = int(((self.ficha.get("conjuracao") or {}).get("espacos_restantes") or {}).get("1", 0))
        return {
            "usos_restantes": restantes,
            "usos_maximos": maximos,
            "alvo_marcado": self.ficha.get("alvo_marca_do_predador"),
            "disponivel": not self.acao_bonus_usada and (restantes > 0 or espacos > 0),
        }

    def recursos_feiticaria_inata(self) -> dict[str, Any] | None:
        if str(self.ficha.get("classe", "")).strip().lower() != "feiticeiro":
            return None
        ativa = bool(self.ficha.get("feiticaria_inata_ativa", False))
        restantes = int(self.ficha.get("usos_feiticaria_inata", 0))
        maximos = int(self.ficha.get("usos_maximos_feiticaria_inata", 2))
        return {
            "ativa": ativa,
            "usos_restantes": restantes,
            "usos_maximos": maximos,
            "bonus_cd": int(self.ficha.get("bonus_cd_magia", 1)) if ativa else 1,
            "vantagem_ataque_magia": bool(self.ficha.get("vantagem_ataque_magia", True)) if ativa else True,
            "disponivel": not self.acao_bonus_usada and not ativa and restantes > 0,
        }

    @property
    def acao_bonus_disponivel(self) -> bool:
        if self.acao_bonus_usada:
            return False
        classe = str(self.ficha.get("classe", "")).strip().lower()
        if classe == "guerreiro":
            return int(self.ficha.get("usos_recuperar_folego", 0)) > 0
        if classe == "barbaro":
            return not bool(self.ficha.get("furia_ativa", False)) and int(self.ficha.get("usos_furia", 0)) > 0
        if classe == "ladino":
            return self.movimento_usado_pes == 0 and not bool(self.ficha.get("vantagem_proximo_ataque", False))
        if classe == "mago":
            return bool((self.recursos_recuperacao_arcana() or {}).get("disponivel"))
        if classe == "feiticeiro":
            return bool((self.recursos_feiticaria_inata() or {}).get("disponivel"))
        if classe == "guardiao":
            return bool((self.recursos_inimigo_favorito() or {}).get("disponivel"))
        if classe == "paladino":
            espacos = int(((self.ficha.get("conjuracao") or {}).get("espacos_restantes") or {}).get("1", 0))
            tem_escudo_fe = espacos > 0 and not bool(self.ficha.get("escudo_da_fe_ativo"))
            return int(self.ficha.get("pool_maos_consagradas", 0)) > 0 or tem_escudo_fe
        if classe == "clerigo":
            espacos = int(((self.ficha.get("conjuracao") or {}).get("espacos_restantes") or {}).get("1", 0))
            return espacos > 0 and not bool(self.ficha.get("escudo_da_fe_ativo"))
        if classe == "druida":
            espacos = int(((self.ficha.get("conjuracao") or {}).get("espacos_restantes") or {}).get("1", 0))
            return espacos > 0
        artes = self.recursos_artes_marciais() or {}
        return bool(artes.get("ataque_desarmado_bonus"))

    def ativar_feiticaria_inata(self) -> dict[str, Any]:
        """Ativa Feitiçaria Inata do Feiticeiro (ação bônus: +1 CD de magia e vantagem em ataques mágicos)."""
        ator = self._exigir_turno_do_jogador()
        if str(self.ficha.get("classe", "")).strip().lower() != "feiticeiro":
            return {"status": "bloqueado", "motivo": "recurso_indisponivel_na_classe"}
        if self.acao_bonus_usada:
            return {"status": "bloqueado", "motivo": "acao_bonus_usada"}
        if self.ficha.get("feiticaria_inata_ativa"):
            return {"status": "bloqueado", "motivo": "feiticaria_inata_ja_ativa"}
        restantes = int(self.ficha.get("usos_feiticaria_inata", 0))
        if restantes <= 0:
            return {"status": "bloqueado", "motivo": "sem_usos_feiticaria_inata"}
        if self.ficha["pv_atuais"] <= 0:
            return {"status": "bloqueado", "motivo": "personagem_inconsciente"}

        inata = self._executar(
            {
                "type": "class_feature",
                "recurso": "feiticaria_inata",
                "character_id": ator,
            },
            [self.ficha],
        ).dados
        if inata.get("resultado") != "ativada":
            return {"status": "bloqueado", "motivo": inata.get("motivo") or "feiticaria_inata_nao_resolvida"}

        bonus_cd = int(inata.get("bonus_cd", 1))
        vantagem_magia = bool(inata.get("vantagem_ataque_magia", True))
        self.ficha["feiticaria_inata_ativa"] = True
        self.ficha["bonus_cd_magia"] = bonus_cd
        self.ficha["vantagem_ataque_magia"] = vantagem_magia
        self.ficha["usos_feiticaria_inata"] = restantes - 1
        self.acao_bonus_usada = True
        self.log.append(
            {
                "evento": "feiticaria_inata",
                "ator": ator,
                "bonus_cd": bonus_cd,
                "usos_restantes": self.ficha["usos_feiticaria_inata"],
            }
        )
        return {
            "status": "resolvido",
            "recurso": "feiticaria_inata",
            "ativa": True,
            "bonus_cd": bonus_cd,
            "vantagem_ataque_magia": vantagem_magia,
            "usos_restantes": self.ficha["usos_feiticaria_inata"],
        }

    def maos_consagradas(self, pontos: int | None = None) -> dict[str, Any]:
        """Executa Mãos Consagradas do Paladino (ação bônus: gasta pontos da reserva para curar PV)."""
        ator = self._exigir_turno_do_jogador()
        if str(self.ficha.get("classe", "")).strip().lower() != "paladino":
            return {"status": "bloqueado", "motivo": "recurso_indisponivel_na_classe"}
        if self.acao_bonus_usada:
            return {"status": "bloqueado", "motivo": "acao_bonus_usada"}
        restante = int(self.ficha.get("pool_maos_consagradas", 0))
        if restante <= 0:
            return {"status": "bloqueado", "motivo": "sem_pontos_maos_consagradas"}
        if self.ficha["pv_atuais"] <= 0:
            return {"status": "bloqueado", "motivo": "personagem_inconsciente"}

        faltante = max(0, int(self.ficha["pv_maximo"]) - int(self.ficha["pv_atuais"]))
        gasto = int(pontos) if pontos is not None else (min(restante, faltante) if faltante > 0 else restante)
        gasto = max(1, min(restante, gasto))
        res = self._executar(
            {
                "type": "class_feature",
                "recurso": "maos_consagradas",
                "character_id": ator,
                "pool_restante": restante,
                "custo": gasto,
            },
            [self.ficha],
        ).dados
        if res.get("resultado") != "cura":
            return {"status": "bloqueado", "motivo": res.get("motivo") or "maos_consagradas_nao_resolvido"}

        cura_total = min(restante, int(res.get("cura", gasto)))
        estado = EstadoVital(
            pv_maximos=int(self.ficha["pv_maximo"]),
            pv_atuais=int(self.ficha["pv_atuais"]),
            pv_temporarios=int(self.ficha.get("pv_temporarios", 0)),
        )
        pv_antes = estado.pv_atuais
        bloqueado_maldicao = bool(self.ficha.get("maldicao_da_mumia"))
        cura_efetiva = 0 if bloqueado_maldicao else cura_total
        self._executar({"type": "healing", "estado": estado, "amount": cura_efetiva}, [])
        self.ficha["pv_atuais"] = estado.pv_atuais
        curado = estado.pv_atuais - pv_antes
        self.ficha["pool_maos_consagradas"] = restante - cura_total
        self.acao_bonus_usada = True
        self.log.append(
            {
                "evento": "maos_consagradas",
                "ator": ator,
                "gasto": cura_total,
                "curado": curado,
                "pool_restante": self.ficha["pool_maos_consagradas"],
                **({"bloqueado_por_maldicao": True} if bloqueado_maldicao else {}),
            }
        )
        return {
            "status": "resolvido",
            "recurso": "maos_consagradas",
            "gasto": cura_total,
            "curado": curado,
            "pv_atuais": estado.pv_atuais,
            "pool_restante": self.ficha["pool_maos_consagradas"],
            **({"bloqueado_por_maldicao": True} if bloqueado_maldicao else {}),
        }

    def recuperacao_arcana(self) -> dict[str, Any]:
        """Executa Recuperação Arcana do Mago (recupera 1 espaço de magia de 1º círculo)."""
        ator = self._exigir_turno_do_jogador()
        if str(self.ficha.get("classe", "")).strip().lower() != "mago":
            return {"status": "bloqueado", "motivo": "recurso_indisponivel_na_classe"}
        if self.acao_bonus_usada:
            return {"status": "bloqueado", "motivo": "acao_bonus_usada"}
        restantes = int(self.ficha.get("usos_recuperacao_arcana", 0))
        if restantes <= 0:
            return {"status": "bloqueado", "motivo": "sem_usos_recuperacao_arcana"}
        if self.ficha["pv_atuais"] <= 0:
            return {"status": "bloqueado", "motivo": "personagem_inconsciente"}
        conjuracao = self.ficha.get("conjuracao") or {}
        espacos_restantes = int((conjuracao.get("espacos_restantes") or {}).get("1", 0))
        espacos_totais = int((conjuracao.get("espacos_totais") or {}).get("1", 2))
        if espacos_restantes >= espacos_totais:
            return {"status": "bloqueado", "motivo": "espacos_de_magia_cheios"}

        rec = self._executar(
            {
                "type": "class_feature",
                "recurso": "recuperacao_arcana",
                "character_id": ator,
            },
            [self.ficha],
        ).dados
        if rec.get("resultado") != "recuperado":
            return {"status": "bloqueado", "motivo": rec.get("motivo") or "recuperacao_arcana_nao_resolvida"}

        circulos = int(rec.get("circulos", 1))
        novo_valor = min(espacos_totais, espacos_restantes + circulos)
        conjuracao["espacos_restantes"]["1"] = novo_valor
        self.ficha["usos_recuperacao_arcana"] = restantes - 1
        self.acao_bonus_usada = True
        self.log.append(
            {
                "evento": "recuperacao_arcana",
                "ator": ator,
                "circulos": circulos,
                "espacos_restantes": dict(conjuracao["espacos_restantes"]),
            }
        )
        return {
            "status": "resolvido",
            "recurso": "recuperacao_arcana",
            "circulos_recuperados": circulos,
            "espacos_restantes": dict(conjuracao["espacos_restantes"]),
            "usos_restantes": self.ficha["usos_recuperacao_arcana"],
        }

    def ativar_furia(self) -> dict[str, Any]:
        """Ativa Fúria do Bárbaro (ação bônus: +2 dano corpo a corpo com Força e resistência física)."""
        ator = self._exigir_turno_do_jogador()
        if str(self.ficha.get("classe", "")).strip().lower() != "barbaro":
            return {"status": "bloqueado", "motivo": "recurso_indisponivel_na_classe"}
        if self.acao_bonus_usada:
            return {"status": "bloqueado", "motivo": "acao_bonus_usada"}
        if self.ficha.get("furia_ativa"):
            return {"status": "bloqueado", "motivo": "furia_ja_ativa"}
        restantes = int(self.ficha.get("usos_furia", 0))
        if restantes <= 0:
            return {"status": "bloqueado", "motivo": "sem_usos_furia"}
        if self.ficha["pv_atuais"] <= 0:
            return {"status": "bloqueado", "motivo": "personagem_inconsciente"}

        furia = self._executar(
            {
                "type": "martial_feature",
                "feature": "furia",
                "character_id": ator,
                "acao": "ativar",
            },
            [self.ficha],
        ).dados
        if furia.get("resultado") != "ativada":
            return {"status": "bloqueado", "motivo": furia.get("motivo") or "furia_nao_resolvida"}

        resistencias = list(furia.get("resistencias", ["contundente", "cortante", "perfurante"]))
        res_esp = list(self.ficha.get("resistencias_especie") or [])
        self.ficha["furia_ativa"] = True
        self.ficha["resistencias_dano"] = list(dict.fromkeys([*resistencias, *res_esp]))
        self.ficha["usos_furia"] = restantes - 1
        self.acao_bonus_usada = True
        self.log.append(
            {
                "evento": "furia",
                "ator": ator,
                "usos_restantes": self.ficha["usos_furia"],
            }
        )
        return {
            "status": "resolvido",
            "recurso": "furia",
            "ativa": True,
            "dano_adicional": int(furia.get("dano_adicional", 2)),
            "resistencias": resistencias,
            "usos_restantes": self.ficha["usos_furia"],
        }

    def mirar(self) -> dict[str, Any]:
        """Executa Mirar do Ladino (ação bônus sem ter se movido: vantagem no próximo ataque e deslocamento 0)."""
        ator = self._exigir_turno_do_jogador()
        if str(self.ficha.get("classe", "")).strip().lower() != "ladino":
            return {"status": "bloqueado", "motivo": "recurso_indisponivel_na_classe"}
        if self.acao_bonus_usada:
            return {"status": "bloqueado", "motivo": "acao_bonus_usada"}
        if self.movimento_usado_pes > 0:
            return {"status": "bloqueado", "motivo": "ja_se_moveu_no_turno"}
        if self.ficha.get("vantagem_proximo_ataque"):
            return {"status": "bloqueado", "motivo": "mirar_ja_ativo"}
        if self.ficha["pv_atuais"] <= 0:
            return {"status": "bloqueado", "motivo": "personagem_inconsciente"}

        self.ficha["vantagem_proximo_ataque"] = True
        self.movimento_usado_pes = self.deslocamento_pes
        self.acao_bonus_usada = True
        self.log.append({"evento": "mirar", "ator": ator})
        return {
            "status": "resolvido",
            "recurso": "mirar",
            "vantagem_proximo_ataque": True,
        }

    def recuperar_folego(self) -> dict[str, Any]:
        """Executa Recuperar o Fôlego (ação bônus do Guerreiro, 1d10 + nível de cura)."""
        ator = self._exigir_turno_do_jogador()
        if str(self.ficha.get("classe", "")).strip().lower() != "guerreiro":
            return {"status": "bloqueado", "motivo": "recurso_indisponivel_na_classe"}
        if self.acao_bonus_usada:
            return {"status": "bloqueado", "motivo": "acao_bonus_usada"}
        restantes = int(self.ficha.get("usos_recuperar_folego", 0))
        if restantes <= 0:
            return {"status": "bloqueado", "motivo": "sem_usos_recuperar_folego"}
        if self.ficha["pv_atuais"] <= 0:
            return {"status": "bloqueado", "motivo": "personagem_inconsciente"}

        rolagem_d10 = self._executar(
            {
                "type": "damage",
                "damage_expression": "1d10",
                "damage_type": "cura",
                "critical": False,
                "seed": self._proxima_semente(),
            },
            [self.ficha],
        ).dados["total"]
        folego = self._executar(
            {
                "type": "martial_feature",
                "feature": "recuperar_folego",
                "character_id": ator,
                "acao": "usar",
                "rolagem_d10": int(rolagem_d10),
            },
            [self.ficha],
        ).dados
        if folego.get("resultado") != "usado":
            return {"status": "bloqueado", "motivo": folego.get("motivo") or "recuperar_folego_nao_resolvido"}

        cura_total = int(folego["cura"])
        estado = EstadoVital(
            pv_maximos=int(self.ficha["pv_maximo"]),
            pv_atuais=int(self.ficha["pv_atuais"]),
            pv_temporarios=int(self.ficha.get("pv_temporarios", 0)),
        )
        pv_antes = estado.pv_atuais
        bloqueado_maldicao = bool(self.ficha.get("maldicao_da_mumia"))
        cura_efetiva = 0 if bloqueado_maldicao else cura_total
        self._executar({"type": "healing", "estado": estado, "amount": cura_efetiva}, [])
        self.ficha["pv_atuais"] = estado.pv_atuais
        curado = estado.pv_atuais - pv_antes
        self.ficha["usos_recuperar_folego"] = restantes - 1
        self.acao_bonus_usada = True
        self.log.append(
            {
                "evento": "recuperar_folego",
                "ator": ator,
                "rolagem": cura_total,
                "curado": curado,
                "usos_restantes": self.ficha["usos_recuperar_folego"],
                **({"bloqueado_por_maldicao": True} if bloqueado_maldicao else {}),
            }
        )
        return {
            "status": "resolvido",
            "recurso": "recuperar_folego",
            "rolagem": cura_total,
            "curado": curado,
            "pv_atuais": estado.pv_atuais,
            "usos_restantes": self.ficha["usos_recuperar_folego"],
            **({"bloqueado_por_maldicao": True} if bloqueado_maldicao else {}),
        }

    def atacar_jogador(
        self,
        alvo_id: str,
        *,
        acao_bonus: bool = False,
        arma: str | None = None,
    ) -> dict[str, Any]:
        ator = self._exigir_turno_do_jogador()
        if acao_bonus:
            artes = self.recursos_artes_marciais() or {}
            if not artes.get("ataque_desarmado_bonus"):
                return {"status": "bloqueado", "motivo": "acao_bonus_indisponivel"}
            if self.acao_bonus_usada:
                return {"status": "bloqueado", "motivo": "acao_bonus_usada"}
            arma_escolhida = "Ataque Desarmado"
        else:
            if self.acao_principal_usada:
                return {"status": "bloqueado", "motivo": "acao_principal_usada"}
            arma_escolhida = str(arma or self.arma_principal)

        if alvo_id not in self.inimigos or alvo_id in self.inimigos_derrotados:
            return {"status": "bloqueado", "motivo": "alvo_invalido"}

        distancia = self.distancia_pes(ator, alvo_id)
        if not acao_bonus and arma is None and distancia > 5:
            if self.arma_distancia:
                arma_escolhida = self.arma_distancia
            elif (
                self.ficha.get("especie") == "draconato"
                and int(self.ficha.get("usos_sopro_draconico", 0)) > 0
                and distancia <= 15
            ):
                arma_escolhida = "Ataque de Sopro"

        if arma_escolhida == "Ataque de Sopro":
            if self.ficha.get("especie") != "draconato" or int(self.ficha.get("usos_sopro_draconico", 0)) <= 0:
                return {"status": "bloqueado", "motivo": "sopro_draconico_indisponivel"}
            if distancia > 15 or not self.board.has_line_of_sight(self.posicoes[ator], self.posicoes[alvo_id]):
                return {"status": "bloqueado", "motivo": "alvo_fora_do_alcance"}
            inimigo_s = self.inimigos[alvo_id]
            sopro = self._executar(
                {
                    "type": "attack",
                    "weapon": "Ataque de Sopro",
                    "character_id": ator,
                    "target_name": inimigo_s["monstro"],
                    "seed": self._proxima_semente(),
                },
                [self.ficha],
            )
            if sopro.status != "resolvido":
                return {"status": "bloqueado", "motivo": sopro.motivo or "sopro_nao_resolvido"}
            self.acao_principal_usada = True
            self.ficha["usos_sopro_draconico"] = max(0, int(self.ficha.get("usos_sopro_draconico", 1)) - 1)
            dano_s = int(sopro.dados.get("dano", 0))
            tipo_s = str(sopro.dados.get("tipo_dano", "ígneo"))
            estado_s = EstadoVital(
                pv_maximos=inimigo_s["pv_maximo"],
                pv_atuais=inimigo_s["pv_atuais"],
                pv_temporarios=inimigo_s["pv_temporarios"],
            )
            self._executar(
                {"type": "damage_application", "estado": estado_s, "damage": dano_s, "damage_type": tipo_s},
                [],
            )
            inimigo_s["pv_atuais"] = estado_s.pv_atuais
            inimigo_s["pv_temporarios"] = estado_s.pv_temporarios
            derrubado_s = estado_s.pv_atuais == 0
            if derrubado_s and self._verificar_fortitude_morto_vivo(alvo_id, dano_s, tipo_s, critico=False):
                derrubado_s = False
            if derrubado_s:
                self._marcar_derrotado(alvo_id)
            self.log.append(
                {
                    "evento": "ataque_jogador",
                    "alvo": alvo_id,
                    "arma": "Ataque de Sopro",
                    "a_distancia": True,
                    "acao_bonus": False,
                    "acertou": True,
                    "dano": dano_s,
                    "pv_alvo": inimigo_s["pv_atuais"],
                }
            )
            return {
                "status": "resolvido",
                "arma": "Ataque de Sopro",
                "a_distancia": True,
                "acertou": True,
                "dano": dano_s,
                "salvaguarda": sopro.dados.get("salvaguarda"),
                "usos_restantes": self.ficha["usos_sopro_draconico"],
                "derrubado": derrubado_s,
            }

        arma_catalogo = CATALOGO_ARMAS.get(arma_escolhida) or {}
        propriedades = set(arma_catalogo.get("propriedades") or ())
        a_distancia = "municao" in propriedades
        if a_distancia:
            alcance_normal = max(5, round(float(arma_catalogo.get("alcance", 24)) * 3.28084 / CASA_PES) * CASA_PES)
            alcance_maximo = alcance_normal * 4
            cobertura = self._cobertura_entre(ator, alvo_id)
        else:
            alcance_normal = 5
            alcance_maximo = 5
            cobertura = "nenhuma"

        geometria = self._executar(
            {
                "type": "attack_geometry",
                "distance": distancia,
                "range": alcance_normal,
                "maximum_range": alcance_maximo,
                "ranged_attack": a_distancia,
                "line_of_sight_blocked": not self.board.has_line_of_sight(self.posicoes[ator], self.posicoes[alvo_id]),
                "cover": cobertura,
            },
            [],
        ).dados
        if geometria.get("resultado") != "permitido":
            motivo = geometria.get("motivo")
            return {
                "status": "bloqueado",
                "motivo": "alvo_fora_do_alcance" if motivo == "fora_de_alcance" else motivo,
            }

        inimigo = self.inimigos[alvo_id]
        efeito_condicao = self._efeito_condicoes_no_ataque(ator, alvo_id, distancia)
        fatos_ataque: dict[str, Any] = {
            "type": "attack",
            "weapon": arma_escolhida,
            "character_id": self.ficha["id"],
            "target_name": inimigo["monstro"],
            "seed": self._proxima_semente(),
        }
        efeito_sub = self.ficha.get("efeito_subclasse") or {}
        if efeito_sub.get("critico_com"):
            fatos_ataque["critical_threshold"] = min(int(v) for v in efeito_sub["critico_com"])
        if cobertura != "nenhuma":
            fatos_ataque["cover"] = cobertura
        if (
            self.ficha.pop("vantagem_proximo_ataque", False)
            or self.ficha.pop("assassinar_disponivel", False)
            or self.ficha.pop("inspiracao_heroica", False)
            or efeito_condicao.get("resultado") == "vantagem"
        ):
            self.ficha.pop("vantagem_maestria_afligir", None)
            self.ficha.pop("inspiracao_heroica", None)
            fatos_ataque["advantage"] = True
        if efeito_condicao.get("resultado") == "desvantagem":
            fatos_ataque["disadvantage"] = True
        if geometria.get("desvantagem_por_alcance") or (a_distancia and distancia == 5):
            fatos_ataque["disadvantage"] = True

        ataque = self._executar(fatos_ataque, [self.ficha])
        if self.ficha.get("sorte_halfling") and ataque.dados.get("roll") == 1:
            fatos_ataque["seed"] = self._proxima_semente()
            ataque = self._executar(fatos_ataque, [self.ficha])
        resultado = ataque.dados.get("result")
        if resultado not in {"hit", "miss"}:
            return {"status": "bloqueado", "motivo": ataque.motivo or "ataque_nao_resolvido"}
        if acao_bonus:
            self.acao_bonus_usada = True
        else:
            self.acao_principal_usada = True
        maestrias_ficha = list(self.ficha.get("maestrias_arma") or ())
        if resultado == "miss":
            dano_garantido = 0
            maestria_miss = None
            derrubado_miss = False
            if arma_escolhida in maestrias_ficha:
                res_m = self._executar(
                    {
                        "type": "class_feature",
                        "recurso": "maestria_em_arma",
                        "character_id": ator,
                        "acao": "aplicar",
                        "arma": arma_escolhida,
                        "armas": maestrias_ficha,
                        "acertou": False,
                        "modificador_ataque": int(ataque.dados.get("damage_modifier", 0)),
                    },
                    [self.ficha],
                ).dados
                if res_m.get("efeito") == "dano_em_erro" and int(res_m.get("dano_garantido", 0)) > 0:
                    maestria_miss = "garantido"
                    bloco_alvo_m = consultar_monstro(inimigo["monstro"]) or {}
                    defesas_m = self._executar(
                        {
                            "type": "damage_defenses",
                            "damage": int(res_m["dano_garantido"]),
                            "damage_type": str(res_m.get("tipo_dano", ataque.dados.get("damage_type", "cortante"))),
                            "defesas": bloco_alvo_m,
                        },
                        [],
                    ).dados
                    dano_garantido = int(defesas_m.get("dano", res_m["dano_garantido"]))
                    estado_m = EstadoVital(
                        pv_maximos=inimigo["pv_maximo"],
                        pv_atuais=inimigo["pv_atuais"],
                        pv_temporarios=inimigo["pv_temporarios"],
                    )
                    self._executar(
                        {
                            "type": "damage_application",
                            "estado": estado_m,
                            "damage": dano_garantido,
                            "damage_type": str(res_m.get("tipo_dano", ataque.dados.get("damage_type", "cortante"))),
                        },
                        [],
                    )
                    inimigo["pv_atuais"] = estado_m.pv_atuais
                    inimigo["pv_temporarios"] = estado_m.pv_temporarios
                    derrubado_miss = estado_m.pv_atuais == 0
                    if derrubado_miss:
                        self._marcar_derrotado(alvo_id)
            self.log.append(
                {
                    "evento": "ataque_jogador",
                    "alvo": alvo_id,
                    "arma": arma_escolhida,
                    "a_distancia": a_distancia,
                    "acao_bonus": acao_bonus,
                    "acertou": False,
                    "maestria_aplicada": maestria_miss,
                    "dano": dano_garantido,
                }
            )
            resposta_erro: dict[str, Any] = {"status": "resolvido", "acertou": False}
            if maestria_miss:
                resposta_erro["maestria_aplicada"] = maestria_miss
                resposta_erro["dano"] = dano_garantido
                resposta_erro["derrubado"] = derrubado_miss
            if acao_bonus:
                resposta_erro["acao_bonus"] = True
                resposta_erro["arma"] = arma_escolhida
            return resposta_erro
        dados = ataque.dados
        classe_ficha = str(self.ficha.get("classe", "")).strip().lower()
        dano_furia = 0
        if (
            classe_ficha == "barbaro"
            and self.ficha.get("furia_ativa")
            and not a_distancia
            and dados.get("attack_ability") == "forca"
        ):
            res_furia = self._executar(
                {"type": "martial_feature", "feature": "furia", "character_id": ator, "acao": "dano"},
                [self.ficha],
            ).dados
            dano_furia = int(res_furia.get("dano_adicional", 0))

        bonus_arma_sub = int(efeito_sub.get("bonus_dano_arma", 0)) + int(efeito_sub.get("bonus_dano_radiante", 0))
        modificador_dano = int(dados["damage_modifier"]) + dano_furia + bonus_arma_sub
        sinal = "+" if modificador_dano >= 0 else "-"
        expressao = f"{dados['weapon_damage']}{sinal}{abs(modificador_dano)}"
        dano_bruto = int(
            self._executar(
                {
                    "type": "damage",
                    "damage_expression": expressao,
                    "damage_type": dados["damage_type"],
                    "critical": bool(dados.get("critical")),
                    "seed": self._proxima_semente(),
                },
                [self.ficha],
            ).dados["total"]
        )

        if (
            classe_ficha == "barbaro"
            and self.ficha.get("furia_ativa")
            and not a_distancia
            and not self.frenesi_usado
            and efeito_sub.get("dano_adicional")
        ):
            exp_frenesi = f"{int(efeito_sub['dano_adicional'])}{efeito_sub.get('dado', 'd6')}"
            dano_frenesi = int(
                self._executar(
                    {
                        "type": "damage",
                        "damage_expression": exp_frenesi,
                        "damage_type": dados["damage_type"],
                        "critical": bool(dados.get("critical")),
                        "seed": self._proxima_semente(),
                    },
                    [self.ficha],
                ).dados["total"]
            )
            dano_bruto += dano_frenesi
            dano_furia += dano_frenesi
            self.frenesi_usado = True

        ataque_furtivo_aplicado = False
        if classe_ficha == "ladino":
            tem_vantagem = bool(fatos_ataque.get("advantage")) and not bool(fatos_ataque.get("disadvantage"))
            res_furtivo = self._executar(
                {
                    "type": "martial_feature",
                    "feature": "ataque_furtivo",
                    "character_id": ator,
                    "vantagem": tem_vantagem,
                    "aliado_adjacente": False,
                    "acuidade_ou_distancia": ("acuidade" in propriedades or "municao" in propriedades),
                    "ja_usou_no_turno": self.ataque_furtivo_usado,
                },
                [self.ficha],
            ).dados
            if res_furtivo.get("resultado") == "resolvido":
                expressao_furtivo = f"{res_furtivo['dados']}{res_furtivo['dado']}"
                dano_furtivo = int(
                    self._executar(
                        {
                            "type": "damage",
                            "damage_expression": expressao_furtivo,
                            "damage_type": dados["damage_type"],
                            "critical": bool(dados.get("critical")),
                            "seed": self._proxima_semente(),
                        },
                        [self.ficha],
                    ).dados["total"]
                )
                if efeito_sub.get("vantagem"):
                    dano_furtivo += int(self.ficha.get("nivel", 1))
                dano_bruto += dano_furtivo
                self.ataque_furtivo_usado = True
                ataque_furtivo_aplicado = True

        dano_marca = 0
        if self.ficha.get("alvo_marca_do_predador") == alvo_id:
            dado_marca = str(self.ficha.get("dado_marca_do_predador", "1d6"))
            dano_marca = int(
                self._executar(
                    {
                        "type": "damage",
                        "damage_expression": dado_marca,
                        "damage_type": "energetico",
                        "critical": bool(dados.get("critical")),
                        "seed": self._proxima_semente(),
                    },
                    [self.ficha],
                ).dados["total"]
            )
            dano_bruto += dano_marca

        if (
            classe_ficha == "guardiao"
            and not self.matador_colossos_usado
            and efeito_sub.get("dado_dano_extra")
            and int(inimigo["pv_atuais"]) < int(inimigo["pv_maximo"])
        ):
            dano_colosso = int(
                self._executar(
                    {
                        "type": "damage",
                        "damage_expression": str(efeito_sub["dado_dano_extra"]),
                        "damage_type": dados["damage_type"],
                        "critical": bool(dados.get("critical")),
                        "seed": self._proxima_semente(),
                    },
                    [self.ficha],
                ).dados["total"]
            )
            dano_bruto += dano_colosso
            dano_marca += dano_colosso
            self.matador_colossos_usado = True

        if (
            self.ficha.get("especie") == "golias"
            and self.ficha.get("ancestralidade_gigante") == "queimadura_de_fogo"
            and int(self.ficha.get("usos_ancestralidade_gigante", 0)) > 0
        ):
            dano_fogo_golias = int(
                self._executar(
                    {
                        "type": "damage",
                        "damage_expression": "1d10",
                        "damage_type": "igneo",
                        "critical": bool(dados.get("critical")),
                        "seed": self._proxima_semente(),
                    },
                    [self.ficha],
                ).dados["total"]
            )
            dano_bruto += dano_fogo_golias
            self.ficha["usos_ancestralidade_gigante"] = max(
                0, int(self.ficha.get("usos_ancestralidade_gigante", 1)) - 1
            )

        if (
            self.ficha.get("especie") == "aasimar"
            and int(self.ficha.get("nivel", 1)) >= 3
            and not self.revelacao_celestial_usada
        ):
            dano_bruto += int(self.ficha.get("bonus_proficiencia", 2))
            self.revelacao_celestial_usada = True

        bloco_alvo = consultar_monstro(inimigo["monstro"]) or {}
        defesas = self._executar(
            {
                "type": "damage_defenses",
                "damage": int(dano_bruto),
                "damage_type": dados["damage_type"],
                "defesas": bloco_alvo,
            },
            [],
        ).dados
        dano = int(defesas.get("dano", dano_bruto))
        modificador_defesa = str(defesas.get("aplicacao", "normal"))
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
        fortitude_ativada = False
        if derrubado and self._verificar_fortitude_morto_vivo(
            alvo_id, int(dano), str(dados["damage_type"]), critico=bool(dados.get("critical"))
        ):
            derrubado = False
            fortitude_ativada = True
        if derrubado:
            self._marcar_derrotado(alvo_id)
        elif acao_bonus and "caido" in (efeito_sub.get("opcoes") or ()):
            self._aplicar_condicao_inimigo(alvo_id, "caido")

        maestria_aplicada = None
        alvo_trespassar = None
        dano_trespassar = 0
        if arma_escolhida in maestrias_ficha:
            res_maestria = self._executar(
                {
                    "type": "class_feature",
                    "recurso": "maestria_em_arma",
                    "character_id": ator,
                    "acao": "aplicar",
                    "arma": arma_escolhida,
                    "armas": maestrias_ficha,
                    "acertou": True,
                    "modificador_ataque": int(dados.get("damage_modifier", 0)),
                    "bonus_proficiencia": int(self.ficha.get("bonus_proficiencia", 2)),
                },
                [self.ficha],
            ).dados
            if res_maestria.get("resultado") == "resolvido":
                maestria_aplicada = str(res_maestria.get("maestria"))
                efeito_m = str(res_maestria.get("efeito"))
                if efeito_m == "vantagem_proximo_ataque":
                    self.ficha["vantagem_proximo_ataque"] = True
                    self.ficha["vantagem_maestria_afligir"] = True
                elif efeito_m == "desvantagem_proximo_ataque_alvo" and not derrubado:
                    inimigo["desvantagem_proximo_ataque"] = True
                elif efeito_m == "reduzir_deslocamento" and not derrubado:
                    inimigo["reducao_deslocamento_pes"] = int(res_maestria.get("reducao_deslocamento_pes", 10))
                elif efeito_m == "empurrar_alvo" and not derrubado:
                    self._empurrar_inimigo(ator, alvo_id, int(res_maestria.get("empurrar_pes", 10)))
                elif efeito_m == "salvaguarda_derrubar" and not derrubado:
                    salv_topple = self._salvaguarda_atributo(
                        alvo_id,
                        str(res_maestria.get("salvaguarda", "constituicao")),
                        int(res_maestria.get("cd", 13)),
                    )
                    if salv_topple.get("result") == "failure":
                        self._aplicar_condicao_inimigo(alvo_id, str(res_maestria.get("condicao", "caido")))
                elif efeito_m == "ataque_adjacente" and not a_distancia and not self.trespassar_usado:
                    adjacentes = [
                        cid
                        for cid in self._alvos_vivos(ator)
                        if cid != alvo_id
                        and self.distancia_pes(ator, cid) <= 5
                        and self.distancia_pes(alvo_id, cid) <= 5
                    ]
                    if adjacentes:
                        alvo_trespassar = adjacentes[0]
                        inimigo_adj = self.inimigos[alvo_trespassar]
                        dano_bruto_t = int(
                            self._executar(
                                {
                                    "type": "damage",
                                    "damage_expression": str(res_maestria.get("dado_dano_adjacente", "1d12")),
                                    "damage_type": dados["damage_type"],
                                    "critical": False,
                                    "seed": self._proxima_semente(),
                                },
                                [self.ficha],
                            ).dados["total"]
                        )
                        bloco_adj = consultar_monstro(inimigo_adj["monstro"]) or {}
                        defesas_t = self._executar(
                            {
                                "type": "damage_defenses",
                                "damage": dano_bruto_t,
                                "damage_type": dados["damage_type"],
                                "defesas": bloco_adj,
                            },
                            [],
                        ).dados
                        dano_trespassar = int(defesas_t.get("dano", dano_bruto_t))
                        estado_adj = EstadoVital(
                            pv_maximos=inimigo_adj["pv_maximo"],
                            pv_atuais=inimigo_adj["pv_atuais"],
                            pv_temporarios=inimigo_adj["pv_temporarios"],
                        )
                        self._executar(
                            {
                                "type": "damage_application",
                                "estado": estado_adj,
                                "damage": dano_trespassar,
                                "damage_type": dados["damage_type"],
                            },
                            [],
                        )
                        inimigo_adj["pv_atuais"] = estado_adj.pv_atuais
                        inimigo_adj["pv_temporarios"] = estado_adj.pv_temporarios
                        if estado_adj.pv_atuais == 0:
                            self._marcar_derrotado(alvo_trespassar)
                        self.trespassar_usado = True

        self.log.append(
            {
                "evento": "ataque_jogador",
                "alvo": alvo_id,
                "arma": arma_escolhida,
                "a_distancia": a_distancia,
                "acao_bonus": acao_bonus,
                "ataque_furtivo": ataque_furtivo_aplicado,
                "dano_furia": dano_furia,
                "dano_marca_do_predador": dano_marca,
                "maestria_aplicada": maestria_aplicada,
                "alvo_trespassar": alvo_trespassar,
                "dano_trespassar": dano_trespassar,
                "critico": bool(dados.get("critical")),
                "acertou": True,
                "dano": int(dano),
                "defesa_aplicada": modificador_defesa,
                "pv_alvo": inimigo["pv_atuais"],
                **({"fortitude_morto_vivo": True} if fortitude_ativada else {}),
            }
        )
        resposta_acerto: dict[str, Any] = {
            "status": "resolvido",
            "arma": arma_escolhida,
            "a_distancia": a_distancia,
            "acao_bonus": acao_bonus,
            "ataque_furtivo": ataque_furtivo_aplicado,
            "dano_furia": dano_furia,
            "dano_marca_do_predador": dano_marca,
            "maestria_aplicada": maestria_aplicada,
            "critico": bool(dados.get("critical")),
            "acertou": True,
            "dano": int(dano),
            "defesa_aplicada": modificador_defesa,
            "derrubado": derrubado,
            **({"fortitude_morto_vivo": True} if fortitude_ativada else {}),
        }
        if alvo_trespassar is not None:
            resposta_acerto["alvo_trespassar"] = alvo_trespassar
            resposta_acerto["dano_trespassar"] = dano_trespassar
        return resposta_acerto

    def encerrar_turno(self) -> dict[str, Any]:
        """Encerra o turno do combatente atual; inimigos agem automaticamente."""
        ator = self.turno_de
        if ator is None:
            return {"status": "bloqueado", "motivo": "encontro_encerrado"}
        if ator != self.ficha["id"]:
            return self._turno_inimigo(ator)
        if "paralisado" in self._condicoes_combatente(ator):
            self._salvaguarda_jogador("constituicao", 10)
            self._remover_condicao_jogador("paralisado")
        if "caido" in self._condicoes_combatente(ator) and self.movimento_restante_pes >= self.deslocamento_pes // 2:
            self._remover_condicao_jogador("caido")
        self.session.end_turn(ator)
        self.movimento_usado_pes = 0
        self.acao_principal_usada = False
        self.acao_bonus_usada = False
        self.ataque_furtivo_usado = False
        self.frenesi_usado = False
        self.matador_colossos_usado = False
        self.trespassar_usado = False
        self.revelacao_celestial_usada = False
        if not self.ficha.pop("vantagem_maestria_afligir", False):
            self.ficha.pop("vantagem_proximo_ataque", None)
        return {"status": "resolvido"}

    def recursos_descanso_curto(self) -> dict[str, Any]:
        """Estado dos Dados de Vida e disponibilidade de Descanso Curto após vencer a sala."""
        nivel = max(1, int(self.ficha.get("nivel", 1)))
        maximos = int(self.ficha.get("dados_vida_maximos", nivel))
        disponiveis = int(self.ficha.get("dados_vida_disponiveis", maximos))
        dado_vida = int(self.ficha.get("dado_vida", 8))
        precisa_cura = int(self.ficha["pv_atuais"]) < int(self.ficha["pv_maximo"]) and disponiveis > 0
        tem_dreno_ou_maldicao = (
            int(self.ficha.get("reducao_forca_sombra", 0)) > 0 or bool(self.ficha.get("maldicao_da_mumia"))
        )
        classe = str(self.ficha.get("classe", "")).strip().lower()
        tem_recurso_classe = False
        if classe == "guerreiro":
            tem_recurso_classe = int(self.ficha.get("usos_recuperar_folego", 0)) < int(
                self.ficha.get("usos_maximos_recuperar_folego", 2)
            )
        elif classe == "barbaro":
            tem_recurso_classe = int(self.ficha.get("usos_furia", 0)) < int(self.ficha.get("usos_maximos_furia", 2))
        elif classe == "mago" and int(self.ficha.get("usos_recuperacao_arcana", 0)) > 0:
            conj = self.ficha.get("conjuracao") or {}
            tem_recurso_classe = int((conj.get("espacos_restantes") or {}).get("1", 0)) < int(
                (conj.get("espacos_totais") or {}).get("1", 0)
            )
        elif classe == "bruxo":
            conj = self.ficha.get("conjuracao") or {}
            tem_recurso_classe = int((conj.get("espacos_restantes") or {}).get("1", 0)) < int(
                (conj.get("espacos_totais") or {}).get("1", 0)
            )
        disponivel = (
            self.status is EncounterStatus.COMPLETED
            and not self.descanso_curto_usado
            and int(self.ficha["pv_atuais"]) > 0
            and (precisa_cura or tem_recurso_classe or tem_dreno_ou_maldicao)
        )
        return {
            "disponivel": disponivel,
            "usado_na_sala": self.descanso_curto_usado,
            "dados_vida_disponiveis": disponiveis,
            "dados_vida_maximos": maximos,
            "dado_vida": f"d{dado_vida}",
        }

    def descansar_curto(self, dados_vida: int = 1) -> dict[str, Any]:
        """Executa um Descanso Curto de 1h pelo motor após concluir a sala."""
        if self.status is not EncounterStatus.COMPLETED:
            return {"status": "bloqueado", "motivo": "encontro_nao_concluido"}
        if self.descanso_curto_usado:
            return {"status": "bloqueado", "motivo": "descanso_curto_ja_realizado"}
        if int(self.ficha["pv_atuais"]) <= 0:
            return {"status": "bloqueado", "motivo": "personagem_inconsciente"}

        nivel = max(1, int(self.ficha.get("nivel", 1)))
        maximos = int(self.ficha.get("dados_vida_maximos", nivel))
        disponiveis = int(self.ficha.get("dados_vida_disponiveis", maximos))
        dado_vida = int(self.ficha.get("dado_vida", 8))
        mod_con = int((self.ficha.get("modificadores") or {}).get("constituicao", 0))

        dreno_forca = int(self.ficha.pop("reducao_forca_sombra", 0))
        if dreno_forca > 0:
            nova_forca = int(self.ficha["atributos"].get("forca", 10)) + dreno_forca
            self.ficha["atributos"]["forca"] = nova_forca
            self.ficha["modificadores"]["forca"] = (nova_forca - 10) // 2
        maldicao_removida = bool(self.ficha.pop("maldicao_da_mumia", False))

        rolagens: list[int] = []
        if int(self.ficha["pv_atuais"]) < int(self.ficha["pv_maximo"]) and disponiveis > 0 and int(dados_vida) > 0:
            qtd = max(1, min(int(dados_vida), disponiveis))
            pv_simulado = int(self.ficha["pv_atuais"])
            for _ in range(qtd):
                if pv_simulado >= int(self.ficha["pv_maximo"]):
                    break
                rolado = int(
                    self._executar(
                        {
                            "type": "damage",
                            "damage_expression": f"1d{dado_vida}",
                            "damage_type": "cura",
                            "critical": False,
                            "seed": self._proxima_semente(),
                        },
                        [self.ficha],
                    ).dados["total"]
                )
                rolagens.append(rolado)
                pv_simulado += max(1, rolado + mod_con)

        classe = str(self.ficha.get("classe", "")).strip().lower()
        recursos_rec: dict[str, int] = {}
        if classe == "guerreiro":
            atuais = int(self.ficha.get("usos_recuperar_folego", 0))
            max_folego = int(self.ficha.get("usos_maximos_recuperar_folego", 2))
            if atuais < max_folego:
                self._executar(
                    {
                        "type": "martial_feature",
                        "feature": "recuperar_folego",
                        "character_id": self.ficha["id"],
                        "acao": "recuperar",
                    },
                    [self.ficha],
                )
                self.ficha["usos_recuperar_folego"] = min(max_folego, atuais + 1)
                recursos_rec["recuperar_folego"] = self.ficha["usos_recuperar_folego"] - atuais
        elif classe == "barbaro":
            atuais_f = int(self.ficha.get("usos_furia", 0))
            max_furia = int(self.ficha.get("usos_maximos_furia", 2))
            if atuais_f < max_furia:
                self.ficha["usos_furia"] = min(max_furia, atuais_f + 1)
                recursos_rec["furia"] = self.ficha["usos_furia"] - atuais_f
        elif classe == "mago" and int(self.ficha.get("usos_recuperacao_arcana", 0)) > 0:
            conj = self.ficha.get("conjuracao") or {}
            totais_1 = int((conj.get("espacos_totais") or {}).get("1", 0))
            restantes_1 = int((conj.get("espacos_restantes") or {}).get("1", 0))
            if restantes_1 < totais_1:
                res_arc = self._executar(
                    {
                        "type": "class_feature",
                        "recurso": "recuperacao_arcana",
                        "character_id": self.ficha["id"],
                        "circulos_recuperados": [1],
                    },
                    [self.ficha],
                ).dados
                if res_arc.get("resultado") == "recuperado":
                    conj["espacos_restantes"]["1"] = min(totais_1, restantes_1 + 1)
                    self.ficha["usos_recuperacao_arcana"] = max(0, int(self.ficha.get("usos_recuperacao_arcana", 1)) - 1)
                    recursos_rec["recuperacao_arcana"] = 1
        elif classe == "bruxo":
            conj = self.ficha.get("conjuracao") or {}
            totais_1 = int((conj.get("espacos_totais") or {}).get("1", 0))
            restantes_1 = int((conj.get("espacos_restantes") or {}).get("1", 0))
            if restantes_1 < totais_1:
                res_pacto = self._executar(
                    {
                        "type": "class_feature",
                        "recurso": "magia_de_pacto",
                        "character_id": self.ficha["id"],
                    },
                    [self.ficha],
                ).dados
                if res_pacto.get("resultado") == "resolvido":
                    conj["espacos_restantes"]["1"] = totais_1
                    recursos_rec["magia_de_pacto"] = totais_1 - restantes_1

        if dreno_forca > 0:
            recursos_rec["forca_restaurada"] = dreno_forca
        if maldicao_removida:
            recursos_rec["maldicao_da_mumia_removida"] = 1

        if not rolagens and not recursos_rec:
            return {"status": "bloqueado", "motivo": "sem_beneficio_descanso_curto"}

        estado = EstadoVital(
            pv_maximos=int(self.ficha["pv_maximo"]),
            pv_atuais=int(self.ficha["pv_atuais"]),
            pv_temporarios=int(self.ficha.get("pv_temporarios", 0)),
            dados_vida_maximos=maximos,
            dados_vida_disponiveis=disponiveis,
        )
        res_descanso = self._executar(
            {
                "type": "short_rest",
                "estado": estado,
                "duration_hours": 1,
                "hit_dice_rolls": rolagens,
                "constitution_modifier": mod_con,
                "recoverable_resources": recursos_rec,
            },
            [],
        ).dados
        self.ficha["pv_atuais"] = estado.pv_atuais
        self.ficha["dados_vida_disponiveis"] = int(estado.dados_vida_disponiveis or 0)
        self.descanso_curto_usado = True
        curado = int(res_descanso.get("pv_recuperados", 0))
        self.log.append(
            {
                "evento": "descanso_curto",
                "ator": self.ficha["id"],
                "curado": curado,
                "dados_vida_gastos": len(rolagens),
                "rolagens": rolagens,
                "recursos_recuperados": recursos_rec,
            }
        )
        return {
            "status": "resolvido",
            "descanso": "curto",
            "curado": curado,
            "pv_atuais": estado.pv_atuais,
            "dados_vida_gastos": len(rolagens),
            "dados_vida_disponiveis": self.ficha["dados_vida_disponiveis"],
            "rolagens": rolagens,
            "recursos_recuperados": recursos_rec,
        }

    def avancar_sala(self) -> dict[str, Any]:
        """Transita para a próxima sala do catálogo após vencer o encontro atual."""
        if self.status is not EncounterStatus.COMPLETED:
            return {"status": "bloqueado", "motivo": "encontro_nao_concluido"}
        if not self.proxima_sala:
            return {"status": "bloqueado", "motivo": "sem_proxima_sala"}
        destino = str(self.proxima_sala)
        self._iniciar_sala(destino)
        self.log.append(
            {"evento": "avancar_sala", "mapa_id": self.mapa_id, "andar": self.andar, "sala": self.sala_numero}
        )
        return {
            "status": "resolvido",
            "mapa_id": self.mapa_id,
            "andar": self.andar,
            "sala": self.sala_numero,
        }

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
        efeito_sub = self.ficha.get("efeito_subclasse") or {}
        if efeito_sub.get("pv_temporarios_ao_abater"):
            pv_temp = int(efeito_sub["pv_temporarios_ao_abater"])
            self.ficha["pv_temporarios"] = max(int(self.ficha.get("pv_temporarios", 0)), pv_temp)
        if self.session.status is EncounterStatus.COMPLETED and self.recompensa is None:
            self._consolidar_recompensa()

    def _aplicar_subclasse_nivel_3(self) -> dict[str, Any] | None:
        """Resolve a subclasse padrão da classe no Nível 3 pelo Rule Engine."""
        classe = str(self.ficha.get("classe", "bardo")).strip().lower()
        sub = SUBCLASSE_PADRAO_POR_CLASSE.get(classe)
        if not sub:
            return None
        escolha_sub = self._executar(
            {"type": "class_feature", "recurso": "subclasse", "character_id": self.ficha["id"]},
            [self.ficha],
        ).dados
        opcoes = set(escolha_sub.get("opcoes") or ())
        if opcoes and sub["id"] not in opcoes:
            return None
        mod_car = int((self.ficha.get("modificadores") or {}).get("carisma", 0))
        dados_sub = self._executar(
            {
                "type": "class_feature",
                "recurso": "subclasse",
                "character_id": self.ficha["id"],
                "subclasse": sub["id"],
                "caracteristica": sub["caracteristica"],
                "modificador_carisma": mod_car,
            },
            [self.ficha],
        ).dados
        if dados_sub.get("resultado") != "resolvido":
            return None
        self.ficha["subclasse"] = sub["id"]
        self.ficha["subclasse_nome"] = sub["nome"]
        self.ficha["caracteristica_subclasse"] = sub["caracteristica"]
        self.ficha["caracteristica_subclasse_nome"] = sub["caracteristica_nome"]
        self.ficha["efeito_subclasse"] = dict(dados_sub)
        if dados_sub.get("pv_extra_por_nivel"):
            pv_extra = int(dados_sub["pv_extra_por_nivel"]) * int(self.ficha.get("nivel", 3))
            self.ficha["pv_maximo"] = int(self.ficha["pv_maximo"]) + pv_extra
            self.ficha["pv_atuais"] = min(int(self.ficha["pv_maximo"]), int(self.ficha["pv_atuais"]) + pv_extra)
        self.ficha["ca"] = calcular_ca(self.orquestrador, self.ficha)
        return {
            "subclasse": sub["id"],
            "subclasse_nome": sub["nome"],
            "caracteristica_subclasse": sub["caracteristica_nome"],
        }

    def _consolidar_recompensa(self) -> None:
        """Calcula o XP pelo bestiário oficial no motor, aplica XP/ouro e verifica subida de nível."""
        monstros = [inimigo["monstro"] for inimigo in self.inimigos.values()]
        xp_res = self._executar({"type": "bestiary", "operacao": "xp_encontro", "nomes": monstros}, [self.ficha])
        xp_ganho = int(xp_res.dados.get("xp_total", 0))
        padrao = SALAS_PADRAO.get(self.mapa_id, {})
        ouro_ganho = int(self.mapa.get("recompensa_ouro_po", padrao.get("recompensa_ouro_po", 0)))
        aplicar_recompensa(self.ficha, xp=xp_ganho, ouro_po=ouro_ganho)
        self.recompensa = {"xp": xp_ganho, "ouro_po": ouro_ganho}
        self.log.append({"evento": "recompensa", "xp": xp_ganho, "ouro_po": ouro_ganho})
        self._verificar_subida_de_nivel()

    def _verificar_subida_de_nivel(self) -> dict[str, Any] | None:
        """Consulta a regra ``level_up`` no motor e aplica a evolução quando o XP atinge o marco."""
        classe = str(self.ficha.get("classe", "bardo")).strip().lower()
        mod_con = int((self.ficha.get("modificadores") or {}).get("constituicao", 0))
        talentos = list(self.ficha.get("talentos") or ())
        ultima_subida: dict[str, Any] | None = None

        while int(self.ficha.get("nivel", 1)) < 20:
            nivel_atual = int(self.ficha.get("nivel", 1))
            res = self._executar(
                {
                    "type": "level_up",
                    "current_level": nivel_atual,
                    "class": classe,
                    "xp": int(self.ficha.get("xp", 0)),
                    "constitution_modifier": mod_con,
                    "talentos": talentos,
                },
                [self.ficha],
            ).dados
            if res.get("resultado") != "nivel_adquirido":
                break
            novo_nivel = int(res["nivel"])
            pv_ganhos = int(res["pv_ganhos"]) + int(self.ficha.get("pv_bonus_especie_por_nivel", 0))
            bp_anterior = int(self.ficha.get("bonus_proficiencia", 2))
            novo_bp = int(res["bonus_proficiencia"])
            self.ficha["nivel"] = novo_nivel
            self.ficha["bonus_proficiencia"] = novo_bp
            if novo_bp > bp_anterior:
                ganho_bp = novo_bp - bp_anterior
                if self.ficha.get("especie") == "draconato":
                    self.ficha["usos_sopro_draconico"] = int(self.ficha.get("usos_sopro_draconico", 0)) + ganho_bp
                if self.ficha.get("especie") == "golias":
                    self.ficha["usos_ancestralidade_gigante"] = (
                        int(self.ficha.get("usos_ancestralidade_gigante", 0)) + ganho_bp
                    )
            self.ficha["pv_maximo"] = int(self.ficha["pv_maximo"]) + pv_ganhos
            self.ficha["pv_atuais"] = min(int(self.ficha["pv_maximo"]), int(self.ficha["pv_atuais"]) + pv_ganhos)
            self.ficha["dados_vida_maximos"] = novo_nivel
            self.ficha["dados_vida_disponiveis"] = min(
                novo_nivel, int(self.ficha.get("dados_vida_disponiveis", nivel_atual)) + 1
            )

            if classe in {"bardo", "clerigo", "druida", "mago"} and "conjuracao" in self.ficha:
                prog = self._executar(
                    {
                        "type": "spellcaster_feature",
                        "feature": "progressao_conjuracao",
                        "classe": classe,
                        "nivel": novo_nivel,
                        **(self.ficha.get("atributos") or {}),
                    },
                    [self.ficha],
                ).dados
                espacos = prog.get("espacos") or []
                if espacos:
                    conj = self.ficha["conjuracao"]
                    antigo_total_1 = int((conj.get("espacos_totais") or {}).get("1", 0))
                    novo_total_1 = int(espacos[0])
                    ganho_1 = max(0, novo_total_1 - antigo_total_1)
                    conj["espacos_totais"]["1"] = novo_total_1
                    conj["espacos_restantes"]["1"] = min(
                        novo_total_1, int((conj.get("espacos_restantes") or {}).get("1", 0)) + ganho_1
                    )
            elif classe in {"feiticeiro", "bruxo", "guardiao"} and "conjuracao" in self.ficha:
                prog_adv = self._executar(
                    {
                        "type": "class_feature",
                        "recurso": "conjuracao",
                        "character_id": self.ficha["id"],
                    },
                    [self.ficha],
                ).dados
                espacos_adv = prog_adv.get("espacos")
                if espacos_adv is not None:
                    conj = self.ficha["conjuracao"]
                    antigo_total_1 = int((conj.get("espacos_totais") or {}).get("1", 0))
                    novo_total_1 = (
                        int(espacos_adv[0]) if isinstance(espacos_adv, (list, tuple)) else int(espacos_adv)
                    )
                    ganho_1 = max(0, novo_total_1 - antigo_total_1)
                    conj["espacos_totais"]["1"] = novo_total_1
                    conj["espacos_restantes"]["1"] = min(
                        novo_total_1, int((conj.get("espacos_restantes") or {}).get("1", 0)) + ganho_1
                    )
            elif classe == "paladino":
                maos = self._executar(
                    {
                        "type": "class_feature",
                        "recurso": "maos_consagradas",
                        "character_id": self.ficha["id"],
                        "pontos": 0,
                    },
                    [self.ficha],
                ).dados
                antigo_pool = int(self.ficha.get("pool_maximo_maos_consagradas", 5))
                novo_pool = int(maos.get("pool_maximo", 5 * novo_nivel))
                self.ficha["pool_maximo_maos_consagradas"] = novo_pool
                self.ficha["pool_maos_consagradas"] = min(
                    novo_pool, int(self.ficha.get("pool_maos_consagradas", 0)) + max(0, novo_pool - antigo_pool)
                )

            caracteristicas = list(res.get("caracteristicas") or [])
            dados_sub_aplicada = None
            if res.get("escolha_subclasse") or (novo_nivel >= 3 and "efeito_subclasse" not in self.ficha):
                dados_sub_aplicada = self._aplicar_subclasse_nivel_3()
                if dados_sub_aplicada:
                    rotulo_sub = f"{dados_sub_aplicada['subclasse_nome']} ({dados_sub_aplicada['caracteristica_subclasse']})"
                    caracteristicas = [rotulo_sub if c == "Subclasse" else c for c in caracteristicas]
            ultima_subida = {
                "nivel": novo_nivel,
                "pv_ganhos": pv_ganhos,
                "caracteristicas": caracteristicas,
            }
            if dados_sub_aplicada:
                ultima_subida.update(dados_sub_aplicada)
            self.subida_nivel = ultima_subida
            self.log.append(
                {
                    "evento": "subiu_nivel",
                    "ator": self.ficha["id"],
                    "nivel": novo_nivel,
                    "pv_ganhos": pv_ganhos,
                    "caracteristicas": caracteristicas,
                    **(dados_sub_aplicada or {}),
                }
            )
        return ultima_subida

    def _turno_inimigo(self, cid: str) -> dict[str, Any]:
        """IA determinística: ataca se estiver em posição válida; senão aproxima-se e tenta atacar.

        Comando pendente e condição Caído alteram o turno (ver ``COMANDOS``).
        """
        jogador = self.ficha["id"]
        if self.ficha["pv_atuais"] <= 0:
            return {"status": "bloqueado", "motivo": "jogador_derrotado"}
        inimigo = self.inimigos[cid]
        comando = inimigo.pop("comando_pendente", None)
        reducao_pes = int(inimigo.pop("reducao_deslocamento_pes", 0))
        deslocamento_efetivo = max(0, int(inimigo["deslocamento_pes"]) - reducao_pes)
        resultado: dict[str, Any] = {"status": "resolvido", "acao": "nenhuma"}
        passos = deslocamento_efetivo // CASA_PES

        # Se estiver Caído e puder se levantar neste turno, gasta metade do deslocamento.
        if "caido" in self._condicoes_combatente(cid) and comando not in {"abaixar", "parar", "largar"}:
            efeito_caido = self._executar(
                {"type": "condition_effect", "target_conditions": ["caido"]}, []
            ).dados
            if efeito_caido.get("movimento_para_levantar") == "metade_do_deslocamento" and passos > 0:
                passos //= 2
                self._remover_condicao_inimigo(cid, "caido")

        if comando in {"largar", "parar"}:
            resultado = {"status": "resolvido", "acao": f"comando_{comando}"}
        elif comando == "abaixar":
            self._aplicar_condicao_inimigo(cid, "caido")
            resultado = {"status": "resolvido", "acao": "comando_abaixar"}
        elif comando == "fugir":
            self._fugir(cid, passos)
            resultado = {"status": "resolvido", "acao": "comando_fugir"}
        else:
            deve_mover = comando == "aproximar" or self._precisa_aproximar(cid)
            passos_dados = 0
            if deve_mover and passos > 0:
                # A casa do próprio alvo não bloqueia a rota: o caminho termina nela.
                ocupadas = self._ocupadas(cid) - {self.posicoes[jogador]}
                caminho = self.board.shortest_path(self.posicoes[cid], self.posicoes[jogador], occupied=ocupadas)
                if caminho:
                    for pos in caminho[1:-1][:passos]:
                        self.posicoes[cid] = pos
                        passos_dados += 1
                        if comando != "aproximar" and not self._precisa_aproximar(cid):
                            break
                self.log.append(
                    {"evento": "movimento_inimigo", "ator": cid, "para": (self.posicoes[cid].x, self.posicoes[cid].y)}
                )
                resultado = {"status": "resolvido", "acao": "moveu"}
            inimigo["passos_movidos_pes_turno"] = passos_dados * CASA_PES
            # Comando "aproximar" encerra o turno ao se mover: não ataca neste turno.
            if comando != "aproximar" and self._pode_atacar(cid) and self.ficha["pv_atuais"] > 0:
                resultado = self._atacar_com_inimigo(cid)
            inimigo.pop("passos_movidos_pes_turno", None)
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

    def _cobertura_entre(self, origem: str, destino: str) -> str:
        """Determina se há cobertura parcial entre dois combatentes no tabuleiro."""
        ocupadas = self._ocupadas(origem) - {self.posicoes[destino]}
        tem_obstaculo = self.board.has_cover_obstacle(
            self.posicoes[origem], self.posicoes[destino], occupied=ocupadas
        )
        return "meia" if tem_obstaculo else "nenhuma"

    def _avaliar_ataque_inimigo(self, cid: str) -> tuple[dict[str, Any], dict[str, Any]]:
        """Escolhe a ação (corpo a corpo ou à distância) e valida a geometria pelo motor."""
        jogador = self.ficha["id"]
        distancia = self.distancia_pes(cid, jogador)
        stats = carregar_inimigo(self.inimigos[cid]["perfil"])
        acao = escolher_acao_inimigo(stats, distancia)
        bloqueada = not self.board.has_line_of_sight(self.posicoes[cid], self.posicoes[jogador])
        cobertura = self._cobertura_entre(cid, jogador)
        geometria = validar_geometria_ataque(
            self.orquestrador,
            acao,
            distancia_pes=distancia,
            linha_de_visao_bloqueada=bloqueada,
            cobertura=cobertura,
        )
        return acao, geometria

    def _pode_atacar(self, cid: str) -> bool:
        """Verifica no motor se o inimigo pode atacar da posição atual (alcance e linha de visão)."""
        _, geometria = self._avaliar_ataque_inimigo(cid)
        return geometria.get("resultado") == "permitido"

    def _precisa_aproximar(self, cid: str) -> bool:
        """Indica se o inimigo precisa se mover para obter alcance normal e linha de visão."""
        _, geometria = self._avaliar_ataque_inimigo(cid)
        return geometria.get("resultado") != "permitido" or bool(geometria.get("desvantagem_por_alcance", False))

    def _aplicar_efeito_especial_monstro(self, cid: str, resultado: dict[str, Any]) -> None:
        """Aplica os efeitos especiais de acerto dos monstros SRD 5.2.1 pelo motor."""
        inimigo = self.inimigos[cid]
        res_esp = self._executar(
            {
                "type": "bestiary",
                "operacao": "efeito_especial_monstro",
                "nome": inimigo["monstro"],
                "gatilho": "ao_acertar",
                "a_distancia": bool(resultado.get("a_distancia", False)),
                "passos_movidos_pes": int(inimigo.get("passos_movidos_pes_turno", 0)),
                "alvo_especie": str(self.ficha.get("especie", "")),
                "dano_causado": int(resultado.get("dano", 0)),
            },
            [],
        ).dados
        if res_esp.get("resultado") != "resolvido":
            return
        efeito = str(res_esp.get("efeito", ""))
        critico = bool(resultado.get("critico", False))

        if efeito in {"investida", "maldicao_da_mumia"} and res_esp.get("dado_dano_extra"):
            tipo_extra = str(res_esp.get("tipo_dano_extra", "perfurante"))
            dano_extra_bruto = int(
                self._executar(
                    {
                        "type": "damage",
                        "damage_expression": str(res_esp["dado_dano_extra"]),
                        "damage_type": tipo_extra,
                        "critical": critico,
                        "seed": self._proxima_semente(),
                    },
                    [self.ficha],
                ).dados["total"]
            )
            dano_extra = dano_extra_bruto
            if any(self.ficha.get(k) for k in ("resistencias_dano", "imunidades_dano", "vulnerabilidades_dano")):
                defesas_ex = self._executar(
                    {
                        "type": "damage_defenses",
                        "damage": dano_extra_bruto,
                        "damage_type": tipo_extra,
                        "defesas": dict(self.ficha),
                    },
                    [],
                ).dados
                dano_extra = int(defesas_ex.get("dano", dano_extra_bruto))
            estado = EstadoVital(
                pv_maximos=int(self.ficha["pv_maximo"]),
                pv_atuais=int(self.ficha["pv_atuais"]),
                pv_temporarios=int(self.ficha.get("pv_temporarios", 0)),
            )
            self._executar(
                {
                    "type": "damage_application",
                    "estado": estado,
                    "damage": dano_extra,
                    "damage_type": tipo_extra,
                    "critical": critico,
                },
                [],
            )
            self.ficha["pv_atuais"] = estado.pv_atuais
            self.ficha["pv_temporarios"] = estado.pv_temporarios
            resultado["dano"] = int(resultado.get("dano", 0)) + dano_extra
            resultado["pv_atuais"] = estado.pv_atuais
            resultado["pv_temporarios"] = estado.pv_temporarios
            resultado["derrubado"] = estado.pv_atuais == 0
            if efeito == "investida":
                resultado["dano_investida"] = dano_extra
            else:
                resultado["dano_necrotico_extra"] = dano_extra

        if efeito == "toque_paralisante" and self.ficha["pv_atuais"] > 0:
            salv = self._salvaguarda_jogador(
                str(res_esp["salvaguarda"]["atributo"]),
                int(res_esp["salvaguarda"]["cd"]),
            )
            resultado["efeito_especial"] = "toque_paralisante"
            if salv.get("result") == "failure":
                cond = str(res_esp.get("condicao_em_falha", "paralisado"))
                self._aplicar_condicao_jogador(cond)
                resultado["condicao_aplicada"] = cond

        elif efeito == "dreno_forca" and self.ficha["pv_atuais"] > 0:
            dreno = int(
                self._executar(
                    {
                        "type": "damage",
                        "damage_expression": str(res_esp.get("dado_dreno", "1d4")),
                        "damage_type": "necrotico",
                        "critical": False,
                        "seed": self._proxima_semente(),
                    },
                    [self.ficha],
                ).dados["total"]
            )
            forca_atual = int(self.ficha["atributos"].get("forca", 10))
            nova_forca = max(0, forca_atual - dreno)
            drenado_real = forca_atual - nova_forca
            self.ficha["atributos"]["forca"] = nova_forca
            self.ficha["modificadores"]["forca"] = (nova_forca - 10) // 2
            self.ficha["reducao_forca_sombra"] = int(self.ficha.get("reducao_forca_sombra", 0)) + drenado_real
            resultado["efeito_especial"] = "dreno_forca"
            resultado["dreno_forca"] = drenado_real
            if nova_forca == 0:
                self.ficha["pv_atuais"] = 0
                resultado["pv_atuais"] = 0
                resultado["derrubado"] = True

        elif efeito == "dreno_vida" and self.ficha["pv_atuais"] > 0:
            salv = self._salvaguarda_jogador(
                str(res_esp["salvaguarda"]["atributo"]),
                int(res_esp["salvaguarda"]["cd"]),
            )
            resultado["efeito_especial"] = "dreno_vida"
            reducao = int(res_esp.get("reducao_pv_maximo", 0))
            if salv.get("result") == "failure" and reducao > 0:
                pv_max_antes = int(self.ficha["pv_maximo"])
                novo_pv_max = max(0, pv_max_antes - reducao)
                reduzido_real = pv_max_antes - novo_pv_max
                self.ficha["pv_maximo"] = novo_pv_max
                self.ficha["pv_atuais"] = min(int(self.ficha["pv_atuais"]), novo_pv_max)
                self.ficha["reducao_pv_maximo"] = int(self.ficha.get("reducao_pv_maximo", 0)) + reduzido_real
                resultado["reducao_pv_maximo"] = reduzido_real
                resultado["pv_atuais"] = self.ficha["pv_atuais"]
                if novo_pv_max == 0:
                    resultado["derrubado"] = True

        elif efeito == "investida" and self.ficha["pv_atuais"] > 0:
            salv = self._salvaguarda_jogador(
                str(res_esp["salvaguarda"]["atributo"]),
                int(res_esp["salvaguarda"]["cd"]),
            )
            resultado["efeito_especial"] = "investida"
            if salv.get("result") == "failure":
                self._empurrar_inimigo(cid, self.ficha["id"], int(res_esp.get("empurrar_pes_em_falha", 10)))
                cond = str(res_esp.get("condicao_em_falha", "caido"))
                self._aplicar_condicao_jogador(cond)
                resultado["condicao_aplicada"] = cond

        elif efeito == "maldicao_da_mumia" and self.ficha["pv_atuais"] > 0:
            salv = self._salvaguarda_jogador(
                str(res_esp["salvaguarda"]["atributo"]),
                int(res_esp["salvaguarda"]["cd"]),
            )
            resultado["efeito_especial"] = "maldicao_da_mumia"
            if salv.get("result") == "failure":
                self.ficha["maldicao_da_mumia"] = True
                resultado["condicao_aplicada"] = "maldicao_da_mumia"

    def _atacar_com_inimigo(self, cid: str) -> dict[str, Any]:
        jogador = self.ficha["id"]
        distancia = self.distancia_pes(cid, jogador)
        acao, _ = self._avaliar_ataque_inimigo(cid)
        efeito_condicao = self._efeito_condicoes_no_ataque(cid, jogador, distancia)
        desvantagem = bool(
            self.inimigos[cid].get("desvantagem_proximo_ataque")
            or efeito_condicao.get("resultado") == "desvantagem"
        )
        bloqueada = not self.board.has_line_of_sight(self.posicoes[cid], self.posicoes[jogador])
        cobertura = self._cobertura_entre(cid, jogador)
        pv_temp_antes = int(self.ficha.get("pv_temporarios", 0))
        dano_agathys_ativo = int(self.ficha.get("armadura_de_agathys_dano", 0))
        resultado = atacar_inimigo(
            self.orquestrador,
            self.inimigos[cid]["perfil"],
            self.ficha,
            seed=self._proxima_semente(),
            desvantagem=desvantagem,
            acao_nome=acao["nome"],
            distancia_pes=distancia,
            linha_de_visao_bloqueada=bloqueada,
            cobertura=cobertura,
        )
        if resultado.get("status") == "bloqueado":
            return {"status": "bloqueado", "motivo": resultado.get("motivo")}
        if resultado.get("acertou"):
            self.ficha["pv_atuais"] = resultado["pv_atuais"]
            self.ficha["pv_temporarios"] = resultado["pv_temporarios"]
            self._aplicar_efeito_especial_monstro(cid, resultado)
        evento_log: dict[str, Any] = {
            "evento": "ataque_inimigo",
            "ator": cid,
            "acao": resultado.get("acao"),
            "acertou": resultado.get("acertou"),
            "dano": resultado.get("dano"),
            "defesa_aplicada": resultado.get("defesa_aplicada", "normal"),
        }
        for chave_extra in (
            "efeito_especial",
            "condicao_aplicada",
            "dreno_forca",
            "reducao_pv_maximo",
            "dano_investida",
            "dano_necrotico_extra",
        ):
            if chave_extra in resultado:
                evento_log[chave_extra] = resultado[chave_extra]
        self.log.append(evento_log)
        if resultado.get("acertou") and pv_temp_antes > 0 and dano_agathys_ativo > 0 and distancia == 5:
            inimigo = self.inimigos[cid]
            bloco_alvo = consultar_monstro(inimigo["monstro"]) or {}
            defesas_ag = self._executar(
                {
                    "type": "damage_defenses",
                    "damage": dano_agathys_ativo,
                    "damage_type": "gelido",
                    "defesas": bloco_alvo,
                },
                [],
            ).dados
            dano_ag = int(defesas_ag.get("dano", dano_agathys_ativo))
            estado_in = EstadoVital(
                pv_maximos=inimigo["pv_maximo"],
                pv_atuais=inimigo["pv_atuais"],
                pv_temporarios=inimigo["pv_temporarios"],
            )
            self._executar(
                {"type": "damage_application", "estado": estado_in, "damage": dano_ag, "damage_type": "gelido"},
                [],
            )
            inimigo["pv_atuais"] = estado_in.pv_atuais
            inimigo["pv_temporarios"] = estado_in.pv_temporarios
            resultado["dano_retaliacao_agathys"] = dano_ag
            if estado_in.pv_atuais == 0:
                self._marcar_derrotado(cid)
            if int(self.ficha.get("pv_temporarios", 0)) <= 0:
                self.ficha.pop("armadura_de_agathys_dano", None)
        if (
            self.ficha["pv_atuais"] <= 0
            and int(self.ficha["pv_maximo"]) > 0
            and int(self.ficha["atributos"].get("forca", 10)) > 0
            and self.ficha.get("vigor_implacavel_disponivel")
        ):
            self.ficha["pv_atuais"] = 1
            self.ficha["vigor_implacavel_disponivel"] = False
            resultado["pv_atuais"] = 1
            resultado["derrubado"] = False
            resultado["vigor_implacavel"] = True
            self.log.append({"evento": "vigor_implacavel", "ator": self.ficha["id"]})
        if self.ficha["pv_atuais"] <= 0:
            self._marcar_derrotado(self.ficha["id"])
        return {"status": "resolvido", "acao": "atacou", **resultado}
