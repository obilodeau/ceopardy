# Ceopardy
# https://github.com/obilodeau/ceopardy/
#
# Olivier Bilodeau <olivier@bottomlesspit.org>
# Copyright (C) 2017-2026 Olivier Bilodeau
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
Flask back-end for Ceopardy.

Since v0.5 the front-end has been rewritten as a Vite + Vue SPA. This module
now only does three things:

  * expose a REST API under /api/v1 (see api.routes)
  * broadcast realtime state changes on the /game Socket.IO namespace
  * serve the built SPA (and some legacy static assets)

For development run Flask (`python ceopardy.py`) and Vite (`npm run dev`)
side by side. Vite proxies /api and /socket.io to Flask.
"""
import json
import logging
import os
import sys

from flask import Flask, g, jsonify, send_from_directory
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

from config import config

with open(os.path.join(os.path.dirname(__file__), "package.json")) as _f:
    VERSION = json.load(_f)["version"]

# The Vite build drops its output here. `npm run build` writes the production
# bundle; during dev Vite serves directly on :5173 and proxies /api to us.
FRONTEND_DIST = os.path.join(config["BASE_DIR"], "static", "dist")


app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static",
)
app.config["SECRET_KEY"] = "Alex Trebek forever!"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + config["DATABASE_FILENAME"]
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# CORS for dev so that http://localhost:5173 can hit http://127.0.0.1:5000.
# We deliberately don't make this configurable — the app isn't meant to be
# exposed over a network.
try:
    from flask_cors import CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
except ImportError:
    # flask-cors is optional; prod serves everything from the same origin.
    pass

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
)
db = SQLAlchemy(app)


# ---------------------------------------------------------------------------
# SPA hosting
# ---------------------------------------------------------------------------
SPA_ROUTES = {"", "viewer", "host", "start"}


def _spa_response():
    """Return the SPA's index.html if it has been built, otherwise a hint."""
    index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index):
        return send_from_directory(FRONTEND_DIST, "index.html")
    return (
        "<h1>Ceopardy front-end not built.</h1>"
        "<p>Run <code>cd frontend && npm install && npm run build</code>,"
        " or use <code>npm run dev</code> and browse"
        " <a href='http://localhost:5173/'>http://localhost:5173/</a>.</p>",
        503,
    )


@app.route("/")
@app.route("/viewer")
@app.route("/host")
@app.route("/start")
def serve_spa():
    return _spa_response()


@app.route("/assets/<path:filename>")
def serve_spa_asset(filename):
    return send_from_directory(os.path.join(FRONTEND_DIST, "assets"), filename)


@app.route("/api/v1/version")
def version():
    return jsonify(version=VERSION)


# ---------------------------------------------------------------------------
# Socket.IO - single namespace both host and viewer listen on
# ---------------------------------------------------------------------------
GAME_NS = "/game"


@socketio.on("connect", namespace=GAME_NS)
def on_connect():
    # Initial state is fetched over REST; nothing to do here.
    pass


@socketio.on("disconnect", namespace=GAME_NS)
def on_disconnect():
    pass


def create_app():
    # Logging
    file_handler = logging.FileHandler("ceopardy.log")
    file_handler.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "{asctime} {levelname}: {message} [in {pathname}:{lineno}]", style="{"
    )
    file_handler.setFormatter(fmt)
    app.logger.addHandler(file_handler)

    with app.app_context():
        # Hand a couple of things on the app object so modules that don't
        # import from here can still reach them.
        app.db = db
        app.socketio = socketio

        from controller import Controller

        app.controller = Controller()

        # Register the REST blueprint. It depends on app.controller being set.
        from api.routes import api_bp

        app.register_blueprint(api_bp)

        @app.teardown_appcontext
        def teardown_controller(exception):  # noqa: ARG001
            _ctl = getattr(g, "_ctl", None)
            if _ctl is not None:
                _ctl = None

    return app


if __name__ == "__main__":
    create_app()
    # WARNING: This app is not ready to be exposed on the network.
    #          Game host interface would be exposed.
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
