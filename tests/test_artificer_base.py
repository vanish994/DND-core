"""Regression tests for the Artificer 5.5e base class."""
import unittest

from rule_engine.artificer_base import ARTIFICER_GEAR, ARTIFICER_PREPARED_SPELLS, resolve_artificer_feature
from rule_engine.character import criar_personagem, ficha_personagem
from rule_engine.class_features import resolver_caracteristica
from rule_engine.class_progression import caracteristicas_no_nivel
from rule_engine.spellcasting import progresso_artifice


class ArtificerProgressionTests(unittest.TestCase):
    def test_level_one_artificer_spellcasting_checks_known_and_prepared_spells(self):
        base = {
            "classe": "artifice", "nivel": 1, "recurso": "conjuracao",
            "acao": "conjurar", "truques_conhecidos": ["Raio de Fogo", "Luz"],
            "magias_preparadas": ["Curar Ferimentos", "Alarme"],
            "espacos_restantes": {"1": 2}, "inteligencia": 16,
        }
        known_cantrip = resolver_caracteristica({**base, "magia": "Reparar"})
        self.assertNotEqual(known_cantrip.get("motivo"), "truque_nao_conhecido")
        unprepared = resolver_caracteristica({**base, "magia": "Fogo das Fadas"})
        self.assertEqual(unprepared["resultado"], "bloqueado")
        self.assertEqual(unprepared["motivo"], "magia_nao_preparada")
        no_slot = resolver_caracteristica({**base, "magia": "Curar Ferimentos", "espacos_restantes": {"1": 0}})
        self.assertEqual(no_slot["motivo"], "sem_espacos_de_magia")

    def test_level_one_artificer_spellcasting_delegates_prepared_spell_to_general_resolver(self):
        result = resolver_caracteristica({
            "classe": "artifice", "nivel": 1, "recurso": "conjuracao", "acao": "conjurar",
            "magia": "Curar Ferimentos", "magias_preparadas": ["Curar Ferimentos"],
            "truques_conhecidos": ["Raio de Fogo", "Luz"], "espacos_restantes": {"1": 2},
            "inteligencia": 16, "bonus_proficiencia": 2, "alvo_pv_atuais": 2, "alvo_pv_maximos": 10,
        })
        self.assertNotEqual(result.get("motivo"), "magia_nao_preparada")
        self.assertNotEqual(result.get("motivo"), "magia_fora_da_lista_do_artifice")
        self.assertEqual(result.get("slot_consumido"), 1)
        self.assertEqual(result["delta_espacos"], {"1": -1})
        self.assertEqual(result["espacos_restantes_depois"], {"1": 1})

    def test_fixed_prepared_spell_table_for_all_levels(self):
        self.assertEqual(
            [progresso_artifice(level, 16)["magias_preparadas"] for level in range(1, 21)],
            [ARTIFICER_PREPARED_SPELLS[level] for level in range(1, 21)],
        )

    def test_cantrip_thresholds_and_slots(self):
        self.assertEqual(progresso_artifice(1, 16)["truques"], 2)
        self.assertEqual(progresso_artifice(9, 16)["truques"], 2)
        self.assertEqual(progresso_artifice(10, 16)["truques"], 3)
        self.assertEqual(progresso_artifice(14, 16)["truques"], 4)
        self.assertEqual(progresso_artifice(20, 16)["espacos_totais"], {
            "1": 4, "2": 3, "3": 3, "4": 3, "5": 2
        })

    def test_english_feature_aliases_obey_level_gates(self):
        early_tinker = resolver_caracteristica({
            "classe": "artifice", "recurso": "Magic Item Tinker", "nivel": 1,
        })
        self.assertEqual(early_tinker["resultado"], "bloqueado")
        self.assertEqual(early_tinker["nivel_minimo"], 6)
        early_adept = resolver_caracteristica({
            "classe": "artifice", "recurso": "Magic Item Adept", "nivel": 1,
        })
        self.assertEqual(early_adept["nivel_minimo"], 10)
        early_master = resolver_caracteristica({
            "classe": "artifice", "recurso": "Magic Item Master", "nivel": 1,
        })
        self.assertEqual(early_master["nivel_minimo"], 18)
        early_boon = resolver_caracteristica({
            "classe": "artifice", "recurso": "Epic Boon", "nivel": 18,
        })
        self.assertEqual(early_boon["nivel_minimo"], 19)

    def test_long_rest_recovers_artificer_resources_and_expires_tinker_items(self):
        result = resolver_caracteristica({
            "classe": "artifice", "recurso": "recuperacao_recursos", "nivel": 7,
            "tipo_descanso": "longo", "inteligencia": 16,
            "itens_tinkers_atuais": [{"id": "mundane-1", "nome": "Corda", "criado_por": "tinkers_magic"}],
        })
        self.assertEqual(result["resultado"], "recursos_recuperados")
        self.assertEqual(result["recursos"]["magia_de_artifice"]["usos_maximos"], 3)
        self.assertEqual(result["recursos"]["lampejo_de_genio"]["usos_gastos"], 0)
        self.assertEqual(result["recursos"]["drenar_item_magico"]["usado_no_descanso_longo"], False)
        self.assertEqual(result["itens_tinkers_que_expiram"][0]["id"], "mundane-1")
        self.assertEqual(result["delta_inventario"]["remover_ids"], ["mundane-1"])
        self.assertEqual(result["delta_mundo"]["remover_ids"], ["mundane-1"])
        self.assertEqual(result["delta_conjuracao"]["espacos_restantes"], {"1": 4, "2": 3})
        self.assertTrue(result["delta_conjuracao"]["troca_truque_disponivel"])
        self.assertTrue(result["delta_conjuracao"]["mudanca_magias_preparadas_disponivel"])

    def test_short_rest_recovers_flash_of_genius_according_to_level(self):
        level_14 = resolver_caracteristica({
            "classe": "artifice", "recurso": "recuperacao_recursos", "nivel": 14,
            "tipo_descanso": "curto", "inteligencia": 16, "lampejo_usos_gastos": 2,
        })
        self.assertEqual(level_14["recursos"]["lampejo_de_genio"]["usos_gastos"], 1)
        level_20 = resolver_caracteristica({
            "classe": "artifice", "recurso": "recuperacao_recursos", "nivel": 20,
            "tipo_descanso": "curto", "inteligencia": 16, "sintonizado_item_magico": True,
            "lampejo_usos_gastos": 2,
        })
        self.assertEqual(level_20["recursos"]["lampejo_de_genio"]["usos_gastos"], 0)
        self.assertEqual(level_20["usos_lampejo_recuperados"], "todos")

    def test_level_6_10_14_18_and_epic_boon_are_in_progression(self):
        self.assertIn("Ajustador de Item Mágico", caracteristicas_no_nivel("artifice", 6))
        self.assertIn("Adepto de Item Mágico", caracteristicas_no_nivel("artifice", 10))
        self.assertIn("Artífice Avançado", caracteristicas_no_nivel("artifice", 14))
        self.assertIn("Mestre de Item Mágico", caracteristicas_no_nivel("artifice", 18))
        self.assertIn("Dádiva Épica", caracteristicas_no_nivel("artifice", 19))
        self.assertIn("Alma do Artífice", caracteristicas_no_nivel("artifice", 20))

    def test_inventory_preserves_replicated_item_metadata_and_removes_destroyed_items(self):
        from rule_engine.economy import resolver_inventario
        old = {"id": "old-item", "plano": "dazzling_weapon", "nome": "Arma Deslumbrante",
               "raridade": "raro", "sintonizacao": True, "replicado": True, "peso": 1}
        added = {"id": "new-item", "plano": "manifold_tool", "nome": "Ferramenta Multiforme",
                 "raridade": "comum", "sintonizacao": True, "replicado": True, "peso": 1}
        result = resolver_inventario({
            "itens": [old], "item_novo": added, "remover_ids": ["old-item"],
            "sintonizados": ["old-item"],
        })
        self.assertEqual([x["id"] for x in result["itens"]], ["new-item"])
        self.assertEqual(result["itens_removidos"][0]["id"], "old-item")
        self.assertEqual(result["sintonizados"], [])

    def test_new_eberron_magic_items_have_deterministic_actions(self):
        from rule_engine.economy import usar_item_magico

        manifold = usar_item_magico({
            "item": "item-1", "metadados_item": {"plano": "manifold_tool", "nome": "Ferramenta Multiforme", "sintonizacao": True},
            "sintonizados": ["item-1"], "acao": "transformar", "ferramenta_artesao": "ferramentas_de_carpinteiro",
        })
        self.assertEqual(manifold["resultado"], "transformado")
        self.assertTrue(manifold["proficiencia_concedida_ao_usar"])

        dazzling = usar_item_magico({
            "item": "item-2", "metadados_item": {"plano": "dazzling_weapon", "nome": "Arma Deslumbrante", "sintonizacao": True},
            "sintonizados": ["item-2"], "acao": "cegar_atacante", "foi_atingido_por_ataque": True,
            "reacao_disponivel": True, "cargas": 4, "salvaguarda_constituicao_total": 12,
        })
        self.assertEqual(dazzling["cargas_restantes"], 3)
        self.assertEqual(dazzling["condicao_aplicada"], "cego")

        boots = usar_item_magico({
            "item": "item-3", "metadados_item": {"plano": "boots_of_the_winding_path", "nome": "Botas do Caminho Sinuoso", "sintonizacao": True},
            "sintonizados": ["item-3"], "acao": "teleportar", "distancia_m": 4,
            "espaco_visto": True, "espaco_desocupado": True, "ocupou_este_turno": True,
        })
        self.assertEqual(boots["resultado"], "teletransportado")

        sharpener = usar_item_magico({
            "item": "item-4", "metadados_item": {"plano": "mind_sharpener", "nome": "Aguçador Mental", "sintonizacao": True},
            "sintonizados": ["item-4"], "acao": "manter_concentracao", "salvaguarda_constituicao_falhou": True,
            "reacao_disponivel": True, "cargas": 4,
        })
        self.assertEqual(sharpener["cargas_restantes"], 3)
        self.assertTrue(sharpener["salvaguarda_sucesso"])

        helm = usar_item_magico({
            "item": "item-helm", "metadados_item": {"plano": "helm_of_awareness", "nome": "Elmo da Consciência", "sintonizacao": False},
        })
        self.assertTrue(helm["vantagem_iniciativa"])
        self.assertTrue(helm["nao_pode_ser_surpreendido_enquanto_consciente"])

        repeating = usar_item_magico({
            "item": "item-repeat", "metadados_item": {"plano": "repeating_shot", "nome": "Disparo Repetidor", "sintonizacao": True},
            "sintonizados": ["item-repeat"],
        })
        self.assertEqual(repeating["bonus_ataque"], 1)
        self.assertTrue(repeating["ignora_propriedade_recarga"])
        self.assertTrue(repeating["cria_municao_magica_se_necessario"])

        returning = usar_item_magico({
            "item": "item-return", "metadados_item": {"plano": "returning_weapon", "nome": "Arma Retornante", "sintonizacao": False},
        })
        self.assertEqual(returning["bonus_dano"], 1)
        self.assertTrue(returning["retorna_apos_ataque_a_distancia"])

        shield = usar_item_magico({
            "item": "item-5", "metadados_item": {"plano": "repulsion_shield", "nome": "Escudo de Repulsão", "sintonizacao": False},
            "acao": "repelir", "foi_atingido_por_ataque_corpo_a_corpo": True, "tamanho_atacante": "grande",
            "distancia_m": 1, "reacao_disponivel": True, "cargas": 4,
        })
        self.assertEqual(shield["deslocamento_empurrado_m"], 4.5)

        ring = usar_item_magico({
            "item": "item-6", "metadados_item": {"plano": "spell_refueling_ring", "nome": "Anel de Reabastecimento de Magia",
            "sintonizacao": True, "sintonizacao_requer_classe": "conjurador"},
            "sintonizados": ["item-6"], "conjurador": True, "acao": "recuperar_espaco",
            "usado_hoje": False, "espaco_gasto": True, "nivel_espaco": 2,
        })
        self.assertEqual(ring["resultado"], "espaco_recuperado")
        self.assertTrue(ring["usado_hoje"])

    def test_tinkers_magic_uses_exact_published_26_item_list(self):
        self.assertEqual(len(ARTIFICER_GEAR), 26)
        self.assertIn("esferas_de_rolamento", ARTIFICER_GEAR)
        self.assertIn("caixa_de_isca", ARTIFICER_GEAR)
        for disallowed in ("garrafa_de_vidro", "arpeu", "armadilha_de_caca", "algemas", "estacas_de_ferro", "corrente"):
            self.assertNotIn(disallowed, ARTIFICER_GEAR)

        from rule_engine.artificer_base import ARTIFICER_GEAR_CATALOG_NAMES
        from rule_engine.catalog import CATALOGO_EQUIPAMENTOS
        self.assertEqual(set(ARTIFICER_GEAR_CATALOG_NAMES), ARTIFICER_GEAR)
        for gear_id, catalog_name in ARTIFICER_GEAR_CATALOG_NAMES.items():
            with self.subTest(gear=gear_id):
                data = CATALOGO_EQUIPAMENTOS[catalog_name]
                self.assertIn("peso", data)
                self.assertIn("custo_po", data)

    def test_tinkers_magic_creates_gear_with_tools_and_uses(self):
        result = resolver_caracteristica({
            "classe": "artifice", "recurso": "Magia de Artífice", "nivel": 1,
            "inteligencia": 16, "acao": "criar", "item": "Estrepes", "item_id": "tinker-gear-1",
            "ferramentas_tinkering_em_maos": True, "distancia_m": 1, "espaco_desocupado": True,
            "posicao_criacao": {"x": 1, "y": 2}, "usos_gastos": 1, "ids_objetos_existentes": [],
        })
        self.assertEqual(result["resultado"], "criado")
        self.assertEqual(result["delta_mundo"]["adicionar_objeto"]["id"], "tinker-gear-1")
        self.assertEqual(result["delta_mundo"]["adicionar_objeto"]["posicao"], {"x": 1, "y": 2})
        self.assertEqual(result["item_criado"]["unidades_por_item"], 20)
        self.assertEqual(result["usos_maximos"], 3)
        self.assertEqual(result["usos_restantes"], 1)
        self.assertEqual(result["usos_gastos_depois"], 2)
        self.assertEqual(result["delta_usos"], -1)
        self.assertEqual(result["item_criado"]["id"], "tinker-gear-1")
        self.assertEqual(result["item_criado"]["expira"], "proximo_descanso_longo")
        self.assertIn("peso", result["item_criado"])
        self.assertIn("custo_po", result["item_criado"])
        self.assertEqual(result["dados_catalogo"]["peso"], result["item_criado"]["peso"])
        self.assertTrue(result["requer_id_unico_ao_persistir"])
        self.assertEqual(result["desaparece"], "proximo_descanso_longo")

    def test_tinkers_magic_accepts_canonical_tool_name_and_rejects_invalid_distance(self):
        result = resolver_caracteristica({
            "classe": "artifice", "recurso": "Magia de Artífice", "nivel": 1,
            "inteligencia": 12, "acao": "criar", "item": "Corda",
            "ferramentas_de_funileiro_em_maos": True, "distancia_m": 1.5,
            "espaco_desocupado": True, "posicao_criacao": {"x": 3, "y": 5},
            "item_id": "tinker-canonical-1", "usos_gastos": 0, "ids_objetos_existentes": [],
        })
        self.assertEqual(result["resultado"], "criado")
        self.assertTrue(result["requer_id_unico_ao_persistir"])

        invalid = resolver_caracteristica({
            "classe": "artifice", "recurso": "Magia de Artífice", "nivel": 1,
            "inteligencia": 12, "acao": "criar", "item": "Corda",
            "ferramentas_de_funileiro_em_maos": True, "distancia_m": -0.1,
            "espaco_desocupado": True, "usos_gastos": 0,
        })
        self.assertEqual(invalid["resultado"], "bloqueado")
        self.assertEqual(invalid["motivo"], "espaco_de_criacao_fora_de_1_5_metro")

    def test_every_tinkers_magic_item_creates_full_catalogued_world_object(self):
        from rule_engine.artificer_base import ARTIFICER_GEAR, ARTIFICER_GEAR_CATALOG_NAMES
        from rule_engine.class_features import resolver_caracteristica
        from rule_engine.catalog import CATALOGO_EQUIPAMENTOS

        failures = []
        for gear_id in sorted(ARTIFICER_GEAR):
            result = resolver_caracteristica({
                "classe": "artifice", "nivel": 1, "recurso": "tinkers_magic", "acao": "criar",
                "inteligencia": 16, "usos_gastos": 0,
                "ferramentas_de_funileiro_em_maos": True,
                "distancia_m": 1.5, "espaco_desocupado": True,
                "posicao_criacao": {"x": 1, "y": 1},
                "item": gear_id, "item_id": f"tinker-{gear_id}",
                "ids_objetos_existentes": [],
            })
            if result.get("resultado") != "criado":
                failures.append((gear_id, result.get("resultado"), result.get("motivo")))
                continue
            created = result.get("delta_mundo", {}).get("adicionar_objeto", {})
            catalog_name = ARTIFICER_GEAR_CATALOG_NAMES[gear_id]
            catalog_data = CATALOGO_EQUIPAMENTOS[catalog_name]
            if (
                created.get("nome") != catalog_name
                or created.get("peso") != catalog_data.get("peso")
                or created.get("custo_po") != catalog_data.get("custo_po")
                or not created.get("id")
                or created.get("expira") != "proximo_descanso_longo"
                or result.get("delta_usos") != -1
            ):
                failures.append((gear_id, "metadados_ou_delta_incorretos", created))
        self.assertEqual(failures, [], f"Itens de Tinker's Magic sem criação funcional: {failures}")

    def test_tinkers_magic_runs_through_registered_rule_engine_and_returns_world_delta(self):
        from rule_engine.rules import build_default_engine

        engine = build_default_engine()
        result = engine.evaluate({
            "type": "class_feature",
            "classe": "artifice", "nivel": 1, "recurso": "tinkers_magic", "acao": "criar",
            "inteligencia": 16, "usos_gastos": 0,
            "ferramentas_de_funileiro_em_maos": True,
            "distancia_m": 1.5, "espaco_desocupado": True,
            "posicao_criacao": {"x": 2, "y": 4},
            "item": "corda", "item_id": "pc-1:tinker:1",
            "ids_objetos_existentes": ["pc-1", "npc-1"],
        })
        self.assertEqual(result.status, "resolved")
        self.assertIn("class.feature", result.matched_rules)
        outcome = result.outcome
        self.assertEqual(outcome["resultado"], "criado")
        self.assertEqual(outcome["delta_mundo"]["adicionar_objeto"]["id"], "pc-1:tinker:1")
        self.assertEqual(outcome["delta_mundo"]["adicionar_objeto"]["posicao"], {"x": 2, "y": 4})
        self.assertEqual(outcome["delta_usos"], -1)
        self.assertTrue(outcome["requer_id_unico_ao_persistir"])

    def test_tinkers_magic_rejects_world_object_id_collision(self):
        from rule_engine.class_features import resolver_caracteristica

        result = resolver_caracteristica({
            "classe": "artifice", "nivel": 1, "recurso": "tinkers_magic", "acao": "criar",
            "inteligencia": 16, "usos_gastos": 0,
            "ferramentas_de_funileiro_em_maos": True,
            "distancia_m": 1, "espaco_desocupado": True,
            "posicao_criacao": {"x": 1, "y": 1},
            "item": "corda", "item_id": "already-exists",
            "ids_objetos_existentes": ["already-exists"],
        })
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "id_do_objeto_ja_existe_no_mundo")

    def test_tinkers_magic_grants_repair_without_counting_it_as_a_selected_cantrip(self):
        from rule_engine.spellcasting import validar_escolhas_artifice, ARTIFICER_SPELL_LEVELS
        valid = validar_escolhas_artifice(
            1, 16, ["Bolha Ácida", "Luz"],
            ["Curar Ferimentos", "Detectar Magia"], {"1": 2},
        )
        self.assertEqual(valid["truques"], 2)
        self.assertNotIn("Consertar", ARTIFICER_SPELL_LEVELS)
        repair = resolver_caracteristica({
            "classe": "artifice", "recurso": "Magia de Artífice", "nivel": 1,
        })
        self.assertEqual(repair["truque_conhecido"], "Reparar")

    def test_every_level_one_artificer_spell_choice_has_an_executable_effect(self):
        from rule_engine.spellcasting import ARTIFICER_SPELL_LEVELS
        from rule_engine.spells import resolver_magia
        unsupported = []
        for name, circle in ARTIFICER_SPELL_LEVELS.items():
            if circle not in {0, 1}:
                continue
            result = resolver_magia({
                "magia": name,
                "has_slot": True,
                "espaco": circle,
                "nivel_personagem": 1,
            })
            if result.get("resultado") != "conjurada":
                unsupported.append((name, result.get("resultado"), result.get("motivo")))
        self.assertEqual(unsupported, [], f"Magias de nível 1 sem efeito executável: {unsupported}")

    def test_every_first_circle_artificer_spell_runs_through_class_feature_resolver(self):
        from rule_engine.class_features import resolver_caracteristica
        from rule_engine.spellcasting import ARTIFICER_SPELL_LEVELS

        failures = []
        first_level_spells = [
            name for name, circle in ARTIFICER_SPELL_LEVELS.items() if circle == 1
        ]
        for spell in first_level_spells:
            prepared = [spell, "Detectar Magia"]
            if spell == "Detectar Magia":
                prepared = ["Detectar Magia", "Curar Ferimentos"]
            facts = {
                "classe": "artifice", "nivel": 1, "recurso": "conjuracao", "acao": "conjurar",
                "magia": spell, "inteligencia": 16,
                "truques_conhecidos": ["Bolha Ácida", "Luz"],
                "magias_preparadas": prepared,
                "espacos_restantes": {"1": 2},
                "foco_conjuracao_em_maos": True,
                "foco_conjuracao": "Ferramentas de Funileiro",
                "ferramentas_de_funileiro_em_maos": True,
                "materiais_especiais_disponiveis": True,
                "gatilho_reacao_ocorrido": True,
                "reacao_disponivel": True,
                "componentes_disponiveis": ["V", "S", "M"],
            }
            result = resolver_caracteristica(facts)
            if result.get("resultado") != "conjurada" or not result.get("mecanica"):
                failures.append((spell, result.get("resultado"), result.get("motivo")))
        self.assertEqual(failures, [], f"Magias que falham na rota real do Artífice: {failures}")

    def test_tinkers_magic_granted_mending_cantrip_is_executable(self):
        from rule_engine.class_features import resolver_caracteristica
        from rule_engine.spells import resolver_magia

        # Reparar é concedido pela característica e não ocupa uma das duas escolhas.
        result = resolver_magia({
            "magia": "Reparar",
            "nivel_personagem": 1,
        })
        self.assertEqual(result.get("resultado"), "conjurada")
        self.assertEqual(result.get("circulo_base"), 0)
        self.assertTrue(result.get("mecanica"))

        feature = resolver_caracteristica({
            "classe": "artifice", "nivel": 1, "recurso": "tinkers_magic",
            "inteligencia": 16,
        })
        self.assertEqual(feature.get("resultado"), "resolvido")
        self.assertEqual(feature.get("truque_conhecido"), "Reparar")

    def test_artificer_can_cast_prepared_ritual_without_spending_a_slot(self):
        ritual = resolver_caracteristica({
            "classe": "artifice", "nivel": 1, "recurso": "conjuracao", "acao": "conjurar",
            "magia": "Alarme", "ritual": True, "inteligencia": 15,
            "truques_conhecidos": ["Bolha Ácida", "Luz"],
            "magias_preparadas": ["Alarme", "Detectar Magia"],
            "ferramentas_de_funileiro_em_maos": True,
            "foco_conjuracao_em_maos": True, "foco_conjuracao": "Ferramentas de Funileiro",
        })
        self.assertEqual(ritual["resultado"], "conjurada")
        self.assertTrue(ritual["ritual"])
        self.assertEqual(ritual["tempo_conjuracao_base"], "1_minuto")
        self.assertEqual(ritual["minutos_adicionais_ritual"], 10)
        self.assertIsNone(ritual["slot_consumido"])
        self.assertNotIn("delta_espacos", ritual)

        not_ritual = resolver_caracteristica({
            "classe": "artifice", "nivel": 1, "recurso": "conjuracao", "acao": "conjurar",
            "magia": "Fogo das Fadas", "ritual": True, "inteligencia": 15,
            "truques_conhecidos": ["Bolha Ácida", "Luz"],
            "magias_preparadas": ["Fogo das Fadas", "Detectar Magia"],
            "espacos_restantes": {"1": 2},
        })
        self.assertEqual(not_ritual["resultado"], "bloqueado")
        self.assertEqual(not_ritual["motivo"], "magia_nao_tem_tag_ritual")

    def test_level_one_artificer_rejects_more_slots_than_progression_allows(self):
        result = resolver_caracteristica({
            "classe": "artifice", "nivel": 1, "recurso": "conjuracao", "acao": "conjurar",
            "magia": "Curar Ferimentos", "inteligencia": 15,
            "truques_conhecidos": ["Bolha Ácida", "Luz"],
            "magias_preparadas": ["Curar Ferimentos", "Detectar Magia"],
            "espacos_restantes": {"1": 3},
        })
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "estado_de_espacos_restantes_invalido")

    def test_level_one_artificer_passos_longos_has_executable_mechanics(self):
        from rule_engine.spells import mecanica_de_magia, resolver_magia
        mechanic = mecanica_de_magia("Passos Longos")
        self.assertIsNotNone(mechanic)
        self.assertEqual(mechanic["tipo"], "buff_deslocamento")
        self.assertEqual(mechanic["bonus_deslocamento_m"], 3)
        cast = resolver_magia({"magia": "Passos Longos", "has_slot": True, "espaco": 1})
        self.assertEqual(cast["resultado"], "conjurada")
        self.assertEqual(cast["mecanica"]["bonus_deslocamento_m"], 3)

    def test_spell_storing_preserves_concentration_requirement(self):
        result = resolver_caracteristica({
            "classe": "artifice", "recurso": "Item Armazenador de Magia", "nivel": 11,
            "magia": "Teia", "nivel_magia": 2, "objeto_adequado": True,
            "descanso_longo_concluido": True, "distancia_m": 1,
            "tempo_conjuracao_acao": True,
        })
        self.assertEqual(result["resultado"], "armazenado")
        self.assertTrue(result["concentracao_requerida"])

    def test_spell_storing_rejects_non_action_spell_even_if_caller_claims_action(self):
        result = resolver_caracteristica({
            "classe": "artifice", "recurso": "Item Armazenador de Magia", "nivel": 11,
            "magia": "Retirada Acelerada", "nivel_magia": 1, "objeto_adequado": True,
            "descanso_longo_concluido": True, "distancia_m": 1,
            "tempo_conjuracao_acao": True,
        })
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "tempo_de_conjuracao_nao_e_uma_acao")

    def test_replicate_catalog_is_tiered_and_returns_item_metadata(self):
        level_2 = resolve_artificer_feature("replicar_item_magico", 2, {})
        level_6 = resolve_artificer_feature("replicar_item_magico", 6, {})
        level_10 = resolve_artificer_feature("replicar_item_magico", 10, {})
        level_14 = resolve_artificer_feature("replicar_item_magico", 14, {})
        self.assertEqual(len(level_2["planos_disponiveis"]), 16)
        self.assertEqual(len(level_6["planos_disponiveis"]), 38)
        self.assertEqual(len(level_10["planos_disponiveis"]), 49)
        self.assertEqual(len(level_14["planos_disponiveis"]), 56)
        self.assertIn("alchemy_jug", [p["id"] for p in level_2["planos_disponiveis"]])
        self.assertNotIn("armor_plus_1", [p["id"] for p in level_2["planos_disponiveis"]])
        self.assertIn("armor_plus_1", [p["id"] for p in level_6["planos_disponiveis"]])
        self.assertIn("armor_of_resistance", [p["id"] for p in level_10["planos_disponiveis"]])
        self.assertIn("ring_of_the_ram", [p["id"] for p in level_14["planos_disponiveis"]])

    def test_replicate_plan_milestones_add_a_new_plan(self):
        result = resolver_caracteristica({
            "classe": "artifice", "recurso": "Replicar Item Mágico", "nivel": 6,
            "acao": "aprender_plano", "ao_subir_de_nivel": True,
            "plano_novo": "armor_plus_1",
            "planos_conhecidos": ["alchemy_jug", "bag_of_holding", "cap_of_water_breathing", "wand_of_secrets"],
        })
        self.assertEqual(result["resultado"], "plano_aprendido")
        self.assertEqual(len(result["planos_conhecidos"]), 5)

    def test_replicate_plan_replacement_only_on_level_up(self):
        result = resolver_caracteristica({
            "classe": "artifice", "recurso": "Replicar Item Mágico", "nivel": 2,
            "acao": "substituir_plano", "plano_antigo": "alchemy_jug",
            "plano_novo": "goggles_of_night",
            "planos_conhecidos": ["alchemy_jug", "bag_of_holding", "cap_of_water_breathing", "wand_of_secrets"],
        })
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "planos_so_podem_ser_substituidos_ao_subir_de_nivel")

    def test_replicate_creation_replaces_oldest_when_at_capacity(self):
        result = resolver_caracteristica({
            "classe": "artifice", "recurso": "Replicar Item Mágico", "nivel": 2,
            "acao": "criar", "ferramentas_artesao_em_maos": True, "descanso_longo_concluido": True,
            "planos_conhecidos": ["alchemy_jug", "bag_of_holding", "cap_of_water_breathing", "wand_of_secrets"],
            "planos": ["alchemy_jug", "bag_of_holding"],
            "itens_atuais": [{"id": "old-item-1", "plano": "cap_of_water_breathing", "nome": "Bolsa antiga"}],
        })
        self.assertEqual(result["resultado"], "criado")
        self.assertEqual(result["itens_que_desaparecem"][0]["plano"], "cap_of_water_breathing")
        self.assertEqual(len(result["itens_atuais_apos_criacao"]), 2)

    def test_replicate_item_requires_artisan_tools_and_distinct_plans(self):
        missing_tools = resolver_caracteristica({
            "classe": "artifice", "recurso": "Replicar Item Mágico", "nivel": 2,
            "acao": "criar", "planos": ["plano_a"],
        })
        self.assertEqual(missing_tools["resultado"], "requer_dados")
        duplicate = resolver_caracteristica({
            "classe": "artifice", "recurso": "Replicar Item Mágico", "nivel": 2,
            "acao": "criar", "planos": ["plano_a", "plano_a"],
            "ferramentas_artesao_em_maos": True, "descanso_longo_concluido": True,
        })
        self.assertEqual(duplicate["motivo"], "cada_item_deve_usar_plano_diferente")

    def test_starting_equipment_is_a_choice_and_uses_selected_artisan_tool(self):
        character = criar_personagem({
            "character_id": "pc-artifice-test-1",
            "name": "Artífice de Teste", "species": "humano", "class": "artifice",
            "level": 1,
            "ability_scores": {"forca": 8, "destreza": 14, "constituicao": 13,
                               "inteligencia": 15, "sabedoria": 12, "carisma": 10},
            "class_skill_proficiencies": ["arcanismo", "investigacao"],
            "artisan_tool_proficiency": "Ferramentas de Ferreiro",
            "artificer_cantrips": ["Bolha Ácida", "Luz"],
            "artificer_prepared_spells": ["Curar Ferimentos", "Detectar Magia"],
            "class_equipment": "A",
        })
        sheet = ficha_personagem(character)
        self.assertEqual(sheet["equipamento_classe"]["escolha"], "A")
        self.assertEqual(
            sheet["equipamento_classe"]["itens"],
            ["Armadura de Couro Batido", "Adaga", "Ferramentas de Ladrão",
             "Ferramentas de Funileiro", "Pacote de Exploração de Masmorras"],
        )
        self.assertNotIn("Ferramentas de Ferreiro", sheet["equipamento_classe"]["itens"])
        self.assertIn("Ferramentas de Ferreiro", sheet["proficiencias_classe"]["ferramentas"])
        self.assertEqual(sheet["equipamento_classe"]["ouro"], 16)
        self.assertFalse(sheet["equipamento_classe_pendente"])
        self.assertEqual(sheet["conjuracao"]["truques_conhecidos"], ["Bolha Ácida", "Luz"])
        self.assertEqual(sheet["conjuracao"]["magias_preparadas"], ["Curar Ferimentos", "Detectar Magia"])
        self.assertEqual(sheet["conjuracao"]["espacos_totais"], {"1": 2})
        self.assertEqual(sheet["conjuracao"]["cd_magia"], 12)
        self.assertEqual(sheet["id"], "pc-artifice-test-1")
        self.assertEqual(sheet["classe_de_armadura"]["sem_armadura"], 12)
        self.assertEqual(sheet["classe_de_armadura"]["armadura_inicial"]["ca"], 14)
        self.assertFalse(sheet["classe_de_armadura"]["armadura_inicial"]["equipada_automaticamente"])
        self.assertEqual(sheet["recursos_iniciais"]["magia_de_artifice"]["usos_maximos"], 2)
        self.assertEqual(sheet["recursos_iniciais"]["espacos_de_magia"]["espacos_restantes"], {"1": 2})
        self.assertFalse(sheet["recursos_iniciais"]["troca_truque_disponivel"])
        inventory = sheet["inventario_inicial"]
        self.assertEqual(inventory["resultado"], "pronto")
        self.assertEqual(inventory["ouro"], 16)
        ids = [item["id"] for item in inventory["itens"]]
        self.assertEqual(len(ids), len(set(ids)))
        dagger = next(item for item in inventory["itens"] if item["nome"] == "Adaga")
        self.assertEqual(dagger["dano"], "1d4")
        armor = next(item for item in inventory["itens"] if item["nome"] == "Armadura de Couro Batido")
        self.assertEqual(armor["ca"], 12)
        pack = next(item for item in inventory["itens"] if item["nome"] == "Pacote de Exploração de Masmorras")
        self.assertEqual(len(pack["conteudo_ids"]), 9)
        self.assertAlmostEqual(inventory["peso_total"], 42.0)

    def test_artificer_attunement_limit_accepts_replicated_item_metadata(self):
        from rule_engine.economy import resolver_sintonizacao
        known = ["item_a", "item_b", "item_c"]
        metadata = {"nome": "Ferramenta Multiforme", "raridade": "incomum", "sintonizacao": True}
        result = resolver_sintonizacao({
            "item": "manifold_tool", "metadados_item": metadata,
            "sintonizados": known, "classe": "artifice", "nivel": 10,
        })
        self.assertEqual(result["resultado"], "sintonizado")
        self.assertEqual(result["limite"], 4)
        blocked = resolver_sintonizacao({
            "item": "wand_of_the_war_mage_plus_1",
            "metadados_item": {"nome": "Varinha do Mago de Guerra +1", "sintonizacao": True},
            "sintonizados": ["a", "b", "c", "d"], "classe": "artifice", "nivel": 10,
        })
        self.assertEqual(blocked["motivo"], "limite_de_itens_sintonizados")

    def test_inventory_resolver_adds_multiple_items_with_metadata_and_rejects_duplicate_ids(self):
        from rule_engine.economy import resolver_inventario

        added = resolver_inventario({
            "forca": 10,
            "itens": [{"id": "existing", "nome": "Corda", "peso": 2.5, "quantidade": 1}],
            "itens_novos": [
                {"id": "new-1", "nome": "Adaga", "peso": 0.5, "quantidade": 1, "dano": "1d4"},
                {"id": "new-2", "nome": "Tochas", "peso": 0.5, "quantidade": 4},
            ],
        })
        self.assertEqual(added["resultado"], "normal")
        self.assertAlmostEqual(added["peso"], 5.0)
        self.assertEqual(len(added["itens_adicionados"]), 2)
        self.assertEqual(next(x for x in added["itens"] if x["id"] == "new-1")["dano"], "1d4")

        duplicate = resolver_inventario({
            "itens": [{"id": "already", "nome": "Corda", "peso": 1}],
            "itens_novos": [
                {"id": "new", "nome": "Adaga", "peso": 0.5},
                {"id": "new", "nome": "Tocha", "peso": 0.5},
            ],
        })
        self.assertEqual(duplicate["resultado"], "bloqueado")
        self.assertEqual(duplicate["motivo"], "id_de_item_ja_existe")

    def test_artificer_initial_inventory_can_be_inserted_into_existing_inventory_engine(self):
        from rule_engine.economy import resolver_inventario

        character = criar_personagem({
            "character_id": "pc-artifice-inventory-engine",
            "name": "Artífice Inventário", "species": "humano", "class": "artifice", "level": 1,
            "ability_scores": {"forca": 8, "destreza": 14, "constituicao": 13,
                               "inteligencia": 15, "sabedoria": 12, "carisma": 10},
            "class_skill_proficiencies": ["arcanismo", "investigacao"],
            "artisan_tool_proficiency": "Ferramentas de Ferreiro",
            "artificer_cantrips": ["Bolha Ácida", "Luz"],
            "artificer_prepared_spells": ["Curar Ferimentos", "Detectar Magia"],
            "class_equipment": "A",
        })
        sheet = ficha_personagem(character)
        inventory = resolver_inventario({
            "forca": character.atributos["forca"],
            "itens": [],
            "itens_novos": sheet["inventario_inicial"]["itens"],
        })
        self.assertEqual(inventory["resultado"], "normal")
        self.assertEqual(len(inventory["itens"]), len(sheet["inventario_inicial"]["itens"]))
        self.assertAlmostEqual(inventory["peso"], sheet["inventario_inicial"]["peso_total"])
        self.assertTrue(all(item.get("id") and item.get("nome") and "peso" in item for item in inventory["itens"]))

    def test_rule_engine_creates_full_artificer_sheet_and_resolves_level_one_spell(self):
        from rule_engine.rules import build_default_engine

        engine = build_default_engine()
        created = engine.evaluate({
            "type": "character_creation",
            "character_id": "pc-artifice-engine-1",
            "name": "Artífice Engine",
            "species": "humano",
            "class": "artifice",
            "level": 1,
            "ability_scores": {"forca": 8, "destreza": 14, "constituicao": 13,
                               "inteligencia": 15, "sabedoria": 12, "carisma": 10},
            "class_skill_proficiencies": ["arcanismo", "investigacao"],
            "artisan_tool_proficiency": "Ferramentas de Ferreiro",
            "artificer_cantrips": ["Bolha Ácida", "Luz"],
            "artificer_prepared_spells": ["Curar Ferimentos", "Detectar Magia"],
            "class_equipment": "A",
        })
        self.assertEqual(created.status, "resolved")
        self.assertEqual(created.outcome["resultado"], "criado")
        sheet = created.outcome["ficha"]
        self.assertEqual(sheet["nivel"], 1)
        self.assertEqual(sheet["proficiencias_salvaguarda"], ["constituicao", "inteligencia"])
        self.assertEqual(sheet["conjuracao"]["espacos_totais"], {"1": 2})
        self.assertEqual(sheet["inventario_inicial"]["resultado"], "pronto")

        cast = engine.evaluate({
            "type": "class_feature",
            "classe": "artifice",
            "recurso": "conjuracao",
            "nivel": 1,
            "acao": "conjurar",
            "magia": "Curar Ferimentos",
            "inteligencia": 15,
            "truques_conhecidos": ["Bolha Ácida", "Luz"],
            "magias_preparadas": ["Curar Ferimentos", "Detectar Magia"],
            "espacos_restantes": {"1": 2},
        })
        self.assertEqual(cast.status, "resolved")
        self.assertIn("class.feature", cast.matched_rules)
        self.assertEqual(cast.outcome["resultado"], "conjurada")
        self.assertEqual(cast.outcome["slot_consumido"], 1)
        self.assertEqual(cast.outcome["delta_espacos"], {"1": -1})
        self.assertEqual(cast.outcome["espacos_restantes_depois"], {"1": 1})

    def test_artificer_can_swap_cantrip_and_prepared_spells_after_long_rest(self):
        from rule_engine.class_features import resolver_caracteristica

        base = {
            "classe": "artifice", "nivel": 1, "recurso": "conjuracao", "inteligencia": 15,
            "truques_conhecidos": ["Bolha Ácida", "Luz"],
            "magias_preparadas": ["Curar Ferimentos", "Detectar Magia"],
            "descanso_longo_concluido": True,
        }
        cantrip = resolver_caracteristica({
            **base, "acao": "trocar_truque", "troca_truque_disponivel": True,
            "truque_antigo": "Luz", "truque_novo": "Raio de Fogo",
        })
        self.assertEqual(cantrip["resultado"], "truque_substituido")
        self.assertEqual(cantrip["delta_conjuracao"]["truques_conhecidos"], ["Bolha Ácida", "Raio de Fogo"])
        self.assertFalse(cantrip["delta_conjuracao"]["troca_truque_disponivel"])

        prepared = resolver_caracteristica({
            **base, "acao": "trocar_magias_preparadas", "mudanca_magias_preparadas_disponivel": True,
            "magias_preparadas_novas": ["Fogo das Fadas", "Queda Suave"],
        })
        self.assertEqual(prepared["resultado"], "magias_preparadas_alteradas")
        self.assertEqual(prepared["delta_conjuracao"]["magias_preparadas"], ["Fogo das Fadas", "Queda Suave"])
        self.assertFalse(prepared["delta_conjuracao"]["mudanca_magias_preparadas_disponivel"])

        no_rest = resolver_caracteristica({
            **base, "acao": "trocar_truque", "descanso_longo_concluido": False,
            "troca_truque_disponivel": True, "truque_antigo": "Luz", "truque_novo": "Raio de Fogo",
        })
        self.assertEqual(no_rest["resultado"], "bloqueado")

    def test_drain_item_uses_rarity_and_is_bonus_action(self):
        result = resolver_caracteristica({
            "classe": "artifice", "recurso": "Ajustador de Item Mágico", "nivel": 6,
            "acao": "drenar", "item_replicado": True, "item_id": "replica-1", "distancia_m": 1, "usado_no_descanso_longo": False,
            "raridade": "raro",
        })
        self.assertEqual(result["resultado"], "drenado")
        self.assertEqual(result["nivel_espaco_recuperado"], 2)
        self.assertEqual(result["acao"], "acao_bonus")


if __name__ == "__main__":
    unittest.main()
