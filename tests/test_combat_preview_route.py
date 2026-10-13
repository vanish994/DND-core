from __future__ import annotations

from io import BytesIO
from wsgiref.util import setup_testing_defaults

from character_creator.web import create_app


def request(app, path: str):
    environ = {}
    setup_testing_defaults(environ)
    environ["PATH_INFO"] = path
    environ["REQUEST_METHOD"] = "GET"
    environ["wsgi.input"] = BytesIO(b"")
    environ["CONTENT_LENGTH"] = "0"
    response = {}

    def start_response(status, headers):
        response["status"] = status
        response["headers"] = dict(headers)

    response["body"] = b"".join(app(environ, start_response))
    return response


def test_combat_preview_route_serves_own_interface():
    response = request(create_app(), "/combat-preview")
    assert response["status"].startswith("200")
    assert response["headers"]["Content-Type"].startswith("text/html")
    assert b"action-dock" in response["body"]
    assert b"Magias" in response["body"]


def test_combat_preview_assets_are_served_as_static_files():
    app = create_app()
    css = request(app, "/static/combat.css")
    js = request(app, "/static/combat.js")
    assert css["status"].startswith("200")
    assert b"position:fixed" in css["body"]
    assert js["status"].startswith("200")
    assert b"function choose" in js["body"]
