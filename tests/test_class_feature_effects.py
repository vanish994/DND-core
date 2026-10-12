"""Efeitos das características de classe do PHB 2024.

Cobre as mecânicas implementadas no ladder de
``class_features.resolver_caracteristica`` para Bárbaro, Guerreiro, Monge,
Ladino, Bardo, Clérigo, Druida, Paladino e Guardião, com valores conferidos
contra o Livro do Jogador 2024 (capítulo 3).
"""

import unittest

from rule_engine.class_features import resolver_caracteristica


def caracteristica(classe, recurso, nivel=20, **fatos):
    return resolver_caracteristica({"classe": classe, "recurso": recurso, "nivel": nivel, **fatos})


class BarbaroFeatureTests(unittest.TestCase):
    def test_ataque_imprudente(self):
        resultado = caracteristica("barbaro", "Ataque Imprudente", 2)
        self.assertEqual(resultado["resultado"], "ativado")
        self.assertTrue(resultado["vantagem_ataques_forca"])
        self.assertTrue(resultado["vantagem_ataques_contra_voce"])

    def test_bote_instintivo_move_metade_do_deslocamento(self):
        resultado = caracteristica("barbaro", "Bote Instintivo", 7)
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["movimento"], "metade_do_deslocamento")

    def test_instintos_primitivos(self):
        resultado = caracteristica("barbaro", "Instintos Primitivos", 7)
        self.assertTrue(resultado["vantagem_iniciativa"])

    def test_golpe_brutal_sem_efeito_oferece_opcoes(self):
        resultado = caracteristica("barbaro", "Golpe Brutal", 9)
        self.assertEqual(resultado["resultado"], "escolha")
        self.assertEqual(resultado["opcoes"], ["golpe_debilitador", "golpe_poderoso"])
        self.assertEqual(resultado["dano_adicional"], "1d10")

    def test_golpe_brutal_aprimorado_adiciona_efeitos_no_nivel_13(self):
        resultado = caracteristica("barbaro", "Golpe Brutal Fortalecido", 13)
        self.assertIn("golpe_atordoante", resultado["opcoes"])
        self.assertIn("golpe_destruidor", resultado["opcoes"])
        self.assertEqual(resultado["efeitos_por_uso"], 1)

    def test_golpe_brutal_no_nivel_17_causa_2d10_com_dois_efeitos(self):
        resultado = caracteristica(
            "barbaro",
            "Golpe Brutal Fortalecido",
            17,
            efeito=["golpe_debilitador", "golpe_poderoso"],
            ataque_imprudente=True,
        )
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["dano_adicional"], "2d10")
        self.assertEqual(len(resultado["efeitos"]), 2)
        self.assertEqual(resultado["efeitos"][0]["deslocamento_reduzido_m"], 4.5)

    def test_golpe_brutal_exige_ataque_imprudente(self):
        resultado = caracteristica("barbaro", "Golpe Brutal", 9, efeito="golpe_poderoso")
        self.assertEqual(resultado["resultado"], "bloqueado")
        self.assertEqual(resultado["motivo"], "requer_ataque_imprudente")

    def test_golpe_brutal_rejeita_efeito_invalido(self):
        resultado = caracteristica("barbaro", "Golpe Brutal", 9, efeito="inexistente", ataque_imprudente=True)
        self.assertEqual(resultado["resultado"], "bloqueado")
        self.assertEqual(resultado["motivo"], "efeito_invalido")

    def test_furia_persistente_recupera_na_iniciativa(self):
        resultado = caracteristica("barbaro", "Fúria Persistente", 15)
        self.assertEqual(resultado["resultado"], "recuperado")
        self.assertEqual(resultado["usos_de_furia"], "todos")
        self.assertEqual(resultado["recarga"], "descanso_longo")

    def test_furia_persistente_duracao_dez_minutos(self):
        resultado = caracteristica("barbaro", "Fúria Persistente", 15, acao="duracao")
        self.assertEqual(resultado["duracao_furia"], "10 minutos")
        self.assertIn("inconsciente", resultado["encerra_com"])


class GuerreiroFeatureTests(unittest.TestCase):
    def test_mestre_tatico_substitui_a_maestria(self):
        resultado = caracteristica("guerreiro", "Mestre Tático", 9)
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["propriedades_substitutas"], ["empurra", "drenar", "lentidao"])


