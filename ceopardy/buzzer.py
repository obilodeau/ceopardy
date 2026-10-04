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
Judging a buzzer race between remote players.

The race starts when a player's buzzer page receives "open", not when the
clue shows up on the stream. The page measures the player's reaction from
that moment and reports it. The server can't trust the report, but it can
bound it: it knows when it sent "open", when the buzz arrived, and the
socket's round-trip time, so a report faster than physics allows is clamped
to the server's own estimate minus a small jitter tolerance. A modified
client can still slow its ping replies to look farther away; that gain is
capped by the RTT cap and shows up in the numbers the host sees.

The first buzz of a race starts a collection window as long as the largest
latency correction anyone could get, so a far player's faster press that
arrives later can still win. Then the lowest reaction wins.

No Flask or Socket.IO in here, so the rules can be tested with a fake clock.
"""

import math
import statistics
import threading
import time
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

RTT_SAMPLES = 8


@dataclass(frozen=True)
class FairnessSettings:
    rtt_cap_ms: float = 250
    jitter_tolerance_ms: float = 50
    early_lockout_ms: float = 250
    human_floor_ms: float = 100

    @classmethod
    def from_config(cls, config: dict) -> "FairnessSettings":
        return cls(
            rtt_cap_ms=config["BUZZER_RTT_CAP_MS"],
            jitter_tolerance_ms=config["BUZZER_JITTER_TOLERANCE_MS"],
            early_lockout_ms=config["BUZZER_EARLY_LOCKOUT_MS"],
            human_floor_ms=config["BUZZER_HUMAN_FLOOR_MS"],
        )


@dataclass(frozen=True)
class Entry:
    """One team's best buzz in a race."""

    tid: str
    reaction_ms: float
    suspicious: bool


@dataclass(frozen=True)
class Decision:
    epoch: int
    winner: str
    # Fastest first.
    entries: list[Entry]


@dataclass
class _Player:
    tid: str
    rtts: deque = field(default_factory=lambda: deque(maxlen=RTT_SAMPLES))
    open_sent: float | None = None
    early_press: float | None = None
    floor_ms: float = 0


