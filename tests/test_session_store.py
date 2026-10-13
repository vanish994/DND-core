"""Testes dos backends usados para retomar encontros entre reinícios."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dungeon_game.session_store import (
    MemorySessionStore,
    SQLiteSessionStore,
    SessionStoreError,
    criar_session_store,
)


class SessionStoreTests(unittest.TestCase):
    def test_memoria_faz_round_trip_sem_compartilhar_objetos_mutaveis(self):
        store = MemorySessionStore()
        original = {"ficha": {"pv": 9}, "posicoes": {"bardo": [1, 2]}}
        store.save("sessao-1", original)
        restaurado = store.load("sessao-1")
        self.assertEqual(restaurado, original)
        self.assertIsNot(restaurado, original)
        self.assertIsNot(restaurado["ficha"], original["ficha"])

    def test_sqlite_preserva_estado_apos_recriar_store(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "sessions.sqlite3"
            SQLiteSessionStore(caminho).save("sessao-2", {"turno": 3, "pv": 12})
            store_recriado = SQLiteSessionStore(caminho)
            self.assertEqual(store_recriado.load("sessao-2"), {"turno": 3, "pv": 12})

    def test_store_padrao_sem_ambiente_e_memoria(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsInstance(criar_session_store(), MemorySessionStore)

    def test_store_sqlite_pode_ser_selecionado_por_ambiente(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = str(Path(diretorio) / "sessions.sqlite3")
            with patch.dict("os.environ", {"DND_CORE_DATABASE": caminho}, clear=True):
                self.assertIsInstance(criar_session_store(), SQLiteSessionStore)

    def test_deploy_com_persistencia_obrigatoria_falha_sem_banco(self):
        with patch.dict("os.environ", {"DND_REQUIRE_PERSISTENCE": "true"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "exige DATABASE_URL"):
                criar_session_store()

    def test_snapshot_nao_json_e_recusado(self):
        store = MemorySessionStore()
        with self.assertRaises(SessionStoreError):
            store.save("sessao-3", {"pv": object()})


if __name__ == "__main__":
    unittest.main()
