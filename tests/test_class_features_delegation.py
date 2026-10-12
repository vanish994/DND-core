"""Delegação de características de classe para os resolvedores especializados.

A camada de ``class_features.resolver_caracteristica`` encaminha as mecânicas já
implementadas em ``martial``, ``spellcasters``, ``advanced_casters``,
``warlock_invocations`` e ``martial_subclasses``, além de resolver os marcos
estruturais (Subclasse, Característica de Subclasse, Dádiva Épica e Estilo de
Luta). Valores esperados conferem com os módulos de origem e com o PHB 2024.
"""

import unittest

from rule_engine import FEATS
from rule_engine.class_features import resolver_caracteristica


def caracteristica(classe, recurso, nivel=20, **fatos):
    return resolver_caracteristica({"classe": classe, "recurso": recurso, "nivel": nivel, **fatos})


class MartialDelegationTests(unittest.TestCase):
    def test_maestria_em_arma_limite_do_guerreiro(self):
        resultado = caracteristica("guerreiro", "Maestria em Arma", 20)
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["limite"], 6)

    def test_maestria_em_arma_quantidade_excedida_bloqueia(self):
        resultado = caracteristica("guerreiro", "Maestria em Arma", 3, armas=["a", "b", "c", "d"])
        self.assertEqual(resultado["resultado"], "bloqueado")
        self.assertEqual(resultado["motivo"], "quantidade_de_maestrias_excedida")

    def test_ataque_extra_do_guerreiro_no_nivel_20(self):
        resultado = caracteristica("guerreiro", "Três Ataques Extras")
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["ataques"], 4)

    def test_ataque_extra_do_barbaro_no_nivel_5(self):
        resultado = caracteristica("barbaro", "Ataque Extra", 5)
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["ataques"], 2)

    def test_furia_ativada_sem_armadura_pesada(self):
        resultado = caracteristica("barbaro", "Fúria", 20, acao="ativar")
        self.assertEqual(resultado["resultado"], "ativada")
        self.assertEqual(resultado["usos_maximos"], 6)
        self.assertEqual(resultado["dano_adicional"], 4)

    def test_furia_bloqueada_com_armadura_pesada(self):
        resultado = caracteristica("barbaro", "Fúria", 5, armadura_pesada=True)
        self.assertEqual(resultado["resultado"], "bloqueado")
        self.assertEqual(resultado["motivo"], "armadura_pesada_ou_incapacitado")

    def test_recuperar_folego_no_nivel_20(self):
        resultado = caracteristica("guerreiro", "Recuperar Fôlego", 20, acao="recuperar")
        self.assertEqual(resultado["resultado"], "recuperado")
        self.assertEqual(resultado["usos"], 4)

    def test_ataque_furtivo_do_ladino_no_nivel_20(self):
        resultado = caracteristica("ladino", "Ataque Furtivo", 20, vantagem=True, acuidade_ou_distancia=True)
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["dados"], 10)
        self.assertEqual(resultado["dado"], "d6")

    def test_ataque_furtivo_sem_requisitos_fica_bloqueado(self):
        resultado = caracteristica("ladino", "Ataque Furtivo", 20)
        self.assertEqual(resultado["resultado"], "bloqueado")
        self.assertEqual(resultado["motivo"], "requisitos_ataque_furtivo")

    def test_esquiva_sobrenatural_metade_do_dano(self):
        resultado = caracteristica("ladino", "Esquiva Sobrenatural", 5, dano=14)
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["dano_final"], 7)

    def test_evasao_com_sucesso_zera_o_dano(self):
        resultado = caracteristica("monge", "Evasão", 7, dano=20, sucesso=True)
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["dano_final"], 0)

    def test_evasao_sem_fato_de_dano_vira_contrato(self):
        resultado = caracteristica("monge", "Evasão", 7)
        self.assertEqual(resultado["resultado"], "contrato")
        self.assertIn("dano", resultado["fatos_exigidos"])

    def test_foco_do_monge_com_torrente_de_golpes(self):
        resultado = caracteristica("monge", "Foco do Monge", 5, acao="torrente_de_golpes", foco_disponivel=1)
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["custo"], 1)
        self.assertIn("dois_ataques_desarmados", resultado["efeitos"])

    def test_defletir_ataques_reduz_e_pode_redirecionar(self):
        resultado = caracteristica(
            "monge", "Defletir Ataques", 5, dano=10, rolagem_d10=6, modificador_destreza=3, foco_disponivel=1
        )
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["dano_restante"], 0)
        self.assertTrue(resultado["pode_redirecionar"])


