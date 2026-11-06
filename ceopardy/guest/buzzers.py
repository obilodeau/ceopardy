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
"""The players' buzzer page and its /buzz namespace."""

import threading
import time
from collections.abc import Callable, Iterable

import socketio

from ceopardy import buzzer, utils
from ceopardy.buzzer import BuzzArbiter, Decision, FairnessSettings
from ceopardy.guest import GuestPage

BUZZ_NS = "/buzz"
PING_INTERVAL_S = 2


class BuzzersPage(GuestPage):
    """
    Glue between buzzer pages, the arbiter, and the game.

    `tokens()`, `team_names()` and `on_decision()` are called from the guest
    server's threads and must set up their own Flask app context.
    """

    urls = {"/": "buzzer.html"}

    def __init__(
        self,
        settings: FairnessSettings,
        tokens: Callable[[], dict[str, str]],
        team_names: Callable[[], dict[str, str]],
        on_decision: Callable[[Decision], None],
        on_presence: Callable[[dict[str, int]], None],
        max_players_per_team: int = 16,
    ) -> None:
        super().__init__(BUZZ_NS)
        self.arbiter = BuzzArbiter(settings)
        self._tokens = tokens
        self._team_names = team_names
        self._on_decision = on_decision
        self._on_presence = on_presence
        self._max_players = max_players_per_team
        self._ping_n = 0

    # ---- events from pages ------------------------------------------------
    def on_connect(self, sid: str, environ: dict, auth: object = None) -> None:
        token = auth.get("token") if isinstance(auth, dict) else None
        tid = utils.match_buzzer_token(token, self._tokens())
        if tid is None:
            raise socketio.exceptions.ConnectionRefusedError("invalid link")
        if self.arbiter.presence([tid])[tid] >= self._max_players:
            raise socketio.exceptions.ConnectionRefusedError("team full")
        self.arbiter.join(sid, tid)
        self.enter_room(sid, tid)
        name = self._team_names().get(tid, tid)
        self.emit("team", buzzer.team_payload(name), to=sid)
        if self.arbiter.is_open:
            self._send_open(sid, tid)
        self._presence_changed()

    def on_disconnect(self, sid: str, *_args: object) -> None:
        self.arbiter.leave(sid)
        self._presence_changed()

    def on_buzz(self, sid: str, data: object) -> None:
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
                self.emit("closed", buzzer.closed_payload(won), to=sid)

    def rename(self, names: dict[str, str]) -> None:
        for tid, name in names.items():
            self.emit("team", buzzer.team_payload(name), room=tid)

    def revoke(self, tid: str) -> None:
        """Disconnect everyone on a team whose link was just replaced."""
        for sid, player_tid in self.arbiter.players():
            if player_tid == tid:
                self.emit("revoked", buzzer.revoked_payload(), to=sid)
                self.disconnect(sid)

    def presence(self, tids: Iterable[str]) -> dict[str, int]:
        return self.arbiter.presence(tids)

    def start(self) -> None:
        self.server.start_background_task(self._ping_loop)

    # ---- internals --------------------------------------------------------
    def _send_open(self, sid: str, tid: str) -> None:
        if self.arbiter.is_locked_out(tid):
            self.emit("excluded", buzzer.excluded_payload(), to=sid)
            return
        self.arbiter.open_sent(sid)
        self.emit(
            "open",
            buzzer.open_payload(self.arbiter.epoch),
            to=sid,
            callback=self._rtt_callback(sid),
        )

    def _rtt_callback(self, sid: str) -> Callable[..., None]:
        sent = time.monotonic()

        def ack(*_args: object) -> None:
            self.arbiter.rtt_sample(sid, (time.monotonic() - sent) * 1000)

        return ack

    def _ping_loop(self) -> None:
        while True:
            self.server.sleep(PING_INTERVAL_S)
            self._ping_n += 1
            for sid, _tid in self.arbiter.players():
                self.emit(
                    "ping",
                    buzzer.ping_payload(self._ping_n),
                    to=sid,
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
