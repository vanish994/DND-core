"""Inicia a interface local com o servidor WSGI da biblioteca padrão."""

from __future__ import annotations

import os
from wsgiref.simple_server import make_server

from .web import create_app


def main() -> None:
    host = os.environ.get("DND_CORE_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", os.environ.get("DND_CORE_PORT", "8000")))
    app = create_app()
    print(f"Criador D&D disponível em http://{host}:{port}")
    with make_server(host, port, app) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