class MongeFeatureTests(unittest.TestCase):
    def test_movimento_sem_armadura_escalonamento(self):
        self.assertEqual(caracteristica("monge", "Movimento sem Armadura", 2)["bonus_deslocamento_m"], 3)
        self.assertEqual(caracteristica("monge", "Movimento sem Armadura", 6)["bonus_deslocamento_m"], 4.5)
        self.assertEqual(caracteristica("monge", "Movimento sem Armadura", 10)["bonus_deslocamento_m"], 6)
        self.assertEqual(caracteristica("monge", "Movimento sem Armadura", 14)["bonus_deslocamento_m"], 7.5)
        self.assertEqual(caracteristica("monge", "Movimento sem Armadura", 18)["bonus_deslocamento_m"], 9)

    def test_metabolismo_incomum_restaura_foco_e_cura(self):
        resultado = caracteristica("monge", "Metabolismo Incomum", 5, rolagem_dado_artes_marciais=4)
        self.assertEqual(resultado["resultado"], "recuperado")
        self.assertEqual(resultado["pontos_de_foco"], "todos")
        self.assertEqual(resultado["cura"], 9)
        self.assertEqual(resultado["dado_artes_marciais"], "d8")

    def test_golpes_potencializados_sem_escolha(self):
        resultado = caracteristica("monge", "Golpes Potencializados", 6)
        self.assertEqual(resultado["resultado"], "escolha")
        self.assertEqual(resultado["opcoes"], ["energetico", "normal"])

    def test_golpes_potencializados_energetico(self):
        resultado = caracteristica("monge", "Golpes Potencializados", 6, tipo_dano="energetico")
        self.assertEqual(resultado["tipo_dano"], "energetico")

    def test_movimento_acrobatico(self):
        resultado = caracteristica("monge", "Movimento Acrobático", 9)
        self.assertTrue(resultado["sem_queda"])
        self.assertIn("liquidos", resultado["superficies"])

    def test_foco_aprimorado(self):
        resultado = caracteristica("monge", "Foco Aprimorado", 10)
        self.assertEqual(resultado["torrente_de_golpes"]["ataques_desarmados"], 3)
        self.assertIn("pv_temporarios", resultado["defesa_paciente"])

    def test_restauro_pessoal(self):
        resultado = caracteristica("monge", "Restauro Pessoal", 10)
        self.assertEqual(resultado["resultado"], "removida")
        self.assertIn("amedrontado", resultado["opcoes_condicao"])

    def test_defletir_energia_aceita_qualquer_dano(self):
        resultado = caracteristica("monge", "Defletir Energia", 13, dano=12, rolagem_d10=5, modificador_destreza=3)
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["tipos_dano"], "todos")
        self.assertEqual(resultado["dano_restante"], 0)


