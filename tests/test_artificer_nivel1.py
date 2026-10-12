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
