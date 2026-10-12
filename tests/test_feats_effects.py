"""Efeitos mecânicos dos talentos do PHB 2024 (capítulo 5).

Todos os talentos do catálogo resolvem benefícios determinísticos, exceto os
dois talentos de Dádiva Sombria cujos efeitos não constam das fontes do
repositório (``anatomia_aberrante`` e ``toque_da_morte``).
"""

import unittest

from rule_engine import FEATS
from rule_engine.feats import resolver_talento, validar_talento

SEM_FONTE = {"anatomia_aberrante", "toque_da_morte"}


def fatos_de(nome, nivel=20, **extras):
    base = {
        "talento": nome,
        "nivel": nivel,
        "bonus_proficiencia": 6,
        "forca": 18,
        "destreza": 18,
        "constituicao": 18,
        "inteligencia": 18,
        "sabedoria": 18,
        "carisma": 18,
        "caracteristica_conjuracao": True,
        "campanha_ravenloft": True,
    }
    base.update(extras)
    return base


class FeatCompletenessTests(unittest.TestCase):
    def test_todos_os_talentos_resolvem_exceto_os_sem_fonte(self):
        pendentes = []
        for nome in sorted(FEATS):
            resultado = resolver_talento(fatos_de(nome))
            if resultado["resultado"] != "resolvido":
                pendentes.append((nome, resultado.get("motivo")))
        self.assertEqual(pendentes, sorted((n, "efeitos_nao_catalogados_na_fonte") for n in SEM_FONTE))


class OriginFeatTests(unittest.TestCase):
    def test_alerta(self):
        resultado = resolver_talento(fatos_de("alerta", nivel=1))
        self.assertEqual(resultado["bonus_iniciativa"], "bonus_proficiencia")
        self.assertTrue(resultado["troca_iniciativa"])

    def test_artifista(self):
        resultado = resolver_talento(fatos_de("artifista", nivel=1))
        self.assertEqual(resultado["proficiencia_ferramentas"], 3)
        self.assertEqual(resultado["desconto_compra"], "20_porcento")

    def test_atacante_selvagem(self):
        resultado = resolver_talento(fatos_de("atacante_selvagem", nivel=1))
        self.assertTrue(resultado["rola_dano_da_arma_duas_vezes"])
        self.assertEqual(resultado["limite"], "uma_vez_por_turno")

    def test_curandeiro(self):
        resultado = resolver_talento(fatos_de("curandeiro", nivel=1))
        self.assertIn("kit_de_curandeiro", resultado["medico_de_combate"]["requer"])
        self.assertIn("bonus_proficiencia", resultado["medico_de_combate"]["cura"])

    def test_habilidoso_repetivel(self):
        resultado = resolver_talento(fatos_de("habilidoso", nivel=1))
        self.assertEqual(resultado["proficiencias"], 3)
        self.assertTrue(resultado["repetivel"])

    def test_iniciado_em_magia(self):
        resultado = resolver_talento(fatos_de("iniciado_em_magia", nivel=1))
        self.assertEqual(resultado["truques"], 2)
        self.assertEqual(resultado["usos_sem_espaco"], 1)
        self.assertEqual(resultado["listas"], ["clerigo", "druida", "mago"])

    def test_musico(self):
        resultado = resolver_talento(fatos_de("musico", nivel=1))
        self.assertEqual(resultado["proficiencia_instrumentos"], 3)
        self.assertEqual(resultado["inspiracao_heroica_aliados"], "bonus_proficiencia")

    def test_sortudo_pontos_igual_proficiencia(self):
        resultado = resolver_talento(fatos_de("sortudo", nivel=1, bonus_proficiencia=3))
        self.assertEqual(resultado["pontos_de_sorte"], 3)

    def test_valentao_de_taverna(self):
        resultado = resolver_talento(fatos_de("valentao_de_taverna", nivel=1))
        self.assertEqual(resultado["dano_desarmado"], "1d4_mais_modificador_de_forca")
        self.assertEqual(resultado["empurra_m"], 1.5)

    def test_vigoroso_dobra_por_nivel(self):
        self.assertEqual(resolver_talento(fatos_de("vigoroso", nivel=5))["pv_adicionais"], 10)
        self.assertEqual(resolver_talento(fatos_de("vigoroso", nivel=10))["pv_adicionais"], 20)


