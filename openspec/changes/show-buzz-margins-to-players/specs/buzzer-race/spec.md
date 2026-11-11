# Spec Delta

## MODIFIED Requirements

### Requirement: The race result is announced
When a race is decided, the winner SHALL be awarded the buzz as for any buzz. Each buzzer page SHALL be told whether its team won. The pages of each entered team SHALL also be told its place and its margin, both from the judged reactions: the winner how far ahead of the runner-up it was, every other entrant how far behind the winner. The host SHALL receive every entered team's reaction, fastest first, with the flags. Pages receive no other team's name or reaction.

#### Scenario: Decision
- **WHEN** team 2 wins a race against team 1
- **THEN** team 2's pages say they won, team 1's say another team was faster, and the host receives both teams' reactions

#### Scenario: Close race
- **WHEN** team 2's judged reaction is 212 ms, team 1's 220 ms and team 3's 412 ms
- **THEN** team 2's pages are told they were first and 8 ms ahead, team 1's second and 8 ms behind, team 3's third and 200 ms behind

#### Scenario: Sole entrant
- **WHEN** only team 2 buzzes in a race
- **THEN** team 2's pages are told they won with no margin

#### Scenario: Team that did not buzz
- **WHEN** team 3 has players connected but none of them buzz in a race team 2 wins
- **THEN** team 3's pages are told another team was faster, with no place or margin

#### Scenario: Keyboard entrant
- **WHEN** a keyboard buzz for team 1 wins a race against a web buzz from team 2
- **THEN** team 2's pages are told they were second, with their margin behind team 1

#### Scenario: Host closes the buzzers
- **WHEN** the host locks the buzzers without a winner
- **THEN** no page is told a place or margin

### Requirement: The host sees the result line
After a web race, the host view SHALL show a line naming each entrant fastest first with its place, the winner with its reaction and each other entrant with its margin, for example `1st Team 2 212 ms · 2nd Team 1 +48 ms`, with a warning icon on flagged reactions. The place SHALL be set smaller and dimmer than the team and time. The line SHALL clear when a question is shown or hidden.

#### Scenario: Result line
- **WHEN** a race is decided
- **THEN** the host view shows each entered team's place and reaction or margin, fastest first

#### Scenario: Places match the pages
- **WHEN** team 1's pages show `2nd · +8 ms`
- **THEN** the host's line shows team 1 as 2nd

#### Scenario: Next clue
- **WHEN** the host selects another question
- **THEN** the result line is gone
