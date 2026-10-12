"""Adaptador HTTP da experiência de criação ao Rule Engine do projeto.

Este módulo não contém cálculos de regras: consulta os catálogos e resolvers
existentes, valida a criação pelo ``character_creation`` do motor e persiste
apenas o registro que o motor aceitou. A camada de aplicação mantém, em um
bloco separado, escolhas de ficha que o modelo mecânico atual ainda não guarda.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from rule_engine import (
    ANTECEDENTES,
    CLASSES,
    ESPECIES,
    FEATS,
    FEATURES_BY_CLASS,
    ORIGIN_FEATS,
    SUBCLASSES_RAVENLOFT,
    TRACOS_ESPECIE,
    aplicar_aumentos_antecedente,
    build_default_engine,
    caracteristicas_no_nivel,
    custo_compra_pontos,
    ficha_personagem,
    modificador,
    obter_magia,
    subclasses_da_classe,
)
from rule_engine.ability_checks import PERICIAS
from rule_engine.backgrounds import DADIVA_RECOMENDADA
from rule_engine.character import (
    CUSTO_COMPRA_PONTOS,
    FERRAMENTAS_ARTESAO,
    PERICIAS_CLASSE_OPCOES,
    PROFICIENCIAS_CLASSE,
    PROFICIENCIAS_SALVAGUARDA_CLASSE,
    QUANTIDADE_PERICIAS_CLASSE,
    escolha_ferramenta_do_antecedente,
)
from rule_engine.feats import DARK_GIFT_FEATS
from rule_engine.species import (
    ANCESTRALIDADES_GIGANTES,
    HERANCA_DRACONICA,
    LEGADOS_INFEROS,
    LINHAGENS_ELFICAS,
    LINHAGENS_GNOMICAS,
)
from rule_engine.spell_lists import CLASSES_CONJURADORAS
from rule_engine.spellcasting import (
    ARTIFICER_SPELL_LEVELS,
    ARTIFICER_SUBCLASS_SPELLS,
    listar_magias_artifice,
    progresso_artifice,
    validar_escolhas_artifice,
)

RULESET = "D&D 5e 2024 — motor do projeto"
ARTIFICER_NOTE = (
    "O Artífice não faz parte do PHB 2024. O repositório combina uma escada de "
    "características legada com helpers de conjuração do Artífice e listas parciais "
    "de suplementos. O motor calcula níveis, atributo, espaços e escolhas de magia "
    "neste fluxo; não implementa o catálogo/validação das infusões nem as "
    "características de item mágico dos níveis 6, 10 e 18. A única subclasse de "
    "Artífice catalogada para criação é Reanimador, sem resolver suas características."
)

ABILITY_LABELS = {
    "forca": "Força",
    "destreza": "Destreza",
    "constituicao": "Constituição",
    "inteligencia": "Inteligência",
    "sabedoria": "Sabedoria",
    "carisma": "Carisma",
}
SKILL_LABELS = {
    "acrobacia": "Acrobacia",
    "adestrar_animais": "Adestrar Animais",
    "arcanismo": "Arcanismo",
    "atletismo": "Atletismo",
    "atuacao": "Atuação",
    "enganacao": "Enganação",
    "furtividade": "Furtividade",
    "historia": "História",
    "intuicao": "Intuição",
    "intimidacao": "Intimidação",
    "investigacao": "Investigação",
    "medicina": "Medicina",
    "natureza": "Natureza",
    "percepcao": "Percepção",
    "persuasao": "Persuasão",
    "prestidigitacao": "Prestidigitação",
    "religiao": "Religião",
    "sobrevivencia": "Sobrevivência",
}
CLASS_LABELS = {
    "barbaro": "Bárbaro",
    "bardo": "Bardo",
    "clerigo": "Clérigo",
    "druida": "Druida",
    "guerreiro": "Guerreiro",
    "monge": "Monge",
    "paladino": "Paladino",
    "guardiao": "Guardião",
    "ladino": "Ladino",
    "feiticeiro": "Feiticeiro",
    "bruxo": "Bruxo",
    "mago": "Mago",
    "artifice": "Artífice",
}
SPECIES_LABELS = {
    "aasimar": "Aasimar",
    "anao": "Anão",
    "draconato": "Draconato",
    "elfo": "Elfo",
    "gnomo": "Gnomo",
    "golias": "Golias",
    "halfling": "Pequenino",
    "humano": "Humano",
    "orc": "Orc",
    "tiefling": "Tiferino",
}
FEATURE_CHOICE_LABELS = {
    "ordem_divina": "Ordem Divina",
    "ordem_primal": "Ordem Primal",
    "estilo_de_luta": "Estilo de Luta",
    "invocacoes_misticas": "Invocações Místicas",
}
OPTION_LABELS = {
    "dominio_de_vida": "Domínio da Vida",
    "potencializar_cura": "Potencializar Cura",
    "mago": "Mago",
    "combatente": "Combatente",
    "arquearia": "Arquearia",
    "combate_com_armas_de_arremesso": "Combate com Armas de Arremesso",
    "combate_com_armas_grandes": "Combate com Armas Grandes",
    "combate_com_duas_armas": "Combate com Duas Armas",
    "combate_desarmado": "Combate Desarmado",
    "defensivo": "Defensivo",
    "duelismo": "Duelismo",
    "interceptacao": "Interceptação",
    "luta_as_cegas": "Luta às Cegas",
    "protetivo": "Protetivo",
    "armadura_de_sombras": "Armadura de Sombras",
    "mente_mistica": "Mente Mística",
    "pacto_da_corrente": "Pacto da Corrente",
    "pacto_da_lamina": "Pacto da Lâmina",
    "pacto_do_tomo": "Pacto do Tomo",
    "forca": "Força",
    "destreza": "Destreza",
    "pequeno": "Pequeno",
    "medio": "Médio",
    "mediano": "Médio",
    "alto_elfo": "Alto Elfo",
    "drow": "Drow",
    "silvestre": "Elfo Silvestre",
    "rochas": "Gnomo das Rochas",
    "bosque": "Gnomo do Bosque",
    "arrepio_do_gelo": "Arrepio do Gelo",
    "queimadura_de_fogo": "Queimadura de Fogo",
    "resistencia_da_pedra": "Resistência da Pedra",
    "salto_da_nuvem": "Salto da Nuvem",
    "tombo_da_colina": "Tombo da Colina",
    "trovao_da_tempestade": "Trovão da Tempestade",
    "abissal": "Abissal",
    "ctonico": "Ctônico",
    "infernal": "Infernal",
    "azul": "Azul",
    "branco": "Branco",
    "bronze": "Bronze",
    "cobre": "Cobre",
    "latao": "Latão",
    "negro": "Negro",
    "ouro": "Ouro",
    "prata": "Prata",
    "verde": "Verde",
    "vermelho": "Vermelho",
}


class CreationError(ValueError):
    """Erro de entrada conhecido e seguro para retornar à interface."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field


class PersistenceError(RuntimeError):
    """A gravação durável não foi confirmada."""


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted(_jsonable(item) for item in value)
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return {name: _jsonable(getattr(value, name)) for name in value.__dataclass_fields__}
    return value


def _normalizar(valor: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "").strip().lower())
    return "".join(char for char in texto if not unicodedata.combining(char)).replace("-", "_").replace(" ", "_")


def _humanizar(chave: Any) -> str:
    texto = str(chave or "").replace("_", " ").replace("-", " ").strip()
    if not texto:
        return ""
    substituicoes = {
        "dadiva": "Dádiva",
        "epica": "Épica",
        "mistica": "Mística",
        "magia": "Magia",
        "artifice": "Artífice",
        "artifista": "Artifista",
        "clerigo": "Clérigo",
        "guardiao": "Guardião",
        "anao": "Anão",
        "pequenino": "Pequenino",
        "intuicao": "Intuição",
        "percepcao": "Percepção",
        "sobrevivencia": "Sobrevivência",
        "prestidigitacao": "Prestidigitação",
        "investigacao": "Investigação",
        "inteligencia": "Inteligência",
        "constituicao": "Constituição",
        "carisma": "Carisma",
        "sabedoria": "Sabedoria",
        "forca": "Força",
        "destreza": "Destreza",
        "acao": "Ação",
        "reacao": "Reação",
        "energia": "Energia",
    }
    palavras = []
    for palavra in texto.split():
        palavras.append(substituicoes.get(_normalizar(palavra), palavra.capitalize()))
    return " ".join(palavras)


def _parse_int(value: Any, *, field: str, label: str) -> int:
    if isinstance(value, bool):
        raise CreationError(f"{label}: informe um número inteiro.", field)
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise CreationError(f"{label}: informe um número inteiro.", field) from exc
    return parsed


