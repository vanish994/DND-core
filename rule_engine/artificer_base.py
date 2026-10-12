"""Resolução determinística da classe base Artífice 5.5e (Eberron: Forge of the Artificer).

As saídas descrevem efeitos mecânicos e requisitos; o estado persistente (usos,
itens, cargas e espaços) continua pertencendo ao chamador do Rule Engine.
"""
from __future__ import annotations

from typing import Any

# Progressão publicada da classe base, sem características de subclasse.
ARTIFICER_PLANS_KNOWN = {2: 4, 6: 5, 10: 6, 14: 7, 18: 8}
ARTIFICER_MAGIC_ITEMS = {2: 2, 6: 3, 10: 4, 14: 5, 18: 6}
ARTIFICER_PREPARED_SPELLS = {
    1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 6, 7: 7, 8: 7, 9: 9, 10: 9,
    11: 10, 12: 10, 13: 11, 14: 11, 15: 12, 16: 12, 17: 14, 18: 14,
    19: 15, 20: 15,
}
ARTIFICER_ATTUNEMENT_LIMIT = {1: 3, 10: 4, 14: 5, 18: 6}
ARTIFICER_GEAR = {
    "esferas_de_rolamento", "cesta", "saco_de_dormir", "sino", "cobertor",
    "talha_e_polias", "balde", "estrepes", "vela", "pe_de_cabra",
    "frasco", "jarro", "lampada", "rede", "oleo", "papel", "pergaminho",
    "vara", "bolsa", "corda", "saco", "pa", "barbante", "caixa_de_isca",
    "tocha", "frasco_de_vidro", "gancho_de_escala",
}
ARTIFICER_FEATURE_ALIASES = {
    "conjuracao": "conjuracao",
    "magia_de_artifice": "tinkers_magic",
    "tinkers_magic": "tinkers_magic",
    "replicar_item_magico": "replicate_magic_item",
    "replicate_magic_item": "replicate_magic_item",
    "artesao_de_item_magico": "magic_item_tinker",
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
            "focos_validos": ["ferramentas_de_ladrao", "ferramentas_de_artifice",
                              "outras_ferramentas_de_artesao_com_proficiencia"],
            "troca_truque_apos_descanso_longo": True,
            "recupera_espacos": "descanso_longo",
        }

    if key == "tinkers_magic":
        item = str(facts.get("item", "")).strip().lower().replace(" ", "_")
        uses = max(1, int_mod)
        if facts.get("acao") in {"criar", "create"}:
            if not item:
                return {**base, "resultado": "escolha", "opcoes": sorted(ARTIFICER_GEAR),
                        "acao": "acao_magica", "ferramentas_requeridas": "ferramentas_de_tinkering"}
            if item not in ARTIFICER_GEAR:
                return {**base, "resultado": "bloqueado", "motivo": "item_nao_permitido",
                        "opcoes": sorted(ARTIFICER_GEAR)}
            gastos = int(facts.get("usos_gastos", 0))
            if gastos < 0 or gastos >= uses:
                return {**base, "resultado": "bloqueado", "motivo": "usos_esgotados",
                        "usos_maximos": uses, "usos_gastos": gastos}
            return {**base, "resultado": "criado", "item": item, "quantidade": 1,
                    "alcance_m": 1.5, "requer_espaco_desocupado": True,
                    "acao": "acao_magica", "usos_maximos": uses,
                    "usos_restantes": uses - gastos - 1, "desaparece": "proximo_descanso_longo"}
        return {**base, "resultado": "resolvido", "truque_conhecido": "consertar",
                "usos_por_descanso_longo": uses, "acao": "acao_magica",
                "requer_ferramentas": "ferramentas_de_tinkering",
                "duracao_itens_criados": "ate_concluir_descanso_longo"}

    if key == "replicate_magic_item":
        plans = _tier_value(ARTIFICER_PLANS_KNOWN, level)
        capacity = _tier_value(ARTIFICER_MAGIC_ITEMS, level)
        tier = 2 if level < 6 else 6 if level < 10 else 10 if level < 14 else 14
        if facts.get("acao") in {"criar", "create"}:
            chosen = facts.get("planos", facts.get("plans", []))
            if not isinstance(chosen, list):
                return {**base, "resultado": "bloqueado", "motivo": "planos_devem_ser_lista"}
            if len(chosen) > capacity:
                return {**base, "resultado": "bloqueado", "motivo": "limite_de_itens_excedido",
                        "limite": capacity}
            known = facts.get("planos_conhecidos")
            if known is not None and any(plan not in known for plan in chosen):
                return {**base, "resultado": "bloqueado", "motivo": "plano_nao_conhecido"}
            return {**base, "resultado": "criado", "itens": chosen,
                    "quantidade": len(chosen), "requer": "descanso_longo",
                    "sintonizacao_imediata_se_necessaria": True}
        return {**base, "resultado": "resolvido", "planos_conhecidos": plans,
                "limite_itens_criados": capacity, "nivel_minimo_do_plano": tier,
                "limiares_de_plano": [2, 6, 10, 14],
                "cria_apos": "descanso_longo", "sintonizacao_imediata_se_necessaria": True}

    if key == "magic_item_tinker":
        action = str(facts.get("acao", "")).lower()
        if action in {"carregar", "charge"}:
            slot = int(facts.get("nivel_espaco", 0))
            current = int(facts.get("cargas_atuais", 0))
            maximum = int(facts.get("cargas_maximas", 0))
            if slot < 1 or maximum < 1 or current < 0 or current > maximum:
                return {**base, "resultado": "bloqueado", "motivo": "dados_de_carga_ou_espaco_invalidos"}
            restored = min(slot, maximum - current)
            return {**base, "resultado": "carregado", "cargas_restauradas": restored,
                    "cargas_atuais": current + restored, "espaco_gasto": slot,
                    "requer_item_replicado": True, "acao": "acao_magica"}
        if action in {"drenar", "drain"}:
            if not facts.get("nivel_espaco_recuperado"):
                return {**base, "resultado": "requer_dados", "motivo": "raridade_do_item_deve_mapear_para_nivel_de_espaco",
                        "requer": ["item_replicado", "nivel_espaco_recuperado"]}
            return {**base, "resultado": "drenado", "item_destruido": True,
                    "nivel_espaco_recuperado": int(facts["nivel_espaco_recuperado"]),
                    "limite": "uma_vez_por_descanso_longo", "acao": "acao_magica"}
        if action in {"transmutar", "transmute"}:
            origem, destino = facts.get("plano_origem"), facts.get("plano_destino")
            conhecidos = facts.get("planos_conhecidos", [])
            if not origem or not destino:
                return {**base, "resultado": "escolha", "requer": ["plano_origem", "plano_destino"]}
            if destino not in conhecidos:
                return {**base, "resultado": "bloqueado", "motivo": "plano_destino_nao_conhecido"}
            return {**base, "resultado": "transmutado", "substitui": origem,
                    "por": destino, "limite": "uma_vez_por_descanso_longo",
                    "requer_item_replicado": True, "acao": "acao_magica"}
        return {**base, "resultado": "escolha", "opcoes": ["carregar", "drenar", "transmutar"]}

    if key == "flash_of_genius":
        if not facts.get("criatura_falhou", facts.get("creature_failed", False)):
            return {**base, "resultado": "bloqueado", "motivo": "so_apos_falha_em_teste_ou_salvaguarda"}
        if facts.get("distancia_m") is not None and float(facts["distancia_m"]) > 9:
            return {**base, "resultado": "bloqueado", "motivo": "alvo_fora_do_alcance"}
        spent = int(facts.get("usos_gastos", 0))
        maximum = max(1, int_mod)
        if spent >= maximum:
            return {**base, "resultado": "bloqueado", "motivo": "usos_esgotados", "usos_maximos": maximum}
        return {**base, "resultado": "aplicado", "bonus": int_mod,
                "novo_total": int(facts.get("total", 0)) + int_mod,
                "reacao": True, "usos_maximos": maximum, "usos_restantes": maximum - spent - 1,
                "alvo": "criatura_que_voce_ve_a_9m_ou_menos"}

    if key == "magic_item_adept":
        return {**base, "resultado": "resolvido", "limite_sintonizacao": 4,
                "beneficio_fabricacao": "incluido_em_magia_de_artifice"}

    if key == "spell_storing_item":
        spell_level = int(facts.get("nivel_magia", facts.get("spell_level", 0)))
        if spell_level < 1 or spell_level > 3:
            return {**base, "resultado": "bloqueado", "motivo": "magia_deve_ser_de_1_a_3_circulo"}
        if facts.get("componente_material_consumido", False):
            return {**base, "resultado": "bloqueado", "motivo": "magia_consume_componente_material"}
        spell = facts.get("magia")
        if not spell:
            return {**base, "resultado": "escolha", "requer": ["magia_de_artifice_de_1_a_3_circulo",
                        "sem_componente_material_consumido"]}
        uses = max(1, 2 * int_mod)
        return {**base, "resultado": "armazenado", "magia": spell, "nivel_magia": spell_level,
                "usos": uses, "acao_para_lancar": "acao_magica", "habilidade_conjuracao": "inteligencia",
                "objeto": facts.get("objeto"), "requer_objeto_adequado": True}

    if key == "advanced_artifice":
        spent = int(facts.get("usos_gastos", 0))
        if facts.get("acao") in {"recuperar", "recover"}:
            return {**base, "resultado": "recuperado", "usos_recuperados": 1,
                    "requer": "descanso_curto", "recurso": "lampejo_de_genio"}
        return {**base, "resultado": "resolvido", "limite_sintonizacao": 5,
                "uso_adicional_lampejo": "apos_descanso_curto", "usos_gastos_informados": spent}

    if key == "magic_item_master":
        return {**base, "resultado": "resolvido", "limite_sintonizacao": 6}

    if key == "soul_of_artifice":
        if facts.get("acao") in {"evitar_morte", "cheat_death"}:
            items = facts.get("itens_destruidos", [])
            if not isinstance(items, list) or not items:
                return {**base, "resultado": "escolha", "requer": "itens_replicados_incomuns_ou_raros"}
            if any(str(item.get("raridade", "")).lower() not in {"incomum", "raro", "uncommon", "rare"}
                   for item in items if isinstance(item, dict)):
                return {**base, "resultado": "bloqueado", "motivo": "raridade_nao_elegivel"}
            return {**base, "resultado": "sobreviveu", "pv_atuais": 20 * len(items),
                    "itens_destruidos": len(items), "gatilho": "cair_a_0_pv",
                    "itens_elegiveis": "replicados_incomuns_ou_raros"}
        return {**base, "resultado": "resolvido", "cheat_death": True,
                "cura_por_item_destruido": 20,
                "restaura_lampejo_apos_descanso_curto": True,
                "requer_sintonizado_a_item_magico": True}

    if key == "epic_boon":
        return {**base, "resultado": "escolha", "opcoes": ["dadiva_epica", "outro_talento"],
                "nivel_minimo": 19}
    return None
