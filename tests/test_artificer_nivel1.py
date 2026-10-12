"""Focused level-1 Artificer integration tests for the existing rule-engine contract."""

import pytest

from rule_engine.class_features import resolver_caracteristica
from rule_engine.spellcasting import progresso_artifice, validar_escolhas_artifice


def test_artifice_nivel_1_progressao_base():
    progresso = progresso_artifice(nivel=1, inteligencia=16)

    assert progresso["resultado"] == "resolvido"
    assert progresso["classe"] == "artifice"
    assert progresso["nivel"] == 1
    assert progresso["atributo_conjuracao"] == "inteligencia"
    assert progresso["circulo_maximo"] == 1
    assert progresso["espacos_totais"] == {"1": 2}
    assert progresso["truques"] == 2


def test_artifice_nivel_1_bloqueia_replicar_item_magico():
    # resolver_caracteristica recebe um único dicionário de fatos; a feature é de nível 2.
    resultado = resolver_caracteristica({
        "classe": "artifice",
        "nivel": 1,
        "recurso": "replicate_magic_item",
        "acao": "criar",
        "planos_conhecidos": [],
        "planos": [],
        "itens_atuais": [],
        "descanso_longo_concluido": True,
        "ferramentas_artesao_em_maos": True,
    })

    assert resultado["resultado"] == "bloqueado"
    assert resultado["motivo"] == "nivel_insuficiente"
    assert resultado["nivel_minimo"] == 2


def test_artifice_nivel_1_descanso_longo_recupera_apenas_recursos_disponiveis():
    resultado = resolver_caracteristica({
        "classe": "artifice",
        "nivel": 1,
        "recurso": "resource_recovery",
        "tipo_descanso": "longo",
        "inteligencia": 16,
        "itens_tinkers_atuais": [],
    })

    assert resultado["resultado"] == "recursos_recuperados"
    assert resultado["recursos"]["espacos_de_magia"]["espacos_restantes"] == {"1": 2}
    assert "lampejo_de_genio" not in resultado["recursos"]
    assert "drenar_item_magico" not in resultado["recursos"]
    assert resultado["replicar_item_magico_disponivel"] is False
    assert resultado["pode_armazenar_outra_magia"] is False


def test_artifice_nivel_1_valida_escolhas_de_magias():
    progresso = progresso_artifice(nivel=1, inteligencia=16)
    pool = ["Curar Ferimentos", "Identificar", "Alarme", "Disfarçar-se"]
    magias_preparadas = pool[:progresso["magias_preparadas"]]

    resultado = validar_escolhas_artifice(
        nivel=1,
        inteligencia=16,
        truques=["Luz", "Mensagem"],
        magias_preparadas=magias_preparadas,
        espacos_totais={"1": 2},
    )

    assert resultado["resultado"] == "resolvido"
    assert resultado["espacos_totais"] == {"1": 2}


def test_artifice_nivel_1_rejeita_magia_de_segundo_circulo():
    progresso = progresso_artifice(nivel=1, inteligencia=16)
    qtd_preparadas = progresso["magias_preparadas"]
    pool = ["Invisibilidade"] + ["Alarme"] * max(0, qtd_preparadas - 1)

    # A validação deve rejeitar a magia de 2º círculo antes de aceitar a lista.
    with pytest.raises(ValueError, match="círculo|indisponível|nível"):
        validar_escolhas_artifice(
            nivel=1,
            inteligencia=16,
            truques=["Luz", "Mensagem"],
            magias_preparadas=pool,
            espacos_totais={"1": 2},
        )


