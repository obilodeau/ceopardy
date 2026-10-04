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
The players' buzzer server: the one port meant to be reachable from the
internet.

It is a bare python-socketio server, not a Flask app, so nothing the host
uses can be reached through it: it serves buzzer.html, the files that page
loads, and the /buzz Socket.IO namespace. Everything else is a 404.
"""

import json
import logging
import mimetypes
import os
import threading
import time
from collections.abc import Callable, Iterable
from urllib.parse import urlsplit

import socketio
from werkzeug.serving import make_server

from ceopardy import buzzer, utils
from ceopardy.buzzer import BuzzArbiter, Decision, FairnessSettings

log = logging.getLogger(__name__)

BUZZ_NS = "/buzz"
SOCKETIO_PATH = "buzz-io"
ENTRY = "buzzer.html"
PING_INTERVAL_S = 2

SECURITY_HEADERS = [
    (
        "Content-Security-Policy",
        "default-src 'self'; connect-src 'self'; img-src 'self' data:; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
    ),
    ("Referrer-Policy", "no-referrer"),
    ("X-Content-Type-Options", "nosniff"),
    ("Cache-Control", "no-store"),
]

WSGIApp = Callable[[dict, Callable], Iterable[bytes]]


# ---------------------------------------------------------------------------
# HTTP: an exact allow-list of files
# ---------------------------------------------------------------------------
def entry_files(manifest: dict, entry: str = ENTRY) -> set[str]:
    """Every file the Vite manifest says `entry` loads, transitively."""
    files: set[str] = set()
    seen: set[str] = set()
    stack = [entry]
    while stack:
        key = stack.pop()
        if key in seen:
            continue
        seen.add(key)
        chunk = manifest.get(key, {})
        if "file" in chunk:
            files.add(chunk["file"])
        files.update(chunk.get("css", []))
        files.update(chunk.get("assets", []))
        stack.extend(chunk.get("imports", []))
    return files


def allowed_files(dist_dir: str) -> dict[str, str]:
    """URL path -> file on disk, for the buzzer page only; {} if not built."""
    manifest_path = os.path.join(dist_dir, ".vite", "manifest.json")
    page = os.path.join(dist_dir, ENTRY)
    if not (os.path.exists(manifest_path) and os.path.exists(page)):
        return {}
    with open(manifest_path) as f:
        manifest = json.load(f)
    files = {"/": page}
    for rel in entry_files(manifest):
        files["/" + rel] = os.path.join(dist_dir, rel)
    return files


def static_app(files: dict[str, str]) -> WSGIApp:
    """Serve exactly these paths. No prefix matching, no directory walking."""

    def app(environ: dict, start_response: Callable) -> Iterable[bytes]:
        filename = files.get(environ.get("PATH_INFO", ""))
        if environ.get("REQUEST_METHOD") not in ("GET", "HEAD") or filename is None:
            if not files and environ.get("PATH_INFO") == "/":
                start_response("503 Service Unavailable", [("Content-Type", "text/plain")])
                return [b"The buzzer page has not been built (npm run build)."]
            start_response("404 Not Found", [("Content-Type", "text/plain")])
            return [b"Not Found"]
        with open(filename, "rb") as f:
            body = f.read()
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        start_response(
            "200 OK", [("Content-Type", content_type), ("Content-Length", str(len(body)))]
        )
        return [body]

    return app


def with_security_headers(wsgi_app: WSGIApp) -> WSGIApp:
    def app(environ: dict, start_response: Callable) -> Iterable[bytes]:
        def start(status: str, headers: list, exc_info=None):  # noqa: ANN001
            return start_response(status, headers + SECURITY_HEADERS, exc_info)

        return wsgi_app(environ, start)

    return app


def origin_allowed(origin: str | None, environ: dict, public_url: str) -> bool:
    """
    Same-origin (as engine.io's default, including behind a proxy that sets
    X-Forwarded-Proto/Host), plus the public URL's origin, which differs when
    the page comes from the Vite dev server.
    """
    allowed = set()
    if "HTTP_HOST" in environ:
        host = environ["HTTP_HOST"]
        allowed.add("{}://{}".format(environ.get("wsgi.url_scheme", "http"), host))
        proto = environ.get("HTTP_X_FORWARDED_PROTO", environ.get("wsgi.url_scheme", "http"))
        fwd_host = environ.get("HTTP_X_FORWARDED_HOST", host)
        allowed.add("{}://{}".format(proto.split(",")[0].strip(), fwd_host.split(",")[0].strip()))
    if public_url:
        parts = urlsplit(public_url)
        allowed.add("{}://{}".format(parts.scheme, parts.netloc))
    return origin in allowed


# ---------------------------------------------------------------------------
# Socket.IO: the /buzz namespace
# ---------------------------------------------------------------------------
class BuzzerServer:
    """
    Glue between buzzer pages, the arbiter, and the game.

    `tokens()`, `team_names()` and `on_decision()` are called from this
    server's threads and must set up their own Flask app context.
    """

    def __init__(
        self,
        settings: FairnessSettings,
        tokens: Callable[[], dict[str, str]],
        team_names: Callable[[], dict[str, str]],
        on_decision: Callable[[Decision], None],
        on_presence: Callable[[dict[str, int]], None],
        public_url: str = "",
        max_players_per_team: int = 16,
    ) -> None:
        self.arbiter = BuzzArbiter(settings)
        self._tokens = tokens
        self._team_names = team_names
        self._on_decision = on_decision
        self._on_presence = on_presence
        self._max_players = max_players_per_team
        self._ping_n = 0
        self.sio = socketio.Server(
            async_mode="threading",
            cors_allowed_origins=lambda origin, environ: origin_allowed(
                origin, environ, public_url
            ),
            max_http_buffer_size=1024,
        )
        self.sio.on("connect", self._connect, namespace=BUZZ_NS)
        self.sio.on("disconnect", self._disconnect, namespace=BUZZ_NS)
        self.sio.on("buzz", self._buzz, namespace=BUZZ_NS)

    def wsgi_app(self, dist_dir: str) -> WSGIApp:
        return with_security_headers(
            socketio.WSGIApp(
                self.sio, static_app(allowed_files(dist_dir)), socketio_path=SOCKETIO_PATH
            )
        )

    # ---- events from pages ------------------------------------------------
    def _connect(self, sid: str, environ: dict, auth: object = None) -> None:
        token = auth.get("token") if isinstance(auth, dict) else None
        tid = utils.match_buzzer_token(token, self._tokens())
        if tid is None:
            raise socketio.exceptions.ConnectionRefusedError("invalid link")
        if self.arbiter.presence([tid])[tid] >= self._max_players:
            raise socketio.exceptions.ConnectionRefusedError("team full")
        self.arbiter.join(sid, tid)
        self.sio.enter_room(sid, tid, namespace=BUZZ_NS)
        name = self._team_names().get(tid, tid)
        self.sio.emit("team", buzzer.team_payload(name), to=sid, namespace=BUZZ_NS)
        if self.arbiter.is_open:
            self._send_open(sid, tid)
        self._presence_changed()

    def _disconnect(self, sid: str, *_args: object) -> None:
        self.arbiter.leave(sid)
        self._presence_changed()

    def _buzz(self, sid: str, data: object) -> None:
        if not isinstance(data, dict):
            return
        delay = self.arbiter.buzz(sid, data.get("epoch"), data.get("reaction_ms"))
        self._schedule(delay)

    # ---- driven by the game -----------------------------------------------
    def buzz_local(self, tid: str) -> None:
        self._schedule(self.arbiter.buzz_local(tid))

    def set_open(self, is_open: bool, locked_out: list[str], winner: str | None = None) -> None:
        if is_open:
            self.arbiter.open(locked_out)
            for sid, tid in self.arbiter.players():
                self._send_open(sid, tid)
        else:
            self.arbiter.close()
            for sid, tid in self.arbiter.players():
                won = None if winner is None else tid == winner
                self.sio.emit("closed", buzzer.closed_payload(won), to=sid, namespace=BUZZ_NS)

    def rename(self, names: dict[str, str]) -> None:
        for tid, name in names.items():
            self.sio.emit("team", buzzer.team_payload(name), room=tid, namespace=BUZZ_NS)

    def revoke(self, tid: str) -> None:
        """Disconnect everyone on a team whose link was just replaced."""
        for sid, player_tid in self.arbiter.players():
            if player_tid == tid:
                self.sio.emit("revoked", buzzer.revoked_payload(), to=sid, namespace=BUZZ_NS)
                self.sio.disconnect(sid, namespace=BUZZ_NS)

    def presence(self, tids: Iterable[str]) -> dict[str, int]:
        return self.arbiter.presence(tids)

    # ---- internals --------------------------------------------------------
    def _send_open(self, sid: str, tid: str) -> None:
        if self.arbiter.is_locked_out(tid):
            self.sio.emit("excluded", buzzer.excluded_payload(), to=sid, namespace=BUZZ_NS)
            return
        self.arbiter.open_sent(sid)
        self.sio.emit(
            "open",
            buzzer.open_payload(self.arbiter.epoch),
            to=sid,
            namespace=BUZZ_NS,
            callback=self._rtt_callback(sid),
        )

    def _rtt_callback(self, sid: str) -> Callable[..., None]:
        sent = time.monotonic()

        def ack(*_args: object) -> None:
            self.arbiter.rtt_sample(sid, (time.monotonic() - sent) * 1000)

        return ack

    def _ping_loop(self) -> None:
        while True:
            self.sio.sleep(PING_INTERVAL_S)
            self._ping_n += 1
            for sid, _tid in self.arbiter.players():
                self.sio.emit(
                    "ping",
                    buzzer.ping_payload(self._ping_n),
                    to=sid,
                    namespace=BUZZ_NS,
                    callback=self._rtt_callback(sid),
                )

    def _schedule(self, delay: float | None) -> None:
        if delay is None:
            return
        timer = threading.Timer(delay, self._decide)
        timer.daemon = True
        timer.start()

    def _decide(self) -> None:
        decision = self.arbiter.decide()
        if decision is not None:
            self._on_decision(decision)

    def _presence_changed(self) -> None:
        self._on_presence(self.arbiter.presence(self._team_names()))

    # ---- lifecycle --------------------------------------------------------
    def serve(self, port: int, dist_dir: str) -> None:
        """Listen on 127.0.0.1:`port` in daemon threads."""
        server = make_server("127.0.0.1", port, self.wsgi_app(dist_dir), threaded=True)
        threading.Thread(target=server.serve_forever, name="buzzer-http", daemon=True).start()
        self.sio.start_background_task(self._ping_loop)
