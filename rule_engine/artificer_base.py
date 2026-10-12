"""Resolução determinística da classe base Artífice 5.5e (Eberron: Forge of the Artificer).

As saídas descrevem efeitos mecânicos e requisitos; o estado persistente (usos,
itens, cargas e espaços) continua pertencendo ao chamador do Rule Engine.
"""
from __future__ import annotations

import unicodedata
from typing import Any


def _modifier(score: int) -> int:
    return (int(score) - 10) // 2


# Progressão publicada da classe base, sem características de subclasse.
ARTIFICER_PLANS_KNOWN = {2: 4, 6: 5, 10: 6, 14: 7, 18: 8}
ARTIFICER_MAGIC_ITEMS = {2: 2, 6: 3, 10: 4, 14: 5, 18: 6}
ARTIFICER_REPLICATE_PLANS = {
    "alchemy_jug": {"nome": "Jarro de Alquimia", "nivel_minimo": 2, "raridade": "incomum", "sintonizacao": False},
    "bag_of_holding": {"nome": "Bolsa de Armazenamento", "nivel_minimo": 2, "raridade": "incomum", "sintonizacao": False},
    "cap_of_water_breathing": {"nome": "Capuz de Respiração Aquática", "nivel_minimo": 2, "raridade": "incomum", "sintonizacao": False},
    "goggles_of_night": {"nome": "Óculos da Noite", "nivel_minimo": 2, "raridade": "incomum", "sintonizacao": False},
    "manifold_tool": {"nome": "Ferramenta Multiforme", "nivel_minimo": 2, "raridade": "comum", "sintonizacao": True, "efeito": "transformar_em_ferramentas_de_artesao_e_conceder_proficiencia"},
    "repeating_shot": {"nome": "Disparo Repetidor", "nivel_minimo": 2, "raridade": "incomum", "sintonizacao": True, "bonus_ataque": 1, "bonus_dano": 1, "efeito": "ignora_recarga_e_cria_municao_magica"},
    "returning_weapon": {"nome": "Arma Retornante", "nivel_minimo": 2, "raridade": "incomum", "sintonizacao": False, "bonus_ataque": 1, "bonus_dano": 1, "efeito": "retorna_apos_ataque_a_distancia"},
    "rope_of_climbing": {"nome": "Corda de Escalada", "nivel_minimo": 2, "raridade": "incomum", "sintonizacao": False},
    "sending_stones": {"nome": "Pedras de Envio", "nivel_minimo": 2, "raridade": "incomum", "sintonizacao": False},
    "shield_plus_1": {"nome": "Escudo +1", "nivel_minimo": 2, "raridade": "incomum", "sintonizacao": False},
    "wand_of_magic_detection": {"nome": "Varinha de Detecção de Magia", "nivel_minimo": 2, "raridade": "comum", "sintonizacao": False},
    "wand_of_secrets": {"nome": "Varinha dos Segredos", "nivel_minimo": 2, "raridade": "incomum", "sintonizacao": False},
    "wand_of_the_war_mage_plus_1": {"nome": "Varinha do Mago de Guerra +1", "nivel_minimo": 2, "raridade": "incomum", "sintonizacao": True},
    "weapon_plus_1": {"nome": "Arma +1", "nivel_minimo": 2, "raridade": "incomum", "sintonizacao": False},
    "wraps_of_unarmed_power_plus_1": {"nome": "Envoltórios de Poder Desarmado +1", "nivel_minimo": 2, "raridade": "incomum", "sintonizacao": False},
    "armor_plus_1": {"nome": "Armadura +1", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "boots_of_elvenkind": {"nome": "Botas Élficas", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "boots_of_the_winding_path": {"nome": "Botas do Caminho Sinuoso", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": True, "efeito": "teleporte_4_5m_para_espaco_ocupado_este_turno"},
    "cloak_of_elvenkind": {"nome": "Manto Élfico", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": True},
    "cloak_of_the_manta_ray": {"nome": "Manto da Arraia", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": True},
    "dazzling_weapon": {"nome": "Arma Deslumbrante", "nivel_minimo": 6, "raridade": "raro", "sintonizacao": True, "bonus_ataque": 1, "bonus_dano": 1, "cargas": 4, "recarga": "1d4_ao_amanhecer", "efeito": "luz_e_cegar_atacante_dc15"},
    "eyes_of_charming": {"nome": "Olhos Encantadores", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": True},
    "eyes_of_minute_seeing": {"nome": "Olhos de Visão Minuciosa", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "gloves_of_thievery": {"nome": "Luvas de Ladroagem", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "helm_of_awareness": {"nome": "Elmo da Consciência", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False, "efeito": "vantagem_em_iniciativa"},
    "lantern_of_revealing": {"nome": "Lanterna da Revelação", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "mind_sharpener": {"nome": "Aguçador Mental", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": True, "cargas": 4, "recarga": "1d4_ao_amanhecer", "efeito": "reacao_sucesso_salvaguarda_constituicao_concentracao"},
    "necklace_of_adaptation": {"nome": "Colar da Adaptação", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": True},
    "pipes_of_haunting": {"nome": "Flautas Assombradoras", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "repulsion_shield": {"nome": "Escudo de Repulsão", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False, "bonus_ca": 1, "cargas": 4, "recarga": "1d4_ao_amanhecer", "efeito": "reacao_empurrar_atacante_4_5m"},
    "ring_of_swimming": {"nome": "Anel de Natação", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "ring_of_water_walking": {"nome": "Anel de Caminhar sobre a Água", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "sentinel_shield": {"nome": "Escudo Sentinela", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "spell_refueling_ring": {"nome": "Anel de Reabastecimento de Magia", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": True, "sintonizacao_requer_classe": "conjurador", "efeito": "recupera_espaco_de_magia_3_ou_menor_uma_vez_ao_amanhecer"},
    "wand_of_magic_missiles": {"nome": "Varinha de Mísseis Mágicos", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "wand_of_web": {"nome": "Varinha de Teia", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": True},
    "weapon_of_warning": {"nome": "Arma de Aviso", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": True},
    "armor_of_resistance": {"nome": "Armadura da Resistência", "nivel_minimo": 10, "raridade": "raro", "sintonizacao": True},
    "dagger_of_venom": {"nome": "Adaga Venenosa", "nivel_minimo": 10, "raridade": "raro", "sintonizacao": False},
    "elven_chain": {"nome": "Cota Élfica", "nivel_minimo": 10, "raridade": "raro", "sintonizacao": False},
    "ring_of_feather_falling": {"nome": "Anel da Queda Suave", "nivel_minimo": 10, "raridade": "raro", "sintonizacao": True},
    "ring_of_jumping": {"nome": "Anel de Salto", "nivel_minimo": 10, "raridade": "incomum", "sintonizacao": True},
    "ring_of_mind_shielding": {"nome": "Anel de Proteção Mental", "nivel_minimo": 10, "raridade": "incomum", "sintonizacao": True},
    "shield_plus_2": {"nome": "Escudo +2", "nivel_minimo": 10, "raridade": "raro", "sintonizacao": False},
    "wand_of_the_war_mage_plus_2": {"nome": "Varinha do Mago de Guerra +2", "nivel_minimo": 10, "raridade": "raro", "sintonizacao": True},
    "weapon_plus_2": {"nome": "Arma +2", "nivel_minimo": 10, "raridade": "raro", "sintonizacao": False},
    "wraps_of_unarmed_power_plus_2": {"nome": "Envoltórios de Poder Desarmado +2", "nivel_minimo": 10, "raridade": "raro", "sintonizacao": False},
    "armor_plus_2": {"nome": "Armadura +2", "nivel_minimo": 14, "raridade": "raro", "sintonizacao": False},
    "arrow_catching_shield": {"nome": "Escudo Capturador de Flechas", "nivel_minimo": 14, "raridade": "raro", "sintonizacao": True},
    "flame_tongue": {"nome": "Língua Flamejante", "nivel_minimo": 14, "raridade": "raro", "sintonizacao": True},
    "ring_of_free_action": {"nome": "Anel de Ação Livre", "nivel_minimo": 14, "raridade": "raro", "sintonizacao": True},
    "ring_of_protection": {"nome": "Anel de Proteção", "nivel_minimo": 14, "raridade": "raro", "sintonizacao": True},
    "ring_of_the_ram": {"nome": "Anel do Carneiro", "nivel_minimo": 14, "raridade": "raro", "sintonizacao": True},
}


def _plan_metadata(plan_id: str, level: int) -> dict[str, Any] | None:
    """Metadata for a published plan or a repeatable custom magic-item plan."""
    if plan_id in ARTIFICER_REPLICATE_PLANS:
        data = dict(ARTIFICER_REPLICATE_PLANS[plan_id])
    else:
        prefixes = (
            ("common_magic_item:", 2, "comum", "Item Mágico Comum"),
            ("uncommon_wondrous_item:", 10, "incomum", "Item Maravilhoso Incomum"),
            ("rare_wondrous_item:", 14, "raro", "Item Maravilhoso Raro"),
        )
        match = next((entry for entry in prefixes if plan_id.startswith(entry[0]) and plan_id[len(entry[0]):].strip()), None)
        if match is None:
            return None
        prefix, min_level, rarity, label = match
        custom_name = plan_id[len(prefix):].strip()
        custom_norm = unicodedata.normalize("NFKD", custom_name.lower())
        custom_norm = "".join(ch for ch in custom_norm if not unicodedata.combining(ch))
        forbidden = ("potion", "pocao", "scroll", "pergaminho", "cursed", "amaldicoado", "amaldi")
        if any(token in custom_norm for token in forbidden):
            return None
        data = {"nome": f"{label}: {custom_name.replace('_', ' ')}",
                "nivel_minimo": min_level, "raridade": rarity, "sintonizacao": "varia"}
    if level < data["nivel_minimo"]:
        return None
    return data


ARTIFICER_NON_ACTION_SPELLS = {
    "alarme": "1 minuto",
    "retirada acelerada": "ação bônus",
    "identificar": "1 minuto",
    "queda suave": "reação",
    "salto": "ação bônus",
    "santuário": "ação bônus",
    "boca encantada": "1 minuto",
    "sopro de dragão": "ação bônus",
    "vigor arcano": "ação bônus",
    "glifo de protecao": "1 hora",
    "fabricar": "10 minutos",
    "santuario particular de mordenkainen": "10 minutos",
    "criacao": "1 minuto",
}

ARTIFICER_CONCENTRATION_SPELLS = {
    "fogo das fadas", "detectar magia", "retirada acelerada",
    "alterar se", "desfoque", "sopro de dragao", "aprimorar atributo",
    "aumentar/reduzir", "esquentar metal", "invisibilidade", "levitacao",
    "escalada de aranha", "teia", "arma elemental", "voar", "celeridade",
    "protecao contra energia", "esfera resiliente de otiluke", "pele de pedra",
    "invocar constructo", "animar objetos", "mao de bigby", "circulo de poder",
    "muralha de pedra",
}

ARTIFICER_PREPARED_SPELLS = {
    1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 6, 7: 7, 8: 7, 9: 9, 10: 9,
    11: 10, 12: 10, 13: 11, 14: 11, 15: 12, 16: 12, 17: 14, 18: 14,
    19: 15, 20: 15,
}
ARTIFICER_ATTUNEMENT_LIMIT = {1: 3, 10: 4, 14: 5, 18: 6}
ARTIFICER_GEAR = {
    "esferas_de_rolamento", "cesta", "saco_de_dormir", "sino", "cobertor",
    "talha_e_polias", "garrafa_de_vidro", "balde", "estrepes", "vela",
    "pe_de_cabra", "frasco", "arpeu", "armadilha_de_caca", "jarro",
    "lampada", "algemas", "rede", "oleo", "papel", "pergaminho", "vara",
    "bolsa", "corda", "saco", "pa", "estacas_de_ferro", "barbante",
    "caixa_de_isca", "tocha", "frasco_de_vidro",
}
ARTIFICER_GEAR_LABELS = {
    "esferas_de_rolamento": "Esferas de rolamento",
    "cesta": "Cesta",
    "saco_de_dormir": "Saco de dormir",
    "sino": "Sino",
    "cobertor": "Cobertor",
    "talha_e_polias": "Talha e polias",
    "garrafa_de_vidro": "Garrafa de vidro",
    "balde": "Balde",
    "estrepes": "Estrepes",
    "vela": "Vela",
    "pe_de_cabra": "Pé de cabra",
    "frasco": "Frasco",
    "arpeu": "Arpéu",
    "armadilha_de_caca": "Armadilha de caça",
    "jarro": "Jarro",
    "lampada": "Lâmpada",
    "algemas": "Algemas",
    "rede": "Rede",
    "oleo": "Óleo",
    "papel": "Papel",
    "pergaminho": "Pergaminho",
    "vara": "Vara",
    "bolsa": "Bolsa",
    "corda": "Corda",
    "saco": "Saco",
    "pa": "Pá",
    "estacas_de_ferro": "Estacas de ferro",
    "barbante": "Barbante",
    "caixa_de_isca": "Caixa de isqueiro",
    "tocha": "Tocha",
    "frasco_de_vidro": "Frasco de vidro",
}
ARTIFICER_GEAR_CATALOG_NAMES = {
    "esferas_de_rolamento": "Esferas de rolamento",
    "cesta": "Cesta",
    "saco_de_dormir": "Saco de Dormir",
    "sino": "Sino",
    "cobertor": "Cobertor",
    "talha_e_polias": "Roldana e Polias",
    "garrafa_de_vidro": "Garrafa de Vidro",
    "balde": "Balde",
    "estrepes": "Estrepes",
    "vela": "Vela",
    "pe_de_cabra": "Pé de Cabra",
    "frasco": "Frasco",
    "arpeu": "Arpéu",
    "armadilha_de_caca": "Armadilha de Caça",
    "jarro": "Jarro",
    "lampada": "Lâmpada",
    "algemas": "Algemas",
    "rede": "Rede",
    "oleo": "Óleo",
    "papel": "Papel",
    "pergaminho": "Pergaminho",
    "vara": "Vara",
    "bolsa": "Bolsa",
    "corda": "Corda",
    "saco": "Saco",
    "pa": "Pá",
    "estacas_de_ferro": "Estacas de Ferro",
    "barbante": "Barbante",
    "caixa_de_isca": "Caixa de isqueiro",
    "tocha": "Tocha",
    "frasco_de_vidro": "Frasco de vidro",
}
ARTIFICER_GEAR_ALIASES = {
    "basket": "cesta",
    "bell": "sino",
    "blanket": "cobertor",
    "bucket": "balde",
    "candle": "vela",
    "ball_bearings": "esferas_de_rolamento",
    "bedroll": "saco_de_dormir",
    "block_and_tackle": "talha_e_polias",
    "bottle,_glass": "garrafa_de_vidro",
    "glass_bottle": "garrafa_de_vidro",
    "caltrops": "estrepes",
    "crowbar": "pe_de_cabra",
    "flask": "frasco",
    "grappling_hook": "arpeu",
    "hunting_trap": "armadilha_de_caca",
    "jug": "jarro",
    "lamp": "lampada",
    "manacles": "algemas",
    "net": "rede",
    "oil": "oleo",
    "paper": "papel",
    "parchment": "pergaminho",
    "pole": "vara",
    "pouch": "bolsa",
    "rope": "corda",
    "sack": "saco",
    "shovel": "pa",
    "spikes,_iron": "estacas_de_ferro",
    "iron_spikes": "estacas_de_ferro",
    "string": "barbante",
    "tinderbox": "caixa_de_isca",
    "caixa_de_isqueiro": "caixa_de_isca",
    "torch": "tocha",
    "vial": "frasco_de_vidro",
}
ARTIFICER_FEATURE_ALIASES = {
    "conjuracao": "conjuracao",
    "magia_de_artifice": "tinkers_magic",
    "tinkers_magic": "tinkers_magic",
    "tinker_s_magic": "tinkers_magic",
    "replicar_item_magico": "replicate_magic_item",
    "replicate_magic_item": "replicate_magic_item",
    "artesao_de_item_magico": "magic_item_tinker",
    "ajustador_de_item_magico": "magic_item_tinker",
    "magic_item_tinker": "magic_item_tinker",
    "adepto_de_item_magico": "magic_item_adept",
    "magic_item_adept": "magic_item_adept",
    "lampejo_de_genio": "flash_of_genius",
    "flash_of_genius": "flash_of_genius",
    "item_armazenador_de_magia": "spell_storing_item",
    "spell_storing_item": "spell_storing_item",
    "artifice_avancado": "advanced_artifice",
    "advanced_artifice": "advanced_artifice",
    "mestre_de_item_magico": "magic_item_master",
    "magic_item_master": "magic_item_master",
    "alma_do_artifice": "soul_of_artifice",
    "soul_of_artifice": "soul_of_artifice",
    "dádiva_épica": "epic_boon",
    "dadiva_epica": "epic_boon",
    "epic_boon": "epic_boon",
    "resource_recovery": "resource_recovery",
    "recuperacao_recursos": "resource_recovery",
}


def _mod(score: int) -> int:
    return (int(score) - 10) // 2


def _tier_value(table: dict[int, int], level: int) -> int:
    return max((value for required, value in table.items() if level >= required), default=0)


def resolve_artificer_feature(feature: str, level: int, facts: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve a base Artificer feature; None means this module does not own it."""
    key = ARTIFICER_FEATURE_ALIASES.get(feature, feature)
    if key not in set(ARTIFICER_FEATURE_ALIASES.values()):
        return None
    int_score = int(facts.get("inteligencia", facts.get("intelligence", 10)))
    int_mod = _mod(int_score)
    prof = int(facts.get("bonus_proficiencia", facts.get("proficiency_bonus", 2 + (level - 1) // 4)))
    base = {
        "classe": "artifice", "nivel": level, "caracteristica": key,
        "atributo_conjuracao": "inteligencia",
    }

    if key == "conjuracao":
        from .spellcasting import (
            ARTIFICER_SLOTS,
            ARTIFICER_SPELL_LEVELS,
            normalizar_nome_magia,
            validar_escolhas_artifice,
        )
        from .spells import obter_magia, resolver_magia

        acao = str(facts.get("acao", "")).strip().lower()
        slots_totais = {str(i + 1): qtd for i, qtd in enumerate(ARTIFICER_SLOTS[level]) if qtd > 0}

        if acao in {"trocar_truque", "substituir_truque", "replace_cantrip"}:
            descanso = facts.get("descanso_longo_concluido", facts.get("long_rest_completed"))
            if descanso is not True:
                return {**base, "resultado": "bloqueado" if descanso is False else "requer_dados",
                        "motivo": "troca_de_truque_exige_descanso_longo_concluido"}
            disponivel = facts.get("troca_truque_disponivel", facts.get("cantrip_swap_available"))
            if disponivel is None:
                return {**base, "resultado": "requer_dados", "motivo": "confirmar_troca_de_truque_ainda_nao_usada_neste_descanso"}
            if disponivel is not True:
                return {**base, "resultado": "bloqueado", "motivo": "troca_de_truque_ja_usada_neste_descanso"}
            truques = facts.get("truques_conhecidos", facts.get("cantrips_known"))
            preparadas = facts.get("magias_preparadas", facts.get("prepared_spells"))
            if not isinstance(truques, (list, tuple)) or not isinstance(preparadas, (list, tuple)):
                return {**base, "resultado": "requer_dados", "motivo": "truques_e_magias_preparadas_atuais_necessarios"}
            antigo = facts.get("truque_antigo", facts.get("old_cantrip"))
            novo = facts.get("truque_novo", facts.get("new_cantrip"))
            if not antigo or not novo:
                opcoes = [
                    {"id": nome, "circulo": circulo}
                    for nome, circulo in ARTIFICER_SPELL_LEVELS.items()
                    if circulo == 0 and normalizar_nome_magia(nome) != normalizar_nome_magia("Reparar")
                ]
                return {**base, "resultado": "escolha", "requer": ["truque_antigo", "truque_novo"],
                        "truques_atuais": list(truques), "opcoes_novo_truque": opcoes}
            antigo_norm, novo_norm = normalizar_nome_magia(antigo), normalizar_nome_magia(novo)
            mapa_truques = {normalizar_nome_magia(n): n for n, circle in ARTIFICER_SPELL_LEVELS.items() if circle == 0}
            if antigo_norm not in {normalizar_nome_magia(x) for x in truques}:
                return {**base, "resultado": "bloqueado", "motivo": "truque_antigo_nao_conhecido"}
            if novo_norm not in mapa_truques:
                return {**base, "resultado": "bloqueado", "motivo": "novo_truque_fora_da_lista_do_artifice"}
            if novo_norm == normalizar_nome_magia("Reparar"):
                return {**base, "resultado": "bloqueado", "motivo": "reparar_e_concedido_por_magia_de_artifice_e_nao_usa_escolha"}
            novos_truques = [
                mapa_truques[novo_norm] if normalizar_nome_magia(x) == antigo_norm else x
                for x in truques
            ]
            if len({normalizar_nome_magia(x) for x in novos_truques}) != len(novos_truques):
                return {**base, "resultado": "bloqueado", "motivo": "truque_novo_ja_conhecido"}
            try:
                validar_escolhas_artifice(level, int_score, list(novos_truques), list(preparadas), slots_totais,
                                          facts.get("subclasse"))
            except ValueError as exc:
                return {**base, "resultado": "bloqueado", "motivo": "configuracao_de_magias_invalida", "detalhe": str(exc)}
            return {**base, "resultado": "truque_substituido", "substitui": antigo, "por": mapa_truques[novo_norm],
                    "delta_conjuracao": {"truques_conhecidos": list(novos_truques), "troca_truque_disponivel": False},
                    "requer_descanso_longo_concluido": True}

        if acao in {"trocar_magias_preparadas", "alterar_magias_preparadas", "change_prepared_spells"}:
            descanso = facts.get("descanso_longo_concluido", facts.get("long_rest_completed"))
            if descanso is not True:
                return {**base, "resultado": "bloqueado" if descanso is False else "requer_dados",
                        "motivo": "troca_de_magias_preparadas_exige_descanso_longo_concluido"}
            disponivel = facts.get(
                "mudanca_magias_preparadas_disponivel",
                facts.get("prepared_spell_change_available"),
            )
            if disponivel is None:
                return {**base, "resultado": "requer_dados", "motivo": "confirmar_mudanca_de_magias_ainda_nao_usada_neste_descanso"}
            if disponivel is not True:
                return {**base, "resultado": "bloqueado", "motivo": "magias_preparadas_ja_alteradas_neste_descanso"}
            truques = facts.get("truques_conhecidos", facts.get("cantrips_known"))
            novas = facts.get("magias_preparadas_novas", facts.get("new_prepared_spells"))
            if not isinstance(truques, (list, tuple)):
                return {**base, "resultado": "requer_dados", "motivo": "lista_atual_de_truques_necessaria"}
            if not isinstance(novas, (list, tuple)):
                opcoes = [
                    {"id": nome, "circulo": circle}
                    for nome, circle in ARTIFICER_SPELL_LEVELS.items()
                    if 1 <= circle <= len(ARTIFICER_SLOTS[level])
                ]
                return {**base, "resultado": "escolha", "requer": "magias_preparadas_novas",
                        "quantidade": ARTIFICER_PREPARED_SPELLS[level], "opcoes": opcoes}
            try:
                validar_escolhas_artifice(level, int_score, list(truques), list(novas), slots_totais,
                                          facts.get("subclasse"))
            except ValueError as exc:
                return {**base, "resultado": "bloqueado", "motivo": "configuracao_de_magias_invalida", "detalhe": str(exc)}
            return {**base, "resultado": "magias_preparadas_alteradas",
                    "delta_conjuracao": {"magias_preparadas": list(novas), "mudanca_magias_preparadas_disponivel": False},
                    "requer_descanso_longo_concluido": True}

        if acao in {"conjurar", "cast", "lancar_magia"}:
            nome_magia = str(facts.get("magia", facts.get("spell", ""))).strip()
            if not nome_magia:
                return {**base, "resultado": "requer_dados", "motivo": "nome_da_magia_necessario"}
            chave_magia = normalizar_nome_magia(nome_magia)
            reparo_gratuito = chave_magia in {normalizar_nome_magia("Reparar"), normalizar_nome_magia("Consertar")}
            nivel_magia = 0 if reparo_gratuito else next(
                (circulo for nome, circulo in ARTIFICER_SPELL_LEVELS.items()
                 if normalizar_nome_magia(nome) == chave_magia),
                None,
            )
            if nivel_magia is None:
                return {**base, "resultado": "bloqueado", "motivo": "magia_fora_da_lista_do_artifice", "magia": nome_magia}
            truques = facts.get("truques_conhecidos", facts.get("cantrips_known", []))
            preparadas = facts.get("magias_preparadas", facts.get("prepared_spells", []))
            if not isinstance(truques, (list, tuple)) or not isinstance(preparadas, (list, tuple)):
                return {**base, "resultado": "bloqueado", "motivo": "listas_de_magias_devem_ser_listas"}
            if nivel_magia == 0:
                permitidos = {normalizar_nome_magia(str(m)) for m in truques}
                permitidos.update({normalizar_nome_magia("Reparar"), normalizar_nome_magia("Consertar")})
                if chave_magia not in permitidos:
                    return {**base, "resultado": "bloqueado", "motivo": "truque_nao_conhecido", "magia": nome_magia}
            else:
                permitidos = {normalizar_nome_magia(str(m)) for m in preparadas}
                if chave_magia not in permitidos:
                    return {**base, "resultado": "bloqueado", "motivo": "magia_nao_preparada", "magia": nome_magia}

            magic_entry = obter_magia(nome_magia)
            if magic_entry is None:
                return {**base, "resultado": "bloqueado", "motivo": "magia_sem_entrada_no_catalogo", "magia": nome_magia}
            ritual_cast = bool(facts.get("ritual", facts.get("como_ritual", False)))
            if ritual_cast and magic_entry.get("ritual") is not True:
                return {**base, "resultado": "bloqueado", "motivo": "magia_nao_tem_tag_ritual", "magia": nome_magia}
            components = str(magic_entry.get("componentes", ""))
            has_material = "M" in {part.strip() for part in components.replace("(", ",").replace(")", ",").split(",")}
            material_normalized = normalizar_nome_magia(components)
            needs_special_material = has_material and (
                "consumido" in material_normalized
                or ("po" in material_normalized and any(ch.isdigit() for ch in components))
            )
            if needs_special_material:
                special_material = facts.get("materiais_especiais_disponiveis")
                if special_material is None:
                    return {**base, "resultado": "requer_dados", "motivo": "material_especial_da_magia_necessario",
                            "componentes_materiais": components}
                if special_material is not True:
                    return {**base, "resultado": "bloqueado", "motivo": "material_especial_da_magia_ausente",
                            "componentes_materiais": components}
            if has_material and not needs_special_material:
                focus_in_hand = facts.get("foco_conjuracao_em_maos", facts.get("spellcasting_focus_in_hand"))
                if focus_in_hand is None:
                    return {**base, "resultado": "requer_dados", "motivo": "confirmar_foco_de_conjuracao_em_maos",
                            "focos_validos": ["Ferramentas de Ladrão", "Ferramentas de Funileiro",
                                              "ferramenta_artesao_com_proficiencia"]}
                if focus_in_hand is not True:
                    return {**base, "resultado": "bloqueado", "motivo": "foco_de_conjuracao_nao_esta_em_maos"}
                focus = str(facts.get("foco_conjuracao", facts.get("spellcasting_focus", ""))).strip()
                foco_artesao = str(facts.get("ferramenta_artesao", facts.get("artisan_tool_proficiency", ""))).strip()
                allowed_focuses = {
                    normalizar_nome_magia("Ferramentas de Ladrão"),
                    normalizar_nome_magia("Ferramentas de Funileiro"),
                }
                if foco_artesao:
                    allowed_focuses.add(normalizar_nome_magia(foco_artesao))
                if not focus:
                    return {**base, "resultado": "requer_dados", "motivo": "tipo_de_foco_de_conjuracao_necessario",
                            "focos_validos": sorted(allowed_focuses)}
                if normalizar_nome_magia(focus) not in allowed_focuses:
                    return {**base, "resultado": "bloqueado", "motivo": "foco_de_conjuracao_sem_proficiencia"}

            tempo_por_magia = {
                "alarme": "1_minuto",
                "identificar": "1_minuto",
                "queda suave": "reacao",
                "retirada acelerada": "acao_bonus",
                "salto": "acao_bonus",
                "santuario": "acao_bonus",
                "reparar": "1_minuto",
                "consertar": "1_minuto",
            }
            tempo_conjuracao_base = tempo_por_magia.get(chave_magia, "acao")
            if tempo_conjuracao_base == "reacao":
                if ritual_cast:
                    return {**base, "resultado": "bloqueado", "motivo": "magia_de_reacao_nao_pode_ser_conjurada_como_ritual"}
                if facts.get("gatilho_reacao_ocorrido") is None:
                    return {**base, "resultado": "requer_dados", "motivo": "gatilho_da_reacao_necessario",
                            "tempo_conjuracao": tempo_conjuracao_base}
                if facts.get("gatilho_reacao_ocorrido") is not True:
                    return {**base, "resultado": "bloqueado", "motivo": "gatilho_da_reacao_nao_ocorreu"}
                if facts.get("reacao_disponivel") is not True:
                    return {**base, "resultado": "bloqueado", "motivo": "reacao_indisponivel"}

            tempo_conjuracao = "ritual_10_minutos_adicionais" if ritual_cast else tempo_conjuracao_base
            slot_level = nivel_magia
            slots: dict[str, int] = {}
            if nivel_magia > 0 and not ritual_cast:
                slot_value = facts.get("espaco", facts.get("slot_level", nivel_magia))
                try:
                    slot_level = int(slot_value)
                except (TypeError, ValueError):
                    return {**base, "resultado": "bloqueado", "motivo": "circulo_de_espaco_invalido"}
                state_slots = facts.get("espacos_restantes", facts.get("slots_remaining"))
                if state_slots is None:
                    return {**base, "resultado": "requer_dados", "motivo": "estado_de_espacos_restantes_necessario",
                            "espacos_totais_sugeridos": slots_totais}
                if not isinstance(state_slots, dict):
                    return {**base, "resultado": "bloqueado", "motivo": "espacos_restantes_devem_ser_um_mapa"}
                try:
                    for slot_key, remaining in state_slots.items():
                        normalized_key = str(int(slot_key))
                        if (normalized_key not in slots_totais or isinstance(remaining, bool)
                                or not isinstance(remaining, (int, str)) or int(remaining) < 0
                                or int(remaining) > slots_totais[normalized_key]):
                            raise ValueError
                        slots[normalized_key] = int(remaining)
                except (TypeError, ValueError):
                    return {**base, "resultado": "bloqueado", "motivo": "estado_de_espacos_restantes_invalido"}
                for slot_key in slots_totais:
                    slots.setdefault(slot_key, 0)
                if slot_level < nivel_magia or str(slot_level) not in slots_totais:
                    return {**base, "resultado": "bloqueado", "motivo": "circulo_de_espaco_invalido",
                            "circulo_minimo": nivel_magia, "circulo_maximo": max(int(k) for k in slots_totais)}
                if slots.get(str(slot_level), 0) < 1:
                    return {**base, "resultado": "bloqueado", "motivo": "sem_espacos_de_magia",
                            "magia": nome_magia, "circulo_espaco": slot_level}

            dados_magia = {
                k: v for k, v in facts.items()
                if k not in {
                    "classe", "nivel", "recurso", "feature", "acao",
                    "espacos_restantes", "slots_remaining", "ritual", "como_ritual",
                }
            }
            dados_magia["magia"] = nome_magia
            if nivel_magia > 0 and not ritual_cast:
                dados_magia["has_slot"] = True
                dados_magia["espaco"] = slot_level
            elif nivel_magia == 0:
                dados_magia["espaco"] = 0
            resolucao = resolver_magia(dados_magia)
            saida = {
                **base, **resolucao, "caracteristica": key, "magia": nome_magia,
                "slot_consumido": None, "ritual": ritual_cast,
                "tempo_conjuracao": tempo_conjuracao,
                "tempo_conjuracao_base": tempo_conjuracao_base,
                "minutos_adicionais_ritual": 10 if ritual_cast else 0,
                "acao_economica": tempo_conjuracao,
            }
            if nivel_magia > 0 and not ritual_cast and resolucao.get("resultado") == "conjurada":
                slots[str(slot_level)] -= 1
                saida.update({
                    "slot_consumido": slot_level,
                    "delta_espacos": {str(slot_level): -1},
                    "espacos_restantes_depois": slots,
                })
            return saida

        cantrips = 2 if level < 10 else 3 if level < 14 else 4
        return {
            **base, "resultado": "resolvido", "truques_conhecidos": cantrips,
            "magias_preparadas": ARTIFICER_PREPARED_SPELLS[level],
            "espacos": slots_totais,
            "circulo_maximo": max(int(key) for key in slots_totais),
            "cd_magia": 8 + prof + int_mod, "ataque_magia": prof + int_mod,
            "focos_validos": ["ferramentas_de_ladrao", "ferramentas_de_funileiro",
                              "outras_ferramentas_de_artesao_com_proficiencia"],
            "troca_truque_apos_descanso_longo": True,
            "troca_magias_preparadas_apos_descanso_longo": True,
            "recupera_espacos": "descanso_longo",
        }

    if key == "tinkers_magic":
        item = unicodedata.normalize("NFKD", str(facts.get("item", "")).strip().lower())
        item = "".join(ch for ch in item if not unicodedata.combining(ch)).replace(" ", "_").replace("-", "_")
        item = ARTIFICER_GEAR_ALIASES.get(item, item)
        uses = max(1, int_mod)
        if facts.get("acao") in {"criar", "create"}:
            if facts.get("usos_gastos") is None:
                return {**base, "resultado": "requer_dados", "motivo": "estado_de_usos_de_magia_de_artifice_necessario"}
            tools_in_hand = facts.get(
                "ferramentas_tinkering_em_maos",
                facts.get("ferramentas_de_funileiro_em_maos", facts.get("tinker_tools_in_hand")),
            )
            if tools_in_hand is None:
                return {**base, "resultado": "requer_dados", "motivo": "confirmar_ferramentas_de_funileiro_em_maos"}
            if tools_in_hand is not True:
                return {**base, "resultado": "bloqueado", "motivo": "ferramentas_de_funileiro_nao_estao_em_maos"}
            if facts.get("distancia_m") is None:
                return {**base, "resultado": "requer_dados", "motivo": "distancia_ate_o_espaco_de_criacao_necessaria"}
            try:
                distance = float(facts["distancia_m"])
            except (TypeError, ValueError):
                return {**base, "resultado": "bloqueado", "motivo": "distancia_de_criacao_invalida"}
            if distance < 0 or distance > 1.5:
                return {**base, "resultado": "bloqueado", "motivo": "espaco_de_criacao_fora_de_1_5_metro"}
            if facts.get("espaco_desocupado") is None:
                return {**base, "resultado": "requer_dados", "motivo": "confirmar_espaco_desocupado"}
            if facts.get("espaco_desocupado") is not True:
                return {**base, "resultado": "bloqueado", "motivo": "nao_ha_espaco_desocupado"}
            if not item:
                return {**base, "resultado": "escolha", "opcoes": [
                    {"id": gear, "nome": ARTIFICER_GEAR_LABELS[gear]} for gear in sorted(ARTIFICER_GEAR)
                ], "acao": "acao_magica", "ferramentas_requeridas": "ferramentas_de_funileiro"}
            if item not in ARTIFICER_GEAR:
                return {**base, "resultado": "bloqueado", "motivo": "item_nao_permitido",
                        "opcoes": [{"id": gear, "nome": ARTIFICER_GEAR_LABELS[gear]} for gear in sorted(ARTIFICER_GEAR)]}
            gastos = facts.get("usos_gastos")
            if isinstance(gastos, bool):
                return {**base, "resultado": "bloqueado", "motivo": "usos_gastos_invalidos"}
            try:
                gastos = int(gastos)
            except (TypeError, ValueError):
                return {**base, "resultado": "bloqueado", "motivo": "usos_gastos_invalidos"}
            if gastos < 0 or gastos >= uses:
                return {**base, "resultado": "bloqueado", "motivo": "usos_esgotados",
                        "usos_maximos": uses, "usos_gastos": gastos}
            item_id = facts.get("item_id")
            if not isinstance(item_id, str) or not item_id.strip():
                return {**base, "resultado": "requer_dados", "motivo": "id_unico_do_objeto_no_mundo_necessario"}
            position = facts.get("posicao_criacao", facts.get("creation_position", facts.get("espaco_id")))
            if position is None or position == "" or position == {}:
                return {**base, "resultado": "escolha", "motivo": "selecione_o_espaco_desocupado_dentro_do_alcance",
                        "requer": "posicao_criacao", "alcance_m": 1.5}
            from .catalog import CATALOGO_EQUIPAMENTOS
            nome_catalogo = ARTIFICER_GEAR_CATALOG_NAMES[item]
            dados_catalogo = CATALOGO_EQUIPAMENTOS.get(nome_catalogo)
            if dados_catalogo is None:
                return {**base, "resultado": "erro_catalogo", "motivo": "equipamento_sem_dados_mecanicos", "item": item}
            item_criado = {
                "id": item_id.strip(),
                "nome": nome_catalogo,
                "item": item,
                "quantidade": 1,
                "categoria": dados_catalogo.get("categoria", "equipamento_mundano"),
                "peso": dados_catalogo["peso"],
                "custo_po": dados_catalogo["custo_po"],
                "unidades_por_item": int(dados_catalogo.get("unidades_por_item", 1)),
                "criado_por": "tinkers_magic",
                "expira": "proximo_descanso_longo",
                "posicao": position,
                "distancia_m": distance,
            }
            return {
                **base, "resultado": "criado", "item": item, "nome_item": nome_catalogo,
                "dados_catalogo": dict(dados_catalogo), "quantidade": 1,
                "unidades_por_item": int(dados_catalogo.get("unidades_por_item", 1)),
                "item_criado": item_criado, "requer_id_unico_ao_persistir": False,
                "delta_mundo": {"adicionar_objeto": item_criado},
                "alcance_m": 1.5, "espaco_desocupado_validado": True,
                "acao": "acao_magica", "usos_maximos": uses,
                "usos_gastos_depois": gastos + 1, "delta_usos": -1,
                "usos_restantes": uses - gastos - 1, "desaparece": "proximo_descanso_longo",
            }
        return {
            **base, "resultado": "resolvido", "truque_conhecido": "Reparar",
            "usos_por_descanso_longo": uses, "acao": "acao_magica",
            "requer_ferramentas": "ferramentas_de_funileiro", "foco": "ferramentas_de_funileiro",
            "duracao_itens_criados": "ate_concluir_descanso_longo",
        }

    if key == "replicate_magic_item":
        plans_count = _tier_value(ARTIFICER_PLANS_KNOWN, level)
        capacity = _tier_value(ARTIFICER_MAGIC_ITEMS, level)
        tier = 2 if level < 6 else 6 if level < 10 else 10 if level < 14 else 14
        available = [
            {"id": plan_id, **metadata}
            for plan_id in sorted(ARTIFICER_REPLICATE_PLANS)
            if (metadata := _plan_metadata(plan_id, level)) is not None
        ]
        if level >= 2:
            available.extend([
                {"id": "common_magic_item:<item_id>", "nome": "Item Mágico Comum à escolha",
                 "nivel_minimo": 2, "raridade": "comum", "sintonizacao": "varia", "repetivel": True}
            ])
        if level >= 10:
            available.append({"id": "uncommon_wondrous_item:<item_id>", "nome": "Item Maravilhoso Incomum à escolha",
                              "nivel_minimo": 10, "raridade": "incomum", "sintonizacao": "varia", "repetivel": True})
        if level >= 14:
            available.append({"id": "rare_wondrous_item:<item_id>", "nome": "Item Maravilhoso Raro à escolha",
                              "nivel_minimo": 14, "raridade": "raro", "sintonizacao": "varia", "repetivel": True})
        if facts.get("acao") in {"definir_planos", "set_known_plans"}:
            known = facts.get("planos_conhecidos", facts.get("planos", []))
            if not isinstance(known, list) or any(not isinstance(plan, str) for plan in known):
                return {**base, "resultado": "bloqueado", "motivo": "planos_conhecidos_devem_ser_lista_de_ids"}
            if len(known) != plans_count:
                return {**base, "resultado": "bloqueado", "motivo": "quantidade_de_planos_conhecidos_incorreta",
                        "quantidade_esperada": plans_count}
            if len(set(known)) != len(known):
                return {**base, "resultado": "bloqueado", "motivo": "planos_conhecidos_duplicados"}
            if any(_plan_metadata(plan, level) is None for plan in known):
                return {**base, "resultado": "bloqueado", "motivo": "plano_conhecido_invalido_para_nivel"}
            return {**base, "resultado": "planos_definidos", "planos_conhecidos": known,
                    "quantidade_planos_conhecidos": plans_count}
        if facts.get("acao") in {"aprender_plano", "learn_plan"}:
            if facts.get("ao_subir_de_nivel") is not True or level not in {6, 10, 14, 18}:
                return {**base, "resultado": "bloqueado", "motivo": "novo_plano_concedido_nos_niveis_6_10_14_18_ao_subir_de_nivel"}
            known = facts.get("planos_conhecidos")
            new_plan = facts.get("plano_novo")
            if not isinstance(known, list) or any(not isinstance(plan, str) for plan in known):
                return {**base, "resultado": "requer_dados", "motivo": "lista_de_planos_conhecidos_necessaria"}
            if len(known) != plans_count - 1:
                return {**base, "resultado": "bloqueado", "motivo": "quantidade_de_planos_antes_do_marco_incorreta",
                        "quantidade_esperada": plans_count - 1}
            if len(set(known)) != len(known) or any(_plan_metadata(plan, level) is None for plan in known):
                return {**base, "resultado": "bloqueado", "motivo": "planos_conhecidos_invalidos"}
            metadata = _plan_metadata(str(new_plan or ""), level)
            if metadata is None or new_plan in known:
                return {**base, "resultado": "bloqueado", "motivo": "plano_novo_invalido_ou_ja_conhecido"}
            return {**base, "resultado": "plano_aprendido", "plano_novo": new_plan,
                    "metadados": metadata, "planos_conhecidos": [*known, new_plan],
                    "quantidade_planos_conhecidos": plans_count}
        if facts.get("acao") in {"criar", "create"}:
            if facts.get("ferramentas_artesao_em_maos") is None:
                return {**base, "resultado": "requer_dados", "motivo": "confirmar_ferramentas_de_artesao_em_maos"}
            if facts.get("ferramentas_artesao_em_maos") is not True:
                return {**base, "resultado": "bloqueado", "motivo": "ferramentas_de_artesao_nao_estao_em_maos"}
            if facts.get("descanso_longo_concluido") is None:
                return {**base, "resultado": "requer_dados", "motivo": "confirmar_conclusao_de_descanso_longo"}
            if facts.get("descanso_longo_concluido") is not True:
                return {**base, "resultado": "bloqueado", "motivo": "descanso_longo_nao_concluido"}
            chosen = facts.get("planos", facts.get("plans", []))
            known = facts.get("planos_conhecidos")
            if not isinstance(chosen, list) or any(not isinstance(plan, str) for plan in chosen):
                return {**base, "resultado": "bloqueado", "motivo": "planos_devem_ser_lista_de_ids"}
            if not chosen:
                return {**base, "resultado": "escolha", "requer": "ao_menos_um_plano_conhecido"}
            if len(set(chosen)) != len(chosen):
                return {**base, "resultado": "bloqueado", "motivo": "cada_item_deve_usar_plano_diferente"}
            if len(chosen) > capacity:
                return {**base, "resultado": "bloqueado", "motivo": "limite_de_itens_excedido", "limite": capacity}
            if not isinstance(known, list):
                return {**base, "resultado": "requer_dados", "motivo": "lista_de_planos_conhecidos_necessaria"}
            if any(not isinstance(plan, str) for plan in known):
                return {**base, "resultado": "bloqueado", "motivo": "planos_conhecidos_devem_ser_ids"}
            if len(known) != plans_count:
                return {**base, "resultado": "bloqueado", "motivo": "quantidade_de_planos_conhecidos_incorreta",
                        "quantidade_esperada": plans_count}
            if len(set(known)) != len(known):
                return {**base, "resultado": "bloqueado", "motivo": "planos_conhecidos_duplicados"}
            if any(_plan_metadata(str(plan), level) is None for plan in known):
                return {**base, "resultado": "bloqueado", "motivo": "plano_conhecido_invalido_para_nivel"}
            if any(plan not in known for plan in chosen):
                return {**base, "resultado": "bloqueado", "motivo": "plano_nao_conhecido"}
            created = [{"plano": plan, **_plan_metadata(str(plan), level), "replicado": True,
                        "desaparece_apos_morte_em_dias": "1d4",
                        "plano_substituido_remove_imediatamente": True} for plan in chosen]
            current_items = facts.get("itens_atuais")
            if not isinstance(current_items, list):
                return {**base, "resultado": "requer_dados", "motivo": "inventario_atual_de_itens_replicados_necessario"}
            if any(not isinstance(item, dict) or not item.get("id") for item in current_items):
                return {**base, "resultado": "bloqueado", "motivo": "cada_item_atual_precisa_de_id_unico"}
            combined = [*current_items, *created]
            removed = combined[:-capacity] if len(combined) > capacity else []
            retained = combined[-capacity:]
            return {**base, "resultado": "criado", "planos": chosen, "itens_criados": created,
                    "itens_que_desaparecem": removed, "itens_atuais_apos_criacao": retained,
                    "quantidade": len(created), "limite_itens_criados": capacity,
                    "requer_id_unico_ao_adicionar_inventario": True,
                    "requer": "descanso_longo_concluido_e_ferramentas_de_artesao_em_maos",
                    "sintonizacao_imediata_se_necessaria": True,
                    "varinha_ou_arma_replicada_pode_ser_foco_de_conjuracao": True,
                    "desaparece_quando_voce_morre": "apos_1d4_dias",
                    "itens_de_plano_substituido": "desaparecem_imediatamente",
                    "conteudo_de_recipiente_desaparecido": "reaparece_inofensivamente_no_espaco"}
        if facts.get("acao") in {"substituir_plano", "replace_plan"}:
            if facts.get("ao_subir_de_nivel") is not True:
                return {**base, "resultado": "bloqueado", "motivo": "planos_so_podem_ser_substituidos_ao_subir_de_nivel"}
            old_plan, new_plan = facts.get("plano_antigo"), facts.get("plano_novo")
            known = facts.get("planos_conhecidos")
            if not isinstance(known, list):
                return {**base, "resultado": "requer_dados", "motivo": "lista_de_planos_conhecidos_necessaria"}
            if len(known) != plans_count or old_plan not in known:
                return {**base, "resultado": "bloqueado", "motivo": "plano_antigo_deve_ser_conhecido"}
            new_metadata = _plan_metadata(str(new_plan or ""), level)
            if new_metadata is None:
                return {**base, "resultado": "bloqueado", "motivo": "plano_novo_invalido_para_nivel"}
            if new_plan == old_plan:
                return {**base, "resultado": "bloqueado", "motivo": "plano_novo_deve_ser_diferente"}
            if new_plan in known:
                return {**base, "resultado": "bloqueado", "motivo": "plano_novo_ja_conhecido"}
            if any(not isinstance(plan, str) or _plan_metadata(plan, level) is None for plan in known):
                return {**base, "resultado": "bloqueado", "motivo": "planos_conhecidos_invalidos"}
            updated_known = [new_plan if plan == old_plan else plan for plan in known]
            return {**base, "resultado": "plano_substituido", "planos_conhecidos_antes": known,
                    "planos_conhecidos_depois": updated_known, "remove": old_plan, "adiciona": new_plan,
                    "itens_a_remover": [{"plano": old_plan, "remover_todos": True}],
                    "itens_criados_com_plano_antigo": "desaparecem_imediatamente"}
        known = facts.get("planos_conhecidos")
        return {**base, "resultado": "resolvido", "planos_conhecidos": plans_count,
                "quantidade_planos_conhecidos": plans_count, "planos_conhecidos_selecionados": known,
                "limite_itens_criados": capacity, "nivel_minimo_do_plano": tier,
                "planos_disponiveis": available, "limiares_de_plano": [2, 6, 10, 14],
                "cria_apos": "descanso_longo", "requer_ferramentas_de_artesao_em_maos": True,
                "sintonizacao_imediata_se_necessaria": True,
                "desaparece_quando_voce_morre": "apos_1d4_dias",
                "itens_de_plano_substituido": "desaparecem_imediatamente"}
    
    if key == "magic_item_tinker":
        action = str(facts.get("acao", "")).lower()
        if action in {"carregar", "charge", "drenar", "drain", "transmutar", "transmute"}:
            item_metadata = facts.get("metadados_item") if isinstance(facts.get("metadados_item"), dict) else {}
            if not facts.get("item_id"):
                return {**base, "resultado": "requer_dados", "motivo": "id_unico_do_item_necessario"}
            if facts.get("item_replicado", item_metadata.get("replicado")) is not True:
                return {**base, "resultado": "requer_dados", "motivo": "confirmar_que_o_item_foi_criado_por_replicar_item_magico",
                        "requer": "item_replicado=True"}
            if facts.get("distancia_m") is None:
                return {**base, "resultado": "requer_dados", "motivo": "distancia_ate_o_item_necessaria"}
            if float(facts["distancia_m"]) > 1.5:
                return {**base, "resultado": "bloqueado", "motivo": "item_fora_de_1_5_metro"}
        if action in {"carregar", "charge"}:
            slot = int(facts.get("nivel_espaco", 0))
            if facts.get("espaco_disponivel") is None:
                return {**base, "resultado": "requer_dados", "motivo": "confirmar_disponibilidade_do_espaco"}
            if facts.get("espaco_disponivel") is not True:
                return {**base, "resultado": "bloqueado", "motivo": "espaco_de_magia_indisponivel"}
            current_value = facts.get("cargas_atuais")
            maximum_value = facts.get("cargas_maximas", item_metadata.get("cargas"))
            if current_value is None or maximum_value is None:
                return {**base, "resultado": "requer_dados", "motivo": "cargas_maximas_e_atuais_necessarias"}
            current = int(current_value)
            maximum = int(maximum_value)
            if slot < 1 or slot > 5 or maximum < 1 or current < 0 or current > maximum:
                return {**base, "resultado": "bloqueado", "motivo": "dados_de_carga_ou_espaco_invalidos"}
            restored = min(slot, maximum - current)
            if restored <= 0:
                return {**base, "resultado": "bloqueado", "motivo": "item_ja_esta_com_cargas_maximas"}
            return {**base, "resultado": "carregado", "item_id": facts["item_id"],
                    "cargas_restauradas": restored, "cargas_atuais": current + restored,
                    "espaco_gasto": slot, "requer_item_replicado": True, "acao": "acao_bonus"}
        if action in {"drenar", "drain"}:
            if facts.get("usado_no_descanso_longo") is None:
                return {**base, "resultado": "requer_dados", "motivo": "estado_de_drenar_apos_descanso_longo_necessario"}
            if facts.get("usado_no_descanso_longo", False):
                return {**base, "resultado": "bloqueado", "motivo": "drenar_item_ja_usado_apos_descanso_longo"}
            rarity = str(facts.get("raridade", "")).lower()
            if rarity not in {"comum", "incomum", "raro", "common", "uncommon", "rare"}:
                return {**base, "resultado": "requer_dados", "motivo": "raridade_do_item_replicado_necessaria"}
            slot_level = 1 if rarity in {"comum", "common"} else 2
            return {**base, "resultado": "drenado", "item_id": facts["item_id"], "item_destruido": True,
                    "nivel_espaco_recuperado": slot_level, "limite": "uma_vez_por_descanso_longo",
                    "espaco_expira": "descanso_longo", "requer_item_replicado": True, "acao": "acao_bonus"}
        if action in {"transmutar", "transmute"}:
            if facts.get("usado_no_descanso_longo") is None:
                return {**base, "resultado": "requer_dados", "motivo": "estado_de_transmutar_apos_descanso_longo_necessario"}
            if facts.get("usado_no_descanso_longo", False):
                return {**base, "resultado": "bloqueado", "motivo": "transmutar_item_ja_usado_apos_descanso_longo"}
            origem, destino = facts.get("plano_origem", item_metadata.get("plano")), facts.get("plano_destino")
            conhecidos = facts.get("planos_conhecidos")
            if not isinstance(conhecidos, list) or any(not isinstance(plan, str) for plan in conhecidos):
                return {**base, "resultado": "requer_dados", "motivo": "lista_de_planos_conhecidos_necessaria"}
            if not origem or not destino:
                return {**base, "resultado": "escolha", "requer": ["plano_origem", "plano_destino"]}
            if origem == destino:
                return {**base, "resultado": "bloqueado", "motivo": "plano_destino_deve_ser_diferente"}
            if any(_plan_metadata(plan, level) is None for plan in conhecidos):
                return {**base, "resultado": "bloqueado", "motivo": "plano_conhecido_invalido_para_nivel"}
            if origem not in conhecidos:
                return {**base, "resultado": "bloqueado", "motivo": "plano_origem_nao_conhecido"}
            if destino not in conhecidos:
                return {**base, "resultado": "bloqueado", "motivo": "plano_destino_nao_conhecido"}
            destination_metadata = _plan_metadata(str(destino), level)
            if destination_metadata is None:
                return {**base, "resultado": "bloqueado", "motivo": "plano_destino_invalido_para_nivel"}
            return {**base, "resultado": "transmutado", "item_id": facts["item_id"],
                    "substitui": origem, "por": destino,
                    "novo_item": {"plano": destino, **destination_metadata, "replicado": True,
                                  "desaparece_apos_morte_em_dias": "1d4",
                                  "plano_substituido_remove_imediatamente": True},
                    "limite": "uma_vez_por_descanso_longo", "requer_item_replicado": True,
                    "acao": "acao_magica"}
        return {**base, "resultado": "escolha", "opcoes": ["carregar", "drenar", "transmutar"]}

    if key == "flash_of_genius":
        if facts.get("usos_gastos") is None:
            return {**base, "resultado": "requer_dados", "motivo": "estado_de_usos_de_lampejo_necessario"}
        if not facts.get("criatura_falhou", facts.get("creature_failed", False)):
            return {**base, "resultado": "bloqueado", "motivo": "so_apos_falha_em_teste_ou_salvaguarda"}
        if facts.get("reacao_disponivel") is None:
            return {**base, "resultado": "requer_dados", "motivo": "confirmar_disponibilidade_de_reacao"}
        if facts.get("reacao_disponivel") is not True:
            return {**base, "resultado": "bloqueado", "motivo": "reacao_indisponivel"}
        test_type = str(facts.get("tipo_teste", "")).lower()
        if test_type not in {"teste_de_habilidade", "salvaguarda", "ability_check", "saving_throw"}:
            return {**base, "resultado": "bloqueado", "motivo": "lampejo_so_afeta_teste_de_habilidade_ou_salvaguarda"}
        if facts.get("distancia_m") is None:
            return {**base, "resultado": "requer_dados", "motivo": "distancia_ate_a_criatura_necessaria"}
        if float(facts["distancia_m"]) > 9:
            return {**base, "resultado": "bloqueado", "motivo": "alvo_fora_do_alcance"}
        if float(facts["distancia_m"]) > 0 and facts.get("alvo_visivel") is not True:
            return {**base, "resultado": "requer_dados", "motivo": "confirmar_que_voce_ve_o_alvo",
                    "requer": "alvo_visivel=True"}
        spent = int(facts.get("usos_gastos", 0))
        maximum = max(1, int_mod)
        if spent >= maximum:
            return {**base, "resultado": "bloqueado", "motivo": "usos_esgotados", "usos_maximos": maximum}
        result = {**base, "resultado": "aplicado", "bonus": max(1, int_mod),
                  "reacao": True, "usos_maximos": maximum, "usos_restantes": maximum - spent - 1,
                  "alvo": "voce_ou_criatura_que_voce_ve_a_9m_ou_menos"}
        if facts.get("total") is not None:
            result["novo_total"] = int(facts["total"]) + max(1, int_mod)
        return result

    if key == "magic_item_adept":
        return {**base, "resultado": "resolvido", "limite_sintonizacao": 4,
                "beneficio_fabricacao": "incluido_em_magia_de_artifice"}

    if key == "spell_storing_item":
        if facts.get("descanso_longo_concluido") is not True:
            return {**base, "resultado": "requer_dados", "motivo": "confirmar_conclusao_de_descanso_longo"}
        if facts.get("distancia_m") is None:
            return {**base, "resultado": "requer_dados", "motivo": "distancia_ate_o_objeto_necessaria"}
        if float(facts["distancia_m"]) > 1.5:
            return {**base, "resultado": "bloqueado", "motivo": "objeto_fora_de_1_5_metro"}
        spell_level = int(facts.get("nivel_magia", facts.get("spell_level", 0)))
        if spell_level < 1 or spell_level > 3:
            return {**base, "resultado": "bloqueado", "motivo": "magia_deve_ser_de_1_a_3_circulo"}
        if facts.get("componente_material_consumido", False):
            return {**base, "resultado": "bloqueado", "motivo": "magia_consume_componente_material"}
        if facts.get("objeto_adequado") is not True:
            return {**base, "resultado": "requer_dados", "motivo": "objeto_deve_ser_arma_simples_marcial_ou_foco_de_conjuracao",
                    "requer": "objeto_adequado=True"}
        spell = facts.get("magia")
        if not spell:
            return {**base, "resultado": "escolha", "requer": ["magia_de_artifice_de_1_a_3_circulo",
                        "tempo_de_conjuracao_de_uma_acao", "sem_componente_material_consumido"]}
        from .spellcasting import ARTIFICER_SPELL_LEVELS, normalizar_nome_magia
        spell_level_in_list = next((v for name, v in ARTIFICER_SPELL_LEVELS.items()
                                    if normalizar_nome_magia(name) == normalizar_nome_magia(spell)), None)
        if spell_level_in_list is None or spell_level_in_list != spell_level:
            return {**base, "resultado": "bloqueado", "motivo": "magia_nao_esta_na_lista_do_artifice_no_nivel_informado"}
        normalized_spell = normalizar_nome_magia(spell)
        if normalized_spell in ARTIFICER_NON_ACTION_SPELLS:
            return {**base, "resultado": "bloqueado", "motivo": "tempo_de_conjuracao_nao_e_uma_acao",
                    "tempo_conjuracao": ARTIFICER_NON_ACTION_SPELLS[normalized_spell]}
        if facts.get("tempo_conjuracao_acao") is not True:
            return {**base, "resultado": "requer_dados", "motivo": "confirmar_tempo_de_conjuracao_de_uma_acao",
                    "requer": "tempo_conjuracao_acao=True"}
        if facts.get("criatura_ja_usou_neste_turno", False):
            return {**base, "resultado": "bloqueado", "motivo": "criatura_deve_aguardar_inicio_do_proximo_turno"}
        return {**base, "resultado": "armazenado", "magia": spell, "nivel_magia": spell_level,
                "usos": max(2, 2 * int_mod), "acao_para_lancar": "acao_magica", "habilidade_conjuracao": "inteligencia",
                "objeto": facts.get("objeto"), "requer_objeto_adequado": True,
                "concentracao_requerida": normalized_spell in ARTIFICER_CONCENTRATION_SPELLS,
                "bloqueio_por_criatura_ate": "inicio_do_proximo_turno_daquela_criatura",
                "componentes_materiais_consumidos": False, "substitui_armazenamento_anterior": True}

    if key == "advanced_artifice":
        spent = int(facts.get("usos_gastos", 0))
        if facts.get("acao") in {"recuperar", "recover"}:
            if facts.get("descanso_curto_concluido") is not True:
                return {**base, "resultado": "requer_dados", "motivo": "confirmar_conclusao_de_descanso_curto"}
            return {**base, "resultado": "recuperado", "usos_recuperados": 1,
                    "requer": "descanso_curto", "recurso": "lampejo_de_genio"}
        return {**base, "resultado": "resolvido", "limite_sintonizacao": 5,
                "uso_adicional_lampejo": "apos_descanso_curto", "usos_gastos_informados": spent}

    if key == "magic_item_master":
        return {**base, "resultado": "resolvido", "limite_sintonizacao": 6}

    if key == "soul_of_artifice":
        if facts.get("acao") in {"recuperar_lampejo", "recover_flash"}:
            if facts.get("descanso_curto_concluido") is not True:
                return {**base, "resultado": "requer_dados", "motivo": "confirmar_conclusao_de_descanso_curto"}
            if facts.get("sintonizado_item_magico") is not True:
                return {**base, "resultado": "bloqueado", "motivo": "requer_sintonizacao_com_item_magico"}
            return {**base, "resultado": "recuperado", "usos_recuperados": "todos",
                    "recurso": "lampejo_de_genio"}
        if facts.get("acao") in {"evitar_morte", "cheat_death"}:
            if facts.get("caiu_a_0_pv") is not True:
                return {**base, "resultado": "requer_dados", "motivo": "confirmar_que_os_pv_chegaram_a_zero"}
            if facts.get("morte_instantanea", False):
                return {**base, "resultado": "bloqueado", "motivo": "nao_funciona_contra_morte_instantanea"}
            items = facts.get("itens_destruidos", [])
            if not isinstance(items, list) or not items:
                return {**base, "resultado": "escolha", "requer": "itens_replicados_incomuns_ou_raros"}
            if any(not isinstance(item, dict) or not item.get("id") or item.get("replicado") is not True
                   or str(item.get("raridade", "")).lower() not in {"incomum", "raro", "uncommon", "rare"}
                   for item in items):
                return {**base, "resultado": "bloqueado", "motivo": "raridade_nao_elegivel"}
            item_ids = [item["id"] for item in items]
            if len(set(item_ids)) != len(item_ids):
                return {**base, "resultado": "bloqueado", "motivo": "itens_destruidos_devem_ser_unicos"}
            return {**base, "resultado": "sobreviveu", "pv_atuais": 20 * len(items),
                    "itens_destruidos": len(items), "ids_itens_destruidos": item_ids, "gatilho": "cair_a_0_pv",
                    "itens_elegiveis": "replicados_incomuns_ou_raros"}
        return {**base, "resultado": "resolvido", "cheat_death": True,
                "cura_por_item_destruido": 20,
                "restaura_lampejo_apos_descanso_curto": True,
                "requer_sintonizado_a_item_magico": True}

    if key == "resource_recovery":
        rest = str(facts.get("tipo_descanso", facts.get("rest_type", ""))).lower()
        int_mod = _modifier(int(facts.get("inteligencia", 10)))
        uses_max = max(1, int_mod)
        if rest in {"longo", "long", "descanso_longo", "long_rest"}:
            tinker_items = facts.get("itens_tinkers_atuais")
            if not isinstance(tinker_items, list):
                return {**base, "resultado": "requer_dados", "motivo": "lista_de_itens_tinkers_atuais_necessaria"}
            if any(not isinstance(item, dict) or not item.get("id") for item in tinker_items):
                return {**base, "resultado": "requer_dados", "motivo": "todos_os_itens_tinkers_precisam_de_id_unico_para_expirar"}
            if any(item.get("criado_por") != "tinkers_magic" for item in tinker_items):
                return {**base, "resultado": "bloqueado", "motivo": "a_lista_de_expiracao_deve_conter_apenas_itens_criados_por_magia_de_artifice"}
            ids_itens_tinkers = [str(item["id"]) for item in tinker_items]
            if len(set(ids_itens_tinkers)) != len(ids_itens_tinkers):
                return {**base, "resultado": "bloqueado", "motivo": "ids_de_itens_tinkers_duplicados"}
            from .spellcasting import ARTIFICER_SLOTS

            slots_restaurados = {
                str(i + 1): quantidade
                for i, quantidade in enumerate(ARTIFICER_SLOTS[level])
                if quantidade > 0
            }
            resources = {
                "magia_de_artifice": {"usos_gastos": 0, "usos_maximos": uses_max},
                "espacos_de_magia": {
                    "espacos_restantes": dict(slots_restaurados),
                    "usos_gastos": {circulo: 0 for circulo in slots_restaurados},
                },
            }
            if level >= 6:
                resources["drenar_item_magico"] = {"usado_no_descanso_longo": False}
                resources["transmutar_item_magico"] = {"usado_no_descanso_longo": False}
            if level >= 7:
                resources["lampejo_de_genio"] = {"usos_gastos": 0, "usos_maximos": uses_max}
            return {
                **base,
                "resultado": "recursos_recuperados",
                "tipo_descanso": "longo",
                "recursos": resources,
                "replicar_item_magico_disponivel": level >= 2,
                "pode_armazenar_outra_magia": level >= 11,
                "itens_tinkers_que_expiram": tinker_items,
                "delta_inventario": {"remover_ids": ids_itens_tinkers},
                "delta_mundo": {"remover_ids": ids_itens_tinkers},
                "delta_conjuracao": {
                    "espacos_restantes": dict(slots_restaurados),
                    "troca_truque_disponivel": True,
                    "mudanca_magias_preparadas_disponivel": True,
                },
            }
        if rest in {"curto", "short", "descanso_curto", "short_rest"}:
            if level >= 20 and facts.get("sintonizado_item_magico") is None:
                return {**base, "resultado": "requer_dados", "motivo": "confirmar_sintonizacao_para_recuperar_lampejo"}
            if level >= 20 and facts.get("sintonizado_item_magico") is True:
                return {**base, "resultado": "recursos_recuperados", "tipo_descanso": "curto",
                        "recursos": {"lampejo_de_genio": {"usos_gastos": 0, "usos_maximos": uses_max}},
                        "usos_lampejo_recuperados": "todos"}
            if level >= 14:
                spent = facts.get("lampejo_usos_gastos")
                if spent is None:
                    return {**base, "resultado": "requer_dados", "motivo": "usos_gastos_de_lampejo_necessarios"}
                spent = int(spent)
                if spent < 0 or spent > uses_max:
                    return {**base, "resultado": "bloqueado", "motivo": "estado_de_usos_de_lampejo_invalido"}
                restored = min(1, spent)
                return {**base, "resultado": "recursos_recuperados", "tipo_descanso": "curto",
                        "recursos": {"lampejo_de_genio": {"usos_gastos": spent - restored,
                                                          "usos_maximos": uses_max}},
                        "usos_lampejo_recuperados": restored}
            return {**base, "resultado": "nenhum_recurso_de_artifice_recuperado",
                    "tipo_descanso": "curto"}
        return {**base, "resultado": "requer_dados", "motivo": "tipo_descanso_deve_ser_curto_ou_longo"}

    if key == "epic_boon":
        return {**base, "resultado": "escolha", "opcoes": ["dadiva_epica", "outro_talento"],
                "nivel_minimo": 19}
    return None
