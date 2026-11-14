# buzzer-race Specification

## Purpose
Defines how the server decides which team buzzed first, for keyboard and web
buzzers in both modes, and how each team learns its place and margin. For web
players, latency compensation keeps a player's distance from the server from
deciding the winner, and a modified client can gain only a small, bounded and
host-visible margin.

## Requirements

### Requirement: The race starts when the page receives the open cue
A web buzz SHALL be judged on the player's reaction time, measured by the buzzer page from the moment it received the open cue to the press, using a monotonic clock. Client and server clocks SHALL NOT be compared.

#### Scenario: Far, faster player wins
- **WHEN** a player on a 300 ms link reacts in 210 ms and a player on a 5 ms link reacts in 260 ms
- **THEN** the player on the 300 ms link wins

### Requirement: The server measures each player's latency
The server SHALL sample each connected player's round-trip time from a ping every 2 seconds and from the acknowledgement of the open cue, and use the median of recent samples capped at the RTT cap (250 ms by default). A player with no samples SHALL be treated as having the capped RTT.

#### Scenario: Slow link
- **WHEN** a player's recent round-trip times are around 400 ms
- **THEN** their latency is taken as 250 ms under the default cap

### Requirement: Reported reactions are bounded by the server's estimate
The server SHALL estimate each reaction as the time since it sent the open cue to that player minus their latency. The reaction used SHALL be the reported one, raised to at least that estimate minus the jitter tolerance (50 ms by default), and kept between zero and the elapsed time.

#### Scenario: Honest client
- **WHEN** a client reports a reaction close to the server's estimate
- **THEN** the reported reaction is used as is

#### Scenario: Client claims 0 ms
- **WHEN** a client reports a reaction of 0 ms
- **THEN** its reaction is taken as the server's estimate minus the tolerance, gaining at most 50 ms

#### Scenario: Reaction longer than possible
- **WHEN** a client reports a reaction longer than the time since the open cue was sent
- **THEN** the elapsed time is used instead

### Requirement: Faked latency gains at most the RTT cap
A client that delays its ping replies to look farther away SHALL gain no more than the RTT cap minus its real round-trip time plus the jitter tolerance.

#### Scenario: Inflated pings
- **WHEN** a client delays its ping replies by several seconds and claims a 0 ms reaction
- **THEN** its latency counts as at most 250 ms

### Requirement: Malformed reactions fall back to the server estimate
A buzz whose reported reaction is missing, not a number, a boolean, or not finite SHALL be judged on the server's own estimate.

#### Scenario: Garbage value
- **WHEN** a buzz reports its reaction as the string `"fast"`
- **THEN** the server judges it on its own estimate

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

### Requirement: A team counts once with its best player
A team's reaction SHALL be the lowest among its players' buzzes in the race. Further buzzes from the same team SHALL NOT count again. Ties SHALL go to the earliest arrival.

#### Scenario: Two teammates
- **WHEN** two players on team 1 buzz in the same race
- **THEN** team 1 is entered once, with the faster of the two reactions

#### Scenario: Tie
- **WHEN** two teams have the same judged reaction
- **THEN** the team whose buzz arrived first wins

### Requirement: Each opening is a separate race
Each time buzzers open SHALL start a new numbered race, sent with the open cue and echoed by each web buzz. A buzz for an older race SHALL NOT count. A buzz while buzzers are closed SHALL NOT count, with one exception: after the decision, the first buzz for that race of a team not yet in it and not locked out, from a page or the keyboard, SHALL be judged as any other and count for its standing only, never for the win. Closing the buzzers SHALL cancel a race in progress.

#### Scenario: Stale press
- **WHEN** a buzz names a race that has since been closed and re-opened
- **THEN** it does not count in the new race

#### Scenario: Host closes during the window
- **WHEN** the host locks the buzzers while a race's window is running
- **THEN** no team is awarded the buzz

#### Scenario: Buzz after the decision
- **WHEN** team 3 buzzes after team 2 was declared the winner
- **THEN** team 2 keeps the buzz and team 3 is given a standing

### Requirement: Locked-out teams cannot enter
A buzz from a team locked out of the clue SHALL NOT enter the race, even when it would be fastest. Its pages SHALL be told they are excluded instead of receiving the open cue.

#### Scenario: Fastest but locked out
- **WHEN** a locked-out team's player presses faster than everyone else
- **THEN** another team wins

