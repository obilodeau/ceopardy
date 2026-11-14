# Spec Delta

## MODIFIED Requirements

### Requirement: Race tuning is configurable
The RTT cap, jitter tolerance, early lockout, human floor, close-race threshold and per-team player limit SHALL be configuration values with defaults of 250 ms, 50 ms, 250 ms, 100 ms, 500 ms and 16 players.

#### Scenario: Defaults
- **WHEN** the operator changes nothing
- **THEN** races use a 250 ms RTT cap, 50 ms tolerance, 250 ms early lockout, 100 ms human floor and 500 ms close-race threshold

### Requirement: Each opening is a separate race
Each time buzzers open SHALL start a new numbered race, sent with the open cue and echoed by each web buzz. A buzz for an older race, or while buzzers are closed, SHALL NOT count, except a team's first buzz for the race just decided, while its result is kept: from the keyboard, or from a page sent that race's open cue, by a team not yet in the race and not locked out. It SHALL be judged as any other and count for its standing only. Closing the buzzers SHALL cancel a race in progress.

#### Scenario: Stale press
- **WHEN** a buzz names a race that has since been closed and re-opened
- **THEN** it does not count in the new race

#### Scenario: Host closes during the window
- **WHEN** the host locks the buzzers while a race's window is running
- **THEN** no team is awarded the buzz

#### Scenario: Buzz after the decision
- **WHEN** team 3 buzzes after team 2 was declared the winner
- **THEN** team 2 keeps the buzz and team 3 is given a standing

#### Scenario: Unlocked after the award
- **WHEN** team 3 was locked out when the race opened, the host un-marks it after team 2's award, and a team 3 player presses on their page
- **THEN** the press doesn't count, since that page was never sent the race's open cue, while a team 3 keypress on the host still does

## ADDED Requirements

### Requirement: The viewer shows close margins on the team cards
In either mode, when a team is placed second or third in a race, at the decision or by its first buzz after it, and its margin behind the winner is at most the close-race threshold, the viewer SHALL show that margin, such as `+8 ms`, under the team name on its card. The margin SHALL flash in and SHALL use a different font from the team name. The team in control and every other card SHALL show no margin.

#### Scenario: Photo finish
- **WHEN** team 2 wins at 212 ms, team 1 follows at 220 ms and team 3 at 243 ms, under the default threshold
- **THEN** team 1's card shows `+8 ms`, team 3's card shows `+31 ms`, and team 2's card shows no margin

#### Scenario: Only the runner-up is close
- **WHEN** team 2 wins at 212 ms, team 1 follows at 240 ms and team 3 at 900 ms
- **THEN** team 1's card shows `+28 ms` and team 3's card shows none

#### Scenario: Not close
- **WHEN** the runner-up is 501 ms or more behind the winner under the default threshold
- **THEN** no card shows a margin

#### Scenario: Sole entrant
- **WHEN** only one team buzzes before the decision
- **THEN** no card shows a margin

#### Scenario: Tie
- **WHEN** two teams have the same judged reaction
- **THEN** the second team's card shows `+0 ms`

#### Scenario: Keyboard race offline
- **WHEN** offline, key `2` and then key `1` arrive 20 ms apart, so team 2 is awarded the buzz at once and key `1` lands after the decision
- **THEN** team 1's card shows `+20 ms`

### Requirement: Close margins fade when the race is over
The margins SHALL fade out when the host returns to the game board or the buzzers unlock again, whichever comes first. Returning to the board SHALL end the race, so no later buzz can bring a margin back. Clearing them SHALL NOT change which team is in control or its frame.

#### Scenario: Back to the board
- **WHEN** team 1's card shows `+8 ms`, team 2 is in control, and the host returns to the game board
- **THEN** the margin fades out and team 2's card keeps its frame

#### Scenario: Buzz after returning to the board
- **WHEN** the host returns to the game board after a race and key `3` is pressed
- **THEN** no card shows a margin and the host's result line is unchanged

#### Scenario: Wrong answer
- **WHEN** team 1's card shows `+8 ms` and the host marks team 2 *Bad*, which re-opens the buzzers
- **THEN** the margin fades out

#### Scenario: Scoring before returning
- **WHEN** team 1's card shows `+8 ms` and the host marks team 2's answer *Good* while the clue is still on screen
- **THEN** the margin stays until the host returns to the game board

### Requirement: A margin shown never changes
Once a card shows a margin, later buzzes in the same race SHALL NOT change or remove it. A team placed fourth or later SHALL NOT show a margin, however close.

#### Scenario: Close late buzz
- **WHEN** team 2 won alone at 212 ms and team 1's buzz after the decision is judged at 400 ms
- **THEN** team 1's card shows `+188 ms`

#### Scenario: Late team after a close race
- **WHEN** team 1's card shows `+8 ms` and team 3 then buzzes after the decision, judged 900 ms behind the winner
- **THEN** team 1's card still shows `+8 ms` and team 3's card shows none

#### Scenario: Fourth place
- **WHEN** in a four-team game, the fourth team is placed 40 ms behind the winner
- **THEN** its card shows no margin
