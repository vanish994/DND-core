"""Talentos do Livro do Jogador 2024: Origem, Gerais e Dádivas Épicas."""

import unicodedata


def _normalizar_nome(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor).strip().lower())
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return "_".join(texto.replace("-", " ").split())


ORIGIN_FEATS = {
    "alerta": {"categoria": "origem", "efeitos": ["proficiência_iniciativa", "troca_iniciativa"]},
    "artifista": {
        "categoria": "origem",
        "efeitos": ["proficiência_3_ferramentas", "desconto_20_porcento", "fabricacao_rapida"],
    },
    "atacante_selvagem": {"categoria": "origem", "efeitos": ["rolar_dano_da_arma_duas_vezes"]},
    "curandeiro": {"categoria": "origem", "efeitos": ["medico_de_combate", "cura_garantida"]},
    "habilidoso": {"categoria": "origem", "repetivel": True, "efeitos": ["proficiência_3_pericias_ou_ferramentas"]},
    "iniciado_em_magia": {"categoria": "origem", "repetivel": True, "efeitos": ["dois_truques", "magia_1_circulo"]},
    "musico": {"categoria": "origem", "efeitos": ["proficiência_3_instrumentos", "inspiracao_heroica_aliados"]},
    "sortudo": {
        "categoria": "origem",
        "efeitos": ["pontos_de_sorte_igual_proficiencia", "vantagem_ou_desvantagem_d20"],
    },
    "valentao_de_taverna": {
        "categoria": "origem",
        "efeitos": ["ataque_desarmado_1d4", "proficiência_armas_improvisadas", "empurra_1_5m"],
    },
    "vigoroso": {"categoria": "origem", "efeitos": ["pv_maximos_mais_2_nivel"]},
}

_GENERAL_NAMES = [
    "adepto_elemental",
    "agressor",
    "analitico",
    "atirador_arcano",
    "atleta",
    "ator",
    "aumento_no_valor_de_atributo",
    "chef",
    "combatente_montado",
    "conjurador_belico",
    "conjurador_ritualista",
    "duelista_defensivo",
    "envenenador",
    "esmagador",
    "especialista_ambidestro",
    "especialista_em_armaduras_leves",
    "especialista_em_armaduras_medias",
    "especialista_em_armaduras_pesadas",
    "especialista_em_besta",
    "especialista_em_pericia",
    "exterminador_de_conjuradores",
    "imobilizador",
    "lider_inspirador",
    "mente_agucada",
    "mestre_das_armas",
    "mestre_em_armaduras_medias",
    "mestre_em_armaduras_pesadas",
    "mestre_em_armas_de_haste",
    "mestre_em_armas_grandes",
    "mestre_em_escudos",
    "mestre_atirador",
    "perfurador",
    "resiliente",
    "resistente",
    "sentinela",
    "sorrateiro",
    "talhador",
    "telecinético",
    "telepatico",
    "tocado_pela_sombra",
    "tocado_pelas_fadas",
    "treinamento_com_armas_marciais",
    "velocista",
]
GENERAL_FEATS = {
    name: {"categoria": "geral", "nivel": 4, "efeitos": ["aumento_de_atributo_1"]} for name in _GENERAL_NAMES
}
for name in {"aumento_no_valor_de_atributo"}:
    GENERAL_FEATS[name] = {
        "categoria": "geral",
        "nivel": 4,
        "repetivel": True,
        "efeitos": ["aumento_de_atributo_2_ou_dois_1"],
    }
for name in {"adepto_elemental", "atirador_arcano", "conjurador_belico", "conjurador_ritualista"}:
    GENERAL_FEATS[name]["requer_conjuracao"] = True
for name in {
    "atleta",
    "agressor",
    "especialista_ambidestro",
    "especialista_em_besta",
    "imobilizador",
    "mestre_atirador",
    "sentinela",
    "sorrateiro",
    "velocista",
    "treinamento_com_armas_marciais",
}:
    GENERAL_FEATS[name]["atributo_13"] = ["forca", "destreza"]