class LadinoFeatureTests(unittest.TestCase):
    def test_especializacao_duas_pericias(self):
        resultado = caracteristica("ladino", "Especialização", 1)
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["pericias"], 2)
        self.assertEqual(resultado["multiplicador_proficiencia"], 2)

    def test_giria_dos_ladroes(self):
        resultado = caracteristica("ladino", "Gíria dos Ladrões", 1)
        self.assertIn("giria_dos_ladroes", resultado["idiomas"])

    def test_acao_ardilosa_sem_acao_oferece_opcoes(self):
        resultado = caracteristica("ladino", "Ação Ardilosa", 2)
        self.assertEqual(resultado["resultado"], "escolha")
        self.assertEqual(resultado["opcoes"], ["correr", "desengajar", "esconder"])

    def test_acao_ardilosa_permitida(self):
        resultado = caracteristica("ladino", "Ação Ardilosa", 2, acao="esconder")
        self.assertEqual(resultado["resultado"], "permitido")

    def test_golpe_astuto_opcoes_iniciais(self):
        resultado = caracteristica("ladino", "Golpe Astuto", 5, modificador_destreza=4, bonus_proficiencia=3)
        self.assertEqual(resultado["resultado"], "escolha")
        self.assertEqual(resultado["opcoes"], ["envenenar", "retirada", "tropeco"])
        self.assertEqual(resultado["cd"], 15)

    def test_golpe_astuto_aprimorado_permite_dois_efeitos(self):
        resultado = caracteristica(
            "ladino", "Golpe Astuto Aprimorado", 11, efeito=["envenenar", "tropeco"], modificador_destreza=4
        )
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(len(resultado["efeitos"]), 2)
        self.assertEqual(resultado["efeitos"][0]["custo"], "1d6")

    def test_golpes_sujos_adiciona_tres_efeitos(self):
        resultado = caracteristica("ladino", "Golpes Sujos", 14)
        self.assertEqual(resultado["resultado"], "escolha")
        for efeito in ("aturdir", "nocaute", "obscurecer"):
            self.assertIn(efeito, resultado["opcoes"])
        self.assertEqual(resultado["efeitos_por_uso"], 2)

    def test_golpe_astuto_um_efeito_apenas_no_nivel_5(self):
        resultado = caracteristica("ladino", "Golpe Astuto", 5, efeito=["envenenar", "retirada"])
        self.assertEqual(resultado["resultado"], "bloqueado")
        self.assertEqual(resultado["motivo"], "quantidade_de_efeitos_excedida")

    def test_golpe_astuto_nocaute_custo_6d6(self):
        resultado = caracteristica("ladino", "Golpes Sujos", 14, efeito="nocaute")
        self.assertEqual(resultado["efeitos"][0]["custo"], "6d6")
        self.assertEqual(resultado["efeitos"][0]["falha"], "inconsciente_1_minuto_ou_ate_dano")


class ConjuradorFeatureTests(unittest.TestCase):
    def test_segredos_magicos_do_bardo(self):
        resultado = caracteristica("bardo", "Segredos Mágicos", 10)
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["listas_permitidas"], ["bardo", "clerigo", "druida", "mago"])

    def test_golpes_abencoados_escolha(self):
        resultado = caracteristica("clerigo", "Golpes Abençoados", 7)
        self.assertEqual(resultado["resultado"], "escolha")
        self.assertEqual(resultado["opcoes"], ["conjuracao_poderosa", "golpe_divino"])

    def test_golpes_abencoados_aprimorado_golpe_divino(self):
        resultado = caracteristica("clerigo", "Golpes Abençoados Aprimorado", 14, opcao="golpe_divino")
        self.assertEqual(resultado["dano_extra"], "2d8_radiante_ou_necrotico")

    def test_golpes_abencoados_aprimorado_conjuracao_poderosa(self):
        resultado = caracteristica(
            "clerigo", "Golpes Abençoados Aprimorado", 14, opcao="conjuracao_poderosa", sabedoria=16
        )
        self.assertEqual(resultado["pv_temporarios"], 6)
        self.assertEqual(resultado["alcance_m"], 18)

    def test_intervencao_divina_2024(self):
        resultado = caracteristica("clerigo", "Intervenção Divina", 10)
        self.assertIn("5_circulo_ou_inferior", resultado["magia"])
        self.assertTrue(resultado["sem_espaco_sem_componentes_materiais"])

    def test_intervencao_divina_maior_adiciona_desejo(self):
        resultado = caracteristica("clerigo", "Intervenção Divina Maior", 20)
        self.assertEqual(resultado["magia_adicional"], "desejo")
        self.assertEqual(resultado["recarga_se_usar_desejo"], "2d4_descansos_longos")

    def test_furia_elemental_escolha(self):
        resultado = caracteristica("druida", "Fúria Elemental", 7)
        self.assertEqual(resultado["opcoes"], ["ataque_primal", "conjuracao_poderosa"])

    def test_furia_elemental_ataque_primal(self):
        resultado = caracteristica("druida", "Fúria Elemental", 7, opcao="ataque_primal")
        self.assertEqual(resultado["dano_extra"], "1d8")

    def test_furia_elemental_aprimorada_2d8_e_alcance(self):
        ataque = caracteristica("druida", "Fúria Elemental Aprimorada", 15, opcao="ataque_primal")
        self.assertEqual(ataque["dano_extra"], "2d8")
        conjuracao = caracteristica(
            "druida", "Fúria Elemental Aprimorada", 15, opcao="conjuracao_poderosa", sabedoria=18
        )
        self.assertEqual(conjuracao["alcance_m"], 90)


