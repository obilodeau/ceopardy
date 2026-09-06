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
Tests for utils.py pure helper functions.

These tests cover functions that have no Flask or database dependencies
and can run without any app context.
"""

import pytest

from ceopardy.exceptions import InvalidQuestionId, SoundProblem
from ceopardy.utils import (
    SOUND_FILES,
    filter_answer_form,
    list_sounds,
    parse_question_id,
    question_to_html,
    validate_sound_request,
)

# ---------------------------------------------------------------------------
# parse_question_id
# ---------------------------------------------------------------------------


def test_parse_question_id_returns_col_and_row():
    col, row = parse_question_id("c3q2")
    assert col == "3"
    assert row == "2"


def test_parse_question_id_single_digit():
    col, row = parse_question_id("c1q1")
    assert col == "1"
    assert row == "1"


def test_parse_question_id_multi_digit():
    col, row = parse_question_id("c10q25")
    assert col == "10"
    assert row == "25"


def test_parse_question_id_invalid_raises():
    with pytest.raises(InvalidQuestionId):
        parse_question_id("invalid")


def test_parse_question_id_empty_raises():
    with pytest.raises(InvalidQuestionId):
        parse_question_id("")


def test_parse_question_id_partial_raises():
    with pytest.raises(InvalidQuestionId):
        parse_question_id("c3")


# ---------------------------------------------------------------------------
# question_to_html
# ---------------------------------------------------------------------------


def test_question_to_html_plain_text():
    result = question_to_html("What is Python?")
    assert result == "<p>What is Python?</p>"


def test_question_to_html_escapes_angle_brackets():
    result = question_to_html("<script>alert('xss')</script>")
    assert "<script>" not in result
    assert "&lt;script&gt;" in result


def test_question_to_html_fixed_prefix():
    result = question_to_html("[fixed]some code here")
    assert "<tt>some code here</tt>" in result
    assert "[fixed]" not in result


def test_question_to_html_utf8_prefix_stripped():
    result = question_to_html("[utf8]Hello world")
    assert "[utf8]" not in result
    assert "Hello world" in result


def test_question_to_html_newline_becomes_br():
    result = question_to_html("line one\nline two")
    assert "<br/>" in result


def test_question_to_html_image_tag():
    result = question_to_html("[img:photo.png]")
    assert "<img" in result
    assert "photo.png" in result


# ---------------------------------------------------------------------------
# filter_answer_form
# ---------------------------------------------------------------------------


def test_filter_answer_form_excludes_dailydouble_keys():
    data = {"t1": "correct", "t2": "wrong", "t3-dailydouble": "ignored"}
    result = filter_answer_form(data)
    assert "t1" in result
    assert "t2" in result
    assert "t3-dailydouble" not in result


def test_filter_answer_form_dailydouble_mode_keeps_only_dd_keys():
    data = {"t1": "regular", "t1-dailydouble": "dd_answer"}
    result = filter_answer_form(data, dailydouble=True)
    assert "t1" in result
    assert result["t1"] == "dd_answer"
    assert len(result) == 1


def test_filter_answer_form_empty_input():
    assert filter_answer_form({}) == {}
    assert filter_answer_form({}, dailydouble=True) == {}


# ---------------------------------------------------------------------------
# validate_sound_request
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "name",
    ["buzzer1", "buzzer2", "buzzer3", "timeout", "reveal", "thinking", "dailydouble"],
)
@pytest.mark.parametrize("action", ["play", "stop"])
def test_validate_sound_request_accepts_known_pairs(name, action):
    assert validate_sound_request(name, action) == (name, action)


@pytest.mark.parametrize("name", ["buzzer4", "", None, "THINKING", "../../etc/passwd"])
def test_validate_sound_request_rejects_unknown_names(name):
    with pytest.raises(SoundProblem):
        validate_sound_request(name, "play")


@pytest.mark.parametrize("action", ["pause", "", None, "PLAY"])
def test_validate_sound_request_rejects_unknown_actions(action):
    with pytest.raises(SoundProblem):
        validate_sound_request("timeout", action)


# ---------------------------------------------------------------------------
# list_sounds
# ---------------------------------------------------------------------------
def test_list_sounds_covers_every_known_sound():
    sounds = list_sounds()
    assert set(sounds) == set(SOUND_FILES)


def test_list_sounds_returns_served_urls():
    for url in list_sounds().values():
        assert url.startswith("/static/sounds/")


def test_list_sounds_names_are_all_accepted_by_the_validator():
    # The front-end plays whatever this map contains, so every entry must be
    # something the /api/v1/sound endpoint will accept back.
    for name in list_sounds():
        assert validate_sound_request(name, "play") == (name, "play")