GENERAL_FEATS["conjurador_belico"]["efeitos"] += [
    "vantagem_concentracao",
    "magia_reativa",
    "componentes_somaticos_com_maos_ocupadas",
]
GENERAL_FEATS["adepto_elemental"]["efeitos"] += ["ignora_resistencia_elemental", "uns_no_dano_tratados_como_dois"]
GENERAL_FEATS["atirador_arcano"]["efeitos"] += ["ignora_cobertura_magica", "sem_desvantagem_a_1_5m", "alcance_mais_18m"]
GENERAL_FEATS["chef"]["efeitos"] = [
    "proficiência_utensilios_cozinheiro",
    "refeicao_mais_1d8",
    "guloseimas_pv_temporarios",
]
GENERAL_FEATS["resiliente"]["efeitos"] = ["aumento_atributo_1", "proficiência_salvaguarda"]
GENERAL_FEATS["resistente"]["efeitos"] = [
    "aumento_constituicao_1",
    "vantagem_salvaguardas_contra_morte",
    "cura_com_dado_de_vida_acao_bonus",
]
GENERAL_FEATS["mestre_em_armaduras_pesadas"]["efeitos"] += ["reduz_dano_fisico_pela_proficiencia"]
GENERAL_FEATS["mestre_em_escudos"]["efeitos"] += ["golpe_de_escudo", "interpor_escudo"]
GENERAL_FEATS["sentinela"]["efeitos"] += ["ataque_de_oportunidade_ao_desengajar", "zera_deslocamento"]
GENERAL_FEATS["sorrateiro"]["efeitos"] += ["visao_as_cegas_3m", "vantagem_furtividade_combate"]
GENERAL_FEATS["telecinético"]["efeitos"] = ["aumento_atributo_1", "maos_magicas_aprimoradas", "empurrao_telecinetico"]
GENERAL_FEATS["telepatico"]["efeitos"] = ["aumento_atributo_1", "comunicacao_telepatica_18m", "detectar_pensamentos"]
GENERAL_FEATS["tocado_pela_sombra"]["efeitos"] = ["aumento_atributo_1", "magia_sombria", "invisibilidade"]
GENERAL_FEATS["tocado_pelas_fadas"]["efeitos"] = ["aumento_atributo_1", "magia_feerica", "passo_nebuloso"]

EPIC_FEATS = {
    "dadiva_da_fortitude": ["aumento_atributo_1_ate_30", "pv_maximos_mais_40", "cura_adicional_constituicao"],
    "dadiva_da_proeza_em_combate": ["aumento_atributo_1_ate_30", "ataque_errado_acerta_uma_vez_por_turno"],
    "dadiva_da_proficiencia_em_pericia": ["aumento_atributo_1_ate_30", "proficiência_todas_pericias", "especialização"],
    "dadiva_da_recordacao_de_magia": ["aumento_atributo_1_ate_30", "espaco_1_a_4_pode_nao_ser_gasto"],
    "dadiva_da_recuperacao": ["aumento_atributo_1_ate_30", "ao_0_pv_fica_com_1_e_cura_metade", "reserva_dez_d10"],
    "dadiva_da_resistencia_a_energia": [
        "aumento_atributo_1_ate_30",
        "duas_resistencias_escolhidas",
        "redireciona_dano_2d12",
    ],
    "dadiva_da_velocidade": ["aumento_atributo_1_ate_30", "desengajar_acao_bonus", "deslocamento_mais_9m"],
    "dadiva_da_viagem_dimensional": ["aumento_atributo_1_ate_30", "teleporte_9m_apos_atacar_ou_magia"],
    "dadiva_da_visao_verdadeira": ["aumento_atributo_1_ate_30", "visao_verdadeira_18m"],
    "dadiva_do_ataque_irresistivel": [
        "aumento_atributo_1_ate_30",
        "ignora_resistencia_fisica",
        "critico_causa_dano_atributo",
    ],
    "dadiva_do_destino": ["aumento_atributo_1_ate_30", "modifica_teste_d20_2d4"],
    "dadiva_do_espirito_da_noite": [
        "aumento_atributo_1_ate_30",
        "invisibilidade_em_sombras",
        "resistencia_quase_todos_danos",
    ],
}
EPIC_FEATS = {
    name: {"categoria": "dadiva_epica", "nivel": 19, "efeitos": effects} for name, effects in EPIC_FEATS.items()
}

