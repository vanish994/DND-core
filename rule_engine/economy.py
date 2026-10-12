"""Equipamentos, economia e itens mágicos do Livro do Jogador 2024."""

from __future__ import annotations

from typing import Any

from .catalog import CATALOGO_ARMADURAS, CATALOGO_ARMAS, CATALOGO_EQUIPAMENTOS

MOEDAS_POR_PO = {"pc": 0.01, "pp": 0.1, "pe": 0.5, "po": 1.0, "pl": 10.0}
RARIDADES = {"comum": 0, "incomum": 1, "raro": 2, "muito_raro": 3, "lendario": 4, "artefato": 5}

ITENS_MAGICOS = {
    "pocao_de_cura": {
        "nome": "Poção de Cura",
        "raridade": "comum",
        "sintonizacao": False,
        "consumivel": True,
        "efeito": "cura_2d4_mais_2",
    },
    "pocao_de_cura_maior": {
        "nome": "Poção de Cura Maior",
        "raridade": "incomum",
        "sintonizacao": False,
        "consumivel": True,
        "efeito": "cura_4d4_mais_4",
    },
    "varinha_de_misseis": {
        "nome": "Varinha de Mísseis Mágicos",
        "raridade": "incomum",
        "sintonizacao": False,
        "cargas": 7,
        "recarga": "1d6+1_ao_amanhecer",
        "efeito": "misseis_magicos",
    },
    "anel_de_protecao": {
        "nome": "Anel de Proteção",
        "raridade": "raro",
        "sintonizacao": True,
        "efeito": "mais_1_ca_e_salvaguardas",
    },
    "manto_de_protecao": {
        "nome": "Manto de Proteção",
        "raridade": "incomum",
        "sintonizacao": True,
        "efeito": "mais_1_ca_e_salvaguardas",
    },
    "botas_de_velocidade": {
        "nome": "Botas de Velocidade",
        "raridade": "raro",
        "sintonizacao": True,
        "efeito": "dobro_deslocamento",
    },
    "amuleto_de_saude": {
        "nome": "Amuleto de Saúde",
        "raridade": "raro",
        "sintonizacao": True,
        "efeito": "constituicao_19",
    },
    "bolsa_de_componentes": {
        "nome": "Bolsa de Componentes",
        "raridade": "comum",
        "sintonizacao": False,
        "efeito": "componentes_materiais",
    },
}


def converter_para_po(moedas: dict[str, int | float]) -> float:
    return sum(float(quantidade) * MOEDAS_POR_PO.get(str(tipo).lower(), 0) for tipo, quantidade in moedas.items())


def converter_de_po(valor: float) -> dict[str, int]:
    total_pc = round(float(valor) * 100)
    resultado = {
        "pl": total_pc // 1000,
        "po": (total_pc % 1000) // 100,
        "pe": (total_pc % 100) // 50,
        "pp": (total_pc % 50) // 10,
        "pc": total_pc % 10,
    }
    return {tipo: quantidade for tipo, quantidade in resultado.items() if quantidade}


def consultar_item(nome: str, categoria: str | None = None) -> dict[str, Any] | None:
    chave = str(nome).lower()
    if chave in ITENS_MAGICOS:
        return dict(ITENS_MAGICOS[chave], categoria="item_magico")
    catalogos = {
        "arma": CATALOGO_ARMAS,
        "armas": CATALOGO_ARMAS,
        "armadura": CATALOGO_ARMADURAS,
        "armaduras": CATALOGO_ARMADURAS,
        "equipamento": CATALOGO_EQUIPAMENTOS,
        "equipamentos": CATALOGO_EQUIPAMENTOS,
    }
    for tipo, catalogo in catalogos.items():
        if categoria and categoria.lower() not in {tipo, tipo + "s"}:
            continue
        for item, dados in catalogo.items():
            if item.lower() == chave:
                retorno = dict(dados)
                retorno.update({"nome": item, "categoria": tipo})
                if "custo_po" not in retorno:
                    retorno["custo_po"] = retorno.get("custo", 0)
                return retorno
    return None


