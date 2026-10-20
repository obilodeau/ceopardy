# Ceopardy
# https://github.com/obilodeau/ceopardy/
#
# Olivier Bilodeau <olivier@bottomlesspit.org>
# Copyright (C) 2026 Olivier Bilodeau
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
"""
Tests for what the tunnelled buzzer port serves. Werkzeug's test client
against the bare WSGI app: no Flask app, no database, no socket.
"""

import json

import pytest
from werkzeug.test import Client

from ceopardy.buzzer import FairnessSettings
from ceopardy.buzzer_server import BuzzerServer, entry_files, origin_allowed

MANIFEST = {
    "buzzer.html": {
        "file": "assets/buzzer-B1.js",
        "src": "buzzer.html",
        "isEntry": True,
        "imports": ["_vue-V1.js"],
        "css": ["assets/buzzer-C1.css"],
    },
    "_vue-V1.js": {"file": "assets/vue-V1.js", "imports": ["_vue-V1.js"]},
    "index.html": {
        "file": "assets/main-M1.js",
        "src": "index.html",
        "isEntry": True,
        "imports": ["_vue-V1.js"],
        "css": ["assets/main-C2.css"],
    },
}


def test_entry_files_follows_imports_and_skips_other_entries():
    assert entry_files(MANIFEST) == {
        "assets/buzzer-B1.js",
        "assets/buzzer-C1.css",
        "assets/vue-V1.js",
    }


@pytest.fixture
def dist(tmp_path):
    (tmp_path / ".vite").mkdir()
    (tmp_path / ".vite" / "manifest.json").write_text(json.dumps(MANIFEST))
    (tmp_path / "assets").mkdir()
    for name in ("buzzer-B1.js", "buzzer-C1.css", "vue-V1.js", "main-M1.js", "main-C2.css"):
        (tmp_path / "assets" / name).write_text("/* {} */".format(name))
    (tmp_path / "buzzer.html").write_text("<!doctype html><title>Buzzer</title>")
    (tmp_path / "index.html").write_text("<!doctype html><title>Host and viewer</title>")
    return tmp_path


def make_client(dist_dir) -> Client:
    server = BuzzerServer(
        FairnessSettings(),
        tokens=lambda: {},
        team_names=lambda: {},
        on_decision=lambda decision: None,
        on_presence=lambda counts: None,
    )
    return Client(server.wsgi_app(str(dist_dir)))


def test_root_serves_the_buzzer_page_with_security_headers(dist):
    res = make_client(dist).get("/")
    assert res.status_code == 200
    assert b"Buzzer" in res.data
    assert res.headers["Content-Type"].startswith("text/html")
    assert "frame-ancestors 'none'" in res.headers["Content-Security-Policy"]
    assert res.headers["Referrer-Policy"] == "no-referrer"
    assert res.headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.parametrize(
    "path", ["/assets/buzzer-B1.js", "/assets/buzzer-C1.css", "/assets/vue-V1.js"]
)
def test_buzzer_page_files_are_served(dist, path):
    assert make_client(dist).get(path).status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/index.html",
        "/host",
        "/start",
        "/viewer",
        "/api/v1/state",
        "/api/v1/question/select",
        "/api/v1/buzzers/links",
        "/socket.io/",
        "/static/sounds/buzzer1.wav",
        "/assets/main-M1.js",
        "/assets/main-C2.css",
        "/assets/",
        "/.vite/manifest.json",
        "/buzzer.html/../index.html",
        "/assets/buzzer-B1.js/../main-M1.js",
        "/assets/../index.html",
    ],
)
def test_everything_else_is_not_found(dist, path):
    res = make_client(dist).get(path)
    assert res.status_code == 404
    assert "Content-Security-Policy" in res.headers


def test_only_get_and_head(dist):
    assert make_client(dist).post("/").status_code == 404


def test_unbuilt_front_end_says_so(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/").status_code == 503
    assert client.get("/assets/buzzer-B1.js").status_code == 404


ENVIRON = {"wsgi.url_scheme": "http", "HTTP_HOST": "127.0.0.1:5001"}
NGROK_ENVIRON = {
    "wsgi.url_scheme": "http",
    "HTTP_HOST": "quiet-owl.ngrok-free.app",
    "HTTP_X_FORWARDED_PROTO": "https",
}


@pytest.mark.parametrize(
    "origin,environ,public_url,allowed",
    [
        ("http://127.0.0.1:5001", ENVIRON, "", True),
        ("https://quiet-owl.ngrok-free.app", NGROK_ENVIRON, "", True),
        ("http://localhost:5173", ENVIRON, "http://localhost:5173/buzzer.html", True),
        ("https://evil.example", ENVIRON, "", False),
        ("https://evil.example", NGROK_ENVIRON, "https://quiet-owl.ngrok-free.app", False),
        ("http://localhost:5173", ENVIRON, "", False),
        (None, ENVIRON, "", False),
    ],
)
def test_origin_allowed(origin, environ, public_url, allowed):
    assert origin_allowed(origin, environ, public_url) is allowed