# Ravenloft: Horror Wilds. O texto da biblioteca lista os nomes dos talentos de
# origem, mas não traz a descrição deles; os efeitos ficam sem catalogar.
RAVENLOFT_ORIGIN_FEATS = {
    "olho_agucado": {
        "categoria": "origem",
        "fonte": "ravenloft",
        "efeitos": [
            "vantagem_em_teste_de_atributo_da_acao_procurar_ou_estudar",
            "usos_iguais_bonus_proficiencia_por_descanso_longo",
            "uso_gasto_somente_em_sucesso",
        ],
    },
    "sobrevivente": {
        "categoria": "origem",
        "fonte": "ravenloft",
        "efeitos": [
            "hipervigilancia_rerrolar_d20_iniciativa_9_ou_menos_usa_novo",
            "controlar_se_reacao_soma_bp_em_resistencia_falha_contra_enfeiticado_ou_amedrontado_1_por_descanso_longo",
        ],
    },
}
ORIGIN_FEATS.update(RAVENLOFT_ORIGIN_FEATS)

DARK_GIFT_FEATS = {
    "anatomia_aberrante": [],
    "sombra_viva": ["maos_magicas_sem_componentes", "alcance_corpo_a_corpo_mais_3m"],
    "ser_simbiotico": ["proficiencia_1_pericia_da_lista", "idioma_adicional"],
    "alma_ecoante": [
        "proficiencia_2_pericias",
        "especializacao_1_pericia_troca_no_descanso_longo",
        "idioma_adicional",
        "ecos_intrusivos_ao_rolar_1",
    ],
    "andarilho_das_brumas": ["viajante_de_dominios"],
    "toque_da_morte": [],
    "sussurros_reunidos": ["mensagem_sem_componentes_materiais", "augurio_sempre_preparado_1_por_descanso_longo"],
    "segunda_pele": ["alterar_se_sempre_preparado_1_por_descanso_longo"],
    "observadores": ["sentido_bestial_e_falar_com_animais_1_por_descanso_longo", "busca_mais_1d4"],
}
DARK_GIFT_FEATS = {
    name: {"categoria": "dadiva_sombria", "requisito": "campanha_ravenloft", "fonte": "ravenloft", "efeitos": effects}
    for name, effects in DARK_GIFT_FEATS.items()
}

FEATS = {
    _normalizar_nome(nome): dados
    for nome, dados in {**ORIGIN_FEATS, **GENERAL_FEATS, **EPIC_FEATS, **DARK_GIFT_FEATS}.items()
}


def validar_talento(fatos: dict) -> dict:
    nome = _normalizar_nome(fatos.get("talento", ""))
    dados = FEATS.get(nome)
    if not dados:
        return {"resultado": "bloqueado", "motivo": "talento_desconhecido"}
    nivel = int(fatos.get("nivel", fatos.get("nivel_personagem", 1)))
    if nivel < dados.get("nivel", 1):
        return {"resultado": "bloqueado", "motivo": "nivel_insuficiente", "nivel_minimo": dados["nivel"]}
    if dados.get("requisito") == "campanha_ravenloft" and fatos.get("campanha_ravenloft") is not True:
        return {"resultado": "bloqueado", "motivo": "requer_campanha_ravenloft"}
    if dados.get("requer_conjuracao") and not fatos.get(
        "caracteristica_conjuracao", fatos.get("magia_de_pacto", False)
    ):
        return {"resultado": "bloqueado", "motivo": "requer_conjuracao"}
    for atributo in dados.get("atributo_13", []):
        if int(fatos.get(atributo, 0)) >= 13:
            break
    else:
        if dados.get("atributo_13"):
            return {"resultado": "bloqueado", "motivo": "atributo_insuficiente", "atributos": dados["atributo_13"]}
    if dados.get("categoria") == "dadiva_epica" and nivel < 19:
        return {"resultado": "bloqueado", "motivo": "requer_nivel_19"}
    return {"resultado": "disponivel", "talento": nome, "categoria": dados["categoria"], "efeitos": dados["efeitos"]}