def comprar_item(fatos: dict) -> dict[str, Any]:
    item = consultar_item(fatos["item"], fatos.get("categoria"))
    if not item:
        return {"resultado": "bloqueado", "motivo": "item_desconhecido"}
    quantidade = max(1, int(fatos.get("quantidade", 1)))
    preco = float(fatos.get("preco_po", item.get("custo_po", 0))) * quantidade
    saldo = converter_para_po(fatos.get("moedas", {}))
    if saldo < preco:
        return {"resultado": "bloqueado", "motivo": "saldo_insuficiente", "preco_po": preco, "saldo_po": saldo}
    return {
        "resultado": "comprado",
        "item": item["nome"],
        "quantidade": quantidade,
        "preco_po": preco,
        "troco": converter_de_po(saldo - preco),
    }


def vender_item(fatos: dict) -> dict[str, Any]:
    item = consultar_item(fatos["item"], fatos.get("categoria"))
    if not item:
        return {"resultado": "bloqueado", "motivo": "item_desconhecido"}
    quantidade = max(1, int(fatos.get("quantidade", 1)))
    preco = float(fatos.get("preco_po", item.get("custo_po", 0))) * quantidade
    percentual = float(fatos.get("percentual_venda", 50)) / 100
    valor = preco * percentual
    return {
        "resultado": "vendido",
        "item": item["nome"],
        "quantidade": quantidade,
        "recebe_po": valor,
        "moedas": converter_de_po(valor),
    }


def resolver_inventario(fatos: dict) -> dict[str, Any]:
    forca = int(fatos.get("forca", 10))
    peso = float(fatos.get("peso_atual", 0)) + float(fatos.get("peso_adicionado", 0))
    capacidade = max(0, forca) * 7.5
    itens = list(fatos.get("itens", []))
    removidos: list[dict[str, Any]] = []
    remove_ids = {str(x) for x in fatos.get("remover_ids", [])}
    remove_plans = {str(x) for x in fatos.get("remover_planos", [])}
    if remove_ids or remove_plans:
        retained = []
        for item in itens:
            if not isinstance(item, dict):
                retained.append(item)
                continue
            item_id = str(item.get("id", ""))
            plan = str(item.get("plano", ""))
            if (item_id and item_id in remove_ids) or (plan and plan in remove_plans):
                removidos.append(item)
                peso -= float(item.get("peso", 0)) * int(item.get("quantidade", 1))
            else:
                retained.append(item)
        itens = retained
    new_item = fatos.get("item_novo")
    if new_item is not None:
        if not isinstance(new_item, dict) or not new_item.get("id"):
            return {"resultado": "requer_dados", "motivo": "item_novo_precisa_de_metadados_e_id_unico"}
        new_id = str(new_item["id"])
        if any(isinstance(item, dict) and str(item.get("id", "")) == new_id for item in itens):
            return {"resultado": "bloqueado", "motivo": "id_de_item_ja_existe", "item_id": new_id}
        item_copy = dict(new_item)
        item_copy.setdefault("quantidade", 1)
        itens.append(item_copy)
        peso += float(item_copy.get("peso", 0)) * int(item_copy.get("quantidade", 1))
    if fatos.get("adicionar"):
        itens.append({"nome": fatos["adicionar"], "quantidade": int(fatos.get("quantidade", 1))})
    sintonizados = list(fatos.get("sintonizados", []))
    if removidos:
        removed_ids = {str(item.get("id")) for item in removidos if item.get("id") is not None}
        sintonizados = [x for x in sintonizados if str(x) not in removed_ids]
    return {
        "resultado": "sobrecarregado" if peso > capacidade else "normal",
        "peso": peso,
        "capacidade": capacidade,
        "itens": itens,
        "itens_removidos": removidos,
        "sintonizados": sintonizados,
    }


def _item_magico_de_fatos(fatos: dict) -> dict[str, Any] | None:
    item = consultar_item(fatos["item"])
    if item and item.get("categoria") == "item_magico":
        return item
    metadata = fatos.get("metadados_item")
    if not isinstance(metadata, dict) or not metadata:
        return None
    return {
        **metadata,
        "nome": metadata.get("nome", str(fatos["item"])),
        "categoria": "item_magico",
    }


