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
Judging a buzzer race between remote players and keyboard buzzers.

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
arrives later can still win. Then the lowest reaction wins. With no remote
player sent the cue, as offline, there is no window and the first buzz wins.
After the decision, each other team's first buzz is still placed, behind the
others, so every team can learn its margin.

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
    # Fastest first, then teams that buzzed after the decision, in arrival order.
    entries: list[Entry]


@dataclass(frozen=True)
class BuzzOutcome:
    """A counted buzz that needs follow-up: a window to wait out, or a late entry."""

    delay: float | None = None
    late: Decision | None = None


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
        # Kept after the decision so late buzzes can still be placed.
        self._result: Decision | None = None

    # ---- players ----------------------------------------------------------
    def join(self, pid: str, tid: str) -> None:
        with self._lock:
            self._players[pid] = _Player(tid)

    def leave(self, pid: str) -> None:
        with self._lock:
            self._players.pop(pid, None)

    def players(self) -> list[tuple[str, str]]:
        """(pid, tid) for every connected player."""
        with self._lock:
            return [(pid, p.tid) for pid, p in self._players.items()]

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

    @property
    def result(self) -> Decision | None:
        """The decided race still taking late buzzes, if any."""
        return self._result

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
            self._result = None
            for player in self._players.values():
                player.open_sent = None
            return self._epoch

    def set_locked_out(self, locked_out: Iterable[str]) -> None:
        """Replace the lock-out list without starting a race or dropping its result."""
        with self._lock:
            self._locked_out = frozenset(locked_out)

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

    def close(self, keep_result: bool = False) -> None:
        with self._lock:
            self._open = False
            self._deadline = None
            self._buzzes = {}
            if not keep_result:
                self._result = None

    def buzz(self, pid: str, epoch: object, reaction_ms: object) -> BuzzOutcome | None:
        """
        A press from a buzzer page.

        Returns a delay in seconds after which `decide()` should be called when
        this buzz started the race's collection window, the updated decision
        when it entered a decided race late, and None otherwise.
        """
        with self._lock:
            player = self._players.get(pid)
            if player is None:
                return None
            now = self._now()
            if epoch != self._epoch or player.open_sent is None:
                player.early_press = now
                return None
            if not self._open:
                if not self._can_enter_late(player.tid):
                    player.early_press = now
                    return None
                return self._record_late(player.tid, self._judge(player, now, reaction_ms))
            if player.tid in self._locked_out:
                return None
            reaction = self._judge(player, now, reaction_ms)
            return self._record(player.tid, reaction, now)

    def buzz_local(self, tid: str) -> BuzzOutcome | None:
        """A press on the host's keyboard: no network, judged on arrival."""
        with self._lock:
            now = self._now()
            reaction = (now - self._opened_at) * 1000
            if not self._open:
                return self._record_late(tid, reaction) if self._can_enter_late(tid) else None
            if tid in self._locked_out:
                return None
            return self._record(tid, reaction, now)

    def decide(self) -> Decision | None:
        """Close the race and name the winner, once the window has passed."""
        with self._lock:
            if not self._open or self._deadline is None or self._now() < self._deadline:
                return None
            ranked = sorted(self._buzzes.items(), key=lambda kv: kv[1])
            entries = [self._entry(tid, r) for tid, (r, _arrival) in ranked]
            self._open = False
            self._deadline = None
            self._buzzes = {}
            self._result = Decision(self._epoch, entries[0].tid, entries)
            return self._result

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

    def _record(self, tid: str, reaction: float, now: float) -> BuzzOutcome | None:
        best = self._buzzes.get(tid)
        if best is None or reaction < best[0]:
            self._buzzes[tid] = (reaction, now)
        if self._deadline is not None:
            return None
        window_s = self._window_ms() / 1000
        self._deadline = now + window_s
        return BuzzOutcome(delay=window_s)

    def _can_enter_late(self, tid: str) -> bool:
        return (
            self._result is not None
            and tid not in self._locked_out
            and all(e.tid != tid for e in self._result.entries)
        )

    def _record_late(self, tid: str, reaction: float) -> BuzzOutcome:
        result = self._result
        assert result is not None
        self._result = Decision(
            result.epoch, result.winner, [*result.entries, self._entry(tid, reaction)]
        )
        return BuzzOutcome(late=self._result)

    def _entry(self, tid: str, reaction: float) -> Entry:
        return Entry(tid, round(reaction, 1), reaction < self.settings.human_floor_ms)

    def _window_ms(self) -> float:
        # Only web players who got the open cue can still be in flight.
        cued = [p for p in self._players.values() if p.open_sent is not None]
        if not cued:
            return 0.0
        # A player with no sample yet counts at the cap, as `_rtt` says.
        widest = max(self._rtt(p) for p in cued)
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


def standing_payload(place: int, margin_ms: int | None) -> dict:
    return {"place": place, "margin_ms": margin_ms}


def excluded_payload() -> dict:
    return {}


def ping_payload(n: int) -> dict:
    return {"n": n}


def revoked_payload() -> dict:
    return {}


def standing(decision: Decision, tid: str) -> tuple[int, int | None] | None:
    """
    A team's place and margin in whole ms: the winner's lead over the second
    entry (None when alone), anyone else's lag behind the winner. Never
    negative, since a late entry may have judged faster than the winner.
    """
    tids = [e.tid for e in decision.entries]
    if tid not in tids:
        return None
    place = tids.index(tid) + 1
    entries = decision.entries
    if place == 1 and len(entries) == 1:
        return 1, None
    other = entries[1] if place == 1 else entries[place - 1]
    return place, max(0, round(other.reaction_ms - entries[0].reaction_ms))


def result_payload(decision: Decision) -> dict:
    """The race's numbers for the host (on /game, never on /buzz)."""
    return {
        "winner": decision.winner,
        "entries": [
            {"tid": e.tid, "reaction_ms": e.reaction_ms, "suspicious": e.suspicious}
            for e in decision.entries
        ],
    }
