"""Cobertura mecânica de magias específicas do PHB 2024."""

import unittest

from rule_engine.spells import resolver_magia


class RaiseDeadMechanicsTests(unittest.TestCase):
    def test_reviver_os_mortos_tem_mecanica_estruturada(self):
        resultado = resolver_magia(
            {
                "magia": "Reviver os Mortos",
                "espaco": 5,
                "has_slot": True,
            }
        )

        self.assertEqual(resultado["resultado"], "conjurada")
        mecanica = resultado["mecanica"]
        self.assertEqual(mecanica["tipo"], "ressurreicao")
        self.assertEqual(mecanica["acao"], "1_hora")
        self.assertEqual(mecanica["alcance"], "toque")
        self.assertEqual(mecanica["custo_material_minimo_po"], 500)
        self.assertEqual(mecanica["limite_dias_morto"], 10)
        self.assertEqual(mecanica["pv_ao_reviver"], 1)
        self.assertFalse(mecanica["revive_morto_vivo"])
        self.assertEqual(mecanica["penalidade_testes_d20_inicial"], -4)
        self.assertEqual(mecanica["reducao_penalidade_por_descanso_longo"], 1)


if __name__ == "__main__":
    unittest.main()