def resolver_sintonizacao(fatos: dict) -> dict[str, Any]:
    item = _item_magico_de_fatos(fatos)
    if not item:
        return {"resultado": "bloqueado", "motivo": "item_magico_desconhecido"}
    sintonizados = list(fatos.get("sintonizados", []))
    nome = str(fatos["item"]).lower()
    requires_attunement = item.get("sintonizacao")
    if requires_attunement == "varia":
        if fatos.get("sintonizacao_requerida") is None:
            return {"resultado": "requer_dados", "motivo": "sintonizacao_depende_do_item_escolhido"}
        requires_attunement = bool(fatos["sintonizacao_requerida"])
    if not requires_attunement:
        return {"resultado": "nao_requerida", "item": item["nome"]}
    if item.get("sintonizacao_requer_classe") == "conjurador":
        if fatos.get("conjurador") is None:
            return {"resultado": "requer_dados", "motivo": "confirmar_se_usuario_e_conjurador"}
        if fatos.get("conjurador") is not True:
            return {"resultado": "bloqueado", "motivo": "item_requer_sintonizacao_por_conjurador"}
    if fatos.get("acao", "sintonizar") == "encerrar":
        if nome not in {str(x).lower() for x in sintonizados}:
            return {"resultado": "bloqueado", "motivo": "item_nao_sintonizado"}
        return {
            "resultado": "encerrada",
            "item": item["nome"],
            "sintonizados": [x for x in sintonizados if str(x).lower() != nome],
        }
    if nome in {str(x).lower() for x in sintonizados}:
        return {"resultado": "bloqueado", "motivo": "item_ja_sintonizado"}
    limite_informado = fatos.get("limite_sintonizacao")
    if limite_informado is None and str(fatos.get("classe", "")).lower() in {"artifice", "artificer"}:
        from .artificer_base import ARTIFICER_ATTUNEMENT_LIMIT, _tier_value
        limite_informado = _tier_value(ARTIFICER_ATTUNEMENT_LIMIT, int(fatos.get("nivel", 1)))
    limite = max(1, int(limite_informado if limite_informado is not None else 3))
    if len(sintonizados) >= limite:
        motivo = "limite_de_tres_itens" if limite == 3 else "limite_de_itens_sintonizados"
        return {"resultado": "bloqueado", "motivo": motivo, "limite": limite}
    sintonizados.append(nome)
    return {
        "resultado": "sintonizado",
        "item": item["nome"],
        "sintonizados": sintonizados,
        "limite": limite,
        "requer_descanso_curto": True,
    }


