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
The guest server: a bare python-socketio server, not a Flask app, so nothing
the host uses can be reached through it. It serves the guest pages, the files
those pages load, and their Socket.IO namespaces. Everything else is a 404.
"""

import json
import mimetypes
import os
import socket
import threading
from collections.abc import Callable, Iterable
from urllib.parse import urlsplit

import socketio
from werkzeug.serving import make_server

from ceopardy.guest import GuestPage
from ceopardy.guest.buzzers import BuzzersPage
from ceopardy.guest.soundboard import SoundboardPage

SOCKETIO_PATH = "guest-io"
# The page at "/" doubles as the sign that the front-end has been built.
ROOT_ENTRY = "buzzer.html"

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
def entry_files(manifest: dict, entry: str) -> set[str]:
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


def allowed_files(dist_dir: str, urls: dict[str, str]) -> dict[str, str]:
    """URL path -> file on disk, for the given pages only; {} if not built."""
    manifest_path = os.path.join(dist_dir, ".vite", "manifest.json")
    if not (os.path.exists(manifest_path) and os.path.exists(os.path.join(dist_dir, ROOT_ENTRY))):
        return {}
    with open(manifest_path) as f:
        manifest = json.load(f)
    files = {}
    for url, entry in urls.items():
        page = os.path.join(dist_dir, entry)
        if not os.path.exists(page):
            continue
        files[url] = page
        for rel in entry_files(manifest, entry):
            files["/" + rel] = os.path.join(dist_dir, rel)
    return files


def static_app(files: dict[str, str]) -> WSGIApp:
    """Serve exactly these paths. No prefix matching, no directory walking."""

    def app(environ: dict, start_response: Callable) -> Iterable[bytes]:
        filename = files.get(environ.get("PATH_INFO", ""))
        if environ.get("REQUEST_METHOD") not in ("GET", "HEAD") or filename is None:
            if not files and environ.get("PATH_INFO") == "/":
                start_response("503 Service Unavailable", [("Content-Type", "text/plain")])
                return [b"The guest pages have not been built (npm run build)."]
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
# The server
# ---------------------------------------------------------------------------
class GuestServer:
    """Every guest page, on one Socket.IO server and one port."""

    def __init__(
        self, buzzers: BuzzersPage, soundboard: SoundboardPage, public_url: str = ""
    ) -> None:
        self.buzzers = buzzers
        self.soundboard = soundboard
        self.pages: list[GuestPage] = [buzzers, soundboard]
        self.sio = socketio.Server(
            async_mode="threading",
            cors_allowed_origins=lambda origin, environ: origin_allowed(
                origin, environ, public_url
            ),
            max_http_buffer_size=1024,
        )
        for page in self.pages:
            self.sio.register_namespace(page)

    def wsgi_app(self, dist_dir: str) -> WSGIApp:
        urls = {url: entry for page in self.pages for url, entry in page.urls.items()}
        return with_security_headers(
            socketio.WSGIApp(
                self.sio, static_app(allowed_files(dist_dir, urls)), socketio_path=SOCKETIO_PATH
            )
        )

    def serve(self, port: int, dist_dir: str) -> None:
        """Listen on 127.0.0.1:`port` in daemon threads; OSError if it's taken."""
        # Bound here because werkzeug exits on a busy port itself, before the
        # caller can say which flag moves it.
        with socket.create_server(("127.0.0.1", port)) as sock:
            server = make_server(
                "127.0.0.1", port, self.wsgi_app(dist_dir), threaded=True, fd=sock.fileno()
            )
        threading.Thread(target=server.serve_forever, name="guest-http", daemon=True).start()
        for page in self.pages:
            page.start()
