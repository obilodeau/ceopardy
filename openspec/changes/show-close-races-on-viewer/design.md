# Design

## Context

Every race, keyboard or web, is decided in `routes._decide`, which emits
`buzz-result` on `/game` with `result_payload(decision)`: the winner and
every entry, fastest first. Late entries make `routes._publish_late` re-emit
`buzz-result` with the grown result. The host and the viewer share the Pinia
store (`frontend/src/stores/game.ts`), so the viewer already receives
`buzz-result`; it lands in `lastBuzz`, which `question-show` and
`question-hide` clear. Only the host renders it today.

The viewer's team cards are `TeamPanelViewer.vue`, laid out by `TeamRow.vue`
(and `TeamRowDailyDouble.vue` during a daily double): a score box over a name
box that uses the team's own script font (`team<N>-font`). The team in
control, which a buzz winner becomes, has the thick white `team-selected`
frame; this change leaves it alone. Buzzers unlock through the `buzzers`
event with `open: true`, on a new question and when a team is marked wrong.
Returning to the game board emits `question-hide`, and so does selecting a
daily double, before its own `dailydouble` event.

## Goals / Non-Goals

**Goals:**

- One decision, on the server, about which entries are close, so the viewer
  needs no threshold and can't disagree with the server.
- Offline keyboard races show margins even though they are decided on the
  first keypress.
- Margins that last while the clue is on screen and go away when the host
  returns to the board or the next race can start.

**Non-Goals:**

- Sound.
- Showing margins on the host or on buzzer pages; the host already has the
  full result line.
- Keeping margins across a viewer reload.

## Decisions

**The server names the close teams in `buzz-result`.** A pure
`close_entries(decision: Decision, threshold_ms: float) -> list[str]` in
`ceopardy/buzzer.py` returns the tids of the second and third entries whose
margin behind the winner, rounded to whole ms like the host's line, is at
most the threshold. `result_payload` gains a `close` list, filled from
`BUZZER_CLOSE_RACE_MS` by both `_decide` and `_publish_late`. Late entries
must count: offline, a race with no web player cued has no window and is
decided on the first keypress, so the runner-up's keypress, even 20 ms
later, is always a late entry. Late entries are appended and places never
change, so an entry's place and margin are final once it is in the result,
and publishing the close list again after a late entry can only add a team.
Holding the offline decision open for the threshold to collect presses was
considered and rejected: it would delay every award by up to 500 ms, against
the point of deciding at once. Having the viewer compare `reaction_ms`
against a threshold sent in the game state was considered too. It would need
the setting in `/api/v1/state`, and both sides would have to agree on it.

**The store keeps the margins apart from `lastBuzz`.** `lastBuzz` also
clears on `question-show`, while the cards' margins follow their own
lifetime. The store gets `closeMargins: Record<string, number>`, replaced
from each `buzz-result`'s `close` (each close tid's reaction minus the
winner's, rounded, floored at 0). A later result of the same race lists the
same close teams and maybe one more, so replacing the map never changes a
margin already shown. It is emptied on `question-hide` (back to the board, which
also covers a daily double) and on a `buzzers` event with `open: true`. It
never touches `ui_state.team`, so the team in control keeps its frame. A
`closeMarginOf(tid)` getter serves the cards, following the project's rule
of putting getters in the store.

**The margin is a line on the card, under the name.** `TeamPanelViewer.vue`
renders `+8 ms` in a `<p class="close-margin">` below the name inside the
name box, wrapped in a `<Transition name="close-margin">`. The name box
stacks its children in a column, so the name stays centered when there is no
margin. The margin uses the board's sans-serif font in the board's gold,
smaller than the name and with the scores' text shadow. Its entering
animation is a short flash: a bright glow pulsing two or three times within
about a second, then settling. Its leaving transition is a fade of about half
a second. Because `TeamRowDailyDouble` uses the same card and selecting a
daily double hides the question first, the daily-double layout never shows
one.

**The host's embedded viewer shows them too.** It is a real viewer, and
showing the operator what the crowd sees is its purpose.

## Risks / Trade-offs

- [At 500 ms most contested races qualify, so margins are frequent] →
  Intended: it's part of the show. `BUZZER_CLOSE_RACE_MS` tunes it.
- [A flagged (suspicious) reaction can make a race look close] → Accepted:
  the host sees the flag on its line and settles it as any dispute.
- [A long team name leaves little room for the margin on small cards] → The
  margin's font is sized with the viewport like the name, and the name box
  already wraps.
