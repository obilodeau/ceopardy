# Design

## Context

A web race ends in `BuzzersPage._decide` → `BuzzArbiter.decide()` returns a
`Decision` (winner plus `Entry` list, fastest first, reactions rounded to
0.1 ms) → `routes.award_race` → `_award_buzz(winner, result_payload(decision))`
→ `_set_buzzers(False, winner=tid)` → `BuzzersPage.set_open(False, locked_out,
winner)`, which sends each page `closed` with `closed_payload(won)`. Only the
winner's tid survives the trip to the pages; the entries go to the host as
`buzz-result` on `/game`.

Online, every `_award_buzz` comes from a decided race: keyboard buzzes go
through `buzz_local` into the arbiter. Offline there is no guest server.

`tests/test_buzzer.py::test_buzzer_page_payloads_carry_nothing_else` pins the
exact keys of every `/buzz` payload.

## Goals / Non-Goals

**Goals:**

- Each entered team's pages learn their place and margin, computed once on the
  server from the same `Decision` the host sees.
- Nothing about other teams beyond those two numbers reaches a page.

**Non-Goals:**

- Showing a player their own reaction time, or a personal margin when a
  teammate's faster buzz was the one that counted.
- Showing margins on the viewer, or changing the host's result line beyond
  adding places.

## Decisions

**Pass the `Decision` to the pages, not the winner.** `_award_buzz` takes
`decision: Decision | None` instead of a result dict, builds `result_payload`
itself when there is one, and hands the decision to `_set_buzzers(False,
decision=...)`, which passes it to `BuzzersPage.set_open(is_open, locked_out,
decision)`. The winner is `decision.winner`. Having `BuzzersPage` remember the
last decision from `_decide` was considered, but `award_race` may drop a
decision the host already closed, and the remembered one would then need
matching against the race epoch; passing it along the path that already
carries the winner avoids that state.

**Standing is a pure function in `ceopardy/buzzer.py`.**
`standing(decision: Decision, tid: str) -> tuple[int, int | None] | None`
returns `(place, margin_ms)` for an entered team and `None` otherwise. Place
is the 1-based index in `entries`. Margin is rounded to whole ms: for the
winner, runner-up minus winner, or `None` when it raced alone; for
others, their reaction minus the winner's. Ties keep the arbiter's order
(earliest arrival first) and show `+0 ms`. Rounding the difference, not each
reaction, matches the host line closely enough; the host rounds each side, so
the two may differ by 1 ms, which is acceptable.

**`closed` always carries the same keys.** `closed_payload(won, place=None,
margin_ms=None)` returns `{"won", "place", "margin_ms"}` with `null` when
there is nothing to show. Fixed keys keep the "carry nothing else" test exact
and the page's type simple. `set_open` calls `standing` per player's team.

**The page shows a second line.** `BuzzerApp.vue` keeps a `margin` ref set
from `closed`: `"8 ms ahead"` when `won` and `margin_ms` is set,
`` `${ordinal(place)} · +${margin_ms} ms` `` when lost with a place, `""`
otherwise. It is cleared on `open`, `excluded` and a `closed` with no
winner. It renders in a `<p class="margin">` under the status, smaller than
the status text. The `early` phase leaves it alone, so the line survives a
stray press after the race. `ordinal(n: number): string` lives in
`frontend/src/ordinal.ts`, next to `throttle.ts`, since the host view uses it
too; it handles 11th–13th.

**The host's places are a muted prefix.** In `HostView.vue`, `buzzResult`
gives each entry a `place` (`ordinal(i + 1)`) besides its `text`, and the
template renders it as `<span class="buzz-place">` before the text. In
`main.css`, `.buzz-place` is about 0.8em with reduced opacity and a small
right margin, and is excluded from the existing `span + span::before`
separator so the ` · ` still sits only between entries. The place comes from
the entries' order on the host, not from the server's standing: it is the
same order, and it needs no new field on `buzz-result`. A medal icon or a
colored badge was considered, but it would draw more attention than the
times, which are what the host settles disputes on.

## Risks / Trade-offs

- [A team learns how far behind it was, a hint of the winner's reaction] →
  Accepted: the issue asks for exactly this, and without the winner's name or
  absolute time it reveals nothing actionable.
- [Margins come from judged reactions, which clamp a cheating client] → The
  numbers match what the host settles disputes on; a player who sees an odd
  margin can ask the host, who sees the flags.
- [Page and host line differ by 1 ms from rounding] → Accepted; both say the
  same thing at human scale.
- [Teammates who did not buzz see the team's place] → Intended: the team is
  the unit that races.
