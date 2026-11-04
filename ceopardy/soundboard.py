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
The remote soundboard's rules: which files in the operator's soundboard/
folder can be played, and how fast.

A sound's id is its file name, and a request is honoured only when the id is
exactly an entry of a fresh listing, so a path can never match.

No Flask or Socket.IO in here, so the rules can be tested with a fake clock.
"""

import os
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

EXTENSIONS = frozenset({".mp3", ".wav", ".ogg", ".m4a", ".opus"})


@dataclass(frozen=True)
class Sound:
    id: str
    label: str


def list_sounds(folder: str) -> list[Sound]:
    """The playable files directly inside `folder`, sorted by name."""
    try:
        entries = list(os.scandir(folder))
    except (FileNotFoundError, NotADirectoryError):
        return []
    sounds = []
    for entry in entries:
        stem, ext = os.path.splitext(entry.name)
        if entry.name.startswith(".") or ext.lower() not in EXTENSIONS:
            continue
        if not entry.is_file():
            continue
        sounds.append(Sound(entry.name, stem))
    return sorted(sounds, key=lambda s: s.id)


def resolve(folder: str, sound_id: object) -> str | None:
    """`sound_id` if it names a listed sound right now, None otherwise."""
    if not isinstance(sound_id, str):
        return None
    for sound in list_sounds(folder):
        if sound.id == sound_id:
            return sound.id
    return None


class PlayLimiter:
    """At most `rate` plays in any `per_s` seconds. Thread-safe."""

    def __init__(
        self, rate: int = 5, per_s: float = 1.0, now: Callable[[], float] = time.monotonic
    ) -> None:
        self._rate = rate
        self._per_s = per_s
        self._now = now
        self._lock = threading.Lock()
        self._times: deque[float] = deque()

    def allow(self) -> bool:
        with self._lock:
            now = self._now()
            while self._times and now - self._times[0] >= self._per_s:
                self._times.popleft()
            if len(self._times) >= self._rate:
                return False
            self._times.append(now)
            return True


# ---------------------------------------------------------------------------
# What a soundboard page is told. This is the whole server -> page protocol on
# the /soundboard namespace.
# ---------------------------------------------------------------------------
def sounds_payload(sounds: list[Sound]) -> dict:
    return {"sounds": [{"id": s.id, "label": s.label} for s in sounds]}


def revoked_payload() -> dict:
    return {}