class CastingDelegationTests(unittest.TestCase):
    def test_conjuracao_do_paladino_usa_espacos_de_meio_conjurador(self):
        resultado = caracteristica("paladino", "Conjuração", 20)
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["atributo_conjuracao"], "carisma")

    def test_magia_de_pacto_do_bruxo_no_nivel_5(self):
        resultado = caracteristica("bruxo", "Magia de Pacto", 5)
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["invocacoes"], 5)
        self.assertEqual(resultado["atributo_conjuracao"], "carisma")

    def test_invocacoes_misticas_sem_escolha_lista_opcoes(self):
        resultado = caracteristica("bruxo", "Invocações Místicas", 5)
        self.assertEqual(resultado["resultado"], "escolha")
        self.assertIn("explosao_agonizante", resultado["opcoes"])

    def test_invocacao_valida_resolve_efeito(self):
        resultado = caracteristica(
            "bruxo", "Invocações Místicas", 5, invocacao="explosao_agonizante", carisma=18, truque_causa_dano=True
        )
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["bonus_dano"], 4)

    def test_invocacao_sem_truque_de_dano_bloqueia(self):
        resultado = caracteristica("bruxo", "Invocações Místicas", 5, invocacao="explosao_agonizante")
        self.assertEqual(resultado["resultado"], "bloqueado")
        self.assertEqual(resultado["motivo"], "truque_de_dano_obrigatorio")

    def test_invocacao_acima_do_nivel_bloqueia(self):
        resultado = caracteristica("bruxo", "Invocações Místicas", 1, invocacao="explosao_agonizante")
        self.assertEqual(resultado["resultado"], "bloqueado")
        self.assertEqual(resultado["motivo"], "nivel_insuficiente")

    def test_livro_de_magias_do_mago(self):
        resultado = caracteristica("mago", "Livro de Magias", 20, acao="recuperacao_arcana")
        self.assertEqual(resultado["resultado"], "recuperado")
        self.assertEqual(resultado["limite_circulos"], 10)

    def test_forma_selvagem_ativada(self):
        resultado = caracteristica("druida", "Forma Selvagem", 5, acao="ativar")
        self.assertEqual(resultado["resultado"], "ativada")
        self.assertEqual(resultado["pontos_de_vida_temporarios"], 5)

    def test_inspiracao_de_bardo_ainda_passa_pelo_ladder(self):
        # O ladder do bardo já resolve esta característica antes da delegação.
        resultado = caracteristica("bardo", "Inspiração de Bardo", 5, carisma=16)
        self.assertEqual(resultado["resultado"], "concedida")
        self.assertEqual(resultado["dado"], "d8")

    def test_destruicao_do_paladino_espaco_invalido(self):
        resultado = caracteristica("paladino", "Destruição do Paladino", 2)
        self.assertEqual(resultado["resultado"], "bloqueado")
        self.assertEqual(resultado["motivo"], "espaco_invalido")

    def test_destruicao_do_paladino_com_espaco(self):
        resultado = caracteristica("paladino", "Destruição do Paladino", 2, espaco=1)
        self.assertEqual(resultado["resultado"], "requer_resolucao_de_dano")
        self.assertEqual(resultado["dado_adicional"], "2d8")

    def test_guardiao_inimigo_favorito(self):
        resultado = caracteristica("guardiao", "Inimigo Favorito", 5)
        self.assertEqual(resultado["resultado"], "ativado")
        self.assertEqual(resultado["usos"], 3)

    def test_arcana_mistica_no_nivel_20_usa_o_maior_marco(self):
        resultado = caracteristica("bruxo", "Arcana Mística", 20)
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["circulo"], 9)

    def test_delegacao_nao_altera_ladder_existente(self):
        # Astúcia Mágica já era resolvida pelo ladder do bruxo e continua assim.
        resultado = caracteristica("bruxo", "Astúcia Mágica", 20)
        self.assertEqual(resultado["resultado"], "recuperado")


