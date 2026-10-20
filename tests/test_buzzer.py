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
"""Tests for the buzzer race rules in buzzer.py, on a fake clock."""

import pytest

from ceopardy import buzzer
from ceopardy.buzzer import BuzzArbiter, FairnessSettings

SETTINGS = FairnessSettings(
    rtt_cap_ms=250, jitter_tolerance_ms=50, early_lockout_ms=250, human_floor_ms=100
)


class Clock:
    def __init__(self) -> None:
        self.ms = 0.0

    def __call__(self) -> float:
        return self.ms / 1000

    def at(self, ms: float) -> None:
        self.ms = ms


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def arb(clock: Clock) -> BuzzArbiter:
    return BuzzArbiter(SETTINGS, now=clock)


def add_player(arb: BuzzArbiter, pid: str, tid: str, rtt_ms: float | None) -> None:
    arb.join(pid, tid)
    if rtt_ms is not None:
        for _ in range(3):
            arb.rtt_sample(pid, rtt_ms)


def open_race(arb: BuzzArbiter, *pids: str, locked_out: tuple[str, ...] = ()) -> int:
    epoch = arb.open(locked_out)
    for pid in pids:
        arb.open_sent(pid)
    return epoch


def press(arb: BuzzArbiter, clock: Clock, pid: str, epoch: int, rtt: float, reaction: float):
    """An honest press: half the RTT down, the reaction, half the RTT back."""
    clock.at(rtt / 2 + reaction + rtt / 2)
    return arb.buzz(pid, epoch, reaction)


def test_far_faster_player_beats_near_slower_one(arb, clock):
    add_player(arb, "near", "team1", 10)
    add_player(arb, "far", "team2", 200)
    epoch = open_race(arb, "near", "far")

    window = press(arb, clock, "near", epoch, rtt=10, reaction=260)
    assert window == pytest.approx(0.25)  # the far player's RTT + tolerance
    assert press(arb, clock, "far", epoch, rtt=200, reaction=210) is None

    clock.at(270 + 250)
    decision = arb.decide()
    assert decision.winner == "team2"
    assert [(e.tid, e.reaction_ms) for e in decision.entries] == [
        ("team2", 210),
        ("team1", 260),
    ]


def test_claiming_zero_gains_at_most_the_tolerance(arb, clock):
    add_player(arb, "liar", "team1", 50)
    epoch = open_race(arb, "liar")
    clock.at(50 + 300)
    arb.buzz("liar", epoch, 0)
    clock.at(10_000)
    assert arb.decide().entries[0].reaction_ms == 300 - 50


def test_faking_a_slow_link_gains_at_most_the_cap(arb, clock):
    # Real RTT 20 ms, pings delayed to look like 1 s.
    add_player(arb, "cheat", "team1", 1000)
    epoch = open_race(arb, "cheat")
    clock.at(20 + 300)
    arb.buzz("cheat", epoch, 0)
    clock.at(10_000)
    reaction = arb.decide().entries[0].reaction_ms
    assert reaction == 320 - 250 - 50
    assert 300 - reaction <= SETTINGS.rtt_cap_ms - 20 + SETTINGS.jitter_tolerance_ms


@pytest.mark.parametrize("reported", ["fast", float("nan"), True, None])
def test_garbage_reaction_falls_back_to_the_server_estimate(arb, clock, reported):
    add_player(arb, "p", "team1", 40)
    epoch = open_race(arb, "p")
    clock.at(40 + 200)
    arb.buzz("p", epoch, reported)
    clock.at(10_000)
    assert arb.decide().entries[0].reaction_ms == 200


def test_reported_reaction_cannot_exceed_elapsed_time(arb, clock):
    add_player(arb, "p", "team1", 40)
    epoch = open_race(arb, "p")
    clock.at(100)
    arb.buzz("p", epoch, 5000)
    clock.at(10_000)
    assert arb.decide().entries[0].reaction_ms == 100


def test_teammates_count_once_with_the_best_reaction(arb, clock):
    add_player(arb, "a", "team1", 10)
    add_player(arb, "b", "team1", 100)
    add_player(arb, "c", "team2", 10)
    epoch = open_race(arb, "a", "b", "c")
    press(arb, clock, "a", epoch, rtt=10, reaction=300)
    press(arb, clock, "c", epoch, rtt=10, reaction=320)
    press(arb, clock, "b", epoch, rtt=100, reaction=250)
    clock.at(10_000)
    decision = arb.decide()
    assert decision.winner == "team1"
    assert [(e.tid, e.reaction_ms) for e in decision.entries] == [
        ("team1", 250),
        ("team2", 320),
    ]


def test_tie_goes_to_the_earliest_arrival(arb, clock):
    add_player(arb, "a", "team1", 100)
    add_player(arb, "b", "team2", 10)
    epoch = open_race(arb, "a", "b")
    press(arb, clock, "b", epoch, rtt=10, reaction=200)
    press(arb, clock, "a", epoch, rtt=100, reaction=200)
    clock.at(10_000)
    assert arb.decide().winner == "team2"