class BuzzArbiter:
    """
    Thread-safe; every public method takes the lock.

    Players are keyed by an opaque id (the Socket.IO sid). Times from
    `now()` are in seconds; everything reported is in milliseconds.
    """

    def __init__(
        self,
        settings: FairnessSettings | None = None,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings = settings or FairnessSettings()
        self._now = now
        self._lock = threading.Lock()
        self._players: dict[str, _Player] = {}
        self._epoch = 0
        self._open = False
        self._opened_at = 0.0
        self._locked_out: frozenset[str] = frozenset()
        self._deadline: float | None = None
        # tid -> (reaction_ms, arrival)
        self._buzzes: dict[str, tuple[float, float]] = {}

    # ---- players ----------------------------------------------------------
    def join(self, pid: str, tid: str) -> None:
        with self._lock:
            self._players[pid] = _Player(tid)

    def leave(self, pid: str) -> None:
        with self._lock:
            self._players.pop(pid, None)

    def team_of(self, pid: str) -> str | None:
        with self._lock:
            player = self._players.get(pid)
            return player.tid if player else None

    def presence(self, tids: Iterable[str]) -> dict[str, int]:
        """Connected players per team, zero for teams with nobody."""
        with self._lock:
            counts = {tid: 0 for tid in tids}
            for player in self._players.values():
                if player.tid in counts:
                    counts[player.tid] += 1
            return counts

    def rtt_sample(self, pid: str, rtt_ms: float) -> None:
        with self._lock:
            player = self._players.get(pid)
            if player is not None and rtt_ms >= 0:
                player.rtts.append(rtt_ms)

    # ---- the race ---------------------------------------------------------
    @property
    def epoch(self) -> int:
        return self._epoch

    @property
    def is_open(self) -> bool:
        return self._open

    def is_locked_out(self, tid: str) -> bool:
        return tid in self._locked_out

    def open(self, locked_out: Iterable[str] = ()) -> int:
        """Start a new race; returns its epoch, which pages echo back."""
        with self._lock:
            self._epoch += 1
            self._open = True
            self._opened_at = self._now()
            self._locked_out = frozenset(locked_out)
            self._deadline = None
            self._buzzes = {}
            for player in self._players.values():
                player.open_sent = None
            return self._epoch

    def open_sent(self, pid: str) -> None:
        """Record that "open" just went out to this player."""
        with self._lock:
            player = self._players.get(pid)
            if player is None:
                return
            now = self._now()
            player.open_sent = now
            player.floor_ms = 0
            if player.early_press is not None:
                since_ms = (now - player.early_press) * 1000
                player.floor_ms = max(0.0, self.settings.early_lockout_ms - since_ms)

    def close(self) -> None:
        with self._lock:
            self._open = False
            self._deadline = None
            self._buzzes = {}

    def buzz(self, pid: str, epoch: object, reaction_ms: object) -> float | None:
        """
        A press from a buzzer page.

        Returns the number of seconds after which `decide()` should be called
        when this buzz started the race's collection window, None otherwise.
        """
        with self._lock:
            player = self._players.get(pid)
            if player is None:
                return None
            now = self._now()
            if not self._open or epoch != self._epoch or player.open_sent is None:
                player.early_press = now
                return None
            if player.tid in self._locked_out:
                return None
            reaction = self._judge(player, now, reaction_ms)
            return self._record(player.tid, reaction, now)

    def buzz_local(self, tid: str) -> float | None:
        """A press on the host's keyboard: no network, judged on arrival."""
        with self._lock:
            if not self._open or tid in self._locked_out:
                return None
            now = self._now()
            return self._record(tid, (now - self._opened_at) * 1000, now)

    def decide(self) -> Decision | None:
        """Close the race and name the winner, once the window has passed."""
        with self._lock:
            if not self._open or self._deadline is None or self._now() < self._deadline:
                return None
            ranked = sorted(self._buzzes.items(), key=lambda kv: kv[1])
            entries = [
                Entry(tid, round(r, 1), r < self.settings.human_floor_ms)
                for tid, (r, _arrival) in ranked
            ]
            self._open = False
            self._deadline = None
            self._buzzes = {}
            return Decision(self._epoch, entries[0].tid, entries)

    # ---- internals (lock held) --------------------------------------------
    def _rtt(self, player: _Player) -> float:
        cap = self.settings.rtt_cap_ms
        if not player.rtts:
            return cap
        return min(statistics.median(player.rtts), cap)

    def _judge(self, player: _Player, now: float, reported: object) -> float:
        elapsed = (now - player.open_sent) * 1000
        server_estimate = elapsed - self._rtt(player)
        bound = server_estimate - self.settings.jitter_tolerance_ms
        if isinstance(reported, bool) or not isinstance(reported, (int, float)):
            reported = server_estimate
        elif not math.isfinite(reported):
            reported = server_estimate
        reaction = min(max(float(reported), bound, 0.0), elapsed)
        return max(reaction, player.floor_ms)

    def _record(self, tid: str, reaction: float, now: float) -> float | None:
        best = self._buzzes.get(tid)
        if best is None or reaction < best[0]:
            self._buzzes[tid] = (reaction, now)
        if self._deadline is not None:
            return None
        window_s = self._window_ms() / 1000
        self._deadline = now + window_s
        return window_s

    def _window_ms(self) -> float:
        rtts = [self._rtt(p) for p in self._players.values() if p.rtts]
        widest = min(self.settings.rtt_cap_ms, max(rtts, default=0))
        return widest + self.settings.jitter_tolerance_ms


# ---------------------------------------------------------------------------
# What a buzzer page is told. This is the whole server -> page protocol on the
# /buzz namespace; nothing about the game beyond these fields reaches it.
# ---------------------------------------------------------------------------
def team_payload(name: str) -> dict:
    return {"name": name}


def open_payload(epoch: int) -> dict:
    return {"epoch": epoch}


def closed_payload(won: bool | None) -> dict:
    return {"won": won}


def excluded_payload() -> dict:
    return {}


def ping_payload(n: int) -> dict:
    return {"n": n}


def revoked_payload() -> dict:
    return {}


def result_payload(decision: Decision) -> dict:
    """The race's numbers for the host (on /game, never on /buzz)."""
    return {
        "winner": decision.winner,
        "entries": [
            {"tid": e.tid, "reaction_ms": e.reaction_ms, "suspicious": e.suspicious}
            for e in decision.entries
        ],
    }