def _compactar_resultado(resultado: Mapping[str, Any]) -> dict[str, Any]:
    return {key: _jsonable(value) for key, value in resultado.items() if key not in {"trace"}}


class CharacterStore:
    """Pequeno repositório SQLite; uma resposta de sucesso só sai após COMMIT."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with closing(self._connect()) as connection:
                with connection:
                    connection.execute(
                        """
                        CREATE TABLE IF NOT EXISTS characters (
                            id TEXT PRIMARY KEY,
                            name TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            completeness TEXT NOT NULL,
                            payload TEXT NOT NULL
                        )
                        """
                    )
                    connection.execute("CREATE INDEX IF NOT EXISTS characters_created_at ON characters(created_at DESC)")
        except sqlite3.Error as exc:
            raise PersistenceError("Não foi possível inicializar o armazenamento de fichas.") from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=8)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def save(self, record: Mapping[str, Any]) -> dict[str, Any]:
        character_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        name = str(record["character"]["nome"])
        completeness = str(record["completeness"])
        payload = _jsonable(dict(record))
        payload["id"] = character_id
        payload["created_at"] = created_at
        payload["completeness"] = completeness
        validation = payload.get("validation")
        if isinstance(validation, dict):
            validation["persistence"] = "confirmed"
        try:
            with closing(self._connect()) as connection:
                with connection:
                    connection.execute(
                        "INSERT INTO characters (id, name, created_at, completeness, payload) VALUES (?, ?, ?, ?, ?)",
                        (character_id, name, created_at, completeness, json.dumps(payload, ensure_ascii=False)),
                    )
            # The transaction commits before control reaches this return.
        except sqlite3.Error as exc:
            raise PersistenceError("A ficha não foi salva. Tente novamente; suas escolhas continuam no rascunho.") from exc
        return payload

    def list(self, limit: int = 30) -> list[dict[str, Any]]:
        try:
            with closing(self._connect()) as connection:
                rows = connection.execute(
                    "SELECT id, name, created_at, completeness, payload FROM characters ORDER BY created_at DESC LIMIT ?",
                    (max(1, min(int(limit), 100)),),
                ).fetchall()
        except sqlite3.Error as exc:
            raise PersistenceError("Não foi possível consultar as fichas salvas.") from exc
        try:
            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "created_at": row["created_at"],
                    "completeness": row["completeness"],
                    "character": json.loads(row["payload"])["character"],
                }
                for row in rows
            ]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise PersistenceError("O armazenamento contém uma ficha inválida.") from exc

    def get(self, character_id: str) -> dict[str, Any] | None:
        try:
            with closing(self._connect()) as connection:
                row = connection.execute("SELECT payload FROM characters WHERE id = ?", (character_id,)).fetchone()
        except sqlite3.Error as exc:
            raise PersistenceError("Não foi possível consultar esta ficha.") from exc
        if row is None:
            return None
        try:
            return json.loads(row["payload"])
        except (json.JSONDecodeError, TypeError) as exc:
            raise PersistenceError("Esta ficha está inválida no armazenamento.") from exc


class CharacterCreatorService:
    """Fachada de aplicação sobre o motor e o armazenamento persistente."""

    def __init__(self, store: CharacterStore | None = None):
        self.engine = build_default_engine()
        self.store = store
        self._spell_options_cache: dict[str, list[dict[str, Any]]] = {}

    def health(self) -> dict[str, Any]:
        return {"ok": True, "ruleset": RULESET, "engine": "build_default_engine", "persistence": self.store is not None}

    def catalog(self) -> dict[str, Any]:
        classes = []
        for class_key in sorted(CLASSES):
            class_source = (
                "Conteúdo suplementar — implementação parcial no motor"
                if class_key == "artifice"
                else "Livro do Jogador 2024"
            )
            classes.append(
                {
                    "key": class_key,
                    "label": CLASS_LABELS.get(class_key, _humanizar(class_key)),
                    "hit_die": CLASSES[class_key]["dado_vida"],
                    "primary_ability": CLASSES[class_key]["atributo_primario"],
                    "primary_ability_label": self._attribute_phrase(CLASSES[class_key]["atributo_primario"]),
                    "skill_count": QUANTIDADE_PERICIAS_CLASSE[class_key],
                    "skill_options": [
                        {"key": skill, "label": SKILL_LABELS.get(skill, _humanizar(skill))}
                        for skill in sorted(PERICIAS_CLASSE_OPCOES[class_key])
                    ],
                    "saving_throws": [
                        {"key": key, "label": ABILITY_LABELS[key]}
                        for key in PROFICIENCIAS_SALVAGUARDA_CLASSE[class_key]
                    ],
                    "proficiencies": _jsonable(PROFICIENCIAS_CLASSE.get(class_key, {})),
                    "tool_options": sorted(FERRAMENTAS_ARTESAO) if class_key == "artifice" else [],
                    "subclasses": self._subclasses(class_key),
                    "progression": self._progression(class_key),
                    "source": class_source,
                }
            )

        species = []
        for species_key in sorted(TRACOS_ESPECIE):
            resolved = self._species_result(species_key, None, {key: 10 for key in ABILITY_LABELS})
            species.append(
                {
                    "key": species_key,
                    "label": SPECIES_LABELS.get(species_key, _humanizar(species_key)),
                    "size_options": resolved.get("tamanhos", []),
                    "speed_m": resolved.get("deslocamento_m"),
                    "darkvision_m": resolved.get("visao_no_escuro_m"),
                    "resistances": resolved.get("resistencias_dano", []),
                    "traits": [
                        {
                            "name": trait.get("nome"),
                            "effect": trait.get("efeito"),
                            "minimum_level": trait.get("nivel_minimo", 1),
                            "resource": _jsonable(trait.get("recurso")),
                        }
                        for trait in resolved.get("tracos", [])
                    ],
                    "choice": self._species_choice_definition(species_key),
                    "skill_choice": self._species_skill_definition(species_key),
                    "origin_feat_choice": species_key == "humano",
                    "source": "Livro do Jogador 2024",
                }
            )

        backgrounds = []
        for key, background in sorted(ANTECEDENTES.items(), key=lambda item: item[1]["nome"].casefold()):
            tool_choice = escolha_ferramenta_do_antecedente(key)
            backgrounds.append(
                {
                    "key": key,
                    "label": background["nome"],
                    "ability_options": [
                        {"key": ability, "label": ABILITY_LABELS[ability]} for ability in background["atributos"]
                    ],
                    "feat": background["talento"],
                    "feat_label": self._feat_label(background["talento"].split(":", 1)[0]),
                    "alternate_feats": list(background["talentos_alternativos"]),
                    "skills": [
                        {"key": skill, "label": SKILL_LABELS.get(skill, _humanizar(skill))}
                        for skill in background["pericias"]
                    ],
                    "tool": background["ferramenta"],
                    "tool_choice": _jsonable(tool_choice),
                    "equipment": _jsonable(background["equipamento"]),
                    "feat_choice": background["talento"].startswith("dadiva_sombria")
                    or "dadiva_sombria" in background["talentos_alternativos"],
                    "source": background["fonte"],
                    "requires_ravenloft": background["fonte"] == "Ravenloft: Horror Wilds — Antecedentes",
                    "recommended_dark_gift": DADIVA_RECOMENDADA.get(key),
                }
            )

        feats = []
        for feat_key, data in sorted(FEATS.items()):
            feats.append(
                {
                    "key": feat_key,
                    "label": self._feat_label(feat_key),
                    "category": data.get("categoria"),
                    "level": data.get("nivel", 1),
                    "repeatable": data.get("repetivel", False),
                    "requires_spellcasting": data.get("requer_conjuracao", False),
                    "ability_prerequisite": data.get("atributo_13", []),
                    "effects": list(data.get("efeitos", [])),
                    "source": data.get("fonte", "Livro do Jogador 2024"),
                    "requires_ravenloft": data.get("requisito") == "campanha_ravenloft" or data.get("fonte") == "ravenloft",
                }
            )

        skill_catalog = [
            {"key": skill, "label": SKILL_LABELS.get(skill, _humanizar(skill)), "ability": ability}
            for skill, ability in sorted(PERICIAS.items())
        ]
        standard = self.engine.evaluate({"type": "ability_generation", "method": "matriz_padrao"}).outcome["atributos"]
        return {
            "ruleset": RULESET,
            "ruleset_note": "As opções mecânicas vêm dos catálogos e resolvers deste repositório; as fontes adicionais aparecem junto a cada opção.",
            "level": 1,
            "classes": classes,
            "species": species,
            "backgrounds": backgrounds,
            "feats": feats,
            "skills": skill_catalog,
            "abilities": [{"key": key, "label": label} for key, label in ABILITY_LABELS.items()],
            "score_methods": {
                "standard_array": {
                    "label": "Matriz padrão",
                    "values": sorted(standard.values(), reverse=True),
                    "assignment": standard,
                },
                "point_buy": {
                    "label": "Compra por pontos",
                    "budget": 27,
                    "minimum": 8,
                    "maximum": 15,
                    "costs": {str(key): value for key, value in sorted(CUSTO_COMPRA_PONTOS.items())},
                },
            },
            "source_notes": [
                "O criador inicia no nível 1 para não simular decisões de progressão que o contrato de criação do motor não valida.",
                "Equipamento inicial por classe não está catalogado; o pacote A/B do antecedente é validado e registrado.",
                ARTIFICER_NOTE,
            ],
        }

    def score_preview(self, body: Mapping[str, Any]) -> dict[str, Any]:
        method = str(body.get("method", ""))
        scores = self._ability_scores(body.get("ability_scores"))
        if method == "standard_array":
            standard = self.engine.evaluate({"type": "ability_generation", "method": "matriz_padrao"}).outcome["atributos"]
            if sorted(scores.values(), reverse=True) != sorted(standard.values(), reverse=True):
                raise CreationError("A Matriz padrão usa os valores 15, 14, 13, 12, 10 e 8, cada um uma vez.", "ability_scores")
            return {"valid": True, "points_spent": None, "points_remaining": None, "base_scores": scores}
        if method != "point_buy":
            raise CreationError("Escolha Matriz padrão ou Compra por pontos.", "ability_method")
        try:
            result = self.engine.evaluate({"type": "ability_generation", "method": "compra_pontos", "scores": scores})
            spent = custo_compra_pontos(result.outcome["atributos"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CreationError(str(exc), "ability_scores") from exc
        return {
            "valid": True,
            "points_spent": spent,
            "points_remaining": 27 - spent,
            "base_scores": result.outcome["atributos"],
        }

    def preview(self, body: Mapping[str, Any]) -> dict[str, Any]:
        payload = self._coerce_payload(body)
        profile = self._class_profile_for_payload(payload)
        missing = self._missing_choices(payload, profile)
        if missing:
            return {
                "ready": False,
                "missing": missing,
                "profile": profile,
                "draft_name": str(payload.get("name", "")).strip() or None,
                "ruleset": RULESET,
                "warnings": self._scope_warnings(payload, profile),
            }
        try:
            built = self._build_character(payload, profile)
        except CreationError as exc:
            return {
                "ready": False,
                "missing": [],
                "error": {"message": str(exc), "field": exc.field},
                "profile": profile,
                "draft_name": str(payload.get("name", "")).strip() or None,
                "ruleset": RULESET,
                "warnings": self._scope_warnings(payload, profile),
            }
        return {
            "ready": True,
            "character": built["character"],
            "choices": built["choices"],
            "profile": profile,
            "completeness": built["completeness"],
            "warnings": built["warnings"],
            "validation": built["validation"],
            "score_summary": built["score_summary"],
            "ruleset": RULESET,
        }

    def create(self, body: Mapping[str, Any]) -> dict[str, Any]:
        if self.store is None:
            raise PersistenceError("O serviço de persistência não está configurado; a ficha não foi criada.")
        payload = self._coerce_payload(body)
        profile = self._class_profile_for_payload(payload)
        missing = self._missing_choices(payload, profile)
        if missing:
            raise CreationError("Ainda há escolhas obrigatórias: " + ", ".join(item["label"] for item in missing), missing[0]["field"])
        built = self._build_character(payload, profile)
        record = {
            "ruleset": RULESET,
            "created_by": "character_creator",
            "character": built["character"],
            "choices": built["choices"],
            "completeness": built["completeness"],
            "warnings": built["warnings"],
            "validation": built["validation"],
            "score_summary": built["score_summary"],
        }
        return self.store.save(record)

    def _coerce_payload(self, body: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(body, Mapping):
            raise CreationError("O corpo da solicitação precisa ser um objeto JSON.")
        raw = dict(body)
        if len(json.dumps(raw, ensure_ascii=False)) > 500_000:
            raise CreationError("O rascunho excede o limite permitido.")
        if not isinstance(raw.get("class_choices"), Mapping):
            raw["class_choices"] = {}
        if not isinstance(raw.get("spells"), Mapping):
            raw["spells"] = {}
        if not isinstance(raw.get("background_increases"), Mapping):
            raw["background_increases"] = {}
        if not isinstance(raw.get("class_skills"), list):
            raw["class_skills"] = []
        if not isinstance(raw.get("narrative"), Mapping):
            raw["narrative"] = {}
        if "ravenloft" not in raw:
            raw["ravenloft"] = False
        return raw

    def _ability_scores(self, raw: Any) -> dict[str, int]:
        if not isinstance(raw, Mapping):
            raise CreationError("Informe os seis valores de atributo.", "ability_scores")
        if set(raw) != set(ABILITY_LABELS):
            raise CreationError("É necessário informar Força, Destreza, Constituição, Inteligência, Sabedoria e Carisma.", "ability_scores")
        return {key: _parse_int(raw[key], field="ability_scores", label=ABILITY_LABELS[key]) for key in ABILITY_LABELS}

    def _class_profile_for_payload(self, payload: Mapping[str, Any]) -> dict[str, Any] | None:
        class_key = str(payload.get("class", "")).strip().lower()
        if class_key not in CLASSES:
            return None
        try:
            attributes = self._ability_scores(payload.get("ability_scores"))
        except CreationError:
            attributes = {key: 10 for key in ABILITY_LABELS}
        background_key = str(payload.get("background", "")).strip().lower()
        increases = payload.get("background_increases")
        if background_key in ANTECEDENTES and isinstance(increases, Mapping):
            try:
                attributes = aplicar_aumentos_antecedente(background_key, attributes, increases)
            except (ValueError, TypeError):
                pass
        return self._class_profile(class_key, attributes)

    def _class_profile(self, class_key: str, attributes: Mapping[str, int]) -> dict[str, Any]:
        level = 1
        values = {key: int(attributes.get(key, 10)) for key in ABILITY_LABELS}
        prof_bonus = 2
        class_name = CLASS_LABELS.get(class_key, _humanizar(class_key))
        casting_feature_name = "Magia de Pacto" if class_key == "bruxo" else "Conjuração"
        casting_features = {"artifice", *CLASSES_CONJURADORAS}
        if class_key == "artifice":
            casting_facts = self.engine.evaluate(
                {
                    "type": "class_feature",
                    "classe": class_key,
                    "recurso": casting_feature_name,
                    "nivel": level,
                    **values,
                }
            ).outcome
            artificer_progress = progresso_artifice(level, values["inteligencia"])
            spell_profile = {
                "available": True,
                "supported": True,
                "class_key": class_key,
                "attribute": artificer_progress["atributo_conjuracao"],
                "attribute_label": ABILITY_LABELS[artificer_progress["atributo_conjuracao"]],
                "cantrips": artificer_progress["truques"],
                "spells": artificer_progress["magias_preparadas"],
                "spell_label": "magias preparadas",
                "slots": artificer_progress["espacos_totais"],
                "maximum_circle": artificer_progress["circulo_maximo"],
                "source": "rule_engine.spellcasting — lista parcial de Artífice",
                "catalog": [self._spell_payload(item) for item in listar_magias_artifice(level)],
                "always_prepared": [],
                "note": "A contagem e a lista de escolhas são validadas pelo helper do Artífice; a lista de magias é parcial e mistura conteúdo de suplemento conforme registrado no motor.",
                "feature_result": _compactar_resultado(casting_facts),
                "class_spell_catalog_available": True,
            }
        elif class_key in casting_features:
            casting_facts = self.engine.evaluate(
                {
                    "type": "class_feature",
                    "classe": class_key,
                    "recurso": casting_feature_name,
                    "nivel": level,
                    "bonus_proficiencia": prof_bonus,
                    **values,
                }
            ).outcome
            has_counts = isinstance(casting_facts.get("magias_preparadas"), int) or isinstance(
                casting_facts.get("truques"), int
            )
            spell_catalog = self._class_spell_catalog(class_key) if class_key in CLASSES_CONJURADORAS else []
            book_count = None
            if class_key == "mago":
                book_result = self.engine.evaluate(
                    {
                        "type": "class_feature",
                        "classe": "mago",
                        "recurso": "Livro de Magias",
                        "nivel": level,
                    }
                ).outcome
                book_count = book_result.get("magias_iniciais")
            spell_profile = {
                "available": True,
                "supported": bool(has_counts),
                "class_key": class_key,
                "attribute": casting_facts.get("atributo_conjuracao"),
                "attribute_label": ABILITY_LABELS.get(casting_facts.get("atributo_conjuracao")),
                "cantrips": casting_facts.get("truques"),
                "spells": casting_facts.get("magias_preparadas"),
                "spell_label": "magias escolhidas",
                "slots": casting_facts.get("espacos"),
                "maximum_circle": self._maximum_circle(casting_facts),
                "spellbook": book_count,
                "source": "Rule Engine — característica de classe e listas de magias catalogadas",
                "catalog": spell_catalog,
                "feature_result": _compactar_resultado(casting_facts),
                "class_spell_catalog_available": class_key in CLASSES_CONJURADORAS,
                "note": (
                    None
                    if has_counts
                    else "O motor registra progressão/lista, mas não informa aqui quantas magias escolher nesta classe. A interface não inventa uma quantidade; a seleção fica explicitamente fora do validador."
                ),
            }
        else:
            spell_profile = {
                "available": False,
                "supported": False,
                "class_key": class_key,
                "catalog": [],
            }
            casting_facts = None

        feature_results = []
        required_choices = []
        for feature_name in caracteristicas_no_nivel(class_key, level):
            facts = {
                "type": "class_feature",
                "classe": class_key,
                "recurso": feature_name,
                "nivel": level,
                "bonus_proficiencia": prof_bonus,
                **values,
            }
            outcome = self.engine.evaluate(facts).outcome
            feature_results.append({"name": feature_name, "result": _compactar_resultado(outcome)})
            if outcome.get("resultado") == "escolha":
                key = _normalizar(feature_name)
                options = list(outcome.get("opcoes") or [])
                kind = "opcao"
                if key == "estilo_de_luta":
                    kind = "talento"
                elif key == "invocacoes_misticas":
                    kind = "invocacao"
                    options = [
                        option
                        for option in options
                        if self.engine.evaluate(
                            {
                                **facts,
                                "invocacao": option,
                                "invocacoes_escolhidas": [],
                            }
                        ).outcome.get("resultado")
                        not in {"bloqueado", "nao_implementado"}
                    ]
                if key in {"ordem_divina", "ordem_primal", "estilo_de_luta", "invocacoes_misticas"}:
                    required_choices.append(
                        {
                            "key": key,
                            "feature": feature_name,
                            "label": FEATURE_CHOICE_LABELS.get(key, feature_name),
                            "kind": kind,
                            "options": [
                                {
                                    "key": str(option),
                                    "label": OPTION_LABELS.get(str(option), self._invocation_label(str(option))),
                                    "result": self._choice_result(facts, key, kind, str(option)),
                                }
                                for option in options
                            ],
                            "required": True,
                        }
                    )

        if class_key == "ladino":
            expertise_result = self.engine.evaluate(
                {
                    "type": "class_feature",
                    "classe": class_key,
                    "recurso": "Especialização",
                    "nivel": level,
                    **values,
                }
            ).outcome
            if isinstance(expertise_result.get("pericias"), int):
                required_choices.append(
                    {
                        "key": "especializacao",
                        "feature": "Especialização",
                        "label": "Especialização",
                        "kind": "skills",
                        "count": expertise_result["pericias"],
                        "options": [],
                        "required": True,
                        "note": "Escolha entre perícias em que a ficha já tem proficiência.",
                    }
                )

        for feature in feature_results:
            feature["label"] = feature["name"]
        profile = {
            "class": class_key,
            "class_label": class_name,
            "level": level,
            "hit_die": CLASSES[class_key]["dado_vida"],
            "primary_ability": CLASSES[class_key]["atributo_primario"],
            "primary_ability_label": self._attribute_phrase(CLASSES[class_key]["atributo_primario"]),
            "saving_throws": PROFICIENCIAS_SALVAGUARDA_CLASSE[class_key],
            "proficiencies": _jsonable(PROFICIENCIAS_CLASSE.get(class_key, {})),
            "features": feature_results,
            "required_choices": required_choices,
            "spellcasting": spell_profile,
            "artificer_coverage": self._artificer_coverage(values) if class_key == "artifice" else None,
            "progression": self._progression(class_key),
        }
        return profile

    def _choice_result(self, facts: Mapping[str, Any], key: str, kind: str, option: str) -> dict[str, Any]:
        choice_facts = dict(facts)
        choice_facts["recurso"] = FEATURE_CHOICE_LABELS.get(key, key)
        choice_facts["type"] = "class_feature"
        if kind == "talento":
            choice_facts["talento"] = option
        elif kind == "invocacao":
            choice_facts["invocacao"] = option
            choice_facts["invocacoes_escolhidas"] = []
        else:
            choice_facts["opcao"] = option
        result = self.engine.evaluate(choice_facts).outcome
        return _compactar_resultado(result)

    def _artificer_coverage(self, attributes: Mapping[str, int]) -> dict[str, Any]:
        coverage = []
        for level in sorted(FEATURES_BY_CLASS["artifice"]):
            for feature_name in FEATURES_BY_CLASS["artifice"][level]:
                outcome = self.engine.evaluate(
                    {
                        "type": "class_feature",
                        "classe": "artifice",
                        "recurso": feature_name,
                        "nivel": level,
                        "bonus_proficiencia": 2 + (level - 1) // 4,
                        **attributes,
                    }
                ).outcome
                result = outcome.get("resultado")
                if result == "nao_implementado":
                    status = "unimplemented"
                elif feature_name == "Replicar Item Mágico":
                    status = "partial"
                elif feature_name == "Subclasse":
                    status = "partial"
                else:
                    status = "implemented"
                coverage.append(
                    {
                        "level": level,
                        "feature": feature_name,
                        "status": status,
                        "result": _compactar_resultado(outcome),
                    }
                )
        unlinked_subclass_spell_tables = [
            {
                "label": subclass,
                "source": "Eberron: Forge of the Artificer — tabela no helper de conjuração",
                "levels": [{"level": level, "spells": list(spells)} for level, spells in sorted(levels.items())],
            }
            for subclass, levels in ARTIFICER_SUBCLASS_SPELLS.items()
        ]
        return {
            "source_note": ARTIFICER_NOTE,
            "spell_progression_source": "rule_engine.spellcasting.progresso_artifice",
            "spell_progression": [
                progresso_artifice(level, int(attributes.get("inteligencia", 10))) for level in range(1, 21)
            ],
            "available_spell_count": len(ARTIFICER_SPELL_LEVELS),
            "subclass_options": self._subclasses("artifice"),
            "unlinked_subclass_spell_tables": unlinked_subclass_spell_tables,
            "subclass_note": (
                "O catálogo de subclasses ligado à progressão do Artífice registra apenas as opções retornadas pelo Rule Engine. "
                "As tabelas separadas abaixo existem no helper de conjuração (Eberron: Forge of the Artificer), mas não estão "
                "conectadas à seleção/validação de subclasses; por isso não são tratadas como opções jogáveis neste fluxo."
            ),
            "coverage": coverage,
            "infusion_note": "Replicar Item Mágico informa uma quantidade, mas o repositório não tem catálogo nem validação de infusões/itens escolhidos.",
        }

    def _species_result(
        self, species_key: str, choice: str | None, attributes: Mapping[str, int]
    ) -> dict[str, Any]:
        facts: dict[str, Any] = {
            "type": "species_traits",
            "especie": species_key,
            "nivel": 1,
            "bonus_proficiencia": 2,
            "modificador_constituicao": modificador(int(attributes.get("constituicao", 10))),
        }
        field_for_species = {
            "draconato": "heranca_draconica",
            "elfo": "linhagem",
            "gnomo": "linhagem",
            "golias": "ancestralidade",
            "tiefling": "legado",
        }.get(species_key)
        if choice and field_for_species:
            facts[field_for_species] = choice
        return self.engine.evaluate(facts).outcome

    def _species_choice_definition(self, species_key: str) -> dict[str, Any] | None:
        definitions: dict[str, tuple[str, Mapping[str, Any]]] = {
            "draconato": ("heritage", HERANCA_DRACONICA),
            "elfo": ("lineage", LINHAGENS_ELFICAS),
            "gnomo": ("lineage", LINHAGENS_GNOMICAS),
            "golias": ("giant_ancestry", ANCESTRALIDADES_GIGANTES),
            "tiefling": ("infernal_legacy", LEGADOS_INFEROS),
        }
        if species_key not in definitions:
            return None
        field_name, options = definitions[species_key]
        label = {
            "draconato": "Herança dracônica",
            "elfo": "Linhagem élfica",
            "gnomo": "Linhagem gnômica",
            "golias": "Ancestralidade gigante",
            "tiefling": "Legado ínfero",
        }[species_key]
        formatted = []
        for key, data in options.items():
            if species_key == "draconato":
                description = f"Resistência a dano {data['dano']} e Ataque de Sopro do mesmo tipo."
                option_label = data["nome"]
            elif species_key == "elfo":
                description = "; ".join(
                    item
                    for item in [
                        ", ".join(data.get("nivel_1", {}).get("truques", [])),
                        ", ".join(data.get("nivel_3", {}).get("magias", [])),
                        ", ".join(data.get("nivel_5", {}).get("magias", [])),
                        data.get("nivel_1", {}).get("nota"),
                    ]
                    if item
                )
                option_label = data["nome"]
            elif species_key == "gnomo":
                description = "; ".join(
                    item
                    for item in [
                        ", ".join(data.get("nivel_1", {}).get("truques", [])),
                        ", ".join(data.get("nivel_1", {}).get("magias_preparadas", [])),
                        data.get("nivel_1", {}).get("nota"),
                    ]
                    if item
                )
                option_label = data["nome"]
            elif species_key == "golias":
                option_label = data["nome"]
                description = data["efeito"]
            else:
                option_label = data["nome"]
                description = ", ".join(data.get("resistencias_dano", [])) or "Resistência e magias fixas por nível."
            formatted.append({"key": key, "label": option_label, "description": description})
        return {"key": field_name, "label": label, "options": formatted}

    def _species_skill_definition(self, species_key: str) -> dict[str, Any] | None:
        if species_key == "humano":
            return {
                "count": 1,
                "label": "Hábil",
                "options": [{"key": key, "label": SKILL_LABELS[key]} for key in sorted(PERICIAS)],
                "source_note": "A proficiência adicional é registrada nas escolhas da origem; o modelo de ficha do motor não a agrega ao conjunto de perícias.",
            }
        if species_key == "elfo":
            options = ["intuicao", "percepcao", "sobrevivencia"]
            return {
                "count": 1,
                "label": "Sentidos Aguçados",
                "options": [{"key": key, "label": SKILL_LABELS[key]} for key in options],
                "source_note": "A perícia fica registrada nas escolhas da espécie; o motor atual não a agrega ao conjunto de perícias da ficha.",
            }
        return None

    def _subclasses(self, class_key: str) -> list[dict[str, Any]]:
        result = []
        for name in sorted(subclasses_da_classe(class_key)):
            is_ravenloft = name in SUBCLASSES_RAVENLOFT
            result.append(
                {
                    "key": name,
                    "label": OPTION_LABELS.get(name, _humanizar(name)),
                    "source": "Ravenloft: Horror Wilds" if is_ravenloft else "Livro do Jogador 2024",
                    "available_at_level": 3,
                    "details_supported": class_key != "artifice" and class_key in {"barbaro", "guerreiro", "monge", "ladino"},
                }
            )
        return result

    def _progression(self, class_key: str) -> list[dict[str, Any]]:
        progression = []
        for level in range(1, 21):
            features = caracteristicas_no_nivel(class_key, level)
            if not features:
                continue
            progression.append({"level": level, "features": features})
        return progression

    def _maximum_circle(self, casting_facts: Mapping[str, Any]) -> int:
        slots = casting_facts.get("espacos")
        if isinstance(slots, Mapping):
            return max((int(key) for key, value in slots.items() if int(value) > 0), default=0)
        if isinstance(slots, (list, tuple)):
            return len(slots)
        if isinstance(slots, int):
            return int(casting_facts.get("circulo") or 0)
        return 0

    def _class_spell_catalog(self, class_key: str) -> list[dict[str, Any]]:
        cached = self._spell_options_cache.get(class_key)
        if cached is not None:
            return cached
        names: list[str] = []
        for circle in (0, 1):
            response = self.engine.evaluate(
                {
                    "type": "spell_catalog",
                    "operation": "by_class",
                    "classe": class_key,
                    "circulo": circle,
                }
            ).outcome
            names.extend(response.get("magias", []))
        catalog = []
        for name in names:
            spell = obter_magia(name)
            if spell:
                catalog.append(self._spell_payload(spell))
        self._spell_options_cache[class_key] = catalog
        return catalog

    def _spell_payload(self, spell: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "name": spell.get("nome") or spell.get("name"),
            "circle": spell.get("circulo", spell.get("circle")),
            "school": spell.get("escola", spell.get("school")),
            "components": spell.get("componentes", spell.get("components")),
            "concentration": spell.get("concentracao", spell.get("concentration", False)),
            "ritual": spell.get("ritual", False),
            "duration": spell.get("duracao", spell.get("duration")),
            "effect": spell.get("efeito", spell.get("effect")),
        }

    def _feat_label(self, feat_key: str) -> str:
        known = {
            "iniciado_em_magia": "Iniciado em Magia",
            "dadiva_sombria": "Dádiva Sombria",
            "dadiva_da_fortitude": "Dádiva da Fortitude",
            "dadiva_da_proeza_em_combate": "Dádiva da Proeza em Combate",
            "dadiva_da_proficiencia_em_pericia": "Dádiva da Proficiência em Perícia",
            "dadiva_da_recordacao_de_magia": "Dádiva da Recordação de Magia",
            "dadiva_da_recuperacao": "Dádiva da Recuperação",
            "dadiva_da_resistencia_a_energia": "Dádiva da Resistência à Energia",
            "dadiva_da_velocidade": "Dádiva da Velocidade",
            "dadiva_da_viagem_dimensional": "Dádiva da Viagem Dimensional",
            "dadiva_da_visao_verdadeira": "Dádiva da Visão Verdadeira",
            "dadiva_do_ataque_irresistivel": "Dádiva do Ataque Irresistível",
            "dadiva_do_destino": "Dádiva do Destino",
            "dadiva_do_espirito_da_noite": "Dádiva do Espírito da Noite",
            "sombra_viva": "Sombra Viva",
            "ser_simbiotico": "Ser Simbiótico",
            "alma_ecoante": "Alma Ecoante",
            "andarilho_das_brumas": "Andarilho das Brumas",
            "toque_da_morte": "Toque da Morte",
            "sussurros_reunidos": "Sussurros Reunidos",
            "segunda_pele": "Segunda Pele",
            "olho_agucado": "Olho Aguçado",
            "sobrevivente": "Sobrevivente",
            "valentao_de_taverna": "Valentão de Taverna",
            "atacante_selvagem": "Atacante Selvagem",
            "curandeiro": "Curandeiro",
            "habilidoso": "Habilidoso",
            "musico": "Músico",
            "vigoroso": "Vigoroso",
            "alerta": "Alerta",
            "artifista": "Artifista",
            "sortudo": "Sortudo",
        }
        return known.get(feat_key, _humanizar(feat_key))

    def _invocation_label(self, key: str) -> str:
        return OPTION_LABELS.get(key, _humanizar(key))

    def _attribute_phrase(self, value: str) -> str:
        phrase = str(value).replace("_ou_", " ou ").replace("_e_", " e ")
        for key, label in ABILITY_LABELS.items():
            phrase = phrase.replace(key, label)
        return phrase[:1].upper() + phrase[1:]

    def _scope_warnings(self, payload: Mapping[str, Any], profile: Mapping[str, Any] | None) -> list[dict[str, str]]:
        warnings = [
            {
                "kind": "scope",
                "title": "Nível inicial",
                "message": "Este fluxo cria personagens no nível 1. A progressão para níveis superiores tem opções no motor, mas ainda não é validada integralmente pela criação de ficha.",
            },
            {
                "kind": "scope",
                "title": "Equipamento de classe",
                "message": "O motor não catalogou os pacotes iniciais por classe. O pacote A/B do antecedente é validado e salvo; não inventamos um kit de classe.",
            },
        ]
        if payload.get("class") == "artifice":
            warnings.append({"kind": "artificer", "title": "Artífice: cobertura parcial", "message": ARTIFICER_NOTE})
            warnings.append(
                {
                    "kind": "artificer",
                    "title": "Infusões",
                    "message": "A característica Replicar Item Mágico retorna somente uma quantidade; catálogo, itens disponíveis e validação da escolha não estão implementados no repositório.",
                }
            )
        if profile and profile.get("spellcasting", {}).get("available") and not profile.get("spellcasting", {}).get("supported"):
            warnings.append(
                {
                    "kind": "coverage",
                    "title": "Escolhas de magia não validadas pelo motor",
                    "message": profile["spellcasting"].get("note") or "O motor não informa todas as quantidades necessárias para validar escolhas de magia.",
                }
            )
        background_key = str(payload.get("background", ""))
        if background_key in ANTECEDENTES and ANTECEDENTES[background_key]["fonte"].startswith("Ravenloft"):
            warnings.append(
                {
                    "kind": "source",
                    "title": "Conteúdo Ravenloft",
                    "message": "Este antecedente vem de Ravenloft: Horror Wilds e só pode ser usado com a opção de conteúdo Ravenloft ativa.",
                }
            )
        if payload.get("species") in {"humano", "elfo"}:
            warnings.append(
                {
                    "kind": "coverage",
                    "title": "Perícia de espécie",
                    "message": "A escolha da perícia de Humano/Elfo é guardada no registro, mas o modelo mecânico atual não a soma à lista de perícias calculada.",
                }
            )
        background_key = str(payload.get("background", ""))
        selected_feat = self._selected_background_feat(payload, background_key) if background_key in ANTECEDENTES else ""
        if selected_feat in {"anatomia_aberrante", "toque_da_morte"}:
            warnings.append(
                {
                    "kind": "coverage",
                    "title": "Dádiva Sombria sem efeito catalogado",
                    "message": "O motor valida o nome e a fonte desta Dádiva Sombria, mas não contém seus efeitos mecânicos; ela fica registrada como escolha narrativa, sem simulação.",
                }
            )
        return warnings

    def _missing_choices(self, payload: Mapping[str, Any], profile: Mapping[str, Any] | None) -> list[dict[str, str]]:
        missing: list[dict[str, str]] = []

        def need(key: str, label: str) -> None:
            if not any(item["field"] == key for item in missing):
                missing.append({"field": key, "label": label})

        name = str(payload.get("name", "")).strip()
        if not name:
            need("name", "Nome do personagem")
        elif len(name) > 80:
            need("name", "Nome (máximo de 80 caracteres)")
        class_key = str(payload.get("class", "")).strip().lower()
        if class_key not in CLASSES:
            need("class", "Classe")
        species_key = str(payload.get("species", "")).strip().lower()
        if species_key not in ESPECIES:
            need("species", "Espécie")
        background_key = str(payload.get("background", "")).strip().lower()
        if background_key not in ANTECEDENTES:
            need("background", "Antecedente")
        if not isinstance(payload.get("ravenloft"), bool):
            need("ravenloft", "Configuração de conteúdo Ravenloft")
        if background_key in ANTECEDENTES:
            bg = ANTECEDENTES[background_key]
            if bg["fonte"].startswith("Ravenloft") and payload.get("ravenloft") is not True:
                need("ravenloft", "Ative o conteúdo Ravenloft para este antecedente")

        try:
            scores = self._ability_scores(payload.get("ability_scores"))
            method = payload.get("ability_method")
            if method == "standard_array":
                self.score_preview({"method": method, "ability_scores": scores})
            elif method == "point_buy":
                self.score_preview({"method": method, "ability_scores": scores})
            else:
                need("ability_method", "Método de atributos")
        except CreationError as exc:
            need(exc.field or "ability_scores", "Distribuição dos atributos")
            scores = {key: 10 for key in ABILITY_LABELS}

        increases = payload.get("background_increases")
        if background_key in ANTECEDENTES and scores:
            if not isinstance(increases, Mapping) or not increases:
                need("background_increases", "Aumentos de atributo do antecedente")
            else:
                try:
                    aplicar_aumentos_antecedente(background_key, scores, increases)
                except (ValueError, TypeError, KeyError):
                    need("background_increases", "Distribuição válida de +2/+1 ou +1/+1/+1")

        species_choice = str(payload.get("species_choice", "")).strip()
        if species_key in {"draconato", "elfo", "gnomo", "golias", "tiefling"} and not species_choice:
            label = self._species_choice_definition(species_key)
            need("species_choice", label["label"] if label else "Escolha da espécie")
        if species_key in ESPECIES:
            attributes_for_traits = dict(scores)
            if background_key in ANTECEDENTES and isinstance(increases, Mapping):
                try:
                    attributes_for_traits = aplicar_aumentos_antecedente(background_key, scores, increases)
                except (ValueError, TypeError):
                    pass
            try:
                species_result = self._species_result(species_key, species_choice or None, attributes_for_traits)
            except (KeyError, TypeError, ValueError) as exc:
                need("species_choice", str(exc))
                species_result = self._species_result(species_key, None, attributes_for_traits)
            if species_result.get("escolhas_pendentes") and species_key not in {"humano", "elfo"}:
                need("species_choice", "Escolha obrigatória da espécie")
            allowed_sizes = species_result.get("tamanhos") or []
            if len(allowed_sizes) > 1 and str(payload.get("size", "")) not in allowed_sizes:
                need("size", "Tamanho da espécie")

        species_skill_def = self._species_skill_definition(species_key)
        species_skill = str(payload.get("species_skill", "")).strip().lower()
        if species_skill_def:
            allowed_species_skills = {item["key"] for item in species_skill_def["options"]}
            if species_skill not in allowed_species_skills:
                need("species_skill", species_skill_def["label"])
        if species_key == "humano":
            origin_feat = str(payload.get("species_feat", "")).strip().lower()
            if origin_feat not in ORIGIN_FEATS:
                need("species_feat", "Talento de Origem do Humano")
            else:
                if ORIGIN_FEATS[origin_feat].get("fonte") == "ravenloft" and payload.get("ravenloft") is not True:
                    need("ravenloft", "Este talento de espécie exige conteúdo Ravenloft")
                if background_key in ANTECEDENTES:
                    background_feat = self._selected_background_feat(payload, background_key)
                    if origin_feat == background_feat.split(":", 1)[0]:
                        need("species_feat", "Escolha um talento diferente do talento do antecedente")
                feat_result = self.engine.evaluate(
                    {
                        "type": "feat",
                        "operation": "validate",
                        "talento": origin_feat,
                        "nivel": 1,
                        "campanha_ravenloft": payload.get("ravenloft") is True,
                    }
                ).outcome
                if feat_result.get("resultado") != "disponivel":
                    need("species_feat", "Talento de Origem disponível para esta campanha")

        if background_key in ANTECEDENTES:
            tool_choice = escolha_ferramenta_do_antecedente(background_key)
            if tool_choice and str(payload.get("background_tool", "")).strip() not in tool_choice["opcoes"]:
                need("background_tool", tool_choice["rotulo"] + " do antecedente")
            if str(payload.get("background_equipment", "")).upper() not in {"A", "B"}:
                need("background_equipment", "Pacote de equipamento A ou B")
            selected_background_feat = self._selected_background_feat(payload, background_key)
            if selected_background_feat.startswith("dadiva_sombria"):
                need("background_feat", "Escolha uma Dádiva Sombria")
            elif selected_background_feat == "dadiva_sombria" or selected_background_feat in DARK_GIFT_FEATS:
                if selected_background_feat not in DARK_GIFT_FEATS:
                    need("background_feat", "Dádiva Sombria válida")
            if selected_background_feat in DARK_GIFT_FEATS and payload.get("ravenloft") is not True:
                need("ravenloft", "Dádiva Sombria exige conteúdo Ravenloft")
            feat_key = selected_background_feat.split(":", 1)[0]
            feat_result = self.engine.evaluate(
                {
                    "type": "feat",
                    "operation": "validate",
                    "talento": feat_key,
                    "nivel": 1,
                    "campanha_ravenloft": payload.get("ravenloft") is True,
                    "caracteristica_conjuracao": class_key in CLASSES_CONJURADORAS or class_key == "artifice",
                }
            ).outcome
            if feat_result.get("resultado") != "disponivel":
                need("background_feat", "Talento de antecedente compatível com as regras e o conteúdo escolhido")

        if class_key in CLASSES:
            class_skills = payload.get("class_skills")
            if not isinstance(class_skills, list) or len(class_skills) != QUANTIDADE_PERICIAS_CLASSE[class_key]:
                need("class_skills", f"{QUANTIDADE_PERICIAS_CLASSE[class_key]} perícias de classe")
            else:
                normalized_skills = [str(skill).strip().lower() for skill in class_skills]
                if len(set(normalized_skills)) != len(normalized_skills):
                    need("class_skills", "Não repita perícias de classe")
                selected = set(normalized_skills)
                if not selected or selected - PERICIAS_CLASSE_OPCOES[class_key]:
                    need("class_skills", "Use apenas perícias permitidas pela classe")
                background_skills = set(ANTECEDENTES.get(background_key, {}).get("pericias", ()))
                extra_species_skills = {species_skill} if species_skill else set()
                if selected & (background_skills | extra_species_skills):
                    need("class_skills", "Escolha perícias diferentes das já concedidas pela origem ou espécie")
            if class_key == "artifice" and str(payload.get("artisan_tool_proficiency", "")) not in FERRAMENTAS_ARTESAO:
                need("artisan_tool_proficiency", "Ferramentas de Artesão do Artífice")

        if profile:
            for choice in profile.get("required_choices", []):
                if choice.get("key") == "especializacao":
                    chosen = payload.get("expertise", [])
                    if (
                        not isinstance(chosen, list)
                        or len(chosen) != int(choice.get("count", 0))
                        or any(not isinstance(skill, str) for skill in chosen)
                    ):
                        need("expertise", f"Escolha {choice['count']} perícias para Especialização")
                    else:
                        chosen_skills = [skill.strip().lower() for skill in chosen]
                        if len(set(chosen_skills)) != len(chosen_skills):
                            need("expertise", "Não repita perícias na Especialização")
                        known_skills = set(ANTECEDENTES.get(background_key, {}).get("pericias", ()))
                        known_skills.update(str(skill).strip().lower() for skill in (payload.get("class_skills") or []))
                        if species_skill:
                            known_skills.add(species_skill)
                        if not set(chosen_skills) <= known_skills:
                            need("expertise", "A Especialização exige proficiência na perícia escolhida")
                    continue
                selected = str((payload.get("class_choices") or {}).get(choice["key"], "")).strip()
                if selected not in {item["key"] for item in choice.get("options", [])}:
                    need(f"class_choices.{choice['key']}", choice["label"])

            self._missing_spell_choices(payload, profile, need)

        return missing

    def _missing_spell_choices(self, payload: Mapping[str, Any], profile: Mapping[str, Any], need) -> None:
        spell_profile = profile.get("spellcasting") or {}
        if not spell_profile.get("available") or not spell_profile.get("supported"):
            return
        choices = payload.get("spells") or {}
        raw_lists = {key: choices.get(key, []) for key in ("cantrips", "selected", "spellbook")}
        safe_lists: dict[str, list[str]] = {}
        for key, values in raw_lists.items():
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                need(f"spells.{key}", "A lista de magias está em formato inválido")
                safe_lists[key] = []
            else:
                safe_lists[key] = [value.strip() for value in values]
        cantrips = safe_lists["cantrips"]
        selected = safe_lists["selected"]
        spellbook = safe_lists["spellbook"]
        if len(cantrips) != int(spell_profile.get("cantrips") or 0):
            need("spells.cantrips", f"Escolha {spell_profile.get('cantrips') or 0} truques")
        if len(selected) != int(spell_profile.get("spells") or 0):
            need("spells.selected", f"Escolha {spell_profile.get('spells') or 0} magias")
        if spell_profile.get("spellbook") is not None:
            if len(spellbook) != int(spell_profile["spellbook"]):
                need("spells.spellbook", f"Registre {spell_profile['spellbook']} magias no Livro de Magias")
            elif not set(selected) <= set(spellbook):
                need("spells.selected", "As magias preparadas pelo Mago devem estar no Livro de Magias")
        all_selected = cantrips + selected + (spellbook if spell_profile.get("spellbook") is not None else [])
        if len(set(all_selected)) != len(all_selected):
            # Preparadas do Mago são, por definição, um subconjunto do livro; essa repetição é permitida.
            if spell_profile.get("spellbook") is None or len(set(cantrips + spellbook)) != len(cantrips + spellbook):
                need("spells", "Não repita magias na mesma escolha")

    def _selected_background_feat(self, payload: Mapping[str, Any], background_key: str) -> str:
        background = ANTECEDENTES[background_key]
        raw = str(payload.get("background_feat", "")).strip().lower()
        default = str(background["talento"])
        accepts_dark = "dadiva_sombria" in background["talentos_alternativos"] or default.startswith("dadiva_sombria")
        if not raw:
            return default
        if accepts_dark and raw == "sobrevivente" and default.split(":", 1)[0] == "sobrevivente":
            return raw
        if accepts_dark and raw in DARK_GIFT_FEATS:
            return raw
        if not accepts_dark and raw == default:
            return default
        if not accepts_dark and raw == default.split(":", 1)[0]:
            return default
        return raw

    def _build_character(self, payload: Mapping[str, Any], profile: Mapping[str, Any]) -> dict[str, Any]:
        class_key = str(payload["class"]).strip().lower()
        species_key = str(payload["species"]).strip().lower()
        background_key = str(payload["background"]).strip().lower()
        scores = self._ability_scores(payload.get("ability_scores"))
        score_result = self.score_preview(
            {"method": payload.get("ability_method"), "ability_scores": scores}
        )
        background_feat = self._selected_background_feat(payload, background_key)
        human_feat = str(payload.get("species_feat", "")).strip().lower() if species_key == "humano" else None
        talents = [human_feat] if human_feat else []
        species_choice = str(payload.get("species_choice", "")).strip() or None
        facts: dict[str, Any] = {
            "type": "character_creation",
            "name": str(payload["name"]).strip(),
            "species": species_key,
            "class": class_key,
            "level": 1,
            "ability_scores": scores,
            "background": background_key,
            "background_increases": dict(payload["background_increases"]),
            "background_feat": background_feat,
            "background_tool": str(payload.get("background_tool", "")).strip() or None,
            "background_equipment": str(payload.get("background_equipment", "")).strip().upper(),
            "class_skill_proficiencies": [str(item) for item in payload.get("class_skills", [])],
            "feats": talents,
        }
        if class_key == "artifice":
            facts["artisan_tool_proficiency"] = str(payload.get("artisan_tool_proficiency", "")).strip()
        if species_choice and species_key == "draconato":
            # O contrato character_creation reconhece diretamente a herança do Draconato.
            # As outras escolhas pertencem ao resolver species_traits e ficam no registro suplementar.
            facts["species_choice"] = species_choice
        creation_result = self.engine.evaluate(facts)
        if creation_result.outcome.get("resultado") != "criado":
            raise CreationError("O motor não confirmou a criação do personagem.", "character")
        character = creation_result.outcome["personagem"]
        sheet = ficha_personagem(character)
        final_scores = sheet["atributos"]
        species_result = self._species_result(species_key, species_choice, final_scores)
        if species_result.get("escolhas_pendentes"):
            raise CreationError("A espécie ainda tem uma escolha pendente.", "species_choice")
        size = str(payload.get("size", "")).strip() or (species_result.get("tamanhos") or [None])[0]
        if size not in (species_result.get("tamanhos") or []):
            raise CreationError("O tamanho não é permitido para esta espécie.", "size")
        sheet["tamanho_escolhido"] = size
        sheet["tracos_especie"] = _jsonable(species_result)
        sheet["pericias_da_especie_registradas"] = [
            {
                "pericia": str(payload.get("species_skill")),
                "origem": "Hábil" if species_key == "humano" else "Sentidos Aguçados",
                "integrada_ao_motor": False,
            }
        ] if species_key in {"humano", "elfo"} else []
        sheet["talento_de_especie"] = human_feat

        self._validate_class_choices(payload, profile, final_scores)
        spell_data = self._validate_spells(payload, profile, final_scores)
        class_feature_results = []
        for feature in profile.get("features", []):
            feature_name = feature["name"]
            facts_feature = {
                "type": "class_feature",
                "classe": class_key,
                "recurso": feature_name,
                "nivel": 1,
                "bonus_proficiencia": sheet["bonus_proficiencia"],
                **final_scores,
            }
            choice = (payload.get("class_choices") or {}).get(_normalizar(feature_name))
            if choice:
                if _normalizar(feature_name) == "estilo_de_luta":
                    facts_feature["talento"] = choice
                elif _normalizar(feature_name) == "invocacoes_misticas":
                    facts_feature["invocacao"] = choice
                    facts_feature["invocacoes_escolhidas"] = []
                else:
                    facts_feature["opcao"] = choice
            outcome = self.engine.evaluate(facts_feature).outcome
            class_feature_results.append({"name": feature_name, "result": _compactar_resultado(outcome)})

        if class_key == "ladino":
            rogue_expertise = self.engine.evaluate(
                {
                    "type": "class_feature",
                    "classe": class_key,
                    "recurso": "Especialização",
                    "nivel": 1,
                    "pericias": list(payload.get("expertise", [])),
                    **final_scores,
                }
            ).outcome
            class_feature_results.append({"name": "Especialização", "result": _compactar_resultado(rogue_expertise)})

        artifice_coverage = profile.get("artificer_coverage") if class_key == "artifice" else None

        choices = {
            "level": 1,
            "class": class_key,
            "species": species_key,
            "background": background_key,
            "ability_method": payload.get("ability_method"),
            "ability_scores_base": scores,
            "background_increases": dict(payload["background_increases"]),
            "background_tool": payload.get("background_tool") or None,
            "background_equipment": str(payload["background_equipment"]).upper(),
            "background_feat": background_feat,
            "species_choice": species_choice,
            "size": size,
            "species_skill": payload.get("species_skill") or None,
            "species_origin_feat": human_feat,
            "class_skills": list(payload.get("class_skills", [])),
            "artisan_tool_proficiency": payload.get("artisan_tool_proficiency") or None,
            "class_choices": dict(payload.get("class_choices") or {}),
            "expertise": list(payload.get("expertise") or []),
            "spells": spell_data,
            "narrative": self._narrative(payload.get("narrative")),
            "class_feature_results": class_feature_results,
            "artificer_coverage": artifice_coverage,
        }
        completeness = "complete_within_engine_scope"
        warnings = self._scope_warnings(payload, profile)
        selected_background_feat = self._selected_background_feat(payload, background_key)
        if (
            class_key == "artifice"
            or species_key in {"humano", "elfo"}
            or (profile.get("spellcasting", {}).get("available") and not profile.get("spellcasting", {}).get("supported"))
            or selected_background_feat in {"anatomia_aberrante", "toque_da_morte"}
        ):
            completeness = "limited_by_engine_coverage"
        validation = {
            "character_creation": {
                "status": creation_result.status,
                "matched_rules": creation_result.matched_rules,
                "rule_source": creation_result.outcome.get("rule_source"),
            },
            "ability_generation": {
                "status": "validado",
                "method": payload.get("ability_method"),
                "points_spent": score_result["points_spent"],
                "points_remaining": score_result["points_remaining"],
            },
            "species_traits": {"status": species_result.get("resultado"), "source": species_result.get("fonte")},
            "spell_choices": {"status": "validated" if spell_data.get("validated") else "not_supported_by_engine", "details": spell_data},
            "class_choices": {"status": "validated"},
            "persistence": "not_attempted",
        }
        return {
            "character": _jsonable(sheet),
            "choices": _jsonable(choices),
            "completeness": completeness,
            "warnings": warnings,
            "validation": _jsonable(validation),
            "score_summary": {
                "method": payload.get("ability_method"),
                "points_spent": score_result["points_spent"],
                "points_remaining": score_result["points_remaining"],
                "final_scores": final_scores,
            },
        }

    def _validate_class_choices(
        self, payload: Mapping[str, Any], profile: Mapping[str, Any], attributes: Mapping[str, int]
    ) -> None:
        selections = payload.get("class_choices") or {}
        for choice in profile.get("required_choices", []):
            key = choice["key"]
            if key == "especializacao":
                continue
            value = str(selections.get(key, "")).strip()
            if value not in {item["key"] for item in choice.get("options", [])}:
                raise CreationError(f"Escolha uma opção válida para {choice['label']}.", f"class_choices.{key}")
            facts = {
                "type": "class_feature",
                "classe": profile["class"],
                "recurso": choice["feature"],
                "nivel": 1,
                "bonus_proficiencia": 2,
                **attributes,
            }
            if choice["kind"] == "talento":
                facts["talento"] = value
            elif choice["kind"] == "invocacao":
                facts["invocacao"] = value
                facts["invocacoes_escolhidas"] = []
            else:
                facts["opcao"] = value
            result = self.engine.evaluate(facts).outcome
            if result.get("resultado") in {"bloqueado", "nao_implementado", "contrato"}:
                raise CreationError(f"O motor bloqueou a escolha de {choice['label']}: {result.get('motivo', result.get('resultado'))}.", f"class_choices.{key}")
        if profile["class"] == "ladino":
            chosen = payload.get("expertise", [])
            known = set(ANTECEDENTES.get(str(payload.get("background", "")), {}).get("pericias", ()))
            known.update(payload.get("class_skills") or [])
            species_skill = payload.get("species_skill")
            if species_skill:
                known.add(species_skill)
            if not set(chosen) <= known:
                raise CreationError("Especialização só pode usar perícias em que o personagem é proficiente.", "expertise")

    def _validate_spells(
        self, payload: Mapping[str, Any], profile: Mapping[str, Any], attributes: Mapping[str, int]
    ) -> dict[str, Any]:
        spell_profile = profile.get("spellcasting") or {}
        choices = payload.get("spells") or {}
        cantrips = list(choices.get("cantrips") or [])
        selected = list(choices.get("selected") or [])
        spellbook = list(choices.get("spellbook") or [])
        if not spell_profile.get("available"):
            if cantrips or selected or spellbook:
                raise CreationError("Esta classe não tem escolhas de magia neste fluxo.", "spells")
            return {"validated": True, "cantrips": [], "selected": [], "spellbook": []}
        if not spell_profile.get("supported"):
            if cantrips or selected or spellbook:
                raise CreationError("O motor não fornece os limites de escolha necessários para validar estas magias; nenhuma seleção será aceita como regra.", "spells")
            return {
                "validated": False,
                "cantrips": [],
                "selected": [],
                "spellbook": [],
                "note": spell_profile.get("note"),
            }

        if spell_profile["class_key"] == "artifice":
            slots = {str(key): int(value) for key, value in (spell_profile.get("slots") or {}).items()}
            try:
                progress = validar_escolhas_artifice(
                    1,
                    int(attributes["inteligencia"]),
                    cantrips,
                    selected,
                    slots,
                    None,
                )
            except ValueError as exc:
                raise CreationError(str(exc), "spells") from exc
            return {
                "validated": True,
                "cantrips": cantrips,
                "selected": selected,
                "spellbook": [],
                "progression": _jsonable(progress),
                "source": spell_profile.get("source"),
            }

        class_key = spell_profile["class_key"]
        expected_cantrips = int(spell_profile.get("cantrips") or 0)
        expected_spells = int(spell_profile.get("spells") or 0)
        if len(cantrips) != expected_cantrips:
            raise CreationError(f"Escolha exatamente {expected_cantrips} truques.", "spells.cantrips")
        if len(selected) != expected_spells:
            raise CreationError(f"Escolha exatamente {expected_spells} magias.", "spells.selected")
        if len(set(cantrips)) != len(cantrips) or len(set(selected)) != len(selected):
            raise CreationError("Não repita uma magia dentro da mesma escolha.", "spells")
        if spell_profile.get("spellbook") is not None:
            expected_book = int(spell_profile["spellbook"])
            if len(spellbook) != expected_book or len(set(spellbook)) != len(spellbook):
                raise CreationError(f"O Livro de Magias precisa registrar exatamente {expected_book} magias diferentes.", "spells.spellbook")
            if not set(selected) <= set(spellbook):
                raise CreationError("As magias preparadas devem estar no Livro de Magias.", "spells.selected")
        elif spellbook:
            raise CreationError("Apenas o Mago registra um Livro de Magias neste fluxo.", "spells.spellbook")

        def class_spell_names(circle: int) -> set[str]:
            response = self.engine.evaluate(
                {
                    "type": "spell_catalog",
                    "operation": "by_class",
                    "classe": class_key,
                    "circulo": circle,
                }
            ).outcome
            return {_normalizar(name) for name in response.get("magias", [])}

        cantrip_names = class_spell_names(0)
        first_circle_names = class_spell_names(1)
        if any(_normalizar(name) not in cantrip_names for name in cantrips):
            raise CreationError("Um truque escolhido não consta da lista desta classe no catálogo do motor.", "spells.cantrips")
        if any(_normalizar(name) not in first_circle_names for name in selected):
            raise CreationError("Uma magia escolhida não consta da lista de 1º círculo desta classe no motor.", "spells.selected")
        if any(_normalizar(name) not in first_circle_names for name in spellbook):
            raise CreationError("Uma magia do Livro não consta da lista de 1º círculo desta classe no motor.", "spells.spellbook")
        if len(set(cantrips + spellbook)) != len(cantrips) + len(spellbook):
            raise CreationError("Não repita truques ou magias entre as listas.", "spells")
        return {
            "validated": True,
            "cantrips": cantrips,
            "selected": selected,
            "spellbook": spellbook,
            "slots": spell_profile.get("slots"),
            "casting_attribute": spell_profile.get("attribute"),
            "catalog_source": spell_profile.get("source"),
        }

    def _narrative(self, narrative: Any) -> dict[str, str]:
        if not isinstance(narrative, Mapping):
            return {}
        limits = {"pronouns": 60, "appearance": 500, "backstory": 2000, "motive": 500}
        result = {}
        for key, limit in limits.items():
            value = str(narrative.get(key, "")).strip()
            if len(value) > limit:
                raise CreationError(f"O campo narrativo excede {limit} caracteres.", f"narrative.{key}")
            if value:
                result[key] = value
        return result
