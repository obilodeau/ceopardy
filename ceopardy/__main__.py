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
import argparse
import os
import shutil
import sys
from importlib import resources


def _cmd_serve(args):
    from ceopardy import app, create_app, socketio

    # WARNING: This app is not ready to be exposed on the network.
    #          Game host interface would be exposed.
    create_app()
    debug = getattr(args, "debug", False)
    host, port = "127.0.0.1", 5000
    print(f"Ceopardy serving on http://{host}:{port}/")
    print(f"  Viewer: http://localhost:{port}/")
    print(f"  Host:   http://localhost:{port}/host")
    if debug:
        print("  Debug:  ON (verbose logging + auto-reload)")
    # Werkzeug is the only WSGI server we use here. Flask-SocketIO refuses it
    # by default; we opt in because Ceopardy is meant for single-operator
    # local use (binds to 127.0.0.1, see README on exposing via nginx).
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


def _walk(traversable, prefix=""):
    """Yield (relative-path, Traversable) for every file under `traversable`."""
    for child in traversable.iterdir():
        rel = f"{prefix}{child.name}"
        if child.is_dir():
            yield from _walk(child, prefix=rel + "/")
        else:
            yield rel, child


def _cmd_init(_args):
    """Scaffold a fresh game directory in CWD from bundled templates."""
    cwd = os.getcwd()
    templates = resources.files("ceopardy") / "templates"

    created, skipped = [], []

    # Copy bundled template files (e.g. data/1st.round, data/Questions.cp)
    # preserving their relative path under templates/.
    for rel, src in _walk(templates):
        dst = os.path.join(cwd, rel)
        if os.path.exists(dst):
            skipped.append(rel)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with resources.as_file(src) as src_path:
            shutil.copyfile(src_path, dst)
        created.append(rel)

    # Always ensure game-media/ exists (per-game user content lives here).
    media_dir = os.path.join(cwd, "game-media")
    if not os.path.isdir(media_dir):
        os.makedirs(media_dir)
        created.append("game-media/")
    else:
        skipped.append("game-media/")

    for f in created:
        print(f"  created  {f}")
    for f in skipped:
        print(f"  exists   {f}  (skipped)")
    print(f"\nInitialized game directory: {cwd}")
    if not created:
        print("Nothing new written.")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ceopardy")
    sub = parser.add_subparsers(dest="cmd")
    serve = sub.add_parser("serve", help="Run the Ceopardy server (default).")
    serve.add_argument(
        "--debug",
        action="store_true",
        help="Enable Flask debug mode (verbose logging + auto-reload).",
    )
    sub.add_parser(
        "init",
        help="Scaffold data/ and game-media/ in the current directory.",
    )

    args = parser.parse_args(argv)
    cmd = args.cmd or "serve"
    {"serve": _cmd_serve, "init": _cmd_init}[cmd](args)


if __name__ == "__main__":
    sys.exit(main())
