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
"""Tests for the soundboard folder listing, name resolution and rate limit."""

import pytest

from ceopardy.soundboard import PlayLimiter, Sound, list_sounds, resolve, sounds_payload


@pytest.fixture
def folder(tmp_path):
    for name in (
        "b.wav",
        "01-applause.mp3",
        "c.ogg",
        "d.m4a",
        "e.opus",
        "LOUD.MP3",
        "notes.txt",
        ".DS_Store",
        ".hidden.mp3",
        "noext",
    ):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "x.mp3").write_bytes(b"x")
    (tmp_path / "dir.mp3").mkdir()
    return tmp_path


def test_list_sounds_keeps_audio_files_sorted_and_labelled_by_stem(folder):
    assert list_sounds(str(folder)) == [
        Sound("01-applause.mp3", "01-applause"),
        Sound("LOUD.MP3", "LOUD"),
        Sound("b.wav", "b"),
        Sound("c.ogg", "c"),
        Sound("d.m4a", "d"),
        Sound("e.opus", "e"),
    ]


def test_list_sounds_of_a_missing_folder_is_empty(tmp_path):
    assert list_sounds(str(tmp_path / "nope")) == []


def test_resolve_accepts_a_listed_name(folder):
    assert resolve(str(folder), "b.wav") == "b.wav"


@pytest.mark.parametrize(
    "sound_id",
    [
        "../data/Questions.cp",
        "/etc/passwd",
        "sub/x.mp3",
        "notes.txt",
        ".hidden.mp3",
        "dir.mp3",
        "B.WAV",
        "",
        None,
        1,
        ["b.wav"],
        {"id": "b.wav"},
    ],
)
def test_resolve_rejects_anything_else(folder, sound_id):
    assert resolve(str(folder), sound_id) is None


def test_resolve_rejects_a_removed_file(folder):
    (folder / "b.wav").unlink()
    assert resolve(str(folder), "b.wav") is None


def test_sounds_payload_has_only_ids_and_labels():
    assert sounds_payload([Sound("a.mp3", "a")]) == {"sounds": [{"id": "a.mp3", "label": "a"}]}


class Clock:
    def __init__(self) -> None:
        self.t = 100.0

    def __call__(self) -> float:
        return self.t


def test_limiter_allows_five_per_second_then_refuses_until_the_window_moves():
    clock = Clock()
    limiter = PlayLimiter(now=clock)
    for _ in range(5):
        assert limiter.allow()
        clock.t += 0.1
    assert not limiter.allow()
    clock.t = 100.99
    assert not limiter.allow()
    clock.t = 101.0
    assert limiter.allow()
    assert not limiter.allow()


def test_limiter_caps_a_burst():
    limiter = PlayLimiter(now=Clock())
    assert sum(limiter.allow() for _ in range(50)) == 5
