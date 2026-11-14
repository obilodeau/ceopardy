# Spec Delta

## MODIFIED Requirements

### Requirement: Keyboard buzzes race on arrival
In both modes, a keyboard buzz on the host SHALL enter the race with no latency correction, its reaction being the time from buzzers opening to its arrival.

#### Scenario: Keyboard against web
- **WHEN** a keyboard buzz arrives 300 ms after opening and a web player's judged reaction is 200 ms
- **THEN** the web player's team wins

#### Scenario: Keyboard only
- **WHEN** offline, key `2` arrives 400 ms after opening and key `1` 450 ms after
- **THEN** team 2 wins with 400 ms and team 1 is 50 ms behind

### Requirement: The first buzz opens a collection window
The first accepted buzz of a race SHALL start a window of the largest capped latency among web players sent the open cue in that race, plus the jitter tolerance. When the window ends, the team with the lowest reaction SHALL win. No decision SHALL be made before the window ends. When no web player was sent the open cue, the window SHALL be zero and the first buzz SHALL win at once.

#### Scenario: Later arrival wins
- **WHEN** a far player's faster press arrives after a near player's slower one but inside the window
- **THEN** the far player's team wins

#### Scenario: Window still running
- **WHEN** the window has not ended yet
- **THEN** no winner is declared

#### Scenario: No web players
- **WHEN** a keyboard buzz arrives and no web player was sent the open cue, offline or online
- **THEN** its team wins at once

### Requirement: Each opening is a separate race
Each time buzzers open SHALL start a new numbered race, sent with the open cue and echoed by each web buzz. A buzz for an older race or while buzzers are closed SHALL NOT count. After the decision, a team's first buzz for that race, from a page or the keyboard, SHALL be judged as any other and count for its standing only, never for the win. Closing the buzzers SHALL cancel a race in progress.

#### Scenario: Stale press
- **WHEN** a buzz names a race that has since been closed and re-opened
- **THEN** it does not count in the new race

#### Scenario: Host closes during the window
- **WHEN** the host locks the buzzers while a race's window is running
- **THEN** no team is awarded the buzz

#### Scenario: Buzz after the decision
- **WHEN** team 3 buzzes after team 2 was declared the winner
- **THEN** team 2 keeps the buzz and team 3 is given a standing

### Requirement: The host sees the result line
After a race, in either mode, the host view SHALL show a line naming each entrant in place order with its place, the winner with its reaction and each other entrant with its margin, for example `1st Team 2 212 ms · 2nd Team 1 +48 ms`, with a warning icon on flagged reactions. The place SHALL be set smaller and dimmer than the team and time. A team that buzzes after the decision SHALL be added at the end of the line. The line SHALL clear when a question is shown or hidden.

#### Scenario: Result line
- **WHEN** a race is decided
- **THEN** the host view shows each entered team's place and reaction or margin, fastest first

#### Scenario: Offline race
- **WHEN** offline, team 2 buzzes on the keyboard and team 1 follows 50 ms later
- **THEN** the host's line reads `1st Team 2 … · 2nd Team 1 +50 ms`

#### Scenario: Late team
- **WHEN** team 3 buzzes after the decision
- **THEN** the host's line gains team 3 at the end with the next place

#### Scenario: Places match the pages
- **WHEN** team 1's pages show `2nd · +8 ms`
- **THEN** the host's line shows team 1 as 2nd

#### Scenario: Next clue
- **WHEN** the host selects another question
- **THEN** the result line is gone

## ADDED Requirements

### Requirement: Each team is told its standing once
Each team that enters a race SHALL be given its place and its margin once, both from the judged reactions: the winner how far ahead of the runner-up it was, every other team how far behind the winner. The host's result line SHALL show it, and in online mode the team's buzzer pages SHALL be told it. Teams that buzzed before the decision SHALL be given it when the buzz is awarded. Further presses from a team already given one SHALL change nothing. Pages receive no other team's name or reaction.

#### Scenario: Close race
- **WHEN** team 2's judged reaction is 212 ms, team 1's 220 ms and team 3's 412 ms, all in the window
- **THEN** team 2's pages are told they were first and 8 ms ahead, team 1's second and 8 ms behind, team 3's third and 200 ms behind

#### Scenario: Sole entrant
- **WHEN** only team 2 buzzes in a race
- **THEN** team 2's pages are told they were first, with no margin

#### Scenario: Repeated presses
- **WHEN** a team already given its standing presses again, on a page or the keyboard
- **THEN** neither the pages nor the host's line change

#### Scenario: Team that never buzzes
- **WHEN** team 3 has players connected but none of them buzz before buzzers open again
- **THEN** team 3's pages are told no place or margin

#### Scenario: Keyboard entrant
- **WHEN** a keyboard buzz for team 1 wins a race against a web buzz from team 2
- **THEN** team 2's pages are told they were second, with their margin behind team 1

### Requirement: Teams that buzz after the decision are told their standing
A team whose first buzz in a race, from a page or the keyboard, arrives after the decision SHALL be given its standing then, taking the next place; places already given SHALL NOT change. A winner that was alone SHALL be given its margin when the first team buzzes after it. Standings SHALL stop when buzzers open again or the host closes them without a winner.

#### Scenario: Late buzz
- **WHEN** team 2 won alone at 212 ms and team 1 then buzzes with a judged reaction of 900 ms
- **THEN** team 1's pages are told they were second and 688 ms behind, and team 2's that they were 688 ms ahead

#### Scenario: Late keypress
- **WHEN** team 2 won and key `3` is pressed afterwards
- **THEN** the host's line gains team 3 with the next place and its margin

#### Scenario: Places stay
- **WHEN** team 1 was given second place and team 3 then buzzes with a faster judged reaction than team 1's
- **THEN** team 3 is given third place and team 1's standing does not change

#### Scenario: Host closes the buzzers
- **WHEN** the host locks the buzzers without a winner
- **THEN** no team is given a standing for that race

#### Scenario: Next race
- **WHEN** buzzers open again and a team presses with the previous race's number
- **THEN** it is given no standing