class GeneralFeatTests(unittest.TestCase):
    def test_agressor_investida(self):
        resultado = resolver_talento(fatos_de("agressor", nivel=4))
        self.assertEqual(resultado["ataque_em_investida"]["dano"], "1d8")
        self.assertEqual(resultado["correr_bonus_deslocamento_m"], 3)

    def test_atleta(self):
        resultado = resolver_talento(fatos_de("atleta", nivel=4))
        self.assertEqual(resultado["levantar_caido_custa_m"], 1.5)
        self.assertEqual(resultado["salto_apos_mover_m"], 1.5)

    def test_aumento_no_valor_de_atributo(self):
        resultado = resolver_talento(fatos_de("aumento_no_valor_de_atributo", nivel=4))
        self.assertEqual(resultado["aumento_atributo"], "2_ou_dois_atributos_em_1")
        self.assertTrue(resultado["repetivel"])

    def test_chef(self):
        resultado = resolver_talento(fatos_de("chef", nivel=4))
        self.assertEqual(resultado["refeicao"]["cura_adicional"], "1d8")
        self.assertEqual(resultado["guloseimas"]["duracao_horas"], 8)

    def test_especialista_em_armaduras_pesadas(self):
        resultado = resolver_talento(fatos_de("especialista_em_armaduras_pesadas", nivel=4))
        self.assertIn("armadura_pesada", resultado["treinamento"])

    def test_esmagador(self):
        resultado = resolver_talento(fatos_de("esmagador", nivel=4))
        self.assertEqual(resultado["empurra_m"], 1.5)

    def test_lider_inspirador_pv_temporarios(self):
        resultado = resolver_talento(fatos_de("lider_inspirador", nivel=8, modificador_atributo_aumentado=4))
        self.assertEqual(resultado["pv_temporarios"], 12)
        self.assertEqual(resultado["aliados"], 6)

    def test_mestre_em_armaduras_pesadas(self):
        resultado = resolver_talento(fatos_de("mestre_em_armaduras_pesadas", nivel=4))
        self.assertEqual(resultado["reducao_dano_fisico"], "bonus_proficiencia")

    def test_mestre_atirador(self):
        resultado = resolver_talento(fatos_de("mestre_atirador", nivel=4))
        self.assertTrue(resultado["sem_desvantagem_em_alcance_maximo"])

    def test_sentinela(self):
        resultado = resolver_talento(fatos_de("sentinela", nivel=4))
        self.assertTrue(resultado["zera_deslocamento"])

    def test_sorrateiro(self):
        resultado = resolver_talento(fatos_de("sorrateiro", nivel=4))
        self.assertEqual(resultado["visao_as_cegas_m"], 3)

    def test_telecinetico(self):
        resultado = resolver_talento(fatos_de("telecinético", nivel=4))
        self.assertEqual(resultado["empurrao_telecinetico"]["alcance_m"], 9)
        self.assertTrue(resultado["maos_magicas"]["sem_componentes"])

    def test_tocado_pelas_fadas(self):
        resultado = resolver_talento(fatos_de("tocado_pelas_fadas", nivel=4))
        self.assertEqual(resultado["magia_feerica"]["incluso"], "passo_nebuloso")

    def test_velocista(self):
        resultado = resolver_talento(fatos_de("velocista", nivel=4))
        self.assertEqual(resultado["deslocamento_adicional_m"], 3)

    def test_conjura_aceita_dados_em_fatos(self):
        resultado = resolver_talento(fatos_de("conjurador_belico", nivel=4))
        self.assertTrue(resultado["vantagem_concentracao"])


class EpicFeatTests(unittest.TestCase):
    def test_dadiva_da_fortitude(self):
        resultado = resolver_talento(fatos_de("dadiva_da_fortitude", nivel=19))
        self.assertEqual(resultado["pv_maximos_adicionais"], 40)
        self.assertEqual(resultado["maximo_atributo"], 30)

    def test_dadiva_da_recuperacao(self):
        resultado = resolver_talento(fatos_de("dadiva_da_recuperacao", nivel=19))
        self.assertEqual(resultado["reserva_de_dados"]["quantidade"], 10)
        self.assertEqual(resultado["ate_a_morte"]["pv"], 1)

    def test_dadiva_da_resistencia_a_energia(self):
        resultado = resolver_talento(fatos_de("dadiva_da_resistencia_a_energia", nivel=19))
        self.assertEqual(resultado["resistencias"], 2)
        self.assertIn("radiante", resultado["tipos"])

    def test_dadiva_do_destino(self):
        resultado = resolver_talento(fatos_de("dadiva_do_destino", nivel=19))
        self.assertEqual(resultado["modifica_teste_d20"], "2d4")

    def test_dadiva_do_ataque_irresistivel(self):
        resultado = resolver_talento(fatos_de("dadiva_do_ataque_irresistivel", nivel=19))
        self.assertTrue(resultado["ignora_resistencia_fisica"])
        self.assertEqual(resultado["atributos_aumento"], ["forca", "destreza"])


class DarkGiftFeatTests(unittest.TestCase):
    def test_dadiva_sombria_exige_campanha(self):
        bloqueado = validar_talento({"talento": "sombra_viva", "nivel": 10})
        self.assertEqual(bloqueado["motivo"], "requer_campanha_ravenloft")

    def test_dadiva_sombria_resolvida(self):
        resultado = resolver_talento(fatos_de("sombra_viva", nivel=10))
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertTrue(resultado["maos_magicas_sem_componentes"])

    def test_sem_fonte_fica_explicito(self):
        resultado = resolver_talento(fatos_de("anatomia_aberrante", nivel=10))
        self.assertEqual(resultado["resultado"], "nao_implementado")
        self.assertEqual(resultado["motivo"], "efeitos_nao_catalogados_na_fonte")


if __name__ == "__main__":
    unittest.main()