# Benefícios mecânicos por talento (PHB 2024, cap. 5). Valores determinísticos;
# números que dependem de dados ou atributos são calculados em resolver_talento.
_BENEFICIOS = {
    # --- Origem -----------------------------------------------------------
    "alerta": {
        "bonus_iniciativa": "bonus_proficiencia",
        "troca_iniciativa": True,
        "troca_exige": "aliado_voluntario_nao_incapacitado",
    },
    "artifista": {
        "proficiencia_ferramentas": 3,
        "desconto_compra": "20_porcento",
        "fabricacao_rapida": True,
        "fabricacao_duracao": "ate_o_proximo_descanso_longo",
    },
    "atacante_selvagem": {
        "rola_dano_da_arma_duas_vezes": True,
        "limite": "uma_vez_por_turno",
    },
    "curandeiro": {
        "medico_de_combate": {
            "acao": "usar_objeto",
            "cura": "dado_de_vida_da_criatura_mais_bonus_proficiencia",
            "requer": "kit_de_curandeiro",
            "alcance_m": 1.5,
        },
        "cura_garantida": "novo_dado_se_o_resultado_for_1",
    },
    "habilidoso": {"proficiencias": 3, "tipo": "pericias_ou_ferramentas", "repetivel": True},
    "iniciado_em_magia": {
        "truques": 2,
        "listas": ["clerigo", "druida", "mago"],
        "magia_1_circulo_sempre_preparada": True,
        "usos_sem_espaco": 1,
        "recarga": "descanso_longo",
        "atributo_conjuracao": ["inteligencia", "sabedoria", "carisma"],
        "repetivel": True,
    },
    "musico": {
        "proficiencia_instrumentos": 3,
        "inspiracao_heroica_aliados": "bonus_proficiencia",
        "momento": "descanso_curto_ou_longo",
    },
    "sortudo": {
        "pontos_de_sorte": "bonus_proficiencia",
        "vantagem_teste_d20": "gasta_1_ponto",
        "desvantagem_ataque_contra_voce": "gasta_1_ponto",
        "recarga": "descanso_longo",
    },
    "valentao_de_taverna": {
        "dano_desarmado": "1d4_mais_modificador_de_forca",
        "dano_garantido": "novo_dado_se_o_resultado_for_1",
        "proficiencia_armas_improvisadas": True,
        "empurra_m": 1.5,
        "limite": "uma_vez_por_turno",
    },
    "vigoroso": {"pv_por_nivel_adicional": 2},
    "olho_agucado": {
        "vantagem": "teste_de_atributo_de_procurar_ou_estudar",
        "usos": "bonus_proficiencia",
        "recarga": "descanso_longo",
        "consome_apenas_em_sucesso": True,
    },
    "sobrevivente": {
        "rerrolar_iniciativa_se_9_ou_menos": True,
        "resistencia_reacao": "bonus_proficiencia_contra_enfeiticado_ou_amedrontado",
        "usos": 1,
        "recarga": "descanso_longo",
    },
    # --- Gerais -----------------------------------------------------------
    "adepto_elemental": {
        "aumento_atributo": 1,
        "atributos_aumento": ["inteligencia", "sabedoria", "carisma"],
        "dominio_elemental": "escolha_de_1_tipo_acido_eletrico_gelido_igneo_ou_trovejante",
        "ignora_resistencia_do_tipo_escolhido": True,
        "uns_no_dano_tratados_como_dois": True,
        "repetivel": True,
    },
    "agressor": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca", "destreza"],
        "correr_bonus_deslocamento_m": 3,
        "ataque_em_investida": {"dano": "1d8", "alternativa": "empurra_ate_3m", "limite": "uma_vez_por_turno"},
    },
    "analitico": {
        "aumento_atributo": 1,
        "atributos_aumento": ["inteligencia", "sabedoria"],
        "observador_atento": "proficiencia_ou_especializacao_em_intuicao_investigacao_ou_percepcao",
        "procurar_como_acao_bonus": True,
    },
    "atirador_arcano": {
        "aumento_atributo": 1,
        "atributos_aumento": ["inteligencia", "sabedoria", "carisma"],
        "ignora_cobertura": ["parcial", "tres_quartos"],
        "sem_desvantagem_a_1_5m": True,
        "alcance_adicional_m": 18,
    },
    "atleta": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca", "destreza"],
        "deslocamento_de_escalada": "igual_ao_deslocamento",
        "levantar_caido_custa_m": 1.5,
        "salto_apos_mover_m": 1.5,
    },
    "ator": {
        "aumento_atributo": 1,
        "atributos_aumento": ["carisma"],
        "personificacao": "vantagem_em_atuacao_ou_engano_ao_disfarcado",
        "mimetismo_cd": "8_mais_modificador_de_carisma_mais_bonus_proficiencia",
    },
    "aumento_no_valor_de_atributo": {
        "aumento_atributo": "2_ou_dois_atributos_em_1",
        "maximo": 20,
        "repetivel": True,
    },
    "chef": {
        "aumento_atributo": 1,
        "atributos_aumento": ["constituicao", "sabedoria"],
        "proficiencia_utensilios_de_cozinheiro": True,
        "refeicao": {"criaturas": "4_mais_bonus_proficiencia", "cura_adicional": "1d8", "duracao": "descanso_curto"},
        "guloseimas": {
            "quantidade": "bonus_proficiencia",
            "pv_temporarios": "bonus_proficiencia",
            "duracao_horas": 8,
            "acao": "bonus",
        },
    },
    "combatente_montado": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca", "destreza", "sabedoria"],
        "golpe_montado": "vantagem_contra_desmontados_a_1_5m_da_montaria_menores",
        "pulo_lateral": "evasao_para_a_montaria",
        "redirecionar_ataque_da_montaria": True,
    },
    "conjurador_belico": {
        "aumento_atributo": 1,
        "atributos_aumento": ["inteligencia", "sabedoria", "carisma"],
        "vantagem_concentracao": True,
        "magia_reativa": "conjura_no_lugar_do_ataque_de_oportunidade",
        "componentes_somaticos_com_maos_ocupadas": True,
    },
    "conjurador_ritualista": {
        "aumento_atributo": 1,
        "atributos_aumento": ["inteligencia", "sabedoria", "carisma"],
        "magias_rituais_sempre_preparadas": "bonus_proficiencia",
        "ritual_rapido": {"sem_tempo_prolongado": True, "sem_espaco": True, "recarga": "descanso_longo"},
    },
    "duelista_defensivo": {
        "aumento_atributo": 1,
        "atributos_aumento": ["destreza"],
        "aparar": {
            "ca_bonus": "bonus_proficiencia",
            "duracao": "ate_o_inicio_do_proximo_turno",
            "requer": "arma_de_acuidade",
            "acao": "reacao",
        },
    },
    "envenenador": {
        "aumento_atributo": 1,
        "atributos_aumento": ["destreza", "inteligencia"],
        "ignora_resistencia_venenoso": True,
        "proficiencia_kit_de_veneno": True,
        "veneno": {
            "doses": "bonus_proficiencia",
            "custo_po": 50,
            "cd": "8_mais_atributo_aumentado_mais_bonus_proficiencia",
            "dano": "2d8_venenoso",
            "condicao": "envenenado_ate_o_fim_do_seu_proximo_turno",
            "duracao_aplicado": "1_minuto",
        },
    },
    "esmagador": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca", "constituicao"],
        "empurra_m": 1.5,
        "limite_empurrao": "uma_vez_por_turno",
        "critico_vantagem_contra_o_alvo": True,
    },
    "especialista_ambidestro": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca", "destreza"],
        "ataque_extra_leve_como_acao_bonus": True,
        "modificador_de_atributo_no_dano_adicional": False,
        "sacar_ou_embainhar_duas_armas": True,
    },
    "especialista_em_armaduras_leves": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca", "destreza"],
        "treinamento": ["armadura_leve", "escudo"],
    },
    "especialista_em_armaduras_medias": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca", "destreza"],
        "treinamento": ["armadura_media"],
    },
    "especialista_em_armaduras_pesadas": {
        "aumento_atributo": 1,
        "atributos_aumento": ["constituicao", "forca"],
        "treinamento": ["armadura_pesada"],
    },
    "especialista_em_besta": {
        "aumento_atributo": 1,
        "atributos_aumento": ["destreza"],
        "ignora_recarga": ["besta_de_mao", "besta_leve", "besta_pesada"],
        "sem_desvantagem_a_1_5m": True,
        "modificador_de_atributo_no_dano_adicional_leve": True,
    },
    "especialista_em_pericia": {
        "aumento_atributo": 1,
        "proficiencia_pericia": 1,
        "especializacao_pericia": 1,
    },
    "exterminador_de_conjuradores": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca", "destreza"],
        "desvantagem_concentracao_do_alvo": True,
        "resguardo_mental": "sucesso_automatico_em_salvaguarda_mental",
        "recarga": "descanso_curto_ou_longo",
    },
    "imobilizador": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca", "destreza"],
        "socar_e_imobilizar": "dano_e_imobilizar_uma_vez_por_turno",
        "vantagem_contra_imobilizado_por_voce": True,
        "movimento_sem_penalidade_ao_imobilizar": True,
    },
    "lider_inspirador": {
        "aumento_atributo": 1,
        "atributos_aumento": ["sabedoria", "carisma"],
        "aliados": 6,
        "alcance_m": 9,
        "momento": "descanso_curto_ou_longo",
    },
    "mente_agucada": {
        "aumento_atributo": 1,
        "atributos_aumento": ["inteligencia"],
        "conhecimento_vasto": "proficiencia_ou_especializacao_em_arcanismo_historia_investigacao_natureza_ou_religiao",
        "analisar_como_acao_bonus": True,
    },
    "mestre_das_armas": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca", "destreza"],
        "maestria_em_arma": 1,
        "troca": "descanso_longo",
    },
    "mestre_em_armaduras_medias": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca", "destreza"],
        "bonus_ca_destreza_maximo": 3,
    },
    "mestre_em_armaduras_pesadas": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca", "constituicao"],
        "reducao_dano_fisico": "bonus_proficiencia",
    },
    "mestre_em_armas_de_haste": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca", "destreza"],
        "golpe_de_haste": {"dado": "d4", "tipo": "contundente", "acao": "bonus"},
        "golpe_reativo": "ataque_quando_entra_no_seu_alcance",
        "armas": ["cajado", "lanca", "extensao_e_pesado"],
    },
    "mestre_em_armas_grandes": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca"],
        "dano_adicional": "bonus_proficiencia",
        "cortar": "ataque_como_acao_bonus_apos_critico_ou_reduzir_a_0_pv",
    },
    "mestre_em_escudos": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca"],
        "golpe_de_escudo": {
            "cd": "8_mais_modificador_de_forca_mais_bonus_proficiencia",
            "salvaguarda": "forca",
            "efeito": "empurra_1_5m_ou_caido",
            "limite": "uma_vez_por_turno",
        },
        "interpor_escudo": "sem_dano_com_evasao_bem_sucedida",
    },
    "mestre_atirador": {
        "aumento_atributo": 1,
        "atributos_aumento": ["destreza"],
        "ignora_cobertura": ["parcial", "tres_quartos"],
        "sem_desvantagem_a_1_5m": True,
        "sem_desvantagem_em_alcance_maximo": True,
    },
    "perfurador": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca", "destreza"],
        "puncão": "rerrola_um_dado_de_dano_uma_vez_por_turno",
        "critico_dado_de_dano_adicional": True,
    },
    "resiliente": {
        "aumento_atributo": 1,
        "proficiencia_salvaguarda": 1,
    },
    "resistente": {
        "aumento_atributo": 1,
        "atributos_aumento": ["constituicao"],
        "vantagem_salvaguardas_contra_morte": True,
        "recuperacao_rapida": "gasta_dado_de_vida_como_acao_bonus",
    },
    "sentinela": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca", "destreza"],
        "ataque_de_oportunidade_ao_desengajar_ou_atacar_outro": True,
        "zera_deslocamento": True,
    },
    "sorrateiro": {
        "aumento_atributo": 1,
        "atributos_aumento": ["destreza"],
        "visao_as_cegas_m": 3,
        "vantagem_furtividade_durante_o_combate": True,
    },
    "talhador": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca", "destreza"],
        "deslocamento_reduzido_m": 3,
        "tipo_dano": "cortante",
        "critico_desvantagem_ataques_do_alvo": True,
    },
    "telecinetico": {
        "aumento_atributo": 1,
        "atributos_aumento": ["inteligencia", "sabedoria", "carisma"],
        "maos_magicas": {"sem_componentes": True, "alcance_adicional_m": 9},
        "empurrao_telecinetico": {
            "acao": "bonus",
            "alcance_m": 9,
            "salvaguarda": "forca",
            "cd": "8_mais_atributo_aumentado_mais_bonus_proficiencia",
            "efeito": "1_5m_para_perto_ou_para_longe",
        },
    },
    "telepatico": {
        "aumento_atributo": 1,
        "atributos_aumento": ["inteligencia", "sabedoria", "carisma"],
        "comunicacao_telepatica_m": 18,
        "detectar_pensamentos": {"sempre_preparada": True, "usos_sem_espaco": 1, "recarga": "descanso_longo"},
    },
    "tocado_pela_sombra": {
        "aumento_atributo": 1,
        "atributos_aumento": ["inteligencia", "sabedoria", "carisma"],
        "magia_sombria": {
            "escolas": ["ilusao", "necromancia"],
            "circulo": 1,
            "incluso": "invisibilidade",
            "usos_sem_espaco_por_magia": 1,
            "recarga": "descanso_longo",
        },
    },
    "tocado_pelas_fadas": {
        "aumento_atributo": 1,
        "atributos_aumento": ["inteligencia", "sabedoria", "carisma"],
        "magia_feerica": {
            "escolas": ["adivinhacao", "encantamento"],
            "circulo": 1,
            "incluso": "passo_nebuloso",
            "usos_sem_espaco_por_magia": 1,
            "recarga": "descanso_longo",
        },
    },
    "treinamento_com_armas_marciais": {
        "aumento_atributo": 1,
        "atributos_aumento": ["forca", "destreza"],
        "proficiencia_armas_marciais": True,
    },
    "velocista": {
        "aumento_atributo": 1,
        "atributos_aumento": ["destreza", "constituicao"],
        "deslocamento_adicional_m": 3,
        "correr_em_terreno_dificil_sem_custo": True,
        "ataques_de_oportunidade_com_desvantagem": True,
    },
    # --- Dádivas Épicas ---------------------------------------------------
    "dadiva_da_fortitude": {
        "aumento_atributo": 1,
        "maximo_atributo": 30,
        "pv_maximos_adicionais": 40,
        "cura_adicional": "modificador_de_constituicao",
        "recarga_cura_adicional": "inicio_do_proximo_turno",
    },
    "dadiva_da_proeza_em_combate": {
        "aumento_atributo": 1,
        "maximo_atributo": 30,
        "erro_vira_acerto": True,
        "recarga": "inicio_do_proximo_turno",
    },
    "dadiva_da_proficiencia_em_pericia": {
        "aumento_atributo": 1,
        "maximo_atributo": 30,
        "proficiencia_todas_as_pericias": True,
        "especializacao_pericia": 1,
    },
    "dadiva_da_recordacao_de_magia": {
        "aumento_atributo": 1,
        "maximo_atributo": 30,
        "atributos_aumento": ["inteligencia", "sabedoria", "carisma"],
        "conjuracao_livre": "d4_igual_ao_circulo_nao_gasta_o_espaco",
        "circulos_aplicaveis": [1, 2, 3, 4],
    },
    "dadiva_da_recuperacao": {
        "aumento_atributo": 1,
        "maximo_atributo": 30,
        "ate_a_morte": {"pv": 1, "cura": "metade_dos_pv_maximos", "recarga": "descanso_longo"},
        "reserva_de_dados": {"quantidade": 10, "dado": "d10", "acao": "bonus", "recarga": "descanso_longo"},
    },
    "dadiva_da_resistencia_a_energia": {
        "aumento_atributo": 1,
        "maximo_atributo": 30,
        "resistencias": 2,
        "tipos": ["acido", "eletrico", "frio", "fogo", "necrotico", "psiquico", "radiante", "trovejante", "venenoso"],
        "redirecionamento": {
            "dano": "2d12_mais_modificador_de_constituicao",
            "salvaguarda": "destreza",
            "cd": "8_mais_modificador_de_constituicao_mais_bonus_proficiencia",
            "alcance_m": 18,
            "acao": "reacao",
        },
    },
    "dadiva_da_velocidade": {
        "aumento_atributo": 1,
        "maximo_atributo": 30,
        "desengajar_como_acao_bonus": True,
        "remove_imobilizado": True,
        "deslocamento_adicional_m": 9,
    },
    "dadiva_da_viagem_dimensional": {
        "aumento_atributo": 1,
        "maximo_atributo": 30,
        "teleporte_m": 9,
        "momento": "apos_atacar_ou_conjurar",
    },
    "dadiva_da_visao_verdadeira": {
        "aumento_atributo": 1,
        "maximo_atributo": 30,
        "visao_verdadeira_m": 18,
    },
    "dadiva_do_ataque_irresistivel": {
        "aumento_atributo": 1,
        "maximo_atributo": 30,
        "atributos_aumento": ["forca", "destreza"],
        "ignora_resistencia_fisica": True,
        "critico_dano_adicional": "valor_do_atributo_aumentado",
    },
    "dadiva_do_destino": {
        "aumento_atributo": 1,
        "maximo_atributo": 30,
        "modifica_teste_d20": "2d4",
        "alcance_m": 18,
        "recarga": "iniciativa_ou_descanso_curto_ou_longo",
    },
    "dadiva_do_espirito_da_noite": {
        "aumento_atributo": 1,
        "maximo_atributo": 30,
        "invisivel_em_meia_luz_ou_escuridao": True,
        "acao": "bonus",
        "encerra_apos": "qualquer_acao_bonus_ou_reacao",
        "resistencia_em_meia_luz_ou_escuridao": "todos_os_danos_exceto_psiquico_e_radiante",
    },
    # --- Dádivas Sombrias (Ravenloft) --------------------------------------
    "sombra_viva": {
        "maos_magicas_sem_componentes": True,
        "alcance_corpo_a_corpo_adicional_m": 3,
    },
    "ser_simbiotico": {"proficiencia_pericia": 1, "idioma_adicional": 1},
    "alma_ecoante": {
        "proficiencias": 2,
        "especializacao_pericia": 1,
        "troca_especializacao": "descanso_longo",
        "idioma_adicional": 1,
        "ecos_intrusivos_ao_rolar_1": True,
    },
    "andarilho_das_brumas": {"viajante_de_dominios": True},
    "sussurros_reunidos": {
        "mensagem_sem_componentes_materiais": True,
        "augurio_sempre_preparado": True,
        "usos_sem_espaco": 1,
        "recarga": "descanso_longo",
    },
    "segunda_pele": {
        "alterar_se_sempre_preparado": True,
        "usos_sem_espaco": 1,
        "recarga": "descanso_longo",
    },
    "observadores": {
        "sentido_bestial_e_falar_com_animais": True,
        "usos_sem_espaco": 1,
        "recarga": "descanso_longo",
        "busca_bonus": "1d4",
    },
}


def resolver_talento(fatos: dict) -> dict:
    validacao = validar_talento(fatos)
    if validacao["resultado"] != "disponivel":
        return validacao
    nome = validacao["talento"]
    resultado = dict(validacao)
    # Catálogo e validação não equivalem a uma resolução mecânica completa.
    # Só declarar resolvido o talento quando existe um benefício catalogado.
    beneficios = _BENEFICIOS.get(nome)
    if not beneficios:
        resultado["resultado"] = "nao_implementado"
        resultado["motivo"] = "efeitos_nao_catalogados_na_fonte"
        return resultado
    resultado["resultado"] = "resolvido"
    resultado.pop("motivo", None)
    resultado.update(beneficios)
    nivel = int(fatos.get("nivel", fatos.get("nivel_personagem", 1)))
    bonus_proficiencia = int(fatos.get("bonus_proficiencia", 2))
    if nome == "vigoroso":
        resultado["pv_adicionais"] = 2 * nivel
    if nome == "sortudo":
        resultado["pontos_de_sorte"] = bonus_proficiencia
    if nome == "lider_inspirador":
        resultado["pv_temporarios"] = nivel + int(fatos.get("modificador_atributo_aumentado", 0))
    return resultado