def test_artifice_nivel_1_ponta_a_ponta_pelo_motor():
    """Criação, ficha, conjuração, dano e recuperação usam as rotas registradas."""
    from rule_engine.rules import build_default_engine
    from rule_engine.survival import EstadoVital

    engine = build_default_engine()
    criacao = engine.evaluate({
        "type": "character_creation",
        "name": "Ada",
        "species": "humano",
        "class": "artifice",
        "level": 1,
        "ability_scores": {
            "forca": 8,
            "destreza": 14,
            "constituicao": 12,
            "inteligencia": 16,
            "sabedoria": 10,
            "carisma": 10,
        },
        "artificer_cantrips": ["Luz", "Mensagem"],
        "artificer_prepared_spells": ["Curar Ferimentos", "Alarme"],
    })

    assert criacao.status == "resolved"
    assert "character.creation" in criacao.matched_rules
    ficha = criacao.outcome["ficha"]
    assert ficha["conjuracao"]["escolhas_completas"] is True
    assert ficha["conjuracao"]["truque_concedido"] == "Reparar"
    assert "Reparar" not in ficha["conjuracao"]["truques_conhecidos"]
    assert ficha["conjuracao"]["espacos_totais"] == {"1": 2}

    estado = EstadoVital(pv_maximos=12, pv_atuais=12)
    espacos = dict(ficha["recursos_iniciais"]["espacos_de_magia"]["espacos_restantes"])

    def conjurar_curar_ferimentos(espacos_atuais):
        return engine.evaluate({
            "type": "class_feature",
            "classe": "artifice",
            "nivel": 1,
            "recurso": "conjuracao",
            "acao": "conjurar",
            "magia": "Curar Ferimentos",
            "inteligencia": 16,
            "truques_conhecidos": ficha["conjuracao"]["truques_conhecidos"],
            "magias_preparadas": ficha["conjuracao"]["magias_preparadas"],
            "espacos_restantes": dict(espacos_atuais),
            "componentes_disponiveis": ["V", "S"],
        })

    primeira = conjurar_curar_ferimentos(espacos)
    assert primeira.status == "resolved"
    assert "class.feature" in primeira.matched_rules
    assert primeira.outcome["resultado"] == "conjurada"
    assert primeira.outcome["mecanica"]["tipo"] == "cura"
    assert primeira.outcome["mecanica"]["dados_cura_base"] == "2d8"
    assert primeira.outcome["slot_consumido"] == 1
    assert primeira.outcome["delta_espacos"] == {"1": -1}
    espacos = dict(primeira.outcome["espacos_restantes_depois"])
    assert espacos == {"1": 1}

    dano = engine.evaluate({
        "type": "damage_application",
        "estado": estado,
        "damage": 5,
        "source": "teste de integração",
    })
    assert dano.status == "resolved"
    assert estado.pv_atuais == 7

    descanso = engine.evaluate({
        "type": "long_rest",
        "estado": estado,
        "duration_hours": 8,
    })
    assert descanso.status == "resolved"
    assert estado.pv_atuais == 12

    recuperacao = engine.evaluate({
        "type": "class_feature",
        "classe": "artifice",
        "nivel": 1,
        "recurso": "resource_recovery",
        "tipo_descanso": "longo",
        "inteligencia": 16,
        "itens_tinkers_atuais": [],
    })
    assert recuperacao.status == "resolved"
    assert "class.feature" in recuperacao.matched_rules
    assert recuperacao.outcome["resultado"] == "recursos_recuperados"
    assert set(recuperacao.outcome["recursos"]) == {"magia_de_artifice", "espacos_de_magia"}
    # A recuperação produz um delta; a camada que mantém a ficha aplica-o ao estado.
    espacos = dict(recuperacao.outcome["delta_conjuracao"]["espacos_restantes"])
    assert espacos == {"1": 2}

    dano_apos_descanso = engine.evaluate({
        "type": "damage_application",
        "estado": estado,
        "damage": 5,
    })
    assert dano_apos_descanso.status == "resolved"
    assert estado.pv_atuais == 7

    segunda = conjurar_curar_ferimentos(espacos)
    assert segunda.status == "resolved"
    assert "class.feature" in segunda.matched_rules
    assert segunda.outcome["resultado"] == "conjurada"
    assert segunda.outcome["slot_consumido"] == 1
    assert segunda.outcome["espacos_restantes_depois"] == {"1": 1}


def test_artifice_nivel_1_orquestrador_casting_reparo_e_recupera_slots_no_descanso():
    from orchestrator import OrquestradorAcoes
    from rule_engine.rules import build_default_engine
    from rule_engine.survival import EstadoVital

    engine = build_default_engine()
    criado = engine.evaluate({
        "type": "character_creation",
        "name": "Ada",
        "species": "humano",
        "class": "artifice",
        "level": 1,
        "ability_scores": {
            "forca": 8,
            "destreza": 14,
            "constituicao": 12,
            "inteligencia": 16,
            "sabedoria": 10,
            "carisma": 10,
        },
        "artificer_cantrips": ["Luz", "Mensagem"],
        "artificer_prepared_spells": ["Curar Ferimentos", "Alarme"],
    })
    assert criado.status == "resolved"
    ficha = criado.outcome["ficha"]
    orquestrador = OrquestradorAcoes(engine)
    personagens = [ficha]

    reparo = orquestrador.executar_ferramenta(
        "resolver_regra",
        {"fatos": {
            "type": "spell",
            "character_id": ficha["id"],
            "magia": "Reparar",
        }},
        personagens,
    )
    assert reparo.status == "resolved"
    assert reparo.dados["resultado"] == "conjurada"
    assert ficha["conjuracao"].get("espacos_restantes", {"1": 2}) == {"1": 2}
    assert "Reparar" not in ficha["conjuracao"]["truques_conhecidos"]

    primeira = orquestrador.executar_ferramenta(
        "resolver_regra",
        {"fatos": {
            "type": "spell",
            "character_id": ficha["id"],
            "magia": "Curar Ferimentos",
        }},
        personagens,
    )
    assert primeira.status == "resolved"
    assert primeira.dados["resultado"] == "conjurada"
    assert primeira.dados["espacos_restantes"] == {"1": 1}
    assert ficha["conjuracao"]["espacos_restantes"] == {"1": 1}

    estado = EstadoVital(pv_maximos=12, pv_atuais=7)
    descanso = orquestrador.executar_ferramenta(
        "resolver_regra",
        {"fatos": {
            "type": "long_rest",
            "character_id": ficha["id"],
            "estado": estado,
            "duration_hours": 8,
        }},
        personagens,
    )
    assert descanso.status == "resolved"
    assert descanso.dados["descanso"] == "longo"
    assert estado.pv_atuais == 12
    assert ficha["conjuracao"]["espacos_restantes"] == {"1": 2}
    assert descanso.dados["recuperacao_recursos_artifice"]["resultado"] == "recursos_recuperados"

    segunda = orquestrador.executar_ferramenta(
        "resolver_regra",
        {"fatos": {
            "type": "spell",
            "character_id": ficha["id"],
            "magia": "Curar Ferimentos",
        }},
        personagens,
    )
    assert segunda.status == "resolved"
    assert segunda.dados["resultado"] == "conjurada"
    assert segunda.dados["espacos_restantes"] == {"1": 1}
    assert ficha["conjuracao"]["espacos_restantes"] == {"1": 1}

