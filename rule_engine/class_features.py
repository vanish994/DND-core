"""Características de classe executáveis do PHB 2024.

Este módulo mantém os recursos sem estado mutável: a aplicação fornece usos,
atributos e resultados da jogada, e recebe uma resolução determinística.
"""

from __future__ import annotations

import unicodedata

from .class_progression import FEATURES_BY_CLASS
from .artificer_base import resolve_artificer_feature


def _normalizar(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor).strip().lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.replace(" ", "_").replace("-", "_")


def _mod(valor: int) -> int:
    return (int(valor) - 10) // 2


def resolver_caracteristica(f: dict) -> dict:
    classe = _normalizar(f.get("classe", f.get("class", "")))
    recurso = _normalizar(f.get("recurso", f.get("feature", "")))
    try:
        nivel = int(f.get("nivel", f.get("level", 1)))
    except (TypeError, ValueError):
        return {"resultado": "bloqueado", "motivo": "nivel_invalido"}
    if not classe:
        return {"resultado": "bloqueado", "motivo": "classe_ausente"}
    if not 1 <= nivel <= 20:
        return {"resultado": "bloqueado", "motivo": "nivel_invalido"}
    if not recurso:
        return {"resultado": "requer_caracteristica", "classe": classe, "nivel": nivel}

    if classe not in FEATURES_BY_CLASS:
        return {"resultado": "bloqueado", "motivo": "classe_desconhecida", "classe": classe}
    aliases = {
        "asi": "aumento_de_atributo_ou_talento",
        "aumento_de_atributo": "aumento_de_atributo_ou_talento",
        "tinkers_magic": "magia_de_artifice",
        "tinker_s_magic": "magia_de_artifice",
        "replicate_magic_item": "replicar_item_magico",
        "magic_item_tinker": "ajustador_de_item_magico",
        "artesao_de_item_magico": "ajustador_de_item_magico",
        "ajustador_de_item_magico": "ajustador_de_item_magico",
        "magic_item_adept": "adepto_de_item_magico",
        "magic_item_master": "mestre_de_item_magico",
        "epic_boon": "dadiva_epica",
        "flash_of_genius": "lampejo_de_genio",
        "spell_storing_item": "item_armazenador_de_magia",
        "advanced_artifice": "artifice_avancado",
        "soul_of_artifice": "alma_do_artifice",
    }
    chave = aliases.get(recurso, recurso)
    marcos = [n for n, nomes in FEATURES_BY_CLASS[classe].items() if chave in {_normalizar(nome) for nome in nomes}]
    if marcos and nivel < min(marcos):
        return {
            "resultado": "bloqueado",
            "motivo": "nivel_insuficiente",
            "classe": classe,
            "caracteristica": chave,
            "nivel_minimo": min(marcos),
        }

    if recurso in {"asi", "aumento_de_atributo", "aumento_de_atributo_ou_talento"}:
        atributo = f.get("atributo")
        talento = f.get("talento")
        if atributo and atributo not in {"forca", "destreza", "constituicao", "inteligencia", "sabedoria", "carisma"}:
            return {"resultado": "bloqueado", "motivo": "atributo_invalido"}
        if not atributo and not talento:
            return {"resultado": "bloqueado", "motivo": "escolha_obrigatoria"}
        if atributo and int(f.get("aumento", 1)) not in {1, 2}:
            return {"resultado": "bloqueado", "motivo": "aumento_deve_ser_um_ou_dois"}
        return {
            "resultado": "aplicado",
            "atributo": atributo,
            "aumento": int(f.get("aumento", 1)) if atributo else 0,
            "talento": talento,
        }

    if classe == "barbaro":
        if recurso == "defesa_sem_armadura":
            return {
                "resultado": "resolvido",
                "ca": 10 + _mod(f.get("destreza", 10)) + _mod(f.get("constituicao", 10)),
                "usa_escudo": True,
            }
        if recurso == "sentido_de_perigo":
            return {
                "resultado": "resolvido",
                "vantagem_salvaguarda_destreza": not f.get("cego", False)
                and not f.get("surdo", False)
                and not f.get("incapacitado", False),
            }
        if recurso == "conhecimento_primordial":
            return {
                "resultado": "resolvido",
                "pericias_forca_durante_furia": [
                    "acrobacia",
                    "intimidacao",
                    "percepcao",
                    "furtividade",
                    "sobrevivencia",
                ],
                "prof_expertise": f.get("pericia"),
            }
        if recurso == "movimento_rapido":
            return {"resultado": "resolvido", "bonus_deslocamento_m": 3 if not f.get("armadura_pesada", False) else 0}
        if recurso == "furia_implacavel":
            cd = int(f.get("cd", 10))
            if int(f.get("salvaguarda_constituicao", -1)) < cd:
                return {
                    "resultado": "bloqueado",
                    "motivo": "falha_nao_salva_furia",
                    "cd": cd,
                    "cura": 2 * nivel,
                    "recarga": "descanso_longo",
                }
            return {"resultado": "salvo", "cd": cd, "furia_continua": True, "aumentar_cd": 5}
        if recurso == "forca_indomavel":
            valor = int(f.get("resultado_forca", 0))
            forca = int(f.get("forca", 10))
            return {"resultado": "resolvido", "total": max(valor, forca), "substitui_se_inferior": True}
        if recurso == "campeao_primitivo":
            return {"resultado": "resolvido", "bonus_forca": 4, "bonus_constituicao": 4, "maximo_atributo": 25}
        if recurso == "ataque_imprudente":
            return {
                "resultado": "ativado",
                "vantagem_ataques_forca": True,
                "vantagem_ataques_contra_voce": True,
                "duracao": "ate_o_inicio_do_proximo_turno",
                "exige": "primeira_jogada_de_ataque_do_turno",
            }
        if recurso == "bote_instintivo":
            return {
                "resultado": "resolvido",
                "movimento": "metade_do_deslocamento",
                "momento": "acao_bonus_para_entrar_em_furia",
            }
        if recurso == "instintos_primitivos":
            return {"resultado": "resolvido", "vantagem_iniciativa": True}
        if recurso in {"golpe_brutal", "golpe_brutal_fortalecido"}:
            dano = "1d10" if nivel < 17 else "2d10"
            opcoes = ["golpe_debilitador", "golpe_poderoso"]
            if nivel >= 13:
                opcoes += ["golpe_atordoante", "golpe_destruidor"]
            efeitos_max = 2 if nivel >= 17 else 1
            efeito = f.get("efeito") or f.get("efeitos")
            if not efeito:
                return {
                    "resultado": "escolha",
                    "opcoes": opcoes,
                    "dano_adicional": dano,
                    "efeitos_por_uso": efeitos_max,
                    "exige": "ataque_imprudente",
                }
            escolhidos = list(efeito) if isinstance(efeito, (list, tuple)) else [efeito]
            normalizados = [_normalizar(str(e)) for e in escolhidos]
            if len(normalizados) > efeitos_max:
                return {"resultado": "bloqueado", "motivo": "quantidade_de_efeitos_excedida", "limite": efeitos_max}
            if any(e not in opcoes for e in normalizados):
                return {"resultado": "bloqueado", "motivo": "efeito_invalido", "opcoes": opcoes}
            if not f.get("ataque_imprudente", False):
                return {"resultado": "bloqueado", "motivo": "requer_ataque_imprudente"}
            if f.get("desvantagem", False):
                return {"resultado": "bloqueado", "motivo": "ataque_com_desvantagem"}
            mapa = {
                "golpe_debilitador": {
                    "deslocamento_reduzido_m": 4.5,
                    "duracao": "ate_o_inicio_do_seu_proximo_turno",
                    "limite": "um_golpe_debilitador_por_alvo",
                },
                "golpe_poderoso": {
                    "empurra_m": 4.5,
                    "movimento_apos": "metade_do_deslocamento_sem_ataques_de_oportunidade",
                },
                "golpe_atordoante": {
                    "desvantagem_proxima_salvaguarda": True,
                    "sem_ataques_de_oportunidade": True,
                    "duracao": "ate_o_inicio_do_seu_proximo_turno",
                },
                "golpe_destruidor": {
                    "bonus_proximo_ataque_contra_alvo": 5,
                    "limite": "um_bonus_por_ataque",
                },
            }
            return {"resultado": "resolvido", "dano_adicional": dano, "efeitos": [mapa[e] for e in normalizados]}
        if recurso == "furia_persistente":
            if str(f.get("acao", "recuperar")).lower() == "duracao":
                return {
                    "resultado": "resolvido",
                    "duracao_furia": "10 minutos",
                    "encerra_com": ["inconsciente", "armadura_pesada"],
                }
            return {
                "resultado": "recuperado",
                "usos_de_furia": "todos",
                "momento": "iniciativa",
                "recarga": "descanso_longo",
            }

    if classe == "guerreiro":
        if recurso in {"surto_de_acao", "surto_de_acao_aprimorado"}:
            return {
                "resultado": "resolvido",
                "acao_adicional": True,
                "pode_acao_magica": False,
                "usos": 2 if nivel >= 17 else 1,
                "limite_por_turno": 1,
            }
        if recurso == "mente_tatica":
            return {
                "resultado": "resolvido",
                "bonus_teste": int(f.get("rolagem_d10", 0)) + _mod(f.get("constituicao", 10)),
                "gasta_recuperar_folego": True,
            }
        if recurso in {"indomavel", "indomavel_aprimorado"}:
            usos = 3 if nivel >= 17 else 2 if nivel >= 13 else 1
            if f.get("sucesso", False):
                return {"resultado": "sucesso", "usos": usos}
            return {"resultado": "nova_rolagem", "bonus": nivel, "usos": usos}
        if recurso == "ajuste_tatico":
            return {"resultado": "resolvido", "movimento": "metade_do_deslocamento", "sem_ataque_de_oportunidade": True}
        if recurso == "ataques_estudados":
            return {
                "resultado": "resolvido",
                "vantagem_proximo_ataque": not f.get("acertou", True),
                "alvo": f.get("alvo"),
            }
        if recurso == "mestre_tatico":
            return {
                "resultado": "resolvido",
                "propriedades_substitutas": ["empurra", "drenar", "lentidao"],
                "por_ataque": 1,
                "exige": "propriedade_de_maestria_da_arma",
            }

    if classe == "monge":
        if recurso == "defesa_sem_armadura":
            return {
                "resultado": "resolvido",
                "ca": 10 + _mod(f.get("destreza", 10)) + _mod(f.get("sabedoria", 10)),
                "usa_armadura": False,
                "usa_escudo": False,
            }
        if recurso == "artes_marciais":
            dado = "d6" if nivel < 5 else "d8" if nivel < 11 else "d10" if nivel < 17 else "d12"
            return {"resultado": "resolvido", "dado": dado, "ataque_desarmado_bonus": True, "usa_destreza": True}
        if recurso == "queda_lenta":
            return {"resultado": "resolvido", "reducao": 5 * nivel, "usa_reacao": True}
        if recurso == "golpe_atordoante":
            cd = 8 + int(f.get("bonus_proficiencia", 2)) + _mod(f.get("sabedoria", 10))
            return {
                "resultado": "atordoado" if int(f.get("salvaguarda_constituicao", 0)) < cd else "resistiu",
                "custo_foco": 1,
                "cd": cd,
            }
        if recurso == "sobrevivente_disciplinado":
            return {
                "resultado": "sucesso" if f.get("gastou_foco", False) else "resistencia",
                "todos_testes_resistencia": True,
                "custo_foco": 1,
            }
        if recurso == "foco_perfeito":
            return {
                "resultado": "resolvido",
                "recuperar_foco_na_iniciativa": 4 if not f.get("foco_disponivel", 0) else 0,
            }
        if recurso == "defesa_superior":
            return {
                "resultado": "ativada",
                "custo_foco": 3,
                "resistencia_todos_danos_exceto_forca": True,
                "duracao": "ate_inicio_proximo_turno",
            }
        if recurso == "corpo_e_mente":
            return {"resultado": "resolvido", "bonus_destreza": 4, "bonus_sabedoria": 4, "maximo_atributo": 25}
        if recurso == "movimento_sem_armadura":
            bonus = 3 if nivel < 6 else 4.5 if nivel < 10 else 6 if nivel < 14 else 7.5 if nivel < 18 else 9
            return {"resultado": "resolvido", "bonus_deslocamento_m": bonus, "requer": "sem_armadura_sem_escudo"}
        if recurso == "metabolismo_incomum":
            dado = "d6" if nivel < 5 else "d8" if nivel < 11 else "d10" if nivel < 17 else "d12"
            return {
                "resultado": "recuperado",
                "pontos_de_foco": "todos",
                "cura": nivel + int(f.get("rolagem_dado_artes_marciais", 0)),
                "dado_artes_marciais": dado,
                "momento": "iniciativa",
                "recarga": "descanso_longo",
            }
        if recurso == "golpes_potencializados":
            escolha = f.get("tipo_dano")
            if not escolha:
                return {"resultado": "escolha", "opcoes": ["energetico", "normal"]}
            if escolha not in {"energetico", "normal"}:
                return {"resultado": "bloqueado", "motivo": "tipo_dano_invalido"}
            return {
                "resultado": "resolvido",
                "tipo_dano": "energetico" if escolha == "energetico" else "normal_do_ataque",
            }
        if recurso == "movimento_acrobatico":
            return {
                "resultado": "resolvido",
                "superficies": ["verticais", "liquidos"],
                "sem_queda": True,
                "requer": "sem_armadura_sem_escudo",
            }
        if recurso == "foco_aprimorado":
            return {
                "resultado": "resolvido",
                "defesa_paciente": {"pv_temporarios": "2_dados_de_artes_marciais"},
                "passo_do_vento": {
                    "move_criatura": "Grande ou menor a 1,5 metro",
                    "sem_ataques_de_oportunidade": True,
                    "duracao": "ate_o_fim_do_seu_turno",
                },
                "torrente_de_golpes": {"ataques_desarmados": 3},
            }
        if recurso == "restauro_pessoal":
            return {
                "resultado": "removida",
                "opcoes_condicao": ["amedrontado", "enfeiticado", "envenenado"],
                "momento": "fim_do_seu_turno",
                "limite": "uma_condicao_por_turno",
                "exaustao_por_fome_ou_sede": False,
            }
        if recurso == "defletir_energia":
            reducao = int(f.get("rolagem_d10", 0)) + int(f.get("modificador_destreza", 0)) + nivel
            dano = int(f.get("dano", 0))
            return {
                "resultado": "resolvido",
                "reducao": reducao,
                "dano_restante": max(0, dano - reducao),
                "tipos_dano": "todos",
                "pode_redirecionar": dano <= reducao and int(f.get("foco_disponivel", 0)) >= 1,
            }

    if classe == "ladino":
        if recurso == "acao_ardilosa":
            acao = f.get("acao", "")
            if not acao:
                return {"resultado": "escolha", "opcoes": ["correr", "desengajar", "esconder"]}
            return {
                "resultado": "permitido" if acao in {"correr", "desengajar", "esconder"} else "bloqueado",
                "acao_bonus": acao,
            }
        if recurso in {"especializacao", "especialista"}:
            return {
                "resultado": "resolvido",
                "pericias": int(f.get("quantidade", 2)),
                "multiplicador_proficiencia": 2,
                "exige": "proficiencia_nas_pericias_escolhidas",
            }
        if recurso == "giria_dos_ladroes":
            return {"resultado": "resolvido", "idiomas": ["giria_dos_ladroes"], "idiomas_adicionais": 1}
        if recurso in {"golpe_astuto", "golpe_astuto_aprimorado", "golpes_sujos"}:
            cd = 8 + int(f.get("modificador_destreza", 0)) + int(f.get("bonus_proficiencia", 2))
            opcoes = {
                "envenenar": {
                    "custo": "1d6",
                    "salvaguarda": "constituicao",
                    "cd": cd,
                    "falha": "envenenado_1_minuto_com_nova_salvaguarda_por_turno",
                    "requer": "kit_de_veneno",
                },
                "retirada": {"custo": "1d6", "movimento": "metade_do_deslocamento_sem_ataques_de_oportunidade"},
                "tropeco": {
                    "custo": "1d6",
                    "salvaguarda": "destreza",
                    "cd": cd,
                    "falha": "caido",
                    "limite": "Grande ou menor",
                },
            }
            if nivel >= 14:
                opcoes.update(
                    {
                        "aturdir": {
                            "custo": "2d6",
                            "salvaguarda": "constituicao",
                            "cd": cd,
                            "falha": "proximo_turno_apenas_uma_acao_ou_uma_acao_bonus",
                        },
                        "nocaute": {
                            "custo": "6d6",
                            "salvaguarda": "constituicao",
                            "cd": cd,
                            "falha": "inconsciente_1_minuto_ou_ate_dano",
                        },
                        "obscurecer": {
                            "custo": "3d6",
                            "salvaguarda": "destreza",
                            "cd": cd,
                            "falha": "cego_ate_o_fim_do_proximo_turno",
                        },
                    }
                )
            efeitos_max = 2 if nivel >= 11 else 1
            efeito = f.get("efeito") or f.get("efeitos")
            if not efeito:
                return {
                    "resultado": "escolha",
                    "opcoes": sorted(opcoes),
                    "efeitos_por_uso": efeitos_max,
                    "custo": "dados_de_ataque_furtivo",
                    "cd": cd,
                }
            escolhidos = list(efeito) if isinstance(efeito, (list, tuple)) else [efeito]
            normalizados = [_normalizar(str(e)) for e in escolhidos]
            if len(normalizados) > efeitos_max:
                return {"resultado": "bloqueado", "motivo": "quantidade_de_efeitos_excedida", "limite": efeitos_max}
            if any(e not in opcoes for e in normalizados):
                return {"resultado": "bloqueado", "motivo": "efeito_invalido", "opcoes": sorted(opcoes)}
            return {"resultado": "resolvido", "efeitos": [opcoes[e] for e in normalizados]}
        if recurso == "mira_firme":
            return {
                "resultado": "resolvido",
                "vantagem_proximo_ataque": True,
                "deslocamento_zero": True,
                "limite": "um_ataque_neste_turno",
            }
        if recurso == "talento_confiavel":
            return {
                "resultado": "resolvido",
                "total": max(10, int(f.get("rolagem_d20", 0))) + int(f.get("bonus", 0)),
                "aplica": f.get("proficiente", False),
            }
        if recurso == "mente_escorregadia":
            return {"resultado": "resolvido", "prof_sabedoria": True, "prof_carisma": True}
        if recurso == "elusivo":
            return {"resultado": "resolvido", "inimigo_nao_tem_vantagem": not f.get("incapacitado", False)}
        if recurso == "golpe_de_sorte":
            return {"resultado": "20_natural", "transforma_falha": True, "recarga": "descanso_curto_ou_longo"}

    if classe == "bardo":
        if recurso == "inspiracao_de_bardo":
            dado = "d6" if nivel < 5 else "d8" if nivel < 10 else "d10" if nivel < 15 else "d12"
            return {
                "resultado": "concedida",
                "dado": dado,
                "usos": max(1, _mod(f.get("carisma", 10))),
                "alcance_m": 18,
                "duracao_min": 10,
            }
        if recurso == "pau_pra_toda_obra":
            return {"resultado": "resolvido", "bonus": _mod(f.get("carisma", 10)), "testes": "não_proficientes"}
        if recurso == "especialista":
            return {
                "resultado": "resolvido",
                "pericias_escolhidas": int(f.get("quantidade", 2)),
                "multiplicador_proficiencia": 2,
            }
        if recurso == "fonte_de_inspiracao":
            return {"resultado": "resolvido", "recupera_em": "descanso_curto_ou_longo", "dado": "inspiracao_de_bardo"}
        if recurso == "contra_encantamento":
            return {
                "resultado": "ativado",
                "vantagem": True,
                "aliados_alcance_m": 9,
                "efeito": "amedrontado_ou_enfeiticado",
            }
        if recurso == "inspiracao_superior":
            return {"resultado": "resolvido", "recupera_uso_ao_iniciativa": True}
        if recurso == "palavras_de_criacao":
            return {
                "resultado": "resolvido",
                "cd_aumentada": 2,
                "efeitos": ["incapacitado", "amedrontado", "enfeitiçado"],
            }
        if recurso == "segredos_magicos":
            return {
                "resultado": "resolvido",
                "listas_permitidas": ["bardo", "clerigo", "druida", "mago"],
                "quando": "aumento_de_magias_preparadas",
                "contam_como": "magias_de_bardo",
                "substituicao_tambem_usa_estas_listas": True,
            }

    if classe == "clerigo":
        if recurso == "ordem_divina":
            return {"resultado": "escolha", "opcoes": ["dominio_de_vida", "potencializar_cura"], "quantidade": 1}
        if recurso == "canalizar_divindade":
            return {
                "resultado": "resolvido",
                "usos": 2 if nivel < 6 else 3 if nivel < 18 else 4,
                "recupera_em": "descanso_curto_ou_longo",
            }
        if recurso == "fulminar_mortos_vivos":
            cd = 8 + int(f.get("bonus_proficiencia", 2)) + _mod(f.get("sabedoria", 10))
            return {
                "resultado": "destruido" if f.get("falhou_salvaguarda", False) and nivel >= 5 else "repelido",
                "cd": cd,
                "tipo": "morto_vivo",
            }
        if recurso == "golpes_abencoados":
            opcao = f.get("opcao")
            if not opcao:
                return {"resultado": "escolha", "opcoes": ["conjuracao_poderosa", "golpe_divino"]}
            if opcao == "conjuracao_poderosa":
                return {"resultado": "resolvido", "dano_extra_truques_de_clerigo": _mod(f.get("sabedoria", 10))}
            return {"resultado": "resolvido", "dano_extra": "1d8_radiante_ou_necrotico", "limite": "uma_vez_por_turno"}
        if recurso == "golpes_abencoados_aprimorado":
            opcao = f.get("opcao")
            if not opcao:
                return {
                    "resultado": "escolha",
                    "opcoes": ["conjuracao_poderosa", "golpe_divino"],
                    "exige": "golpes_abencoados",
                }
            if opcao == "conjuracao_poderosa":
                return {
                    "resultado": "resolvido",
                    "pv_temporarios": 2 * _mod(f.get("sabedoria", 10)),
                    "alcance_m": 18,
                    "momento": "ao_causar_dano_com_truque_de_clerigo",
                }
            return {"resultado": "resolvido", "dano_extra": "2d8_radiante_ou_necrotico", "limite": "uma_vez_por_turno"}
        if recurso == "intervencao_divina":
            return {
                "resultado": "resolvido",
                "magia": "qualquer_magia_de_clerigo_de_5_circulo_ou_inferior_sem_reacao",
                "sem_espaco_sem_componentes_materiais": True,
                "recarga": "descanso_longo",
                "acao": "usar_magia",
            }
        if recurso == "intervencao_divina_maior":
            return {
                "resultado": "resolvido",
                "magia_adicional": "desejo",
                "recarga_se_usar_desejo": "2d4_descansos_longos",
                "exige": "intervencao_divina",
            }

    if classe == "druida":
        if recurso == "idioma_druidico":
            return {"resultado": "resolvido", "idioma": "druidico", "pode_falar_com_druidas": True}
        if recurso == "ordem_primal":
            return {"resultado": "escolha", "opcoes": ["mago", "combatente"], "beneficio": "truque_ou_armadura_leve"}
        if recurso == "companheiro_selvagem":
            return {"resultado": "conjurado", "custo": "uso_de_forma_selvagem", "duracao_horas": 1, "familiar": True}
        if recurso == "ressurgimento_selvagem":
            return {"resultado": "recuperado", "pontos_forma_selvagem": 1, "recarga": "descanso_curto_ou_longo"}
        if recurso in {"furia_elemental", "furia_elemental_aprimorada"}:
            aprimorada = nivel >= 15 and recurso == "furia_elemental_aprimorada"
            opcao = f.get("opcao")
            if not opcao:
                return {"resultado": "escolha", "opcoes": ["ataque_primal", "conjuracao_poderosa"]}
            if opcao == "ataque_primal":
                return {
                    "resultado": "resolvido",
                    "dano_extra": "2d8" if aprimorada else "1d8",
                    "tipos": ["eletrico", "frio", "fogo", "trovejante"],
                    "limite": "uma_vez_por_turno",
                }
            return {
                "resultado": "resolvido",
                "dano_extra_truques_de_druida": _mod(f.get("sabedoria", 10)),
                "alcance_m": 90 if aprimorada else None,
                "alcance_minimo_m": 3 if aprimorada else None,
            }
        if recurso == "magias_bestiais":
            return {"resultado": "resolvido", "pode_conjurar_em_forma_selvagem": True, "componentes_somaticos": True}
        if recurso == "arquidruida":
            return {"resultado": "resolvido", "forma_selvagem_usos": "ilimitados", "recupera_foco": True}

    if classe == "mago":
        if recurso == "recuperacao_arcana":
            return {
                "resultado": "recuperado",
                "circulos": min(5, (nivel + 1) // 2),
                "recarga": "descanso_curto_ou_longo",
                "uma_vez_por_dia": True,
            }
        if recurso == "adepto_de_ritual":
            return {"resultado": "resolvido", "pode_conjurar_rituais_do_livro": True, "sem_preparar": True}
        if recurso == "academico":
            return {
                "resultado": "resolvido",
                "especializacao": f.get("pericia", "historia"),
                "dobro_proficiencia": True,
            }
        if recurso == "memorizar_magia":
            return {"resultado": "resolvido", "troca_em_descanso_curto": True, "magias": 1}
        if recurso == "maestria_de_magias":
            return {
                "resultado": "resolvido",
                "magias_sem_espaco": int(f.get("quantidade", 2)),
                "recarga": "descanso_curto_ou_longo",
            }
        if recurso == "assinatura_magica":
            return {"resultado": "resolvido", "magias": 2, "circulo_maximo": 3, "uma_vez_sem_espaco": True}

    if classe == "feiticeiro":
        if recurso == "fonte_de_magia":
            return {"resultado": "resolvido", "pontos": nivel, "conversao": True, "recarga": "descanso_longo"}
        if recurso == "metamagia":
            return {"resultado": "resolvido", "pontos": nivel, "opcoes": 2 if nivel < 10 else 4 if nivel < 17 else 6}
        if recurso == "restauracao_feiticeira":
            return {"resultado": "recuperado", "pontos": nivel // 2, "recarga": "descanso_curto"}
        if recurso == "feiticaria_encarnada":
            return {"resultado": "ativada", "custo_pontos": 2, "duas_metamagias_na_mesma_magia": True}
        if recurso == "apoteose_arcana":
            return {"resultado": "resolvido", "metamagia_sem_custo": True, "uma_vez_por_turno": True}

    if classe == "bruxo":
        if recurso == "astucia_magica":
            return {
                "resultado": "recuperado",
                "espacos": max(1, int(f.get("espacos", 1)) // 2),
                "recarga": "descanso_longo",
                "acao": "minuto",
            }
        if recurso == "contatar_patrono":
            return {"resultado": "resolvido", "consulta": True, "telepatia": True, "recarga": "descanso_longo"}
        if recurso == "arcana_mistica":
            circulo = max((n for n in (11, 13, 15, 17) if nivel >= n), default=None)
            circulo_magia = {11: 6, 13: 7, 15: 8, 17: 9}.get(circulo) if circulo else None
            return {
                "resultado": "resolvido" if circulo_magia else "bloqueado",
                "circulo": circulo_magia,
                "recarga": "descanso_longo",
            }
        if recurso == "mestre_mistico":
            return {"resultado": "resolvido", "invocacao_adicional": True, "recupera_espaco_pacto": True}

    if classe == "artifice":
        resolucao_artifice = resolve_artificer_feature(recurso, nivel, f)
        if resolucao_artifice is not None:
            return resolucao_artifice

    if classe == "paladino":
        if recurso == "maos_consagradas":
            pool_maximo = 5 * nivel
            pool_restante = int(f.get("pool_restante", pool_maximo))
            custo = int(f.get("custo", pool_restante))
            if pool_restante < 0 or pool_restante > pool_maximo:
                return {"resultado": "bloqueado", "motivo": "pool_de_cura_invalido", "pool_maximo": pool_maximo}
            if custo < 0 or custo > pool_restante:
                return {
                    "resultado": "bloqueado",
                    "motivo": "cura_excede_pool_disponivel",
                    "pool_restante": pool_restante,
                }
            return {
                "resultado": "cura",
                "pool_maximo": pool_maximo,
                "cura": custo,
                "pool_restante": pool_restante - custo,
                "acao": "bonus",
            }
        if recurso == "aura_de_protecao":
            return {
                "resultado": "resolvido",
                "bonus_salvaguardas": _mod(f.get("carisma", 10)),
                "alcance_m": int(f.get("alcance_m", 3)),
            }
        if recurso == "aura_de_coragem":
            return {"resultado": "resolvido", "imune_amedrontado": True, "alcance_m": int(f.get("alcance_m", 3))}
        if recurso == "golpes_radiantes":
            return {"resultado": "resolvido", "dano_extra": "1d8_radiante", "limite": "uma_vez_por_turno"}
        if recurso == "toque_restaurador":
            return {
                "resultado": "removida",
                "condicao": f.get("condicao"),
                "custo": 5,
                "condicoes": ["cego", "surdo", "paralisado", "envenenado", "amedrontado", "atordoado"],
            }
        if recurso == "canalizar_divindade":
            return {
                "resultado": "resolvido",
                "usos": 2 if nivel < 11 else 3,
                "recupera_um_uso_em": "descanso_curto",
                "recupera_todos_em": "descanso_longo",
                "efeito_inicial": "sentido_divino",
                "cd": "cd_de_magia_do_paladino",
            }
        if recurso == "montaria_fiel":
            return {
                "resultado": "resolvido",
                "magia": "convocar_montaria",
                "sempre_preparada": True,
                "usos_sem_espaco": 1,
                "recarga": "descanso_longo",
            }
        if recurso == "repudiar_inimigos":
            return {
                "resultado": "resolvido",
                "acao": "usar_magia",
                "custo": "1_uso_de_canalizar_divindade",
                "alvos": max(1, _mod(f.get("carisma", 10))),
                "alcance_m": 18,
                "salvaguarda": "sabedoria",
                "cd": "cd_de_magia_do_paladino",
                "falha": "amedrontado_1_minuto_ou_ate_dano",
                "limitacao": "apenas_uma_opcao_de_acao_por_turno",
            }
        if recurso == "aura_expandida":
            return {"resultado": "resolvido", "emanacao_m": 9, "substitui": "aura_de_protecao"}

    if classe == "guardiao":
        if recurso == "errante":
            return {
                "resultado": "resolvido",
                "bonus_deslocamento_m": 3,
                "escalada_igual_deslocamento": True,
                "natacao_igual_deslocamento": True,
            }
        if recurso == "incansavel":
            return {
                "resultado": "resolvido",
                "pontos_de_vida_temporarios": max(1, _mod(f.get("sabedoria", 10))) + int(f.get("rolagem_d8", 0)),
                "reduzir_exaustao_no_descanso_curto": True,
            }
        if recurso == "sentidos_selvagens":
            return {"resultado": "resolvido", "sentido_as_cegas_m": 9}
        if recurso == "matador_de_inimigos_favoritos":
            return {"resultado": "resolvido", "dado_marca_do_predador": "d10"}
        if recurso == "especialista":
            return {
                "resultado": "resolvido",
                "pericias": int(f.get("quantidade", 2)),
                "multiplicador_proficiencia": 2,
                "exige": "proficiencia_nas_pericias_escolhidas",
            }
        if recurso == "cacador_preciso":
            return {"resultado": "resolvido", "vantagem_ataques_contra": "alvo_da_marca_do_predador"}

    delegado = _delegar_para_especialista(classe, chave, nivel, f)
    if delegado is not None:
        return delegado

    classes_conhecidas = {
        "barbaro",
        "bardo",
        "clerigo",
        "druida",
        "guerreiro",
        "monge",
        "paladino",
        "guardiao",
        "ladino",
        "feiticeiro",
        "bruxo",
        "mago",
        "artifice",
    }
    if classe not in classes_conhecidas:
        return {"resultado": "bloqueado", "motivo": "classe_desconhecida", "classe": classe}
    return {
        "resultado": "nao_implementado",
        "caracteristica": recurso,
        "classe": classe,
        "nivel": nivel,
        "motivo": "caracteristica_catalogada_sem_resolver_especifico",
    }


def _delegar_para_especialista(classe: str, chave: str, nivel: int, f: dict) -> dict | None:
    """Encaminha características para os módulos especializados já implementados.

    Todos os resolvedores especializados seguem o contrato unificado
    ``resolver_*(fatos: dict)`` com as chaves ``classe`` e ``nivel``. Retorna
    ``None`` quando não há delegação definida (a característica segue para o
    diagnóstico de ``nao_implementado``).
    """
    from .advanced_casters import resolver_bruxo, resolver_feiticeiro, resolver_guardiao, resolver_paladino
    from .feats import FEATS
    from .martial import (
        resolver_ataque_extra,
        resolver_ataque_furtivo,
        resolver_defletir_ataques,
        resolver_esquiva_sobrenatural,
        resolver_evasao,
        resolver_foco_monge,
        resolver_furia,
        resolver_maestria_arma,
        resolver_recuperar_folego,
    )
    from .martial_subclasses import resolver_subclasse_marcial
    from .spellcasters import (
        resolver_canalizar_divindade,
        resolver_forma_selvagem,
        resolver_inspiracao_bardo,
        resolver_livro_de_magias,
        resolver_progressao_conjuracao,
    )
    from .warlock_invocations import INVOCATIONS, resolver_invocacao, validar_invocacao

    nivel = int(nivel)
    base = {**f, "classe": classe, "nivel": nivel}

    def completar(dados: dict) -> dict:
        saida = dict(dados)
        saida.setdefault("classe", classe)
        saida.setdefault("nivel", nivel)
        saida.setdefault("fonte", f"class_features:{chave}")
        return saida

    def invocar(fn, fatos: dict) -> dict:
        """Executa o resolvedor; fatos obrigatórios ausentes viram contrato."""
        try:
            return fn(fatos)
        except KeyError as exc:
            faltante = str(exc.args[0]) if exc.args else str(exc)
            return {"resultado": "contrato", "fatos_exigidos": [faltante]}

    # --- Marcos estruturais -------------------------------------------------
    if chave == "subclasse":
        from .class_progression import subclasses_da_classe

        try:
            opcoes = subclasses_da_classe(classe)
        except Exception:  # classe fora do catálogo de subclasse
            opcoes = []
        return completar(
            {
                "resultado": "escolha",
                "marco": "subclasse",
                "opcoes": sorted(opcoes),
            }
        )
    if chave == "caracteristica_de_subclasse":
        subclasse = f.get("subclasse")
        if not subclasse:
            return completar({"resultado": "escolha", "motivo": "subclasse_ausente"})
        if classe in {"barbaro", "guerreiro", "monge", "ladino"}:
            dados = invocar(resolver_subclasse_marcial, {**base, "subclasse": subclasse})
            return completar(dados)
        return completar(
            {
                "resultado": "nao_implementado",
                "motivo": "subclasse_sem_resolvedor_especifico",
                "subclasse": subclasse,
            }
        )
    if chave == "dadiva_epica":
        opcoes = sorted(nome for nome, dados in FEATS.items() if dados.get("categoria") == "dadiva_epica")
        return completar({"resultado": "escolha", "marco": "dadiva_epica", "exige_nivel": 19, "opcoes": opcoes})
    if chave == "estilo_de_luta":
        # Talentos de Estilo de Luta (PHB 2024, cap. 5) — exigem a característica
        # de classe Estilo de Luta; concedidos e resolvidos por este marco.
        estilos = {
            "arquearia": {"ataque_distancia": 2},
            "combate_com_armas_de_arremesso": {"dano_arremesso": 2},
            "combate_com_armas_grandes": {"reroll_dado_baixo_como": 3, "restricao": "duas_maos_ou_versatil"},
            "combate_com_duas_armas": {"dano_ataque_extra_leve": "modificador_de_atributo"},
            "combate_desarmado": {
                "dano_desarmado": "1d6+forca",
                "dado_sem_armas_ou_escudo": "d8",
                "dano_imobilizado": "1d4",
            },
            "defensivo": {"ca": 1, "requer": "armadura"},
            "duelismo": {"dano": 2, "restricao": "uma_arma_corpo_a_corpo_sem_outra"},
            "interceptacao": {"reducao_dano": "1d10+bonus_proficiencia", "acao": "reacao", "requer": "escudo_ou_arma"},
            "luta_as_cegas": {"visao_as_cegas_m": 3},
            "protetivo": {"acao": "reacao", "desvantagem_ataque": True, "alcance_m": 1.5, "requer": "escudo"},
        }
        talento = f.get("talento")
        if not talento:
            return completar({"resultado": "escolha", "marco": "estilo_de_luta", "opcoes": sorted(estilos)})
        chave_estilo = _normalizar(str(talento))
        if chave_estilo not in estilos:
            return completar({"resultado": "bloqueado", "motivo": "talento_invalido", "talento": talento})
        return completar(
            {"resultado": "resolvido", "talento": chave_estilo, "categoria": "estilo_de_luta", **estilos[chave_estilo]}
        )

    # --- Características marciais ------------------------------------------
    if chave in {"ataque_extra", "dois_ataques_extras", "tres_ataques_extras"}:
        return completar(invocar(resolver_ataque_extra, base))
    if chave == "maestria_em_arma":
        return completar(invocar(resolver_maestria_arma, base))
    if chave == "furia":
        return completar(invocar(resolver_furia, base))
    if chave == "recuperar_folego":
        return completar(invocar(resolver_recuperar_folego, base))
    if chave == "ataque_furtivo":
        return completar(invocar(resolver_ataque_furtivo, base))
    if chave == "foco_do_monge":
        return completar(invocar(resolver_foco_monge, base))
    if chave == "defletir_ataques":
        return completar(invocar(resolver_defletir_ataques, base))
    if chave == "esquiva_sobrenatural":
        return completar(invocar(resolver_esquiva_sobrenatural, base))
    if chave == "evasao":
        return completar(invocar(resolver_evasao, base))

    # --- Conjuração --------------------------------------------------------
    if chave == "conjuracao":
        if classe in {"bardo", "clerigo", "druida", "mago"}:
            return completar(invocar(resolver_progressao_conjuracao, base))
        if classe == "feiticeiro":
            return completar(invocar(resolver_feiticeiro, {**base, "acao": "progressao"}))
        if classe == "bruxo":
            return completar(invocar(resolver_bruxo, {**base, "acao": "progressao"}))
        if classe == "guardiao":
            return completar(invocar(resolver_guardiao, {**base, "acao": "progressao"}))
        if classe == "paladino":
            return completar(invocar(resolver_paladino, {**base, "acao": "progressao"}))
        return None
    if chave == "magia_de_pacto":
        return completar(invocar(resolver_bruxo, {**base, "acao": "progressao"}))
    if chave == "invocacoes_misticas":
        invocacao = f.get("invocacao") or f.get("escolha")
        if not invocacao:
            return completar({"resultado": "escolha", "opcoes": sorted(INVOCATIONS), "marco": "invocacoes_misticas"})
        validacao = validar_invocacao({**base, "invocacao": invocacao})
        if validacao.get("resultado") != "disponivel":
            return completar(validacao)
        return completar(invocar(resolver_invocacao, {**base, "invocacao": invocacao}))
    if chave == "feiticaria_inata":
        return completar(invocar(resolver_feiticeiro, {**base, "acao": "feitiçaria_inata"}))
    if chave == "inspiracao_de_bardo":
        return completar(invocar(resolver_inspiracao_bardo, base))
    if chave == "canalizar_divindade" and classe == "clerigo":
        return completar(invocar(resolver_canalizar_divindade, base))
    if chave == "forma_selvagem":
        return completar(invocar(resolver_forma_selvagem, base))
    if chave == "livro_de_magias":
        return completar(invocar(resolver_livro_de_magias, base))
    if chave == "destruicao_do_paladino":
        return completar(invocar(resolver_paladino, {**base, "acao": "destruicao_do_paladino"}))
    if chave in {"inimigo_favorito", "explorador_habil", "predador_implacavel", "veu_da_natureza"}:
        return completar(invocar(resolver_guardiao, {**base, "acao": chave}))
    return None
