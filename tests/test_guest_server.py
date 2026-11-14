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
Tests for what the tunnelled guest port serves. Werkzeug's test client
against the bare WSGI app, and the Socket.IO handlers called directly with a
recorder in place of the socket: no Flask app, no database, no socket.
"""

import json
import socket
from collections.abc import Callable

import pytest
import socketio
from werkzeug.test import Client

from ceopardy.buzzer import BuzzArbiter, BuzzOutcome, Decision, Entry, FairnessSettings
from ceopardy.guest.buzzers import BUZZ_NS, BuzzersPage
from ceopardy.guest.server import GuestServer, entry_files, origin_allowed
from ceopardy.guest.soundboard import SOUNDBOARD_NS, SoundboardPage

MANIFEST = {
    "buzzer.html": {
        "file": "assets/buzzer-B1.js",
        "src": "buzzer.html",
        "isEntry": True,
        "imports": ["_vue-V1.js"],
        "css": ["assets/buzzer-C1.css"],
    },
    "_vue-V1.js": {"file": "assets/vue-V1.js", "imports": ["_vue-V1.js"]},
    "soundboard.html": {
        "file": "assets/soundboard-S1.js",
        "src": "soundboard.html",
        "isEntry": True,
        "imports": ["_vue-V1.js"],
        "css": ["assets/soundboard-C3.css"],
    },
    "index.html": {
        "file": "assets/main-M1.js",
        "src": "index.html",
        "isEntry": True,
        "imports": ["_vue-V1.js"],
        "css": ["assets/main-C2.css"],
    },
}


def test_entry_files_follows_imports_and_skips_other_entries():
    assert entry_files(MANIFEST, "buzzer.html") == {
        "assets/buzzer-B1.js",
        "assets/buzzer-C1.css",
        "assets/vue-V1.js",
    }


@pytest.fixture
def dist(tmp_path):
    (tmp_path / ".vite").mkdir()
    (tmp_path / ".vite" / "manifest.json").write_text(json.dumps(MANIFEST))
    (tmp_path / "assets").mkdir()
    for name in (
        "buzzer-B1.js",
        "buzzer-C1.css",
        "vue-V1.js",
        "main-M1.js",
        "main-C2.css",
        "soundboard-S1.js",
        "soundboard-C3.css",
    ):
        (tmp_path / "assets" / name).write_text("/* {} */".format(name))
    (tmp_path / "buzzer.html").write_text("<!doctype html><title>Buzzer</title>")
    (tmp_path / "soundboard.html").write_text("<!doctype html><title>Soundboard</title>")
    (tmp_path / "index.html").write_text("<!doctype html><title>Host and viewer</title>")
    return tmp_path


def make_server(
    tokens: dict[str, str] | None = None,
    soundboard_token: str = "",
    folder: str = "",
    relay: Callable[[str, str | None], None] = lambda action, sound_id: None,
    on_soundboard_presence: Callable[[int], None] = lambda count: None,
    on_outcome: Callable[[BuzzOutcome], None] = lambda outcome: None,
) -> GuestServer:
    buzzers = BuzzersPage(
        BuzzArbiter(FairnessSettings()),
        tokens=lambda: tokens or {},
        team_names=lambda: {tid: tid for tid in tokens or {}},
        on_outcome=on_outcome,
        on_presence=lambda counts: None,
    )
    soundboard = SoundboardPage(
        token=lambda: soundboard_token,
        folder=folder,
        relay=relay,
        on_presence=on_soundboard_presence,
    )
    return GuestServer(buzzers, soundboard)


def make_client(dist_dir) -> Client:
    return Client(make_server().wsgi_app(str(dist_dir)))


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


def test_soundboard_page_is_served_with_security_headers(dist):
    res = make_client(dist).get("/soundboard.html")
    assert res.status_code == 200
    assert b"Soundboard" in res.data
    assert "frame-ancestors 'none'" in res.headers["Content-Security-Policy"]
    assert res.headers["Referrer-Policy"] == "no-referrer"


@pytest.mark.parametrize("path", ["/assets/soundboard-S1.js", "/assets/soundboard-C3.css"])
def test_soundboard_page_files_are_served(dist, path):
    res = make_client(dist).get(path)
    assert res.status_code == 200
    assert "Content-Security-Policy" in res.headers


def test_buzzer_page_still_served_when_soundboard_is_not_built(dist):
    (dist / "soundboard.html").unlink()
    client = make_client(dist)
    assert client.get("/").status_code == 200
    assert client.get("/soundboard.html").status_code == 404
    assert client.get("/assets/soundboard-S1.js").status_code == 404


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
        "/static/soundboard/x.mp3",
        "/soundboard/x.mp3",
        "/soundboard",
        "/static/game-media/x.png",
        "/api/v1/soundboard/link",
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


def test_serve_on_a_busy_port_raises_for_the_caller_to_report(tmp_path):
    with socket.create_server(("127.0.0.1", 0)) as taken:
        with pytest.raises(OSError):
            make_server().serve(taken.getsockname()[1], str(tmp_path))


def test_unbuilt_front_end_says_so(tmp_path):
    client = make_client(tmp_path)
    res = client.get("/")
    assert res.status_code == 503
    assert b"guest pages" in res.data
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


# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------
TEAM_TOKEN = "team-secret-aaaaaaaaaa"
SOUNDBOARD_TOKEN = "soundboard-secret-bbbb"


class Recorder:
    def __init__(self) -> None:
        self.emitted: list[tuple[str, dict, str, str]] = []
        self.disconnected: list[tuple[str, str]] = []
        self.played: list[tuple[str, str | None, int]] = []
        self.skipped: list[tuple[str, dict, str]] = []
        self.presence: list[int] = []


@pytest.fixture
def sounds(tmp_path):
    folder = tmp_path / "soundboard"
    folder.mkdir()
    (folder / "airhorn.wav").write_bytes(b"x")
    (folder / "applause.mp3").write_bytes(b"x")
    return folder


@pytest.fixture
def board(sounds):
    rec = Recorder()
    server = make_server(
        tokens={"team1": TEAM_TOKEN},
        soundboard_token=SOUNDBOARD_TOKEN,
        folder=str(sounds),
        relay=lambda action, sound_id, volume: rec.played.append((action, sound_id, volume)),
        on_soundboard_presence=rec.presence.append,
    )
    pages = {page.namespace: page for page in server.pages}

    def emit(event, data=None, to=None, room=None, namespace=None, skip_sid=None, **_kwargs):
        rec.emitted.append((event, data, to or room, namespace))
        if skip_sid is not None:
            rec.skipped.append((event, data, skip_sid))

    def disconnect(sid, namespace=None):
        rec.disconnected.append((sid, namespace))
        pages[namespace].on_disconnect(sid)

    server.sio.emit = emit
    server.sio.disconnect = disconnect
    server.sio.enter_room = lambda *args, **kwargs: None
    return server, rec


def connect(server: GuestServer, sid: str, token: object = SOUNDBOARD_TOKEN) -> None:
    server.soundboard.on_connect(sid, {}, {"token": token})


@pytest.mark.parametrize("auth", [{"token": TEAM_TOKEN}, {"token": ""}, {}, None, "x"])
def test_soundboard_refuses_anything_but_its_token(board, auth):
    server, rec = board
    with pytest.raises(socketio.exceptions.ConnectionRefusedError):
        server.soundboard.on_connect("s1", {}, auth)
    assert rec.emitted == []
    assert server.soundboard.presence() == 0


def test_buzzer_refuses_the_soundboard_token(board):
    server, rec = board
    with pytest.raises(socketio.exceptions.ConnectionRefusedError):
        server.buzzers.on_connect("s1", {}, {"token": SOUNDBOARD_TOKEN})
    assert server.buzzers.arbiter.players() == []


def test_buzzer_still_accepts_its_team_token(board):
    server, rec = board
    server.buzzers.on_connect("s1", {}, {"token": TEAM_TOKEN})
    assert server.buzzers.arbiter.players() == [("s1", "team1")]
    assert all(ns == BUZZ_NS for _e, _d, _to, ns in rec.emitted)


def test_soundboard_connect_sends_only_the_sound_list_and_volume(board):
    server, rec = board
    connect(server, "s1")
    assert rec.emitted == [
        (
            "sounds",
            {
                "sounds": [
                    {"id": "airhorn.wav", "label": "airhorn"},
                    {"id": "applause.mp3", "label": "applause"},
                ]
            },
            "s1",
            SOUNDBOARD_NS,
        ),
        ("volume", {"volume": 85}, "s1", SOUNDBOARD_NS),
    ]
    assert rec.presence == [1]


def test_soundboard_connections_are_capped_at_four(board):
    server, rec = board
    for n in range(4):
        connect(server, "s{}".format(n))
    with pytest.raises(socketio.exceptions.ConnectionRefusedError, match="full"):
        connect(server, "s4")
    assert server.soundboard.presence() == 4


def test_play_a_listed_sound(board):
    server, rec = board
    connect(server, "s1")
    server.soundboard.on_play("s1", {"id": "airhorn.wav"})
    assert rec.played == [("play", "airhorn.wav", 85)]


@pytest.mark.parametrize(
    "data",
    [
        {"id": "../data/Questions.cp"},
        {"id": "/etc/passwd"},
        {"id": "missing.mp3"},
        {"id": None},
        {},
        "airhorn.wav",
        None,
    ],
)
def test_play_ignores_unlisted_sounds(board, data):
    server, rec = board
    connect(server, "s1")
    server.soundboard.on_play("s1", data)
    assert rec.played == []


def test_play_from_an_unconnected_sid_is_ignored(board):
    server, rec = board
    server.soundboard.on_play("nobody", {"id": "airhorn.wav"})
    server.soundboard.on_stop("nobody")
    assert rec.played == []


def test_a_sixth_play_within_a_second_is_dropped(board):
    server, rec = board
    connect(server, "s1")
    for _ in range(50):
        server.soundboard.on_play("s1", {"id": "airhorn.wav"})
    assert len(rec.played) == 5


def test_stop_always_goes_through(board):
    server, rec = board
    connect(server, "s1")
    for _ in range(10):
        server.soundboard.on_play("s1", {"id": "airhorn.wav"})
    server.soundboard.on_stop("s1")
    assert rec.played[-1][:2] == ("stop", None)


def test_volume_is_relayed_and_sent_to_the_other_pages(board):
    server, rec = board
    connect(server, "s1")
    connect(server, "s2")
    rec.emitted.clear()
    server.soundboard.on_volume("s1", {"volume": 40})
    assert rec.played == [("volume", None, 40)]
    assert rec.skipped == [("volume", {"volume": 40}, "s1")]
    assert [(e, to, ns) for e, _d, to, ns in rec.emitted] == [("volume", None, SOUNDBOARD_NS)]


def test_a_later_page_and_play_get_the_new_volume(board):
    server, rec = board
    connect(server, "s1")
    server.soundboard.on_volume("s1", {"volume": 40})
    rec.emitted.clear()
    connect(server, "s2")
    assert rec.emitted[-1] == ("volume", {"volume": 40}, "s2", SOUNDBOARD_NS)
    server.soundboard.on_play("s2", {"id": "airhorn.wav"})
    assert rec.played[-1] == ("play", "airhorn.wav", 40)


@pytest.mark.parametrize(
    "data", [{"volume": 150}, {"volume": -1}, {"volume": "loud"}, {"volume": True}, {}, 50, None]
)
def test_invalid_volume_is_ignored(board, data):
    server, rec = board
    connect(server, "s1")
    rec.emitted.clear()
    server.soundboard.on_volume("s1", data)
    server.soundboard.on_play("s1", {"id": "airhorn.wav"})
    assert rec.played == [("play", "airhorn.wav", 85)]
    assert rec.emitted == []


def test_volume_from_an_unconnected_sid_is_ignored(board):
    server, rec = board
    server.soundboard.on_volume("nobody", {"volume": 40})
    assert rec.played == []
    assert rec.emitted == []


def test_a_21st_volume_within_a_second_is_dropped(board):
    server, rec = board
    connect(server, "s1")
    for n in range(100):
        server.soundboard.on_volume("s1", {"volume": n})
    assert [v for _a, _id, v in rec.played] == list(range(20))


def test_refresh_resends_the_list(board, sounds):
    server, rec = board
    connect(server, "s1")
    (sounds / "boo.ogg").write_bytes(b"x")
    rec.emitted.clear()
    server.soundboard.on_refresh("s1")
    [(event, data, to, _ns)] = rec.emitted
    assert event == "sounds" and to == "s1"
    assert [s["id"] for s in data["sounds"]] == ["airhorn.wav", "applause.mp3", "boo.ogg"]


def test_revoke_emits_revoked_then_disconnects(board):
    server, rec = board
    connect(server, "s1")
    connect(server, "s2")
    rec.emitted.clear()
    server.soundboard.revoke()
    assert rec.emitted == [
        ("revoked", {}, "s1", SOUNDBOARD_NS),
        ("revoked", {}, "s2", SOUNDBOARD_NS),
    ]
    assert rec.disconnected == [("s1", SOUNDBOARD_NS), ("s2", SOUNDBOARD_NS)]
    assert server.soundboard.presence() == 0
    assert rec.presence[-1] == 0


def test_revoke_soundboard_leaves_buzzers_alone(board):
    server, rec = board
    server.buzzers.on_connect("b1", {}, {"token": TEAM_TOKEN})
    connect(server, "s1")
    server.soundboard.revoke()
    assert server.buzzers.arbiter.players() == [("b1", "team1")]
    assert rec.disconnected == [("s1", SOUNDBOARD_NS)]


# ---------------------------------------------------------------------------
# Buzzer page relays: the game owns the race, the page only talks to players.
# ---------------------------------------------------------------------------
TEAM_TOKENS = {
    "team1": "t1-secret-aaaaaaaaaa",
    "team2": "t2-secret-aaaaaaaaaa",
    "team3": "t3-secret-aaaaaaaaaa",
}


@pytest.fixture
def race():
    rec = Recorder()
    outcomes: list[BuzzOutcome] = []
    server = make_server(tokens=TEAM_TOKENS, on_outcome=outcomes.append)

    def emit(event, data=None, to=None, room=None, namespace=None, **_kwargs):
        rec.emitted.append((event, data, to or room, namespace))

    server.sio.emit = emit
    server.sio.enter_room = lambda *args, **kwargs: None
    page = server.buzzers
    for n, (tid, token) in enumerate(TEAM_TOKENS.items(), 1):
        page.on_connect(f"p{n}", {}, {"token": token})
    rec.emitted.clear()
    return page, rec, outcomes


def test_send_standings_tells_each_team_only_its_own(race):
    page, rec, _ = race
    decision = Decision(1, "team2", [Entry("team2", 212, False), Entry("team1", 220, False)])
    page.send_standings(decision, ["team2", "team1", "team3"])
    assert rec.emitted == [
        ("standing", {"place": 1, "margin_ms": 8}, "team2", BUZZ_NS),
        ("standing", {"place": 2, "margin_ms": 8}, "team1", BUZZ_NS),
    ]


def test_a_counted_buzz_is_handed_to_the_game(race):
    page, _, outcomes = race
    epoch = page.arbiter.open()
    page.arbiter.open_sent("p1")
    page.on_buzz("p1", {"epoch": epoch, "reaction_ms": 200})
    page.on_buzz("p1", {"epoch": epoch, "reaction_ms": 150})
    assert len(outcomes) == 1 and outcomes[0].delay is not None


def test_set_open_sends_cues_without_touching_the_race(race):
    page, rec, _ = race
    epoch = page.arbiter.open(["team3"])
    page.set_open(True)
    assert page.arbiter.epoch == epoch and page.arbiter.is_open
    assert [(event, to) for event, _data, to, _ns in rec.emitted] == [
        ("open", "p1"),
        ("open", "p2"),
        ("excluded", "p3"),
    ]
    rec.emitted.clear()
    page.set_open(False, winner="team1")
    assert page.arbiter.is_open
    assert [(event, data["won"]) for event, data, _to, _ns in rec.emitted] == [
        ("closed", True),
        ("closed", False),
        ("closed", False),
    ]
