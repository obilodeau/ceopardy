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
The public address of the buzzer port.

With an ngrok authtoken around, Ceopardy opens the tunnel itself through
ngrok's Python SDK, so an online game needs no second terminal and no URL to
paste. This is the only module that knows about ngrok; everything else just
needs some public URL that reaches the buzzer port, which --buzzer-url
provides for any other tunnel.
"""

import os
import re
from collections.abc import Iterable, Mapping

TOKEN_PAGE = "https://dashboard.ngrok.com/get-started/your-authtoken"

# Matches both the v2 (top level) and v3 (under `agent:`) config layouts.
_AUTHTOKEN_LINE = re.compile(r"""^\s*authtoken:\s*["']?([^"'\s#]+)""", re.MULTILINE)

# Kept so the tunnels live as long as the process.
_listeners: list = []


class TunnelError(Exception):
    """The tunnel could not be opened; the message says why."""


def ngrok_config_paths(env: Mapping[str, str], home: str) -> list[str]:
    """Where `ngrok config add-authtoken` writes: Linux, macOS, legacy v2."""
    xdg = env.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    return [
        os.path.join(xdg, "ngrok", "ngrok.yml"),
        os.path.join(home, "Library", "Application Support", "ngrok", "ngrok.yml"),
        os.path.join(home, ".ngrok2", "ngrok.yml"),
    ]


def find_authtoken(env: Mapping[str, str], config_paths: Iterable[str]) -> str | None:
    """NGROK_AUTHTOKEN, else the token in the ngrok agent's own config file."""
    if env.get("NGROK_AUTHTOKEN"):
        return env["NGROK_AUTHTOKEN"]
    for path in config_paths:
        try:
            with open(path) as f:
                match = _AUTHTOKEN_LINE.search(f.read())
        except OSError:
            continue
        if match:
            return match.group(1)
    return None


def forward_addr(port: int) -> str:
    """What the tunnel reaches. Built here, from the buzzer port only."""
    return "127.0.0.1:{}".format(int(port))


def choose(buzzer_url: str, no_tunnel: bool, authtoken: str | None) -> str:
    """
    "manual" when the operator brought their own public URL, "ngrok" when we
    should open one, "none" when told not to, "no-token" when we can't.
    """
    if buzzer_url:
        return "manual"
    if no_tunnel:
        return "none"
    return "ngrok" if authtoken else "no-token"


def open_tunnel(port: int, authtoken: str, domain: str = "") -> str:
    """Open an ngrok tunnel to the buzzer port; returns its public URL."""
    try:
        import ngrok  # A native extension: only loaded for online games.

        options = {"authtoken": authtoken}
        if domain:
            options["domain"] = domain
        listener = ngrok.forward(forward_addr(port), **options)
    except Exception as e:
        # The SDK raises ValueError with a tuple of reasons, sign-up links
        # included, and echoes a rejected token back; one line, no token.
        reason = " ".join(str(a) for a in e.args) if e.args else repr(e)
        reason = " ".join(reason.replace(authtoken, "<authtoken>").split())
        raise TunnelError(reason) from e
    _listeners.append(listener)
    return listener.url()


def setup(config: dict, *, no_tunnel: bool, domain: str, env: Mapping[str, str]) -> str:
    """
    Settle BUZZER_PUBLIC_URL and BUZZER_TUNNEL in `config`, opening the
    tunnel if that's the plan. Returns the banner line.
    """
    local = "http://127.0.0.1:{}/".format(config["BUZZER_PORT"])
    token = find_authtoken(env, ngrok_config_paths(env, os.path.expanduser("~")))
    kind = choose(config["BUZZER_PUBLIC_URL"], no_tunnel, token)
    if kind == "manual":
        config["BUZZER_TUNNEL"] = "manual"
        return "{} (-> {})".format(config["BUZZER_PUBLIC_URL"], local)
    config["BUZZER_TUNNEL"] = "none"
    if kind == "none":
        return "{} (local only)".format(local)
    if kind == "no-token":
        return "{} (local only; set NGROK_AUTHTOKEN to open a tunnel: {})".format(local, TOKEN_PAGE)
    try:
        config["BUZZER_PUBLIC_URL"] = open_tunnel(config["BUZZER_PORT"], token, domain)
    except TunnelError as e:
        return "{} (local only; ngrok failed: {})".format(local, e)
    config["BUZZER_TUNNEL"] = "ngrok"
    return "{} (ngrok -> {})".format(config["BUZZER_PUBLIC_URL"], local)
