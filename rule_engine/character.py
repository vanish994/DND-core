"""Criação e progressão de personagens do PHB 2024 e do Artífice 5.5e."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .backgrounds import ANTECEDENTES, aplicar_aumentos_antecedente
from .catalog import INSTRUMENTOS_MUSICAIS, KITS_DE_JOGOS
from .class_progression import caracteristicas_no_nivel, subclasses_da_classe
from .feats import DARK_GIFT_FEATS, FEATS
from .species import bloco_heranca_draconica, escolha_de_especie, normalizar_escolha

ESPECIES = {
    "aasimar": {"tamanho": "pequeno_ou_medio", "deslocamento": 9},
    "draconato": {"tamanho": "medio", "deslocamento": 9},
    "anao": {"tamanho": "medio", "deslocamento": 9},
    "elfo": {"tamanho": "medio", "deslocamento": 9},
    "gnomo": {"tamanho": "pequeno", "deslocamento": 9},
    "golias": {"tamanho": "medio", "deslocamento": 10.5},
    "halfling": {"tamanho": "pequeno", "deslocamento": 9},
    "humano": {"tamanho": "pequeno_ou_medio", "deslocamento": 9},
    "orc": {"tamanho": "medio", "deslocamento": 9},
    "tiefling": {"tamanho": "pequeno_ou_medio", "deslocamento": 9},
}
EQUIPAMENTO_INICIAL_ARTIFICE = {
    "A": {
        "itens": [
            "Armadura de Couro Batido",
            "Adaga",
            "Ferramentas de Ladrão",
            "Ferramentas de Funileiro",
            "Pacote de Exploração de Masmorras",
        ],
        "ouro": 16,
    },
    "B": {"itens": [], "ouro": 150},
}

CLASSES = {
    "barbaro": {"dado_vida": 12, "atributo_primario": "forca"},
    "bardo": {"dado_vida": 8, "atributo_primario": "carisma"},
    "clerigo": {"dado_vida": 8, "atributo_primario": "sabedoria"},
    "druida": {"dado_vida": 8, "atributo_primario": "sabedoria"},
    "guerreiro": {"dado_vida": 10, "atributo_primario": "forca_ou_destreza"},
    "monge": {"dado_vida": 8, "atributo_primario": "destreza_e_sabedoria"},
    "paladino": {"dado_vida": 10, "atributo_primario": "forca_ou_destreza_e_carisma"},
    "guardiao": {"dado_vida": 10, "atributo_primario": "destreza_e_sabedoria"},
    "ladino": {"dado_vida": 8, "atributo_primario": "destreza"},
    "feiticeiro": {"dado_vida": 6, "atributo_primario": "carisma"},
    "bruxo": {"dado_vida": 8, "atributo_primario": "carisma"},
    "mago": {"dado_vida": 6, "atributo_primario": "inteligencia"},
    "artifice": {"dado_vida": 8, "atributo_primario": "inteligencia"},
}
SUBCLASSES = {classe: {"nivel": 3, "nomes": set()} for classe in CLASSES}
SUBCLASSES["artifice"]["nomes"].update({"reanimador"})
SUBCLASSES["bardo"]["nomes"].update({"colegio_dos_espiritos"})
SUBCLASSES["clerigo"]["nomes"].update({"dominio_da_sepultura"})
SUBCLASSES["guardiao"]["nomes"].update({"guardiao_oculto"})
SUBCLASSES["ladino"]["nomes"].update({"fantasma"})
SUBCLASSES["feiticeiro"]["nomes"].update({"feiticaria_das_sombras"})
SUBCLASSES["bruxo"]["nomes"].update({"patrono_morto_vivo"})
SUBCLASSES_RAVENLOFT = {
    "reanimador": {"classe": "artifice", "nivel": 3},
    "colegio_dos_espiritos": {"classe": "bardo", "nivel": 3},
    "dominio_da_sepultura": {"classe": "clerigo", "nivel": 3},
    "guardiao_oculto": {"classe": "guardiao", "nivel": 3},
    "fantasma": {"classe": "ladino", "nivel": 3},
    "feiticaria_das_sombras": {"classe": "feiticeiro", "nivel": 3},
    "patrono_morto_vivo": {"classe": "bruxo", "nivel": 3},
}
TALENTOS = set(FEATS)
ATRIBUTOS = {"forca", "destreza", "constituicao", "inteligencia", "sabedoria", "carisma"}

# Opções de perícias de classe: PHB 2024; Artífice conforme Eberron: Forge of the Artificer (2025).
PERICIAS_CLASSE_OPCOES = {
    "barbaro": {"adestrar_animais", "atletismo", "intimidacao", "natureza", "percepcao", "sobrevivencia"},
    "bardo": set(
        "acrobacia adestrar_animais arcanismo atletismo atuacao enganacao furtividade historia intuicao intimidacao investigacao medicina natureza percepcao persuasao prestidigitacao religiao sobrevivencia".split()
    ),
    "clerigo": {"historia", "intuicao", "medicina", "persuasao", "religiao"},
    "druida": {
        "arcanismo",
        "adestrar_animais",
        "intuicao",
        "medicina",
        "natureza",
        "percepcao",
        "religiao",
        "sobrevivencia",
    },
    "guerreiro": {
        "acrobacia",
        "adestrar_animais",
        "atletismo",
        "historia",
        "intuicao",
        "intimidacao",
        "percepcao",
        "sobrevivencia",
    },
    "monge": {"acrobacia", "atletismo", "historia", "intuicao", "religiao", "furtividade"},
    "paladino": {"atletismo", "intuicao", "intimidacao", "medicina", "persuasao", "religiao"},
    "guardiao": {
        "adestrar_animais",
        "atletismo",
        "intuicao",
        "investigacao",
        "natureza",
        "percepcao",
        "furtividade",
        "sobrevivencia",
    },
    "ladino": {
        "acrobacia",
        "atletismo",
        "enganacao",
        "intuicao",
        "intimidacao",
        "investigacao",
        "percepcao",
        "persuasao",
        "prestidigitacao",
        "furtividade",
    },
    "feiticeiro": {"arcanismo", "enganacao", "intuicao", "intimidacao", "persuasao", "religiao"},
    "bruxo": {"arcanismo", "enganacao", "historia", "intimidacao", "investigacao", "natureza", "religiao"},
    "mago": {"arcanismo", "historia", "intuicao", "investigacao", "medicina", "religiao"},
    "artifice": {"arcanismo", "historia", "investigacao", "medicina", "natureza", "percepcao", "prestidigitacao"},
}
FERRAMENTAS_ARTESAO = {
    "Suprimentos de Alquimista",
    "Suprimentos de Cervejeiro",
    "Suprimentos de Calígrafo",
    "Ferramentas de Carpinteiro",
    "Ferramentas de Cartógrafo",
    "Ferramentas de Sapateiro",
    "Utensílios de Cozinheiro",
    "Ferramentas de Vidreiro",
    "Ferramentas de Joalheiro",
    "Ferramentas de Coureiro",
    "Ferramentas de Pedreiro",
    "Suprimentos de Pintor",
    "Ferramentas de Oleiro",
    "Ferramentas de Ferreiro",
    "Ferramentas de Tecelão",
    "Ferramentas de Entalhador",
}
# Opções de ferramenta que alguns antecedentes deixam em aberto.
CATEGORIAS_FERRAMENTA_ANTECEDENTE = {
    "ferramentas de artesão": {"rotulo": "Ferramentas de Artesão", "opcoes": sorted(FERRAMENTAS_ARTESAO)},
    "instrumento musical": {"rotulo": "Instrumento Musical", "opcoes": sorted(INSTRUMENTOS_MUSICAIS)},
    "kit de jogos": {"rotulo": "Kit de Jogos", "opcoes": sorted(KITS_DE_JOGOS)},
}
MARCADORES_FERRAMENTA_EQUIPAMENTO = (
    "Ferramentas de Artesão (a mesma que acima)",
    "Instrumento Musical (o mesmo que acima)",
    "Kit de Jogos (o mesmo que acima)",
    "Kit de Jogos (qualquer um)",
)


def escolha_ferramenta_do_antecedente(antecedente: Any) -> dict[str, Any] | None:
    dados = ANTECEDENTES.get(str(antecedente or "").strip().lower())
    if not dados:
        return None
    texto = str(dados.get("ferramenta") or "").strip().lower()
    if not texto.startswith("escolha "):
        return None
    for categoria, dados_categoria in CATEGORIAS_FERRAMENTA_ANTECEDENTE.items():
        if categoria in texto:
            return {"categoria": categoria, **dados_categoria}
    return None


def rotulo_ferramenta_antecedente(categoria: str, item: str) -> str:
    if categoria in ("instrumento musical", "kit de jogos"):
        return f"{CATEGORIAS_FERRAMENTA_ANTECEDENTE[categoria]['rotulo']} ({item})"
    return item


def equipamento_antecedente_resolvido(antecedente: Any, ferramenta: str | None = None) -> dict[str, Any]:
    dados = ANTECEDENTES.get(str(antecedente or "").strip().lower())
    if not dados:
        return {"A": None, "B": None}
    equipamento = dados.get("equipamento", {})
    if isinstance(equipamento, dict):
        pacote_a, pacote_b = str(equipamento.get("A", "")), str(equipamento.get("B", ""))
    else:
        return {"A": equipamento, "B": None}
    if ferramenta:
        for marcador in MARCADORES_FERRAMENTA_EQUIPAMENTO:
            if marcador in pacote_a:
                pacote_a = pacote_a.replace(marcador, ferramenta)
                break
    return {"A": pacote_a, "B": pacote_b}


QUANTIDADE_PERICIAS_CLASSE = {
    "barbaro": 2,
    "bardo": 3,
    "clerigo": 2,
    "druida": 2,
    "guerreiro": 2,
    "monge": 2,
    "paladino": 2,
    "guardiao": 3,
    "ladino": 4,
    "feiticeiro": 2,
    "bruxo": 2,
    "mago": 2,
    "artifice": 2,
}
PROFICIENCIAS_SALVAGUARDA_CLASSE = {
    "barbaro": ["forca", "constituicao"],
    "bardo": ["destreza", "carisma"],
    "clerigo": ["sabedoria", "carisma"],
    "druida": ["inteligencia", "sabedoria"],
    "guerreiro": ["forca", "constituicao"],
    "monge": ["forca", "destreza"],
    "paladino": ["sabedoria", "carisma"],
    "guardiao": ["forca", "destreza"],
    "ladino": ["destreza", "inteligencia"],
    "feiticeiro": ["constituicao", "carisma"],
    "bruxo": ["sabedoria", "carisma"],
    "mago": ["inteligencia", "sabedoria"],
    "artifice": ["constituicao", "inteligencia"],
}
PROFICIENCIAS_CLASSE = {
    "artifice": {
        "armaduras": ["leves", "medias", "escudos"],
        "armas": ["simples"],
        "ferramentas": ["Ferramentas de Ladrão", "Ferramentas de Funileiro", "um tipo de Ferramentas de Artesão"],
    },
    "barbaro": {"armaduras": ["leves", "medias", "escudos"], "armas": ["simples", "marciais"], "ferramentas": []},
    "bardo": {
        "armaduras": ["leves"],
        "armas": ["simples", "bestas_de_mao", "espadas_longas", "rapieiras", "espadas_curtas"],
        "ferramentas": [],
    },
    "clerigo": {"armaduras": ["leves", "medias", "escudos"], "armas": ["simples"], "ferramentas": []},
    "druida": {
        "armaduras": ["leves", "medias", "escudos"],
        "armas": [
            "simples",
            "clavas",
            "adagas",
            "dardos",
            "azagaias",
            "macas",
            "cajados",
            "cimitarras",
            "foices",
            "fundas",
            "lancas",
        ],
        "ferramentas": [],
    },
    "guerreiro": {
        "armaduras": ["leves", "medias", "pesadas", "escudos"],
        "armas": ["simples", "marciais"],
        "ferramentas": [],
    },
    "monge": {"armaduras": [], "armas": ["simples", "espadas_curtas"], "ferramentas": []},
    "paladino": {
        "armaduras": ["leves", "medias", "pesadas", "escudos"],
        "armas": ["simples", "marciais"],
        "ferramentas": [],
    },
    "guardiao": {"armaduras": ["leves", "medias", "escudos"], "armas": ["simples", "marciais"], "ferramentas": []},
    "ladino": {
        "armaduras": ["leves"],
        "armas": ["simples", "bestas_de_mao", "espadas_longas", "rapieiras", "espadas_curtas"],
        "ferramentas": ["Ferramentas de Ladrão"],
    },
    "feiticeiro": {
        "armaduras": [],
        "armas": ["adagas", "dardos", "fundas", "cajados", "bestas_leves"],
        "ferramentas": [],
    },
    "bruxo": {"armaduras": ["leves"], "armas": ["simples"], "ferramentas": []},
    "mago": {"armaduras": [], "armas": ["adagas", "dardos", "fundas", "cajados", "bestas_leves"], "ferramentas": []},
}


@dataclass
class Personagem:
    nome: str
    especie: str
    classe: str
    nivel: int
    atributos: dict[str, int]
    antecedente: str = ""
    subclasse: str | None = None
    talentos: set[str] = field(default_factory=set)
    classes_multiclasse: dict[str, int] = field(default_factory=dict)
    escolhas_talentos: dict[str, str] = field(default_factory=dict)
    pericias_classe: set[str] = field(default_factory=set)
    ferramenta_artesao: str | None = None
    heranca_draconica: str | None = None
    ferramenta_antecedente: str | None = None
    equipamento_antecedente: str | None = None
    equipamento_classe: str | None = None
    truques_artifice: list[str] = field(default_factory=list)
    magias_preparadas_artifice: list[str] = field(default_factory=list)
    id: str | None = None

    @property
    def bonus_proficiencia(self) -> int:
        return 2 + (self.nivel - 1) // 4

    @property
    def pontos_de_vida_iniciais(self) -> int:
        dado = CLASSES[self.classe]["dado_vida"]
        return dado + ((self.atributos.get("constituicao", 10) - 10) // 2)


def validar_atributos(atributos: Mapping[str, int]) -> dict[str, int]:
    if set(atributos) != ATRIBUTOS:
        raise ValueError("É necessário informar exatamente os seis atributos")
    valores = {nome: int(valor) for nome, valor in atributos.items()}
    if any(valor < 1 or valor > 20 for valor in valores.values()):
        raise ValueError("Atributos devem estar entre 1 e 20")
    return valores


def gerar_atributos_matriz_padrao() -> dict[str, int]:
    return {"forca": 15, "destreza": 14, "constituicao": 13, "inteligencia": 12, "sabedoria": 10, "carisma": 8}


def gerar_atributos_compra_pontos(pontos: Mapping[str, int]) -> dict[str, int]:
    valores = validar_atributos(pontos)
    custo = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
    if any(valor not in custo for valor in valores.values()) or sum(custo[valor] for valor in valores.values()) > 27:
        raise ValueError("Compra por pontos inválida: máximo de 27 pontos e valores de 8 a 15")
    return valores


def criar_personagem(fatos: Mapping[str, Any]) -> Personagem:
    especie = str(fatos["species"]).lower()
    classe = str(fatos["class"]).lower()
    nivel = int(fatos.get("level", 1))
    if especie not in ESPECIES:
        raise ValueError("Espécie inválida")
    if classe not in CLASSES:
        raise ValueError("Classe inválida")
    if not 1 <= nivel <= 20:
        raise ValueError("O nível deve estar entre 1 e 20")
    atributos = validar_atributos(fatos["ability_scores"])
    subclasse = fatos.get("subclass")
    if subclasse:
        subclasse = str(subclasse).lower()
        if nivel < SUBCLASSES[classe]["nivel"]:
            raise ValueError("A subclasse só pode ser escolhida no nível adequado")
        catalogadas = subclasses_da_classe(classe)
        if catalogadas and subclasse not in catalogadas:
            raise ValueError("Subclasse inválida para a classe escolhida")
        # Subclasses não detalhadas ainda permanecem aceitas para permitir a expansão
        # progressiva do catálogo das classes do Livro do Jogador.
        if subclasse in SUBCLASSES_RAVENLOFT and SUBCLASSES_RAVENLOFT[subclasse]["classe"] != classe:
            raise ValueError("A subclasse não pertence à classe escolhida")
    talentos = set(fatos.get("feats", ()))
    if not talentos <= TALENTOS:
        raise ValueError("Talento inválido")
    pericias_classe: set[str] = set()
    if "class_skill_proficiencies" in fatos or "pericias_classe" in fatos:
        brutas = fatos.get("class_skill_proficiencies", fatos.get("pericias_classe")) or []
        pericias_classe = {str(p).strip().lower().replace(" ", "_") for p in brutas}
        quantidade = QUANTIDADE_PERICIAS_CLASSE[classe]
        if len(pericias_classe) != len(brutas):
            raise ValueError("Não repita perícias de classe")
        if len(pericias_classe) != quantidade:
            raise ValueError(f"A classe {classe} exige escolher exatamente {quantidade} perícias")
        invalidas = pericias_classe - PERICIAS_CLASSE_OPCOES[classe]
        if invalidas:
            raise ValueError("Perícia não disponível para esta classe: " + ", ".join(sorted(invalidas)))
    equipamento_classe = fatos.get("class_equipment", fatos.get("equipamento_classe"))
    if equipamento_classe is not None:
        equipamento_classe = str(equipamento_classe).strip().upper()
        if classe != "artifice" or equipamento_classe not in EQUIPAMENTO_INICIAL_ARTIFICE:
            raise ValueError("Escolha de equipamento inicial inválida para esta classe")
    ferramenta_artesao = fatos.get("artisan_tool_proficiency", fatos.get("ferramenta_artesao"))
    if ferramenta_artesao:
        ferramenta_artesao = str(ferramenta_artesao).strip()
        if classe != "artifice" or ferramenta_artesao not in FERRAMENTAS_ARTESAO:
            raise ValueError("Ferramenta de artesão inválida para esta classe")
    elif classe == "artifice" and ("class_skill_proficiencies" in fatos or "pericias_classe" in fatos):
        raise ValueError("Escolha um tipo de Ferramentas de Artesão para o Artífice")
    antecedente = str(fatos.get("background", "")).strip().lower()
    if antecedente in ANTECEDENTES:
        if "background_increases" in fatos:
            atributos = aplicar_aumentos_antecedente(antecedente, atributos, fatos["background_increases"])
        talento_origem = _talento_do_antecedente(antecedente, fatos.get("background_feat"))
        if talento_origem:
            talentos.add(talento_origem)
    elif fatos.get("background_increases") or fatos.get("background_feat"):
        raise ValueError("Antecedente inválido")
    escolha_ferramenta = escolha_ferramenta_do_antecedente(antecedente)
    ferramenta_antecedente = fatos.get("background_tool", fatos.get("ferramenta_antecedente"))
    if ferramenta_antecedente:
        ferramenta_antecedente = str(ferramenta_antecedente).strip()
        if not escolha_ferramenta or ferramenta_antecedente not in escolha_ferramenta["opcoes"]:
            raise ValueError(f"Ferramenta inválida para o antecedente {antecedente}")
    equipamento_antecedente = fatos.get("background_equipment", fatos.get("equipamento_antecedente"))
    if equipamento_antecedente is not None:
        equipamento_antecedente = str(equipamento_antecedente).strip().upper()
        if equipamento_antecedente not in ("A", "B"):
            raise ValueError("Escolha o equipamento de antecedente A ou B")
    heranca_draconica = fatos.get("species_choice", fatos.get("heranca_draconica"))
    if heranca_draconica:
        heranca_draconica = normalizar_escolha(especie, heranca_draconica)
    if not str(fatos.get("name", "")).strip():
        raise ValueError("O personagem precisa de um nome")
    escolha_origem = str(fatos.get("background_feat") or ANTECEDENTES.get(antecedente, {}).get("talento", ""))
    escolhas = (
        {"iniciado_em_magia": escolha_origem.split(":", 1)[1]}
        if escolha_origem.startswith("iniciado_em_magia:")
        else {}
    )

    cantrip_keys = ("artificer_cantrips", "truques_artifice")
    prepared_keys = ("artificer_prepared_spells", "magias_preparadas_artifice")
    cantrips_supplied = any(key in fatos for key in cantrip_keys)
    prepared_supplied = any(key in fatos for key in prepared_keys)
    if classe != "artifice" and (cantrips_supplied or prepared_supplied):
        raise ValueError("Escolhas de magia de Artífice só podem ser informadas para essa classe")
    truques_artifice: list[str] = []
    magias_preparadas_artifice: list[str] = []
    if classe == "artifice" and (cantrips_supplied or prepared_supplied):
        if not (cantrips_supplied and prepared_supplied):
            raise ValueError("Informe juntos os truques e as magias preparadas do Artífice")
        truques_artifice = list(fatos.get("artificer_cantrips", fatos.get("truques_artifice")) or [])
        magias_preparadas_artifice = list(
            fatos.get("artificer_prepared_spells", fatos.get("magias_preparadas_artifice")) or []
        )
        from .spellcasting import progresso_artifice, validar_escolhas_artifice

        progress = progresso_artifice(nivel, atributos["inteligencia"])
        validar_escolhas_artifice(
            nivel, atributos["inteligencia"], truques_artifice,
            magias_preparadas_artifice, progress["espacos_totais"], subclasse,
        )

    return Personagem(
        nome=str(fatos["name"]).strip(),
        especie=especie,
        classe=classe,
        nivel=nivel,
        atributos=atributos,
        antecedente=antecedente,
        subclasse=subclasse,
        talentos=talentos,
        escolhas_talentos=escolhas,
        pericias_classe=pericias_classe,
        ferramenta_artesao=ferramenta_artesao,
        heranca_draconica=heranca_draconica,
        ferramenta_antecedente=ferramenta_antecedente,
        equipamento_antecedente=equipamento_antecedente,
        equipamento_classe=equipamento_classe,
        truques_artifice=truques_artifice,
        magias_preparadas_artifice=magias_preparadas_artifice,
        id=(str(fatos.get("character_id") or fatos.get("id") or "").strip() or None),
    )


def _talento_do_antecedente(antecedente: str, escolha: Any = None) -> str | None:
    """Talento concedido pelo antecedente; Dádivas Sombrias exigem escolha explícita."""
    dados = ANTECEDENTES[antecedente]
    padrao = dados["talento"].split(":")[0]
    escolha = str(escolha).strip().lower() if escolha else None
    aceita_dadiva = padrao == "dadiva_sombria" or "dadiva_sombria" in dados["talentos_alternativos"]
    if escolha in (None, padrao, dados["talento"]):
        if padrao == "dadiva_sombria":
            raise ValueError("Escolha uma Dádiva Sombria para este antecedente")
        return padrao
    if aceita_dadiva and escolha in DARK_GIFT_FEATS:
        return escolha
    raise ValueError("Talento incompatível com o antecedente")


def modificador(valor: int) -> int:
    return (valor - 10) // 2


def _inventario_inicial_artifice(personagem: Personagem) -> dict[str, Any] | None:
    """Constrói itens reais do pacote inicial, prontos para persistir no inventário."""
    if personagem.classe != "artifice":
        return None
    escolha = personagem.equipamento_classe
    if escolha is None:
        return {
            "resultado": "escolha",
            "opcoes": {
                chave: {"itens": list(dados["itens"]), "ouro": dados["ouro"]}
                for chave, dados in EQUIPAMENTO_INICIAL_ARTIFICE.items()
            },
        }
    if escolha == "B":
        return {"resultado": "pronto", "escolha": "B", "itens": [], "ouro": 150}
    if not personagem.id:
        return {
            "resultado": "requer_dados",
            "motivo": "character_id_necessario_para_ids_unicos_de_inventario",
            "escolha": "A",
            "itens_sem_ids": list(EQUIPAMENTO_INICIAL_ARTIFICE["A"]["itens"]),
            "ouro": 16,
        }

    from .catalog import CATALOGO_ARMADURAS, CATALOGO_ARMAS, CATALOGO_EQUIPAMENTOS

    prefix = f"{personagem.id}:artifice-inicial"
    inventario: list[dict[str, Any]] = []
    indice = 0
    for nome in EQUIPAMENTO_INICIAL_ARTIFICE["A"]["itens"]:
        indice += 1
        item_id = f"{prefix}:{indice}"
        if nome == "Armadura de Couro Batido":
            dados = CATALOGO_ARMADURAS.get("Couro Batido")
            tipo_item = "armadura"
        elif nome in CATALOGO_ARMAS:
            dados = CATALOGO_ARMAS[nome]
            tipo_item = "arma"
        elif nome == "Pacote de Exploração de Masmorras":
            dados = CATALOGO_EQUIPAMENTOS.get(nome)
            tipo_item = "pacote"
        else:
            dados = CATALOGO_EQUIPAMENTOS.get(nome)
            tipo_item = "ferramenta" if dados and dados.get("categoria") == "ferramenta" else "equipamento"

        if not isinstance(dados, dict):
            return {"resultado": "erro_catalogo", "motivo": "item_inicial_sem_dados_mecanicos", "item": nome}
        if tipo_item != "pacote":
            inventario.append({
                **dict(dados),
                "id": item_id,
                "nome": nome,
                "quantidade": 1,
                "tipo_item": tipo_item,
                "origem": "equipamento_inicial_artifice",
            })
            continue

        # O pacote existe como recipiente, mas seu peso é contabilizado pelos
        # itens internos, não novamente pelo peso total agregado do pacote.
        conteudo_catalogo = dados.get("conteudo")
        if not isinstance(conteudo_catalogo, list):
            return {"resultado": "erro_catalogo", "motivo": "pacote_sem_conteudo_estruturado", "item": nome}
        ids_conteudo: list[str] = []
        id_pacote = item_id
        inventario.append({
            **dict(dados),
            "id": id_pacote,
            "nome": nome,
            "peso": 0,
            "quantidade": 1,
            "tipo_item": "recipiente",
            "peso_declarado_com_conteudo": dados.get("peso", 0),
            "conteudo_ids": ids_conteudo,
            "origem": "equipamento_inicial_artifice",
        })
        for conteudo in conteudo_catalogo:
            nome_conteudo = str(conteudo.get("nome", ""))
            dados_conteudo = CATALOGO_EQUIPAMENTOS.get(nome_conteudo)
            if not isinstance(dados_conteudo, dict):
                return {"resultado": "erro_catalogo", "motivo": "conteudo_de_pacote_sem_dados_mecanicos",
                        "pacote": nome, "item": nome_conteudo}
            indice += 1
            id_conteudo = f"{prefix}:{indice}"
            ids_conteudo.append(id_conteudo)
            inventario.append({
                **dict(dados_conteudo),
                "id": id_conteudo,
                "nome": nome_conteudo,
                "quantidade": int(conteudo.get("quantidade", 1)),
                "container_id": id_pacote,
                "tipo_item": "equipamento",
                "origem": "pacote_exploracao_masmorras",
            })
        inventario[indice - len(conteudo_catalogo) - 1]["conteudo_ids"] = list(ids_conteudo)

    soma_peso = sum(float(item.get("peso", 0)) * int(item.get("quantidade", 1)) for item in inventario)
    peso_catalogo_pacote = float(CATALOGO_EQUIPAMENTOS["Pacote de Exploração de Masmorras"]["peso"])
    if abs(soma_peso - (peso_catalogo_pacote + sum(
        float(d.get("peso", 0)) for name, d in
        [(n, CATALOGO_ARMADURAS.get("Couro Batido", {})) if n == "Armadura de Couro Batido"
         else (n, CATALOGO_ARMAS.get(n, CATALOGO_EQUIPAMENTOS.get(n, {})))
         for n in EQUIPAMENTO_INICIAL_ARTIFICE["A"]["itens"] if n != "Pacote de Exploração de Masmorras"]
    ))) > 0.01:
        return {"resultado": "erro_catalogo", "motivo": "peso_do_pacote_nao_confere_com_seus_itens"}
    return {
        "resultado": "pronto",
        "escolha": "A",
        "itens": inventario,
        "ouro": 16,
        "peso_total": soma_peso,
        "aplicar_com": "resolver_inventario",
    }


def ficha_personagem(personagem: Personagem) -> dict[str, Any]:
    """Valores derivados pelo motor para exibir e persistir a ficha."""
    antecedente = ANTECEDENTES.get(personagem.antecedente)
    pv = personagem.pontos_de_vida_iniciais
    if personagem.nivel > 1:
        dado = CLASSES[personagem.classe]["dado_vida"]
        pv += (personagem.nivel - 1) * (dado // 2 + 1 + modificador(personagem.atributos["constituicao"]))
    if "vigoroso" in personagem.talentos:
        pv += 2 * personagem.nivel
    pericias_antecedente = list(antecedente["pericias"]) if antecedente else []
    pericias_classe = sorted(personagem.pericias_classe)
    pericias_totais = list(dict.fromkeys([*pericias_antecedente, *pericias_classe]))
    escolha_ferramenta = escolha_ferramenta_do_antecedente(personagem.antecedente)
    ferramenta_resolvida = None
    if antecedente:
        if escolha_ferramenta:
            if personagem.ferramenta_antecedente:
                ferramenta_resolvida = rotulo_ferramenta_antecedente(
                    escolha_ferramenta["categoria"], personagem.ferramenta_antecedente
                )
        else:
            ferramenta_resolvida = antecedente["ferramenta"]
    ferramenta_pendente = bool(antecedente and escolha_ferramenta and not personagem.ferramenta_antecedente)
    equipamento_pendente = bool(antecedente and not personagem.equipamento_antecedente)
    pacotes = equipamento_antecedente_resolvido(personagem.antecedente, ferramenta_resolvida)
    escolhas_pendentes: list[str] = []
    if len(pericias_classe) != QUANTIDADE_PERICIAS_CLASSE[personagem.classe]:
        escolhas_pendentes.append("Perícias de classe")
    if personagem.classe == "artifice" and not personagem.ferramenta_artesao:
        escolhas_pendentes.append("Ferramentas de Artesão (classe)")
    escolha_especie = escolha_de_especie(personagem.especie)
    if escolha_especie and not personagem.heranca_draconica:
        escolhas_pendentes.append(escolha_especie["rotulo"])
    if ferramenta_pendente:
        escolhas_pendentes.append(f"{escolha_ferramenta['rotulo']} (antecedente)")
    if equipamento_pendente:
        escolhas_pendentes.append("Equipamento de antecedente (A ou B)")
    equipamento_classe_pendente = personagem.classe == "artifice" and not personagem.equipamento_classe
    if equipamento_classe_pendente:
        escolhas_pendentes.append("Equipamento inicial de Artífice (A ou B)")

    classe_de_armadura: dict[str, Any] = {}
    from .magic_equipment import calcular_ca

    modificador_destreza = modificador(personagem.atributos["destreza"])
    classe_de_armadura["sem_armadura"] = calcular_ca({
        "armor": "nenhuma",
        "dexterity_modifier": modificador_destreza,
        "armor_proficient": True,
    })["ca"]
    classe_de_armadura["com_escudo"] = classe_de_armadura["sem_armadura"] + 2
    classe_de_armadura["nota_escudo"] = "Hipótese de escudo equipado; o equipamento inicial do Artífice não inclui escudo."
    classe_de_armadura["armadura_inicial"] = None
    if personagem.classe == "artifice" and personagem.equipamento_classe == "A":
        from .catalog import CATALOGO_ARMADURAS

        armadura_inicial = CATALOGO_ARMADURAS["Couro Batido"]
        ca_armadura = calcular_ca({
            "armor": armadura_inicial["categoria"],
            "armor_bonus": int(armadura_inicial["ca"]) - 10,
            "dexterity_modifier": modificador_destreza,
            "armor_proficient": True,
        })
        classe_de_armadura["armadura_inicial"] = {
            "nome": "Armadura de Couro Batido",
            "ca": ca_armadura["ca"],
            "base": int(armadura_inicial["ca"]),
            "equipada_automaticamente": False,
        }

    conjuracao_artifice = None
    recursos_iniciais_artifice = None
    if personagem.classe == "artifice":
        from .spellcasting import progresso_artifice

        progresso_magico = progresso_artifice(personagem.nivel, personagem.atributos["inteligencia"])
        truques_corretos = len(personagem.truques_artifice) == progresso_magico["truques"]
        preparadas_corretas = len(personagem.magias_preparadas_artifice) == progresso_magico["magias_preparadas"]
        if not truques_corretos:
            escolhas_pendentes.append("Truques de Artífice")
        if not preparadas_corretas:
            escolhas_pendentes.append("Magias preparadas de Artífice")
        modificador_int = modificador(personagem.atributos["inteligencia"])
        recursos_iniciais_artifice = {
            "magia_de_artifice": {"usos_gastos": 0, "usos_maximos": max(1, modificador_int)},
            "espacos_de_magia": {
                "espacos_restantes": dict(progresso_magico["espacos_totais"]),
                "usos_gastos": {circulo: 0 for circulo in progresso_magico["espacos_totais"]},
            },
            "troca_truque_disponivel": False,
            "mudanca_magias_preparadas_disponivel": False,
            "itens_tinkers_criados": [],
        }
        conjuracao_artifice = {
            **progresso_magico,
            "atributo_conjuracao": "inteligencia",
            "cd_magia": 8 + personagem.bonus_proficiencia + modificador_int,
            "ataque_magia": personagem.bonus_proficiencia + modificador_int,
            "truques_conhecidos": list(personagem.truques_artifice),
            "magias_preparadas": list(personagem.magias_preparadas_artifice),
            "truque_concedido": "Reparar",
            "caracteristica_de_classe": "Magia de Artífice",
            "escolhas_completas": truques_corretos and preparadas_corretas,
            "foco_magico": [
                "Ferramentas de Ladrão", "Ferramentas de Funileiro",
                "Ferramentas de Artesão com proficiência",
            ],
            "espacos_totais": dict(progresso_magico["espacos_totais"]),
        }

    return {
        "id": personagem.id,
        "nome": personagem.nome,
        "especie": personagem.especie,
        "classe": personagem.classe,
        "subclasse": personagem.subclasse,
        "nivel": personagem.nivel,
        "antecedente": personagem.antecedente or None,
        "atributos": dict(personagem.atributos),
        "modificadores": {nome: modificador(valor) for nome, valor in personagem.atributos.items()},
        "bonus_proficiencia": personagem.bonus_proficiencia,
        "pv_maximo": max(1, pv),
        "dado_vida": CLASSES[personagem.classe]["dado_vida"],
        "tamanho": ESPECIES[personagem.especie]["tamanho"],
        "deslocamento": ESPECIES[personagem.especie]["deslocamento"],
        "talentos": sorted(personagem.talentos),
        "escolhas_talentos": dict(personagem.escolhas_talentos),
        "pericias": pericias_totais,
        "pericias_antecedente": pericias_antecedente,
        "pericias_classe": pericias_classe,
        "quantidade_pericias_classe": QUANTIDADE_PERICIAS_CLASSE[personagem.classe],
        "proficiencias_salvaguarda": list(PROFICIENCIAS_SALVAGUARDA_CLASSE[personagem.classe]),
        "proficiencias_classe": {
            **dict(PROFICIENCIAS_CLASSE.get(personagem.classe, {})),
            **(
                {
                    "ferramentas": [
                        "Ferramentas de Ladrão",
                        "Ferramentas de Funileiro",
                        *([personagem.ferramenta_artesao] if personagem.ferramenta_artesao else []),
                    ]
                }
                if personagem.classe == "artifice"
                else {}
            ),
        },
        "ferramenta_artesao": personagem.ferramenta_artesao,
        "heranca_draconica": (
            bloco_heranca_draconica(
                personagem.heranca_draconica,
                personagem.nivel,
                modificador(personagem.atributos["constituicao"]),
                personagem.bonus_proficiencia,
            )
            if escolha_de_especie(personagem.especie) and personagem.heranca_draconica
            else None
        ),
        "proficiencias_pendentes": (
            len(pericias_classe) != QUANTIDADE_PERICIAS_CLASSE[personagem.classe]
            or (personagem.classe == "artifice" and not personagem.ferramenta_artesao)
        ),
        "ferramenta": ferramenta_resolvida,
        "ferramenta_antecedente": personagem.ferramenta_antecedente,
        "ferramenta_pendente": ferramenta_pendente,
        "equipamento_antecedente": {**pacotes, "escolha": personagem.equipamento_antecedente},
        "equipamento_pendente": equipamento_pendente,
        "equipamento_classe": (
            {
                **EQUIPAMENTO_INICIAL_ARTIFICE[personagem.equipamento_classe],
                "escolha": personagem.equipamento_classe,
                "itens": [
                    personagem.ferramenta_artesao if item == "Ferramentas de Artesão (mesmas escolhidas na proficiência)" else item
                    for item in EQUIPAMENTO_INICIAL_ARTIFICE[personagem.equipamento_classe]["itens"]
                ],
            }
            if personagem.classe == "artifice" and personagem.equipamento_classe
            else {"A": EQUIPAMENTO_INICIAL_ARTIFICE["A"], "B": EQUIPAMENTO_INICIAL_ARTIFICE["B"], "escolha": None}
            if personagem.classe == "artifice"
            else None
        ),
        "equipamento_classe_pendente": equipamento_classe_pendente,
        "inventario_inicial": _inventario_inicial_artifice(personagem),
        "caracteristicas_classe": caracteristicas_no_nivel(personagem.classe, personagem.nivel),
        "conjuracao": conjuracao_artifice,
        "recursos_iniciais": recursos_iniciais_artifice,
        "classe_de_armadura": classe_de_armadura,
        "escolhas_pendentes": list(dict.fromkeys(escolhas_pendentes)),
    }


def resolver_progressao(fatos: Mapping[str, Any]) -> dict[str, Any]:
    nivel_atual = int(fatos["current_level"])
    novo_nivel = nivel_atual + 1
    classe = str(fatos["class"]).lower()
    if classe not in CLASSES or not 1 <= nivel_atual < 20:
        raise ValueError("Progressão de nível inválida")
    resultado: dict[str, Any] = {"resultado": "nivel_adquirido", "nivel": novo_nivel}
    asi_niveis = {"guerreiro": {4, 6, 8, 12, 14, 16, 19}, "ladino": {4, 8, 10, 12, 16, 19}}
    if novo_nivel in asi_niveis.get(classe, {4, 8, 12, 16, 19}):
        resultado["escolha"] = (
            "dadiva_epica_ou_talento" if classe == "artifice" and novo_nivel == 19
            else "aumento_de_atributo_ou_talento"
        )
    if novo_nivel == 3:
        resultado["escolha_subclasse"] = True
    resultado["bonus_proficiencia"] = 2 + (novo_nivel - 1) // 4
    resultado["caracteristicas"] = caracteristicas_no_nivel(classe, novo_nivel)
    return resultado


def resolver_multiclasse(fatos: Mapping[str, Any]) -> dict[str, Any]:
    atributos = validar_atributos(fatos["ability_scores"])
    classe = str(fatos["new_class"]).lower()
    if classe not in CLASSES:
        raise ValueError("Classe inválida para multiclasse")
    requisitos = {
        "barbaro": {"forca": 13},
        "guerreiro": {"forca": 13, "destreza": 13},
        "paladino": {"forca": 13, "carisma": 13},
        "guardiao": {"destreza": 13, "sabedoria": 13},
        "monge": {"destreza": 13, "sabedoria": 13},
        "ladino": {"destreza": 13},
        "bardo": {"carisma": 13},
        "clerigo": {"sabedoria": 13},
        "druida": {"sabedoria": 13},
        "feiticeiro": {"carisma": 13},
        "bruxo": {"carisma": 13},
        "mago": {"inteligencia": 13},
        "artifice": {"inteligencia": 13},
    }[classe]
    valido = all(atributos[nome] >= valor for nome, valor in requisitos.items())
    return {"resultado": "permitido" if valido else "bloqueado", "requisitos": requisitos}