def test_buzz_while_closed_or_for_a_stale_epoch_is_ignored(arb, clock):
    add_player(arb, "p", "team1", 10)
    assert arb.buzz("p", 0, 100) is None
    epoch = open_race(arb, "p")
    clock.at(500)
    assert arb.buzz("p", epoch - 1, 100) is None
    clock.at(10_000)
    assert arb.decide() is None


def test_nothing_counts_after_the_decision(arb, clock):
    add_player(arb, "a", "team1", 10)
    add_player(arb, "b", "team2", 10)
    epoch = open_race(arb, "a", "b")
    press(arb, clock, "a", epoch, rtt=10, reaction=200)
    clock.at(10_000)
    assert arb.decide().winner == "team1"
    assert arb.buzz("b", epoch, 1) is None
    assert arb.decide() is None
    assert not arb.is_open


def test_no_decision_before_the_window_ends(arb, clock):
    add_player(arb, "a", "team1", 100)
    epoch = open_race(arb, "a")
    window = press(arb, clock, "a", epoch, rtt=100, reaction=200)
    assert window == pytest.approx(0.15)
    clock.at(300 + 149)
    assert arb.decide() is None
    clock.at(300 + 150)
    assert arb.decide().winner == "team1"


def test_early_press_floors_the_next_reaction(arb, clock):
    add_player(arb, "eager", "team1", 10)
    add_player(arb, "calm", "team2", 10)
    clock.at(-100)
    arb.buzz("eager", 0, 0)  # pressed 100 ms before the cue
    clock.at(0)
    epoch = open_race(arb, "eager", "calm")
    press(arb, clock, "eager", epoch, rtt=10, reaction=50)
    press(arb, clock, "calm", epoch, rtt=10, reaction=140)
    clock.at(10_000)
    decision = arb.decide()
    assert decision.winner == "team2"
    assert decision.entries[1].reaction_ms == 150


def test_early_press_long_before_the_cue_costs_nothing(arb, clock):
    add_player(arb, "p", "team1", 10)
    clock.at(-1000)
    arb.buzz("p", 0, 0)
    clock.at(0)
    epoch = open_race(arb, "p")
    press(arb, clock, "p", epoch, rtt=10, reaction=180)
    clock.at(10_000)
    assert arb.decide().entries[0].reaction_ms == 180


def test_local_buzz_is_judged_on_arrival_and_races_web_buzzes(arb, clock):
    add_player(arb, "web", "team1", 200)
    epoch = open_race(arb, "web")
    clock.at(190)
    assert arb.buzz_local("team3") == pytest.approx(0.25)
    press(arb, clock, "web", epoch, rtt=200, reaction=170)
    clock.at(10_000)
    decision = arb.decide()
    assert [(e.tid, e.reaction_ms) for e in decision.entries] == [
        ("team1", 170),
        ("team3", 190),
    ]


def test_locked_out_team_is_dropped_even_when_fastest(arb, clock):
    add_player(arb, "a", "team1", 10)
    add_player(arb, "b", "team2", 10)
    epoch = open_race(arb, "a", "b", locked_out=("team1",))
    assert press(arb, clock, "a", epoch, rtt=10, reaction=150) is None
    assert arb.buzz_local("team1") is None
    press(arb, clock, "b", epoch, rtt=10, reaction=400)
    clock.at(10_000)
    assert arb.decide().winner == "team2"


def test_sub_human_reactions_are_flagged(arb, clock):
    add_player(arb, "bot", "team1", 10)
    epoch = open_race(arb, "bot")
    press(arb, clock, "bot", epoch, rtt=10, reaction=60)
    clock.at(10_000)
    assert arb.decide().entries[0].suspicious


def test_close_cancels_a_race_in_progress(arb, clock):
    add_player(arb, "p", "team1", 10)
    epoch = open_race(arb, "p")
    press(arb, clock, "p", epoch, rtt=10, reaction=200)
    arb.close()
    clock.at(10_000)
    assert arb.decide() is None


def test_presence_counts_players_per_team(arb):
    add_player(arb, "a", "team1", None)
    add_player(arb, "b", "team1", None)
    add_player(arb, "c", "team3", None)
    arb.leave("b")
    assert arb.presence(["team1", "team2", "team3"]) == {"team1": 1, "team2": 0, "team3": 1}


# ---------------------------------------------------------------------------
# The /buzz protocol: these keys are all a buzzer page ever learns.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "payload,keys",
    [
        (buzzer.team_payload("The Hackers"), {"name"}),
        (buzzer.open_payload(3), {"epoch"}),
        (buzzer.closed_payload(True), {"won"}),
        (buzzer.excluded_payload(), set()),
        (buzzer.ping_payload(7), {"n"}),
        (buzzer.revoked_payload(), set()),
    ],
)
def test_buzzer_page_payloads_carry_nothing_else(payload, keys):
    assert set(payload) == keys
