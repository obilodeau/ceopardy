# Design

## Context

Online, the guest server's `BuzzersPage` owns a `BuzzArbiter` and its
decision timer. A web race ends in `BuzzersPage._decide` →
`BuzzArbiter.decide()` returns a `Decision` (winner plus `Entry` list,
fastest first, reactions rounded to 0.1 ms) → `routes.award_race` →
`_award_buzz(winner, result_payload(decision))` → `_set_buzzers(False,
winner=tid)` → `BuzzersPage.set_open(False, locked_out, winner)`, which
closes the arbiter and sends each page `closed` with `closed_payload(won)`.
The entries go to the host as `buzz-result` on `/game`. Keyboard buzzes reach
the same arbiter through `buzz_local`.

Offline there is no guest server and no arbiter: the `/buzz` route calls
`_award_buzz(tid)` directly, so there is no result line. The host view also
drops keypresses while buzzers are closed.

The window is the largest RTT among connected web players with samples, plus
the jitter tolerance, so a keyboard-only race online still waits 50 ms.

Today `decide()` forgets the race, and any later web press is recorded as an
early press for the next race.

`tests/test_buzzer.py::test_buzzer_page_payloads_carry_nothing_else` pins the
exact keys of every `/buzz` payload.

## Goals / Non-Goals

**Goals:**

- One race for every buzz, in both modes. Latency compensation and the window
  only where there are web players.
- Keep deciding the race separate from reporting margins: the judging and
  `closed` stay as they are.
- Each team's place and margin is given once, as soon as it is known,
  including teams that buzz after the decision, on the host's line and, for
  web players, on their pages.
- Nothing about other teams beyond those two numbers reaches a page.

**Non-Goals:**

- Early-press lockouts for keyboard buzzers: a keypress while closed and
  before any decision stays ignored.
- Showing a player their own reaction time, or a personal margin when a
  teammate's faster buzz was the one that counted.
- Showing margins on the viewer, or changing the host's result line beyond
  adding places and late teams.

## Decisions

**The game owns the race.** `create_app` builds one `BuzzArbiter` from
`FairnessSettings` as `app.arbiter`, in both modes. `start_guest_server`
hands it to `BuzzersPage` instead of the page building its own. `routes`
opens and closes it in `_set_buzzers` before telling the page, so
`BuzzersPage.set_open` only sends cues. The decision timer moves to `routes`
too: a buzz outcome with a delay schedules `_decide` on a `threading.Timer`
in an app context, and a zero delay decides inline. Offline, a keypress is
then awarded within the same `/buzz` request, as today, and `/buzz` keeps
returning `success` with the `tid` when it was. `award_race` keeps its
"buzzers still open" check; the inline path calls it without taking
`_buzz_lock` again. Keeping the arbiter in the guest page and adding a
second, keyboard-only path offline was considered, but two paths would give
two sets of rules for one race.

**No web player, no window.** `_window_ms` looks only at players sent the
open cue in this race (`open_sent` set). With none, the window is zero, so
`decide()` succeeds on the first buzz. Locked-out web players are never sent
the cue, so they no longer stretch the window either.

**The arbiter keeps the decided race until the next opening.** `decide()`
stores the `Decision` it returns. While one is stored, a buzz carrying its
epoch (web) or any keypress (keyboard) from a team not yet placed and not
locked out is judged as usual and appended to the stored entries. It is not
an early press. Any other web press while closed stays an early press, as
today; any other keypress is ignored. `buzz()` and `buzz_local()` return a
`BuzzOutcome` with `delay` (start of a window, as today) or `late` (the
updated `Decision`). The stored decision is dropped by `open()` and by
`close(keep_result=False)`. `_set_buzzers(False, winner=...)` closes with
`keep_result=winner is not None`, so the award's own close keeps it and a
host close without a winner, such as hiding the question, drops it.

**Late keypresses reach the server.** `HostView.onKeyPress` no longer returns
early when buzzers are closed. The `/buzz` route lets the arbiter decide:
open buzzers or a stored decision mean the press counts, otherwise it
returns `ignored`. Two host windows forwarding one keypress still enter the
team once.

**Standing is a pure function in `ceopardy/buzzer.py`.**
`standing(decision: Decision, tid: str) -> tuple[int, int | None] | None`
returns `(place, margin_ms)` for an entered team and `None` otherwise. Place
is the 1-based index in `entries`. Margin is rounded to whole ms: for the
winner, the second entry minus the winner, or `None` when it is alone; for
others, their reaction minus the winner's, floored at 0. Ties keep the
arbiter's order (earliest arrival first) and show `+0 ms`. Late entries are
appended, never sorted in, so places already given stay true. The host
rounds each side, so its line and a page may differ by 1 ms.

**`routes` reports standings; the page delivers them.** After an award,
`routes` emits `buzz-result` as today and, online, calls
`BuzzersPage.send_standings(decision, tids)` with every entered team. On a
late outcome it re-emits `buzz-result` with `result_payload(decision)` and
calls `send_standings` with the new team, plus the winner if it had been
alone. `send_standings` sends `standing` with
`standing_payload(place, margin_ms)` (`{"place", "margin_ms"}`) to each
team's room. A web buzz goes `BuzzersPage.on_buzz` → `app.arbiter.buzz` →
an `on_outcome` callback into `routes`, wired in an app context like
`on_decision` is today. `closed` and `_award_buzz` are unchanged, so the
`Decision` never travels through `_set_buzzers`.

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

- [Offline keyboard buzzes now go through the arbiter] → Same outcome as
  today, the first press is awarded within the request, but a bug in the
  race now affects offline games. Covered by tests of keyboard-only races.
- [A keyboard reaction includes the host machine's press-to-server time] →
  It is local and small, and the same for every keyboard team.
- [A team learns how far behind it was, a hint of the winner's reaction] →
  Accepted: the issue asks for exactly this, and without the winner's name or
  absolute time it reveals nothing actionable.
- [A late team can have a faster judged reaction than an in-window entrant,
  since players received the open cue at different times] → It still takes
  the next place, and its margin can be smaller than the one above it. Rare,
  and keeping places fixed is simpler than sending corrections. Its margin is
  floored at `+0 ms` in the unlikely case it beat the winner.
- [Page and host line differ by 1 ms from rounding] → Accepted.
- [A host close right after the award can race a standing still being sent]
  → The page may show a stale line until the next question opens. Accepted:
  the window is a few milliseconds.
- [Teammates who did not buzz see the team's place] → Intended: the team is
  the unit that races.
- [Web pages may now buzz after the decision] → A late buzz goes through the
  same clamps, counts once per team, and cannot change the winner or a place
  already given; all it reveals is the team's own margin. Presses after it
  cost what presses while closed cost today. A team's first late press is no
  longer an early press, which gains nothing: the lockout only applies within
  250 ms of the next open cue.
- [The keyboard `/buzz` route accepts presses while closed] → The host port
  binds to `127.0.0.1`, so players cannot reach it, and a late keypress
  cannot change the winner either.
- [Web buzzes now cross from the guest server into the game] → Only through
  `on_outcome`, after the arbiter has judged them, as `on_decision` does
  today. Players gain no new access to the game.
