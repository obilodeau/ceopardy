# Design

## Context

A web race ends in `BuzzersPage._decide` → `BuzzArbiter.decide()` returns a
`Decision` (winner plus `Entry` list, fastest first, reactions rounded to
0.1 ms) → `routes.award_race` → `_award_buzz(winner, result_payload(decision))`
→ `_set_buzzers(False, winner=tid)` → `BuzzersPage.set_open(False, locked_out,
winner)`, which closes the arbiter and sends each page `closed` with
`closed_payload(won)`. The entries go to the host as `buzz-result` on `/game`.

Today `decide()` forgets the race, and any later press is recorded as an early
press for the next race.

Online, every `_award_buzz` comes from a decided race: keyboard buzzes go
through `buzz_local` into the arbiter. Offline there is no guest server.

`tests/test_buzzer.py::test_buzzer_page_payloads_carry_nothing_else` pins the
exact keys of every `/buzz` payload.

## Goals / Non-Goals

**Goals:**

- Keep deciding the race separate from reporting margins: the window, the
  judging and `closed` stay as they are.
- Each team's pages learn their place and margin once, as soon as it is known,
  including teams that buzz after the decision.
- Nothing about other teams beyond those two numbers reaches a page.

**Non-Goals:**

- Showing a player their own reaction time, or a personal margin when a
  teammate's faster buzz was the one that counted.
- Late keyboard buzzes: the host's `/buzz` route ignores presses once buzzers
  are closed, and that stays.
- Showing margins on the viewer, or changing the host's result line beyond
  adding places and late teams.

## Decisions

**The arbiter keeps the decided race until the next opening.** `decide()`
stores the `Decision` it returns. While one is stored, a `buzz()` carrying
its epoch from a team not yet placed and not locked out is judged as usual
(the player's `open_sent` is still set) and appended to the stored entries.
It is not an early press. Any other press while closed stays an early press,
as today. `buzz()` returns a `BuzzOutcome` with `delay` (start of a window,
as today) or `late` (the updated `Decision`), so `on_buzz` knows which
follow-up to run. The stored decision is dropped by `open()` and by
`close(keep_result=False)`. `set_open(False, ..., winner)` passes
`keep_result=winner is not None`, so the award's own close keeps it and a
host close without a winner, such as hiding the question, drops it. That
matches the page, which clears its line on that `closed`.

**Standing is a pure function in `ceopardy/buzzer.py`.**
`standing(decision: Decision, tid: str) -> tuple[int, int | None] | None`
returns `(place, margin_ms)` for an entered team and `None` otherwise. Place
is the 1-based index in `entries`. Margin is rounded to whole ms: for the
winner, the second entry minus the winner, or `None` when it is alone; for
others, their reaction minus the winner's, floored at 0. Ties keep the
arbiter's order (earliest arrival first) and show `+0 ms`. Late entries are
appended, never sorted in, so places already sent stay true. Rounding the
difference, not each reaction, matches the host line closely enough; the
host rounds each side, so the two may differ by 1 ms.

**Standings are sent once per team, by `BuzzersPage`.** A new
`standing_payload(place, margin_ms)` returns `{"place", "margin_ms"}`. After
`_decide`, `on_decision` returns whether the race was awarded (`award_race`
already drops a race the host closed while it was judged). Only then does
the page send `standing` to each entered team's room. On a late entry it
sends `standing` to the new team's room, and, if the winner had been alone,
the winner's first margin to the winner's room. It then calls a new
`on_late(decision)`, which `routes` wires to emit `buzz-result` with
`result_payload(decision)`. `closed` and the award path are unchanged, so the
`Decision` never travels through `_award_buzz` or `_set_buzzers`.

**The page shows a second line.** `BuzzerApp.vue` keeps a `margin` ref set
from `standing`: `"8 ms ahead"` when `place` is 1 and `margin_ms` is set,
`` `${ordinal(place)} · +${margin_ms} ms` `` when `place` is above 1, `""`
otherwise. It is cleared on `open`, `excluded` and a `closed` with no
winner. It renders in a `<p class="margin">` under the status, smaller than
the status text. The `role="status"` live region moves from the status
paragraph to a wrapper around both, so screen readers announce the margin
when it arrives. The `early` phase leaves it alone. `ordinal(n: number):
string` lives in `frontend/src/ordinal.ts`, next to `throttle.ts`, since the
host view uses it too; it handles 11th–13th.

**The host's places are a muted prefix.** In `HostView.vue`, `buzzResult`
gives each entry a `place` (`ordinal(i + 1)`) besides its `text`, and the
template renders it as `<span class="buzz-place">` before the text. In
`main.css`, `.buzz-place` is about 0.8em with reduced opacity and a small
right margin, and is excluded from the existing `span + span::before`
separator so the ` · ` still sits only between entries. The place comes from
the entries' order, which is the server's order now that late entries are
appended. The store already replaces `lastBuzz` on every `buzz-result`, so a
re-sent result just extends the line.

## Risks / Trade-offs

- [A team learns how far behind it was, a hint of the winner's reaction] →
  Accepted: the issue asks for exactly this, and without the winner's name or
  absolute time it reveals nothing actionable.
- [A late team can have a faster judged reaction than an in-window entrant,
  since players received the open cue at different times] → It still takes
  the next place, and its margin can be smaller than the one above it. Rare,
  and keeping places fixed is simpler than sending corrections. Its margin is
  floored at `+0 ms` in the unlikely case it beat the winner.
- [Margins come from judged reactions, which clamp a cheating client] → The
  numbers match what the host settles disputes on.
- [Page and host line differ by 1 ms from rounding] → Accepted.
- [A host close right after the award can race a standing still being sent]
  → The page may show a stale line until the next question opens. Accepted:
  the window is a few milliseconds.
- [Teammates who did not buzz see the team's place] → Intended: the team is
  the unit that races.
