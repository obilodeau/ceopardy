# buzzer-race Specification

## Purpose
Defines how the server decides which team buzzed first in an online race, so
that a player's distance from the server does not decide the winner and a
modified client can gain only a small, bounded and host-visible margin.

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
In online mode, a keyboard buzz on the host SHALL enter the race with no latency correction, its reaction being the time from buzzers opening to its arrival.

#### Scenario: Keyboard against web
- **WHEN** a keyboard buzz arrives 300 ms after opening and a web player's judged reaction is 200 ms
- **THEN** the web player's team wins

### Requirement: The first buzz opens a collection window
The first accepted buzz of a race SHALL start a window of the largest capped latency among connected players with samples, plus the jitter tolerance. When the window ends, the team with the lowest reaction SHALL win. No decision SHALL be made before the window ends.

#### Scenario: Later arrival wins
- **WHEN** a far player's faster press arrives after a near player's slower one but inside the window
- **THEN** the far player's team wins

#### Scenario: Window still running
- **WHEN** the window has not ended yet
- **THEN** no winner is declared

### Requirement: A team counts once with its best player
A team's reaction SHALL be the lowest among its players' buzzes in the race. Further buzzes from the same team SHALL NOT count again. Ties SHALL go to the earliest arrival.

#### Scenario: Two teammates
- **WHEN** two players on team 1 buzz in the same race
- **THEN** team 1 is entered once, with the faster of the two reactions

#### Scenario: Tie
- **WHEN** two teams have the same judged reaction
- **THEN** the team whose buzz arrived first wins

### Requirement: Each opening is a separate race
Each time buzzers open SHALL start a new numbered race, sent with the open cue and echoed by each buzz. A buzz for an older race, while buzzers are closed, or after the decision SHALL NOT count. Closing the buzzers SHALL cancel a race in progress.

#### Scenario: Stale press
- **WHEN** a buzz names a race that has since been closed and re-opened
- **THEN** it does not count in the new race

#### Scenario: Host closes during the window
- **WHEN** the host locks the buzzers while a race's window is running
- **THEN** no team is awarded the buzz

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
After a web race, the host view SHALL show a line naming the winner with its reaction and each other entrant with its margin, for example `Team 2 212 ms · Team 1 +48 ms`, with a warning icon on flagged reactions. The line SHALL clear when a question is shown or hidden.

#### Scenario: Result line
- **WHEN** a race is decided
- **THEN** the host view shows each entered team's reaction or margin, fastest first

#### Scenario: Next clue
- **WHEN** the host selects another question
- **THEN** the result line is gone

### Requirement: Race tuning is configurable
The RTT cap, jitter tolerance, early lockout, human floor and per-team player limit SHALL be configuration values with defaults of 250 ms, 50 ms, 250 ms, 100 ms and 16 players.

#### Scenario: Defaults
- **WHEN** the operator changes nothing
- **THEN** races use a 250 ms RTT cap, 50 ms tolerance, 250 ms early lockout and 100 ms human floor