class StructuralMilestoneTests(unittest.TestCase):
    def test_subclasse_oferece_opcoes_da_classe(self):
        resultado = caracteristica("barbaro", "Subclasse", 3)
        self.assertEqual(resultado["resultado"], "escolha")
        self.assertIn("trilha_do_berserker", resultado["opcoes"])

    def test_caracteristica_de_subclasse_sem_subclasse_pede_escolha(self):
        resultado = caracteristica("barbaro", "Característica de Subclasse", 6)
        self.assertEqual(resultado["resultado"], "escolha")
        self.assertEqual(resultado["motivo"], "subclasse_ausente")

    def test_caracteristica_de_subclasse_marcial_lista_as_disponiveis(self):
        resultado = caracteristica("barbaro", "Característica de Subclasse", 6, subclasse="trilha_do_berserker")
        self.assertEqual(resultado["resultado"], "requer_caracteristica")
        self.assertIn("frenesi", resultado["caracteristicas_disponiveis"])

    def test_caracteristica_de_subclasse_desconhecida_bloqueia(self):
        resultado = caracteristica("barbaro", "Característica de Subclasse", 6, subclasse="inexistente")
        self.assertEqual(resultado["resultado"], "bloqueado")
        self.assertEqual(resultado["motivo"], "subclasse_marcial_desconhecida")

    def test_dadiva_epica_lista_os_doze_talentos_epicos(self):
        resultado = caracteristica("guerreiro", "Dádiva Épica", 19)
        self.assertEqual(resultado["resultado"], "escolha")
        self.assertEqual(resultado["exige_nivel"], 19)
        self.assertIn("dadiva_do_destino", resultado["opcoes"])
        self.assertEqual(
            len(resultado["opcoes"]), sum(1 for d in FEATS.values() if d.get("categoria") == "dadiva_epica")
        )

    def test_estilo_de_luta_oferece_os_dez_talentos_do_phb(self):
        resultado = caracteristica("guerreiro", "Estilo de Luta", 1)
        self.assertEqual(resultado["resultado"], "escolha")
        self.assertEqual(
            resultado["opcoes"],
            [
                "arquearia",
                "combate_com_armas_de_arremesso",
                "combate_com_armas_grandes",
                "combate_com_duas_armas",
                "combate_desarmado",
                "defensivo",
                "duelismo",
                "interceptacao",
                "luta_as_cegas",
                "protetivo",
            ],
        )

    def test_estilo_de_luta_resolvido_com_efeito(self):
        resultado = caracteristica("paladino", "Estilo de Luta", 2, talento="Arquearia")
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["ataque_distancia"], 2)

    def test_estilo_de_luta_defensivo(self):
        resultado = caracteristica("guardiao", "Estilo de Luta", 2, talento="Defensivo")
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["ca"], 1)

    def test_estilo_de_luta_invalido_bloqueia(self):
        resultado = caracteristica("guerreiro", "Estilo de Luta", 1, talento="talento_de_outra_categoria")
        self.assertEqual(resultado["resultado"], "bloqueado")
        self.assertEqual(resultado["motivo"], "talento_invalido")

    def test_aumento_de_atributo_ou_talento_continua_aplicando(self):
        resultado = caracteristica("guerreiro", "Aumento de Atributo ou Talento", 4, talento="Alerta")
        self.assertEqual(resultado["resultado"], "aplicado")
        self.assertEqual(resultado["talento"], "Alerta")


if __name__ == "__main__":
    unittest.main()