### Requirement: Early presses cost a lockout
A press while buzzers are closed SHALL be recorded for that player and shown on the page as too early. If the next open cue reaches that player within the early lockout (250 ms by default) of the press, their reaction in that race SHALL be at least the lockout time remaining. A press earlier than that SHALL cost nothing.

#### Scenario: Hammering before the cue
- **WHEN** a player presses 100 ms before the open cue reaches them
- **THEN** their reaction in that race counts as at least 150 ms

#### Scenario: Press long before
- **WHEN** a player presses a second before the open cue
- **THEN** their next reaction is judged normally

### Requirement: Inhuman reactions are flagged, not rejected
A judged reaction below the human floor (100 ms by default) SHALL be flagged to the host. It SHALL still count, so the host settles it as any other dispute.

#### Scenario: Bot-fast press
- **WHEN** a team's judged reaction is 40 ms
- **THEN** it can win and is marked as suspicious for the host

### Requirement: The race result is announced
When a race is decided, the winner SHALL be awarded the buzz as for any buzz. Each buzzer page SHALL be told whether its team won. The host SHALL receive every entered team's reaction, fastest first, with the flags. Pages receive no other team's numbers.

#### Scenario: Decision
- **WHEN** team 2 wins a race against team 1
- **THEN** team 2's pages say they won, team 1's say another team was faster, and the host receives both teams' reactions

### Requirement: The host sees the result line
After a race, in either mode, the host view SHALL show a line naming each entrant in place order with its place, the winner with its reaction and each other entrant with its margin, never below zero, for example `1st Team 2 212 ms · 2nd Team 1 +48 ms`, with a warning icon on flagged reactions. The place SHALL be set smaller and dimmer than the team and time. A team that buzzes after the decision SHALL be added at the end of the line. The line SHALL clear when a question is shown or hidden.

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

### Requirement: Race tuning is configurable
The RTT cap, jitter tolerance, early lockout, human floor and per-team player limit SHALL be configuration values with defaults of 250 ms, 50 ms, 250 ms, 100 ms and 16 players.

#### Scenario: Defaults
- **WHEN** the operator changes nothing
- **THEN** races use a 250 ms RTT cap, 50 ms tolerance, 250 ms early lockout and 100 ms human floor

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
A team whose first buzz in a race, from a page or the keyboard, arrives after the decision SHALL be given its standing then, taking the next place; places already given SHALL NOT change. A winner that was alone SHALL be given its margin when the first team buzzes after it. Margins SHALL never be below zero. Nothing SHALL be reported for a late buzz once the next race opened or buzzers closed without a winner. Standings SHALL stop when buzzers open again or the host closes them without a winner.

#### Scenario: Late buzz
- **WHEN** team 2 won alone at 212 ms and team 1 then buzzes with a judged reaction of 900 ms
- **THEN** team 1's pages are told they were second and 688 ms behind, and team 2's that they were 688 ms ahead

#### Scenario: Late keypress
- **WHEN** team 2 won and key `3` is pressed afterwards
- **THEN** the host's line gains team 3 with the next place and its margin

#### Scenario: Places stay
- **WHEN** team 1 was given second place and team 3 then buzzes with a faster judged reaction than team 1's
- **THEN** team 3 is given third place and team 1's standing does not change

#### Scenario: Late entrant faster than a sole winner
- **WHEN** team 2 won alone at 212 ms and team 1's late buzz is judged at 200 ms
- **THEN** team 1 is second at `+0 ms` on its pages and the host's line, and team 2's pages read `0 ms ahead`

#### Scenario: Host closes the buzzers
- **WHEN** the host locks the buzzers without a winner
- **THEN** no team is given a standing for that race

#### Scenario: Correcting a slider after the award
- **WHEN** team 2 was awarded the buzz and the host moves a locked-out team's slider back to *No Answer*
- **THEN** standings already given stay and a later buzz from team 3 is still given one

#### Scenario: Locked out after the award
- **WHEN** team 2 was awarded the buzz and the host then marks team 3 locked out while buzzers stay closed
- **THEN** a later buzz from team 3 is given no standing

#### Scenario: Game finished
- **WHEN** the host finishes the game after a race
- **THEN** no team is given a standing for that race afterwards

#### Scenario: Next race
- **WHEN** buzzers open again and a team presses with the previous race's number
- **THEN** it is given no standing