def usar_item_magico(fatos: dict) -> dict[str, Any]:
    item = _item_magico_de_fatos(fatos)
    if not item:
        return {"resultado": "bloqueado", "motivo": "item_magico_desconhecido"}
    requires_attunement = item.get("sintonizacao")
    if requires_attunement == "varia":
        if fatos.get("sintonizacao_requerida") is None:
            return {"resultado": "requer_dados", "motivo": "sintonizacao_depende_do_item_escolhido"}
        requires_attunement = bool(fatos["sintonizacao_requerida"])
    item_id = str(fatos["item"]).lower()
    if requires_attunement and item_id not in {str(x).lower() for x in fatos.get("sintonizados", [])}:
        return {"resultado": "bloqueado", "motivo": "requer_sintonizacao"}
    plan = str(item.get("plano", fatos.get("plano", ""))).lower()
    action = str(fatos.get("acao", "passivo")).lower()
    charges = fatos.get("cargas")

    if plan == "manifold_tool":
        if action not in {"transformar", "transform", "usar"}:
            return {"resultado": "escolha", "item": item["nome"], "opcoes": ["transformar"],
                    "acao": "acao_magica"}
        tool = fatos.get("ferramenta_artesao")
        if not tool:
            return {"resultado": "escolha", "motivo": "escolha_tipo_de_ferramenta_de_artesao"}
        return {"resultado": "transformado", "item": item["nome"], "ferramenta": tool,
                "proficiencia_concedida_ao_usar": True, "acao": "acao_magica"}
    if plan == "boots_of_the_winding_path":
        if action not in {"teleportar", "teleport", "usar"}:
            return {"resultado": "escolha", "item": item["nome"], "opcoes": ["teleportar"],
                    "acao": "acao_bonus", "distancia_maxima_m": 4.5}
        if fatos.get("distancia_m") is None or fatos.get("espaco_visto") is None or fatos.get("espaco_desocupado") is None or fatos.get("ocupou_este_turno") is None:
            return {"resultado": "requer_dados", "motivo": "distancia_visibilidade_espaco_e_posicao_anterior_necessarios"}
        if float(fatos["distancia_m"]) > 4.5:
            return {"resultado": "bloqueado", "motivo": "destino_fora_de_4_5_metros"}
        if fatos.get("espaco_visto") is not True or fatos.get("espaco_desocupado") is not True or fatos.get("ocupou_este_turno") is not True:
            return {"resultado": "bloqueado", "motivo": "destino_deve_ser_visto_livre_e_ocupado_este_turno"}
        return {"resultado": "teletransportado", "item": item["nome"], "distancia_m": float(fatos["distancia_m"]),
                "acao": "acao_bonus"}
    if plan == "dazzling_weapon":
        if action in {"iluminar", "light"}:
            return {"resultado": "usado", "item": item["nome"], "acao": "acao_bonus",
                    "luz_brilhante_raio_m": 9, "luz_fraca_raio_adicional_m": 9,
                    "efeito": item.get("efeito")}
        if action in {"cegar_atacante", "blind_attacker"}:
            if fatos.get("foi_atingido_por_ataque") is not True:
                return {"resultado": "bloqueado", "motivo": "gatilho_requer_ser_atingido_por_ataque"}
            if fatos.get("reacao_disponivel") is not True:
                return {"resultado": "bloqueado", "motivo": "reacao_indisponivel"}
            if charges is None:
                return {"resultado": "requer_dados", "motivo": "cargas_atuais_necessarias"}
            if int(charges) <= 0:
                return {"resultado": "bloqueado", "motivo": "sem_cargas"}
            save_total = fatos.get("salvaguarda_constituicao_total")
            if save_total is None:
                return {"resultado": "requer_dados", "motivo": "resultado_da_salvaguarda_de_constituicao_necessario",
                        "cd": 15}
            return {"resultado": "usado", "item": item["nome"], "cargas_restantes": int(charges) - 1,
                    "cd": 15, "salvaguarda_sucesso": int(save_total) >= 15,
                    "condicao_aplicada": None if int(save_total) >= 15 else "cego",
                    "duracao_condicao": "ate_o_fim_do_proximo_turno_do_atacante", "reacao": True}
        return {"resultado": "passivo", "item": item["nome"], "bonus_ataque": 1, "bonus_dano": 1}
    if plan == "helm_of_awareness":
        return {"resultado": "passivo", "item": item["nome"], "vantagem_iniciativa": True,
                "nao_pode_ser_surpreendido_enquanto_consciente": True}
    if plan == "mind_sharpener":
        if action not in {"manter_concentracao", "maintain_concentration"}:
            return {"resultado": "escolha", "item": item["nome"], "opcoes": ["manter_concentracao"]}
        if fatos.get("salvaguarda_constituicao_falhou") is not True:
            return {"resultado": "bloqueado", "motivo": "gatilho_requer_falha_em_salvaguarda_de_constituicao"}
        if fatos.get("reacao_disponivel") is not True:
            return {"resultado": "bloqueado", "motivo": "reacao_indisponivel"}
        if charges is None:
            return {"resultado": "requer_dados", "motivo": "cargas_atuais_necessarias"}
        if int(charges) <= 0:
            return {"resultado": "bloqueado", "motivo": "sem_cargas"}
        return {"resultado": "concentracao_mantida", "item": item["nome"],
                "salvaguarda_sucesso": True, "cargas_restantes": int(charges) - 1, "reacao": True}
    if plan == "repeating_shot":
        return {"resultado": "passivo", "item": item["nome"], "bonus_ataque": 1, "bonus_dano": 1,
                "somente_ataques_a_distancia": True, "ignora_propriedade_recarga": True,
                "cria_municao_magica_se_necessario": True}
    if plan == "repulsion_shield":
        if action in {"repelir", "repel"}:
            if fatos.get("foi_atingido_por_ataque_corpo_a_corpo") is not True:
                return {"resultado": "bloqueado", "motivo": "gatilho_requer_ataque_corpo_a_corpo"}
            if fatos.get("tamanho_atacante") not in {"miudo", "pequeno", "medio", "grande", "tiny", "small", "medium", "large"}:
                return {"resultado": "bloqueado", "motivo": "atacante_deve_ser_grande_ou_menor"}
            if fatos.get("distancia_m") is None:
                return {"resultado": "requer_dados", "motivo": "distancia_do_atacante_necessaria"}
            if float(fatos["distancia_m"]) > 1.5:
                return {"resultado": "bloqueado", "motivo": "atacante_fora_de_1_5_metro"}
            if fatos.get("reacao_disponivel") is not True:
                return {"resultado": "bloqueado", "motivo": "reacao_indisponivel"}
            if charges is None:
                return {"resultado": "requer_dados", "motivo": "cargas_atuais_necessarias"}
            if int(charges) <= 0:
                return {"resultado": "bloqueado", "motivo": "sem_cargas"}
            return {"resultado": "repelido", "item": item["nome"], "cargas_restantes": int(charges) - 1,
                    "deslocamento_empurrado_m": 4.5, "direcao": "linha_reta_para_longe_de_voce", "reacao": True}
        return {"resultado": "passivo", "item": item["nome"], "bonus_ca": 1}
    if plan == "returning_weapon":
        return {"resultado": "passivo", "item": item["nome"], "bonus_ataque": 1, "bonus_dano": 1,
                "retorna_apos_ataque_a_distancia": True, "requer_propriedade_arremesso": True}
    if plan == "spell_refueling_ring":
        if action not in {"recuperar_espaco", "recover_slot"}:
            return {"resultado": "escolha", "item": item["nome"], "opcoes": ["recuperar_espaco"],
                    "acao": "acao_bonus", "nivel_maximo_espaco": 3, "limite": "uma_vez_ate_o_proximo_amanhecer"}
        if fatos.get("conjurador") is not True:
            return {"resultado": "bloqueado", "motivo": "anel_requer_usuario_conjurador"}
        if fatos.get("usado_hoje") is None:
            return {"resultado": "requer_dados", "motivo": "estado_diario_do_anel_necessario"}
        if fatos.get("usado_hoje") is True:
            return {"resultado": "bloqueado", "motivo": "anel_ja_usado_antes_do_proximo_amanhecer"}
        if fatos.get("espaco_gasto") is not True:
            return {"resultado": "bloqueado", "motivo": "deve_haver_espaco_de_magia_gasto"}
        slot_level = int(fatos.get("nivel_espaco", 0))
        if slot_level < 1 or slot_level > 3:
            return {"resultado": "bloqueado", "motivo": "anel_recupera_apenas_espaco_de_nivel_1_a_3"}
        return {"resultado": "espaco_recuperado", "item": item["nome"], "nivel_espaco": slot_level,
                "usado_hoje": True, "acao": "acao_bonus"}

    if requires_attunement and item.get("sintonizacao_requer_classe") == "conjurador" and fatos.get("conjurador") is not True:
        return {"resultado": "bloqueado", "motivo": "item_requer_sintonizacao_por_conjurador"}
    charges = fatos.get("cargas")
    if charges is not None and int(charges) <= 0:
        return {"resultado": "bloqueado", "motivo": "sem_cargas"}
    retorno = {"resultado": "usado", "item": item["nome"], "efeito": item.get("efeito")}
    if charges is not None:
        retorno["cargas_restantes"] = int(charges) - 1
    return retorno