class PaladinoGuardiaoFeatureTests(unittest.TestCase):
    def test_canalizar_divindade_do_paladino(self):
        resultado = caracteristica("paladino", "Canalizar Divindade", 3)
        self.assertEqual(resultado["usos"], 2)
        self.assertEqual(resultado["efeito_inicial"], "sentido_divino")
        reforco = caracteristica("paladino", "Canalizar Divindade", 11)
        self.assertEqual(reforco["usos"], 3)

    def test_montaria_fiel(self):
        resultado = caracteristica("paladino", "Montaria Fiel", 5)
        self.assertEqual(resultado["magia"], "convocar_montaria")
        self.assertTrue(resultado["sempre_preparada"])

    def test_repudiar_inimigos(self):
        resultado = caracteristica("paladino", "Repudiar Inimigos", 9, carisma=18)
        self.assertEqual(resultado["alvos"], 4)
        self.assertEqual(resultado["salvaguarda"], "sabedoria")
        self.assertEqual(resultado["custo"], "1_uso_de_canalizar_divindade")

    def test_aura_expandida(self):
        resultado = caracteristica("paladino", "Aura Expandida", 18)
        self.assertEqual(resultado["emanacao_m"], 9)

    def test_especialista_do_guardiao(self):
        resultado = caracteristica("guardiao", "Especialista", 9)
        self.assertEqual(resultado["pericias"], 2)

    def test_cacador_preciso(self):
        resultado = caracteristica("guardiao", "Caçador Preciso", 17)
        self.assertEqual(resultado["vantagem_ataques_contra"], "alvo_da_marca_do_predador")

    def test_magia_de_artifice_corrigida(self):
        resultado = caracteristica("artifice", "Magia de Artífice", 1)
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["foco"], "ferramentas_de_artifice")

    def test_artifice_magia_de_artifice_e_conjuracao(self):
        resultado = caracteristica("artifice", "Conjuração", 1, inteligencia=16)
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["cd_magia"], 13)
        self.assertEqual(resultado["magias_preparadas"], 2)
        self.assertEqual(resultado["espacos"], {"1": 2})

    def test_artifice_replicar_item_magico_progressao_55(self):
        resultado = caracteristica("artifice", "Replicar Item Mágico", 14)
        self.assertEqual(resultado["planos_conhecidos"], 7)
        self.assertEqual(resultado["limite_itens_criados"], 5)
        self.assertEqual(resultado["nivel_minimo_do_plano"], 14)

    def test_artifice_ajustador_item_magico_carrega_cargas(self):
        resultado = caracteristica("artifice", "Ajustador de Item Mágico", 6,
                                   acao="carregar", nivel_espaco=2, item_replicado=True, distancia_m=1.0, espaco_disponivel=True,
                                   cargas_atuais=1, cargas_maximas=5)
        self.assertEqual(resultado["cargas_restauradas"], 2)
        self.assertEqual(resultado["cargas_atuais"], 3)

    def test_artifice_lampejo_de_genio_requer_falha(self):
        resultado = caracteristica("artifice", "Lampejo de Gênio", 7,
                                   inteligencia=16, criatura_falhou=True, total=9, distancia_m=6, alvo_visivel=True)
        self.assertEqual(resultado["resultado"], "aplicado")
        self.assertEqual(resultado["bonus"], 3)
        self.assertEqual(resultado["novo_total"], 12)

    def test_artifice_item_armazenador_ate_terceiro_circulo(self):
        resultado = caracteristica("artifice", "Item Armazenador de Magia", 11,
                                   inteligencia=16, magia="Dissipar Magia", nivel_magia=3, tempo_conjuracao_acao=True, objeto_adequado=True)
        self.assertEqual(resultado["resultado"], "armazenado")
        self.assertEqual(resultado["usos"], 6)

    def test_artifice_alma_artifice_recupera_20_pv_por_item(self):
        resultado = caracteristica("artifice", "Alma do Artífice", 20,
                                   acao="evitar_morte", caiu_a_0_pv=True,
                                   itens_destruidos=[{"raridade":"incomum", "replicado":True}, {"raridade":"raro", "replicado":True}])
        self.assertEqual(resultado["resultado"], "sobreviveu")
        self.assertEqual(resultado["pv_atuais"], 40)


if __name__ == "__main__":
    unittest.main()
