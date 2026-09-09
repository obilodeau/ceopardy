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
import os

from ceopardy import app, create_app, socketio
from ceopardy.config import config

# Dev-only convenience: `make run` takes no arguments, so this is how you get
# the equivalent of `ceopardy serve --online` while hacking.
config["ONLINE_MODE"] = os.environ.get("CEOPARDY_ONLINE", "") not in ("", "0")

create_app()

if __name__ == "__main__":
    # Dev entrypoint with auto-reload. The installed `ceopardy` console
    # script (see ceopardy.__main__:main) runs the same thing with
    # debug=False.
    # WARNING: This app is not ready to be exposed on the network.
    #          Game host interface would be exposed.
    # allow_unsafe_werkzeug: Flask-SocketIO refuses Werkzeug otherwise. See
    # the same opt-in (and rationale) in ceopardy/__main__.py:_cmd_serve.
    socketio.run(
        app,
        host="127.0.0.1",
        port=5000,
        debug=True,
        allow_unsafe_werkzeug=True,
    )
