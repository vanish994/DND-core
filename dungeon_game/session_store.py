"""Armazenamento de snapshots de encontros para desenvolvimento e hospedagem.

Sem configuração, o jogo usa memória (modo local). Em hospedagem, configure
DATABASE_URL para PostgreSQL ou DND_CORE_DATABASE para um SQLite em disco
persistente. Nunca há fallback silencioso para memória quando persistência é
exigida explicitamente.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Protocol

_TABELA = "dnd_core_combat_sessions"


class SessionStoreError(RuntimeError):
    """Falha segura de leitura/gravação de uma sessão persistente."""


class SessionStore(Protocol):
    def load(self, session_id: str) -> dict[str, Any] | None: ...

    def save(self, session_id: str, state: dict[str, Any]) -> None: ...

    def ping(self) -> None: ...


class MemorySessionStore:
    """Armazenamento efêmero destinado a desenvolvimento e testes."""

    def __init__(self) -> None:
        self._states: dict[str, str] = {}

    def load(self, session_id: str) -> dict[str, Any] | None:
        payload = self._states.get(session_id)
        return None if payload is None else _decode(payload)

    def save(self, session_id: str, state: dict[str, Any]) -> None:
        self._states[session_id] = _encode(state)

    def ping(self) -> None:
        return None


class SQLiteSessionStore:
    """SQLite local; em hospedagem, o arquivo deve estar em volume persistente."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute(
                    f"CREATE TABLE IF NOT EXISTS {_TABELA} ("
                    "session_id TEXT PRIMARY KEY, state_json TEXT NOT NULL, "
                    "updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
                )
        except sqlite3.Error as error:
            raise SessionStoreError("Não foi possível inicializar o armazenamento SQLite") from error

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path, timeout=10)

    def load(self, session_id: str) -> dict[str, Any] | None:
        try:
            with closing(self._connect()) as connection, connection:
                row = connection.execute(
                    f"SELECT state_json FROM {_TABELA} WHERE session_id = ?", (session_id,)
                ).fetchone()
        except sqlite3.Error as error:
            raise SessionStoreError("Não foi possível ler a sessão SQLite") from error
        return None if row is None else _decode(row[0])

    def save(self, session_id: str, state: dict[str, Any]) -> None:
        payload = _encode(state)
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute(
                    f"INSERT INTO {_TABELA} (session_id, state_json) VALUES (?, ?) "
                    "ON CONFLICT(session_id) DO UPDATE SET "
                    "state_json = excluded.state_json, updated_at = CURRENT_TIMESTAMP",
                    (session_id, payload),
                )
        except sqlite3.Error as error:
            raise SessionStoreError("Não foi possível gravar a sessão SQLite") from error

    def ping(self) -> None:
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute("SELECT 1").fetchone()
        except sqlite3.Error as error:
            raise SessionStoreError("O armazenamento SQLite não está disponível") from error


class PostgresSessionStore:
    """PostgreSQL gerenciado (por exemplo, Neon) usando psycopg 3."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        try:
            with self._connect() as connection:
                connection.execute(
                    f"CREATE TABLE IF NOT EXISTS {_TABELA} ("
                    "session_id TEXT PRIMARY KEY, state_json TEXT NOT NULL, "
                    "updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
                )
        except Exception as error:
            raise SessionStoreError("Não foi possível inicializar o armazenamento PostgreSQL") from error

    def _connect(self):
        try:
            import psycopg
        except ImportError as error:
            raise SessionStoreError("Instale psycopg para usar DATABASE_URL PostgreSQL") from error
        return psycopg.connect(self.database_url, connect_timeout=10)

    def load(self, session_id: str) -> dict[str, Any] | None:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    f"SELECT state_json FROM {_TABELA} WHERE session_id = %s", (session_id,)
                ).fetchone()
        except Exception as error:
            raise SessionStoreError("Não foi possível ler a sessão PostgreSQL") from error
        return None if row is None else _decode(row[0])

    def save(self, session_id: str, state: dict[str, Any]) -> None:
        payload = _encode(state)
        try:
            with self._connect() as connection:
                connection.execute(
                    f"INSERT INTO {_TABELA} (session_id, state_json, updated_at) VALUES (%s, %s, NOW()) "
                    "ON CONFLICT(session_id) DO UPDATE SET "
                    "state_json = EXCLUDED.state_json, updated_at = NOW()",
                    (session_id, payload),
                )
        except Exception as error:
            raise SessionStoreError("Não foi possível gravar a sessão PostgreSQL") from error

    def ping(self) -> None:
        try:
            with self._connect() as connection:
                connection.execute("SELECT 1").fetchone()
        except Exception as error:
            raise SessionStoreError("O armazenamento PostgreSQL não está disponível") from error


def criar_session_store() -> SessionStore:
    """Escolhe o armazenamento por ambiente sem expor nem registrar credenciais."""
    database_url = os.environ.get("DATABASE_URL", "").strip()
    sqlite_path = os.environ.get("DND_CORE_DATABASE", "").strip()
    exige_persistencia = os.environ.get("DND_REQUIRE_PERSISTENCE", "").lower() in {"1", "true", "yes"}

    if database_url.startswith("sqlite:///"):
        sqlite_url_path = database_url.removeprefix("sqlite:///")
        return MemorySessionStore() if sqlite_url_path == ":memory:" else SQLiteSessionStore(sqlite_url_path)
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = "postgresql://" + database_url.removeprefix("postgres://")
        return PostgresSessionStore(database_url)
    if sqlite_path:
        return MemorySessionStore() if sqlite_path == ":memory:" else SQLiteSessionStore(sqlite_path)
    if exige_persistencia:
        raise RuntimeError("DND_REQUIRE_PERSISTENCE exige DATABASE_URL ou DND_CORE_DATABASE")
    return MemorySessionStore()


def _encode(state: dict[str, Any]) -> str:
    try:
        return json.dumps(state, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise SessionStoreError("O estado do encontro não pode ser serializado") from error


def _decode(payload: str) -> dict[str, Any]:
    try:
        state = json.loads(payload)
    except (TypeError, ValueError) as error:
        raise SessionStoreError("O snapshot do encontro está inválido") from error
    if not isinstance(state, dict):
        raise SessionStoreError("O snapshot do encontro tem formato inválido")
    return state
