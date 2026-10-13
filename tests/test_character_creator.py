from __future__ import annotations

import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from wsgiref.util import setup_testing_defaults

from character_creator.service import CharacterCreatorService, CharacterStore, PersistenceError
from character_creator.web import CharacterCreatorApplication, create_app
from rule_engine.character import gerar_atributos_matriz_padrao


def valid_fighter_payload() -> dict:
    return {
        "name": "Alda Martelo",
        "class": "guerreiro",
        "species": "anao",
        "background": "fazendeiro",
        "ravenloft": False,
        "ability_method": "standard_array",
        "ability_scores": gerar_atributos_matriz_padrao(),
        "background_increases": {"constituicao": 2, "sabedoria": 1},
        "background_equipment": "A",
        "class_skills": ["atletismo", "percepcao"],
        "class_choices": {"estilo_de_luta": "defensivo"},
        "spells": {"cantrips": [], "selected": [], "spellbook": []},
        "narrative": {"pronouns": "ela/dela", "appearance": "Cicatriz na sobrancelha."},
    }


def call_wsgi(app, path="/", method="GET", payload=None, content_type="application/json"):
    environ = {}
    setup_testing_defaults(environ)
    environ["PATH_INFO"] = path
    environ["REQUEST_METHOD"] = method
    body = b"" if payload is None else (payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8"))
    environ["wsgi.input"] = BytesIO(body)
    environ["CONTENT_LENGTH"] = str(len(body))
    environ["CONTENT_TYPE"] = content_type
    response = {}

    def start_response(status, headers):
        response["status"] = status
        response["headers"] = dict(headers)

    response["body"] = b"".join(app(environ, start_response))
    return response


class FailingStore:
    def save(self, record):
        raise PersistenceError("Falha simulada de gravação.")


class CharacterCreatorServiceTests(unittest.TestCase):
    def test_preview_validates_and_does_not_persist(self):
        with tempfile.TemporaryDirectory() as directory:
            store = CharacterStore(Path(directory) / "characters.sqlite3")
            service = CharacterCreatorService(store)
            result = service.preview(valid_fighter_payload())
            self.assertTrue(result["ready"], result)
            self.assertEqual(result["validation"]["character_creation"]["status"], "resolved")
            self.assertEqual(result["validation"]["persistence"], "not_attempted")
            self.assertEqual(store.list(), [])

    def test_create_confirms_persistence_only_after_store_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            store = CharacterStore(Path(directory) / "characters.sqlite3")
            service = CharacterCreatorService(store)
            record = service.create(valid_fighter_payload())
            self.assertEqual(record["validation"]["persistence"], "confirmed")
            self.assertEqual(store.get(record["id"])["validation"]["persistence"], "confirmed")
            self.assertEqual(store.list()[0]["id"], record["id"])
            self.assertEqual(record["character"]["nome"], "Alda Martelo")

    def test_invalid_score_values_return_a_domain_issue_instead_of_crashing(self):
        payload = valid_fighter_payload()
        payload["ability_method"] = "point_buy"
        payload["ability_scores"] = {"forca": 20, "destreza": 14, "constituicao": 13, "inteligencia": 12, "sabedoria": 10, "carisma": 8}
        result = CharacterCreatorService().preview(payload)
        self.assertFalse(result["ready"])
        self.assertTrue(any(item["field"] == "ability_scores" for item in result["missing"]))

    def test_malformed_nested_choices_are_reported_not_raised(self):
        payload = valid_fighter_payload()
        payload["class"] = "ladino"
        payload["class_skills"] = [{"unexpected": "object"}] * 4
        payload["expertise"] = [{"unexpected": "object"}, {"unexpected": "object"}]
        result = CharacterCreatorService().preview(payload)
        self.assertFalse(result["ready"])
        self.assertTrue(result["missing"])

    def test_artificer_profile_exposes_partial_coverage_and_spell_limits(self):
        service = CharacterCreatorService()
        profile = service.preview({"class": "artifice"})["profile"]
        spellcasting = profile["spellcasting"]
        self.assertTrue(spellcasting["supported"])
        self.assertEqual(spellcasting["cantrips"], 2)
        self.assertTrue(spellcasting["catalog"])
        self.assertEqual(len(profile["artificer_coverage"]["spell_progression"]), 20)
        self.assertIn("Artífice", profile["artificer_coverage"]["source_note"])
        self.assertIn("catálogo/validação das infusões", profile["artificer_coverage"]["source_note"])
        self.assertEqual(
            {item["label"] for item in profile["artificer_coverage"]["unlinked_subclass_spell_tables"]},
            {"Armeiro", "Artilheiro", "Alquimista", "Ferreiro de Batalha", "Cartógrafo"},
        )
        infusion = next(item for item in profile["artificer_coverage"]["coverage"] if item["feature"] == "Replicar Item Mágico")
        self.assertEqual(infusion["status"], "partial")
        self.assertIn("não tem catálogo", profile["artificer_coverage"]["infusion_note"])

    def test_artificer_spell_choices_are_validated_and_saved_with_explicit_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            service = CharacterCreatorService(CharacterStore(Path(directory) / "characters.sqlite3"))
            payload = {
                "name": "Nima Cobre",
                "class": "artifice",
                "species": "anao",
                "background": "artesao",
                "ravenloft": False,
                "ability_method": "standard_array",
                "ability_scores": gerar_atributos_matriz_padrao(),
                "background_increases": {"inteligencia": 2, "destreza": 1},
                "background_tool": "Ferramentas de Carpinteiro",
                "background_equipment": "A",
                "class_skills": ["arcanismo", "historia"],
                "artisan_tool_proficiency": "Ferramentas de Ferreiro",
            }
            profile = service.preview(payload)["profile"]
            spell_profile = profile["spellcasting"]
            payload["spells"] = {
                "cantrips": [spell["name"] for spell in spell_profile["catalog"] if spell["circle"] == 0][: spell_profile["cantrips"]],
                "selected": [spell["name"] for spell in spell_profile["catalog"] if spell["circle"] == 1][: spell_profile["spells"]],
                "spellbook": [],
            }
            preview = service.preview(payload)
            self.assertTrue(preview["ready"], preview)
            self.assertTrue(preview["validation"]["spell_choices"]["details"]["validated"])
            self.assertEqual(preview["completeness"], "limited_by_engine_coverage")
            record = service.create(payload)
            self.assertEqual(record["validation"]["persistence"], "confirmed")
            self.assertEqual(record["choices"]["spells"]["validated"], True)
            self.assertTrue(any(item["kind"] == "artificer" for item in record["warnings"]))

    def test_character_creation_accepts_species_resolved_outside_legacy_creation_facts(self):
        payload = valid_fighter_payload()
        payload.update(
            {
                "species": "elfo",
                "species_choice": "alto_elfo",
                "species_skill": "intuicao",
                "size": "medio",
            }
        )
        payload["class_skills"] = ["atletismo", "percepcao"]
        result = CharacterCreatorService().preview(payload)
        self.assertTrue(result["ready"], result)
        self.assertEqual(result["choices"]["species_choice"], "alto_elfo")
        self.assertEqual(result["character"]["especie"], "elfo")

    def test_create_propagates_persistence_failure_without_a_created_record(self):
        service = CharacterCreatorService(FailingStore())
        with self.assertRaisesRegex(PersistenceError, "Falha simulada"):
            service.create(valid_fighter_payload())


class CharacterCreatorHttpTests(unittest.TestCase):
    def test_static_and_catalog_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(database_path=Path(directory) / "characters.sqlite3")
            page = call_wsgi(app, "/")
            self.assertTrue(page["status"].startswith("200"))
            self.assertIn(b"Ateli\xc3\xaa de Her\xc3\xb3is", page["body"])
            self.assertIn("Content-Security-Policy", page["headers"])
            catalog = call_wsgi(app, "/api/catalog")
            self.assertTrue(catalog["status"].startswith("200"))
            data = json.loads(catalog["body"])
            self.assertEqual(len(data["classes"]), 13)
            self.assertIn("assignment", data["score_methods"]["standard_array"])
            image = call_wsgi(app, "/static/atelier.jpg")
            self.assertTrue(image["status"].startswith("200"))
            self.assertTrue(image["headers"]["Content-Type"].startswith("image/jpeg"))

    def test_http_creation_returns_201_after_persistence_and_supports_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(database_path=Path(directory) / "characters.sqlite3")
            response = call_wsgi(app, "/api/characters", "POST", valid_fighter_payload())
            self.assertTrue(response["status"].startswith("201"), response)
            created = json.loads(response["body"])
            self.assertEqual(created["validation"]["persistence"], "confirmed")
            fetched = call_wsgi(app, f"/api/characters/{created['id']}")
            self.assertTrue(fetched["status"].startswith("200"))
            self.assertEqual(json.loads(fetched["body"])["id"], created["id"])
            listing = call_wsgi(app, "/api/characters")
            self.assertEqual(len(json.loads(listing["body"])["items"]), 1)

    def test_http_refuses_creation_when_database_write_fails(self):
        app = CharacterCreatorApplication(CharacterCreatorService(FailingStore()))
        response = call_wsgi(app, "/api/characters", "POST", valid_fighter_payload())
        self.assertTrue(response["status"].startswith("503"))
        self.assertIn("Falha simulada", json.loads(response["body"])["error"])

    def test_http_rejects_malformed_json_without_calling_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(database_path=Path(directory) / "characters.sqlite3")
            response = call_wsgi(app, "/api/preview", "POST", b"{not json")
            self.assertTrue(response["status"].startswith("400"))
            self.assertIn("JSON UTF-8 válido", json.loads(response["body"])["error"])


if __name__ == "__main__":
    unittest.main()
