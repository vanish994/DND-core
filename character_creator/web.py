"""Aplicação WSGI leve para o criador de personagens e sua API JSON."""

from __future__ import annotations

import json
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import unquote, urlsplit

from .service import CharacterCreatorService, CharacterStore, CreationError, PersistenceError

LOGGER = logging.getLogger(__name__)
PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"
MAX_REQUEST_BYTES = 1_000_000


class CharacterCreatorApplication:
    """WSGI app com rotas próprias, sem dependências externas de servidor."""

    def __init__(self, service: CharacterCreatorService):
        self.service = service

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> Iterable[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = unquote(urlsplit(str(environ.get("PATH_INFO", "/"))).path)
        try:
            status, payload, content_type, cache_control = self._dispatch(method, path, environ)
        except CreationError as exc:
            status, payload, content_type, cache_control = (
                422,
                {"error": str(exc), "field": exc.field},
                "application/json; charset=utf-8",
                "no-store",
            )
        except PersistenceError as exc:
            status, payload, content_type, cache_control = (
                503,
                {"error": str(exc), "field": "persistence"},
                "application/json; charset=utf-8",
                "no-store",
            )
        except _HttpError as exc:
            status, payload, content_type, cache_control = (
                exc.status,
                {"error": str(exc)},
                "application/json; charset=utf-8",
                "no-store",
            )
        except Exception:
            LOGGER.exception("Falha não tratada na aplicação de criação de personagens")
            status, payload, content_type, cache_control = (
                500,
                {"error": "Ocorreu uma falha inesperada. O rascunho permanece neste dispositivo; tente novamente."},
                "application/json; charset=utf-8",
                "no-store",
            )

        if content_type.startswith("application/json"):
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        elif isinstance(payload, bytes):
            body = payload
        else:
            body = str(payload).encode("utf-8")
        reason = _STATUS_TEXT.get(status, "Unknown")
        headers = [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
            ("Cache-Control", cache_control),
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "SAMEORIGIN"),
            ("Referrer-Policy", "same-origin"),
        ]
        if content_type.startswith("text/html"):
            headers.append(
                (
                    "Content-Security-Policy",
                    "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
                    "connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'",
                )
            )
        start_response(f"{status} {reason}", headers)
        if method == "HEAD":
            return [b""]
        return [body]

    def _dispatch(self, method: str, path: str, environ: dict[str, Any]) -> tuple[int, Any, str, str]:
        json_type = "application/json; charset=utf-8"
        if path == "/" and method in {"GET", "HEAD"}:
            return self._static("index.html", "text/html; charset=utf-8")
        if path.startswith("/static/") and method in {"GET", "HEAD"}:
            name = path.removeprefix("/static/")
            if "/" in name or "\\" in name or name in {"", ".", ".."}:
                return self._json_error(404, "Arquivo não encontrado.")
            return self._static(name)

        if path == "/api/health" and method in {"GET", "HEAD"}:
            return 200, self.service.health(), json_type, "no-store"
        if path == "/api/catalog" and method in {"GET", "HEAD"}:
            return 200, self.service.catalog(), json_type, "private, max-age=60"
        if path == "/api/score-preview" and method == "POST":
            return 200, self.service.score_preview(self._read_json(environ)), json_type, "no-store"
        if path == "/api/preview" and method == "POST":
            return 200, self.service.preview(self._read_json(environ)), json_type, "no-store"
        if path == "/api/characters" and method == "POST":
            return 201, self.service.create(self._read_json(environ)), json_type, "no-store"
        if path == "/api/characters" and method in {"GET", "HEAD"}:
            if self.service.store is None:
                raise PersistenceError("O serviço de persistência não está configurado.")
            return 200, {"items": self.service.store.list()}, json_type, "no-store"
        if path.startswith("/api/characters/") and method in {"GET", "HEAD"}:
            if self.service.store is None:
                raise PersistenceError("O serviço de persistência não está configurado.")
            character_id = path.removeprefix("/api/characters/")
            if not character_id or "/" in character_id or "\\" in character_id:
                return self._json_error(404, "Ficha não encontrada.")
            record = self.service.store.get(character_id)
            if record is None:
                return self._json_error(404, "Ficha não encontrada.")
            return 200, record, json_type, "no-store"

        if path.startswith("/api/"):
            return self._json_error(404, "Rota da API não encontrada.")
        if method not in {"GET", "HEAD"}:
            return 405, {"error": "Método não permitido."}, json_type, "no-store"
        return self._json_error(404, "Página não encontrada.")

    def _read_json(self, environ: dict[str, Any]) -> dict[str, Any]:
        content_type = str(environ.get("CONTENT_TYPE", "")).split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise _HttpError(415, "Envie o corpo como application/json.")
        try:
            length = int(environ.get("CONTENT_LENGTH") or "0")
        except (TypeError, ValueError) as exc:
            raise _HttpError(400, "O tamanho da solicitação é inválido.") from exc
        if length < 0:
            raise _HttpError(400, "O tamanho da solicitação é inválido.")
        if length > MAX_REQUEST_BYTES:
            raise _HttpError(413, "O rascunho excede o limite de 1 MB.")
        stream = environ.get("wsgi.input")
        if stream is None:
            raise _HttpError(400, "O corpo JSON está ausente.")
        try:
            raw = stream.read(length)
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _HttpError(400, "O corpo precisa ser um JSON UTF-8 válido.") from exc
        if not isinstance(payload, dict):
            raise _HttpError(400, "O corpo JSON precisa ser um objeto.")
        return payload

    def _static(self, name: str, forced_type: str | None = None) -> tuple[int, bytes, str, str]:
        candidate = (STATIC_DIR / name).resolve()
        if not candidate.is_relative_to(STATIC_DIR.resolve()) or not candidate.is_file():
            return self._json_error(404, "Arquivo não encontrado.")
        content_type = forced_type or mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "image/svg+xml"}:
            content_type += "; charset=utf-8"
        return 200, candidate.read_bytes(), content_type, "public, max-age=300"

    @staticmethod
    def _json_error(status: int, message: str) -> tuple[int, dict[str, str], str, str]:
        return status, {"error": message}, "application/json; charset=utf-8", "no-store"


class _HttpError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def create_app(
    service: CharacterCreatorService | None = None,
    *,
    database_path: str | Path | None = None,
) -> CharacterCreatorApplication:
    """Constrói a aplicação; caminhos de banco podem ser injetados em testes."""
    if service is None:
        path = database_path or os.environ.get("DND_CORE_DATABASE", "data/characters.sqlite3")
        service = CharacterCreatorService(CharacterStore(path))
    return CharacterCreatorApplication(service)


_STATUS_TEXT = {
    200: "OK",
    201: "Created",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    413: "Payload Too Large",
    415: "Unsupported Media Type",
    422: "Unprocessable Entity",
    500: "Internal Server Error",
    503: "Service Unavailable",
}
