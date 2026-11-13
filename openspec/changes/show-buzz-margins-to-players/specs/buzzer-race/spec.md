# Spec Delta

## MODIFIED Requirements

### Requirement: Each opening is a separate race
Each time buzzers open SHALL start a new numbered race, sent with the open cue and echoed by each buzz. A buzz for an older race or while buzzers are closed SHALL NOT count. After the decision, a team's first buzz for that race SHALL be judged as any other and count for its standing only, never for the win. Closing the buzzers SHALL cancel a race in progress.

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
After a web race, the host view SHALL show a line naming each entrant in place order with its place, the winner with its reaction and each other entrant with its margin, for example `1st Team 2 212 ms · 2nd Team 1 +48 ms`, with a warning icon on flagged reactions. The place SHALL be set smaller and dimmer than the team and time. A team that buzzes after the decision SHALL be added at the end of the line. The line SHALL clear when a question is shown or hidden.

#### Scenario: Result line
- **WHEN** a race is decided
- **THEN** the host view shows each entered team's place and reaction or margin, fastest first

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
Each team that enters a race SHALL have its pages told its place and its margin once, both from the judged reactions: the winner how far ahead of the runner-up it was, every other team how far behind the winner. Teams that buzzed before the decision SHALL be told when the buzz is awarded. Further presses from a team already told SHALL send nothing. Pages receive no other team's name or reaction.

#### Scenario: Close race
- **WHEN** team 2's judged reaction is 212 ms, team 1's 220 ms and team 3's 412 ms, all in the window
- **THEN** team 2's pages are told they were first and 8 ms ahead, team 1's second and 8 ms behind, team 3's third and 200 ms behind

#### Scenario: Sole entrant
- **WHEN** only team 2 buzzes in a race
- **THEN** team 2's pages are told they were first, with no margin

#### Scenario: Repeated presses
- **WHEN** a player on a team already told its standing presses again, or a teammate does
- **THEN** no page is told anything new

#### Scenario: Team that never buzzes
- **WHEN** team 3 has players connected but none of them buzz before buzzers open again
- **THEN** team 3's pages are told no place or margin

#### Scenario: Keyboard entrant
- **WHEN** a keyboard buzz for team 1 wins a race against a web buzz from team 2
- **THEN** team 2's pages are told they were second, with their margin behind team 1

### Requirement: Teams that buzz after the decision are told their standing
A team whose first buzz in a race arrives after the decision SHALL be told its standing then, taking the next place; places already told SHALL NOT change. A winner that was alone SHALL be told its margin when the first team buzzes after it. Standings SHALL stop when buzzers open again or the host closes them without a winner.

#### Scenario: Late buzz
- **WHEN** team 2 won alone at 212 ms and team 1 then buzzes with a judged reaction of 900 ms
- **THEN** team 1's pages are told they were second and 688 ms behind, and team 2's that they were 688 ms ahead

#### Scenario: Places stay
- **WHEN** team 1 was told it was second and team 3 then buzzes with a faster judged reaction than team 1's
- **THEN** team 3 is told it was third and team 1 is told nothing new

#### Scenario: Host closes the buzzers
- **WHEN** the host locks the buzzers without a winner
- **THEN** no page is told a standing for that race

#### Scenario: Next race
- **WHEN** buzzers open again and a team presses with the previous race's number
- **THEN** it is told no standing
