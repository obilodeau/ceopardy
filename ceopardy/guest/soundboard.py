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
"""The remote soundboard page and its /soundboard namespace."""

import threading
from collections.abc import Callable

import socketio

from ceopardy import soundboard, utils
from ceopardy.guest import GuestPage
from ceopardy.soundboard import PlayLimiter

SOUNDBOARD_NS = "/soundboard"
MAX_SOUNDBOARDS = 4


class SoundboardPage(GuestPage):
    """
    Glue between soundboard pages and the viewer.

    `token()` and `relay()` are called from the guest server's threads and
    must set up their own Flask app context.
    """

    urls = {"/soundboard.html": "soundboard.html"}

    def __init__(
        self,
        token: Callable[[], str],
        folder: str,
        relay: Callable[[str, str | None, int], None],
        on_presence: Callable[[int], None],
    ) -> None:
        super().__init__(SOUNDBOARD_NS)
        self._token = token
        self._folder = folder
        self._relay = relay
        self._on_presence = on_presence
        self._limiters: dict[str, PlayLimiter] = {}
        self._volume_limiters: dict[str, PlayLimiter] = {}
        self._volume = soundboard.DEFAULT_VOLUME
        self._lock = threading.Lock()

    # ---- events from pages ------------------------------------------------
    def on_connect(self, sid: str, environ: dict, auth: object = None) -> None:
        token = auth.get("token") if isinstance(auth, dict) else None
        with self._lock:
            if utils.match_buzzer_token(token, {"soundboard": self._token()}) is None:
                raise socketio.exceptions.ConnectionRefusedError("invalid link")
            if len(self._limiters) >= MAX_SOUNDBOARDS:
                raise socketio.exceptions.ConnectionRefusedError("full")
            self._limiters[sid] = PlayLimiter()
            self._volume_limiters[sid] = PlayLimiter(rate=20)
            volume = self._volume
        self._send_sounds(sid)
        self.emit("volume", soundboard.volume_payload(volume), to=sid)
        self._on_presence(self.presence())

    def on_disconnect(self, sid: str, *_args: object) -> None:
        with self._lock:
            self._limiters.pop(sid, None)
            self._volume_limiters.pop(sid, None)
        self._on_presence(self.presence())

    def on_play(self, sid: str, data: object = None) -> None:
        with self._lock:
            limiter = self._limiters.get(sid)
        if limiter is None or not isinstance(data, dict) or not limiter.allow():
            return
        sound_id = soundboard.resolve(self._folder, data.get("id"))
        if sound_id is not None:
            with self._lock:
                volume = self._volume
            self._relay("play", sound_id, volume)

    def on_stop(self, sid: str, *_args: object) -> None:
        if sid in self._limiters:
            with self._lock:
                volume = self._volume
            self._relay("stop", None, volume)

    def on_volume(self, sid: str, data: object = None) -> None:
        with self._lock:
            limiter = self._volume_limiters.get(sid)
        if limiter is None or not isinstance(data, dict) or not limiter.allow():
            return
        volume = soundboard.parse_volume(data.get("volume"))
        if volume is None:
            return
        with self._lock:
            self._volume = volume
        self._relay("volume", None, volume)
        self.emit("volume", soundboard.volume_payload(volume), skip_sid=sid)

    def on_refresh(self, sid: str, *_args: object) -> None:
        if sid in self._limiters:
            self._send_sounds(sid)

    # ---- driven by the game -----------------------------------------------
    def revoke(self) -> None:
        """Disconnect every soundboard page; their link was just replaced."""
        with self._lock:
            sids = list(self._limiters)
        for sid in sids:
            self.emit("revoked", soundboard.revoked_payload(), to=sid)
            self.disconnect(sid)

    def presence(self) -> int:
        with self._lock:
            return len(self._limiters)

    def _send_sounds(self, sid: str) -> None:
        sounds = soundboard.list_sounds(self._folder)
        self.emit("sounds", soundboard.sounds_payload(sounds), to=sid)
