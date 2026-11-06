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
The guest port: the one port meant to be reachable from the internet, for the
people in an online game who are not the host.

Each guest page is a GuestPage: the URLs it is served at and its Socket.IO
namespace. GuestServer (server.py) serves those pages and nothing else.
"""

import socketio


class GuestPage(socketio.Namespace):
    """
    A page served on the guest port, and its namespace.

    `urls` maps each URL path to the Vite entry served there; the server
    also serves exactly the files that entry loads. Every `on_<event>` method
    is an event any connected guest can send.
    """

    urls: dict[str, str] = {}

    def start(self) -> None:
        """Called once the guest server is listening."""
