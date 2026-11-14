# Spec Delta

## MODIFIED Requirements

### Requirement: Race tuning is configurable
The RTT cap, jitter tolerance, early lockout, human floor, close-race threshold and per-team player limit SHALL be configuration values with defaults of 250 ms, 50 ms, 250 ms, 100 ms, 500 ms and 16 players.

#### Scenario: Defaults
- **WHEN** the operator changes nothing
- **THEN** races use a 250 ms RTT cap, 50 ms tolerance, 250 ms early lockout, 100 ms human floor and 500 ms close-race threshold

## ADDED Requirements

### Requirement: The viewer shows close margins on the team cards
When a race is decided, in either mode, the viewer SHALL show the margin behind the winner, such as `+8 ms`, under the team name on the card of each second and third team whose margin is at most the close-race threshold. The margin SHALL flash in, and SHALL use a different font from the team name. The winner's card and every other card SHALL show no margin.

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
- **WHEN** offline, key `2` and then key `1` arrive 20 ms apart
- **THEN** team 2 is awarded the buzz and team 1's card shows `+20 ms`

### Requirement: Close margins fade when the race is over
The margins SHALL fade out when the host returns to the game board or the buzzers unlock again, whichever comes first. Clearing them SHALL NOT change which team is in control or its frame.

#### Scenario: Back to the board
- **WHEN** team 1's card shows `+8 ms`, team 2 is in control, and the host returns to the game board
- **THEN** the margin fades out and team 2's card keeps its frame

#### Scenario: Wrong answer
- **WHEN** team 1's card shows `+8 ms` and the host marks team 2 *Bad*, which re-opens the buzzers
- **THEN** the margin fades out

#### Scenario: Scoring before returning
- **WHEN** team 1's card shows `+8 ms` and the host marks team 2's answer *Good* while the clue is still on screen
- **THEN** the margin stays until the host returns to the game board

### Requirement: Late teams never show a close margin
Only teams in a race when it is decided SHALL be considered for close margins. A team that buzzes after the decision SHALL NOT show a margin, and the host's result line growing with late teams SHALL NOT change the margins shown.

#### Scenario: Close late buzz
- **WHEN** team 2 won alone at 212 ms and team 1's late buzz is judged at 400 ms
- **THEN** no card shows a margin

#### Scenario: Late team after a close race
- **WHEN** team 1's card shows `+8 ms` and team 3 then buzzes after the decision
- **THEN** team 1's card still shows `+8 ms` and team 3's card shows none
