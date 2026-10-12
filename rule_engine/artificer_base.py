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
    "all_purpose_tool_plus_1": {"nome": "Ferramenta Multifuncional +1", "nivel_minimo": 2, "raridade": "incomum", "sintonizacao": True},
    "repeating_shot": {"nome": "Disparo Repetidor", "nivel_minimo": 2, "raridade": "incomum", "sintonizacao": True},
    "returning_weapon": {"nome": "Arma Retornante", "nivel_minimo": 2, "raridade": "comum", "sintonizacao": False},
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
    "boots_of_the_winding_path": {"nome": "Botas do Caminho Sinuoso", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": True},
    "cloak_of_elvenkind": {"nome": "Manto Élfico", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": True},
    "cloak_of_the_manta_ray": {"nome": "Manto da Arraia", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": True},
    "dazzling_weapon": {"nome": "Arma Deslumbrante", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": True},
    "eyes_of_charming": {"nome": "Olhos Encantadores", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": True},
    "eyes_of_minute_seeing": {"nome": "Olhos de Visão Minuciosa", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "gloves_of_thievery": {"nome": "Luvas de Ladroagem", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "helm_of_awareness": {"nome": "Elmo da Consciência", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "lantern_of_revealing": {"nome": "Lanterna da Revelação", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "mind_sharpener": {"nome": "Aguçador Mental", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": True},
    "necklace_of_adaptation": {"nome": "Colar da Adaptação", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": True},
    "pipes_of_haunting": {"nome": "Flautas Assombradoras", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "repulsion_shield": {"nome": "Escudo de Repulsão", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "ring_of_swimming": {"nome": "Anel de Natação", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "ring_of_water_walking": {"nome": "Anel de Caminhar sobre a Água", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "sentinel_shield": {"nome": "Escudo Sentinela", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": False},
    "spell_refueling_ring": {"nome": "Anel de Reabastecimento de Magia", "nivel_minimo": 6, "raridade": "incomum", "sintonizacao": True},
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

ARTIFICER_PREPARED_SPELLS = {
    1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 6, 7: 7, 8: 7, 9: 9, 10: 9,
    11: 10, 12: 10, 13: 11, 14: 11, 15: 12, 16: 12, 17: 14, 18: 14,
    19: 15, 20: 15,
}
ARTIFICER_ATTUNEMENT_LIMIT = {1: 3, 10: 4, 14: 5, 18: 6}
ARTIFICER_GEAR = {
    "esferas_de_rolamento", "cesta", "saco_de_dormir", "sino", "cobertor",
    "talha_e_polias", "balde", "estrepes", "vela", "pe_de_cabra", "frasco", "jarro", "lampada",
    "rede", "oleo", "papel", "pergaminho", "vara", "bolsa", "corda", "saco",
    "pa", "barbante", "caixa_de_isca", "tocha", "frasco_de_vidro",
}
ARTIFICER_GEAR_LABELS = {
    "esferas_de_rolamento": "Esferas de rolamento", "cesta": "Cesta",
    "saco_de_dormir": "Saco de dormir", "sino": "Sino", "cobertor": "Cobertor",
    "talha_e_polias": "Talha e polias", "balde": "Balde", "estrepes": "Estrepes",
    "vela": "Vela", "pe_de_cabra": "Pé de cabra", "frasco": "Frasco",
    "jarro": "Jarro", "lampada": "Lâmpada", "rede": "Rede",
    "oleo": "Óleo", "papel": "Papel", "pergaminho": "Pergaminho", "vara": "Vara",
    "bolsa": "Bolsa", "corda": "Corda", "saco": "Saco", "pa": "Pá",
    "barbante": "Barbante", "caixa_de_isca": "Caixa de isqueiro", "tocha": "Tocha",
    "frasco_de_vidro": "Frasco de vidro",
}
ARTIFICER_GEAR_ALIASES = {
    "basket": "cesta", "bell": "sino", "blanket": "cobertor",
    "bucket": "balde", "candle": "vela", "ball_bearings": "esferas_de_rolamento",
    "bedroll": "saco_de_dormir",
    "block_and_tackle": "talha_e_polias", "caltrops": "estrepes", "crowbar": "pe_de_cabra",
    "flask": "frasco", "jug": "jarro",
    "lamp": "lampada", "net": "rede", "oil": "oleo",
    "paper": "papel", "parchment": "pergaminho", "pole": "vara", "pouch": "bolsa",
    "rope": "corda", "sack": "saco", "shovel": "pa", "string": "barbante",
    "tinderbox": "caixa_de_isca", "caixa_de_isqueiro": "caixa_de_isca",
    "torch": "tocha", "vial": "frasco_de_vidro",
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
        from .spellcasting import ARTIFICER_SLOTS
        cantrips = 2 if level < 10 else 3 if level < 14 else 4
        return {
            **base, "resultado": "resolvido", "truques_conhecidos": cantrips,
            "magias_preparadas": ARTIFICER_PREPARED_SPELLS[level],
            "espacos": {str(i + 1): count for i, count in enumerate(ARTIFICER_SLOTS[level])},
            "circulo_maximo": max(range(1, len(ARTIFICER_SLOTS[level]) + 1)),
            "cd_magia": 8 + prof + int_mod, "ataque_magia": prof + int_mod,
            "focos_validos": ["ferramentas_de_ladrao", "ferramentas_de_funileiro",
                              "outras_ferramentas_de_artesao_com_proficiencia", "varinhas_ou_armas_replicadas"],
            "troca_truque_apos_descanso_longo": True,
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
            if facts.get("ferramentas_tinkering_em_maos") is None:
                return {**base, "resultado": "requer_dados", "motivo": "confirmar_ferramentas_de_tinkering_em_maos"}
            if facts.get("ferramentas_tinkering_em_maos") is not True:
                return {**base, "resultado": "bloqueado", "motivo": "ferramentas_de_funileiro_nao_estao_em_maos"}
            if facts.get("distancia_m") is None:
                return {**base, "resultado": "requer_dados", "motivo": "distancia_ate_o_espaco_de_criacao_necessaria"}
            if float(facts["distancia_m"]) > 1.5:
                return {**base, "resultado": "bloqueado", "motivo": "espaco_de_criacao_fora_de_1_5_metro"}
            if facts.get("espaco_desocupado") is None:
                return {**base, "resultado": "requer_dados", "motivo": "confirmar_espaco_desocupado"}
            if facts.get("espaco_desocupado") is not True:
                return {**base, "resultado": "bloqueado", "motivo": "nao_ha_espaco_desocupado"}
            if not item:
                return {**base, "resultado": "escolha", "opcoes": [{"id": gear, "nome": ARTIFICER_GEAR_LABELS[gear]} for gear in sorted(ARTIFICER_GEAR)],
                        "acao": "acao_magica", "ferramentas_requeridas": "ferramentas_de_funileiro"}
            if item not in ARTIFICER_GEAR:
                return {**base, "resultado": "bloqueado", "motivo": "item_nao_permitido",
                        "opcoes": [{"id": gear, "nome": ARTIFICER_GEAR_LABELS[gear]} for gear in sorted(ARTIFICER_GEAR)]}
            gastos = int(facts.get("usos_gastos", 0))
            if gastos < 0 or gastos >= uses:
                return {**base, "resultado": "bloqueado", "motivo": "usos_esgotados",
                        "usos_maximos": uses, "usos_gastos": gastos}
            return {**base, "resultado": "criado", "item": item, "nome_item": ARTIFICER_GEAR_LABELS[item], "quantidade": 1,
                    "alcance_m": 1.5, "requer_espaco_desocupado": True,
                    "acao": "acao_magica", "usos_maximos": uses,
                    "usos_restantes": uses - gastos - 1, "desaparece": "proximo_descanso_longo"}
        return {**base, "resultado": "resolvido", "truque_conhecido": "Reparar",
                "usos_por_descanso_longo": uses, "acao": "acao_magica",
                "requer_ferramentas": "ferramentas_de_funileiro", "foco": "ferramentas_de_funileiro",
                "duracao_itens_criados": "ate_concluir_descanso_longo"}

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
            if not facts.get("item_id"):
                return {**base, "resultado": "requer_dados", "motivo": "id_unico_do_item_necessario"}
            if facts.get("item_replicado") is not True:
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
            current = int(facts.get("cargas_atuais", 0))
            maximum = int(facts.get("cargas_maximas", 0))
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
            origem, destino = facts.get("plano_origem"), facts.get("plano_destino")
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
        from .spells import obter_magia
        spell_metadata = obter_magia(str(spell)) or {}
        return {**base, "resultado": "armazenado", "magia": spell, "nivel_magia": spell_level,
                "usos": max(2, 2 * int_mod), "acao_para_lancar": "acao_magica", "habilidade_conjuracao": "inteligencia",
                "objeto": facts.get("objeto"), "requer_objeto_adequado": True,
                "concentracao_requerida": bool(spell_metadata.get("concentracao", False)),
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
            resources = {
                "magia_de_artifice": {"usos_gastos": 0, "usos_maximos": uses_max},
                "espacos_de_magia": "todos",
            }
            if level >= 6:
                resources["drenar_item_magico"] = {"usado_no_descanso_longo": False}
                resources["transmutar_item_magico"] = {"usado_no_descanso_longo": False}
            if level >= 7:
                resources["lampejo_de_genio"] = {"usos_gastos": 0, "usos_maximos": uses_max}
            return {**base, "resultado": "recursos_recuperados", "tipo_descanso": "longo",
                    "recursos": resources, "replicar_item_magico_disponivel": level >= 2,
                    "pode_armazenar_outra_magia": level >= 11,
                    "itens_tinkers_que_expiram": tinker_items}
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
