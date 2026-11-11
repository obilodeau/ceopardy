# Spec Delta

## Purpose

Lets a game be played as one round or as two consecutive rounds by the same
teams, each round on its own board from its own round file, with scores
accumulating across rounds like a real Jeopardy game.

## ADDED Requirements

### Requirement: Round count is chosen when a new game starts
Starting a new game SHALL set its number of rounds to 1 or 2, chosen by the host on the start screen before picking the round 1 file. A new game request that leaves the count out SHALL make a one-round game. Any other count SHALL be rejected without touching the current game.

#### Scenario: Two-round game
- **WHEN** the host chooses two rounds and picks `1st.round`
- **THEN** the game starts on round 1 of 2 with the board from `1st.round`

#### Scenario: Count left out
- **WHEN** a new game request names a round file but no round count
- **THEN** the game starts as a one-round game

#### Scenario: Invalid count
- **WHEN** a new game request asks for 3 rounds
- **THEN** the request is rejected and the current game, if any, is unchanged

### Requirement: The game state reports the round
The game state sent to the host and the viewer SHALL include the current round number and the game's number of rounds, and SHALL report a game between rounds as such.

#### Scenario: Reload during round 2
- **WHEN** the host page is reloaded during round 2 of a two-round game
- **THEN** the state it loads reports round 2 of 2

### Requirement: Finishing round 1 of a two-round game ends the round
In a two-round game, the host's finish control during round 1 SHALL end the round, not the game: the active clue and any daily double are cleared, the crowd screen shows an end-of-round message, and the game is between rounds. The host's confirmation SHALL say that the round, not the game, is ending.

#### Scenario: End of round 1
- **WHEN** the host confirms finish during round 1 of a two-round game
- **THEN** the crowd screen shows the end-of-round message, the host lands on the start screen, and the game is between rounds

#### Scenario: Confirmation wording
- **WHEN** the host clicks finish during round 1 of a two-round game
- **THEN** the confirmation says round 1 is ending and round 2 comes next

### Requirement: The host picks the round 2 file between rounds
While the game is between rounds, the start screen SHALL offer to start round 2 from any available round file, alongside resuming round 1 and starting a new game. The host page SHALL send the host to the start screen while the game is between rounds.

#### Scenario: Start screen between rounds
- **WHEN** the host opens the start screen between rounds
- **THEN** it offers round 2 with the list of round files, resuming round 1, and a new game

#### Scenario: Host page between rounds
- **WHEN** the host opens the host page between rounds
- **THEN** they are sent to the start screen

### Requirement: Round 2 plays a fresh board for the same teams
Starting round 2 SHALL load the board from the chosen round file and show it with no clue answered. Teams, team names, buzzer links and the soundboard link SHALL stay unchanged, and no team or link SHALL be created or replaced.

#### Scenario: Board after starting round 2
- **WHEN** the host starts round 2 with `2nd.round`
- **THEN** the board shows the categories of `2nd.round` and every clue is unanswered

#### Scenario: Remote players stay connected
- **WHEN** round 2 starts in online mode
- **THEN** every team's buzzer link and the soundboard link keep working without being sent again

#### Scenario: Unreadable round file
- **WHEN** the host starts round 2 with a round file that fails to parse
- **THEN** the request fails, the game stays between rounds, and round 1's board is intact

### Requirement: Next-round requests are only accepted between rounds
A request to start the next round SHALL be rejected unless the game is between rounds.

#### Scenario: During a round
- **WHEN** a request to start the next round arrives during round 1
- **THEN** it is rejected and the game is unchanged

#### Scenario: One-round game finished
- **WHEN** a request to start the next round arrives after a one-round game finished
- **THEN** it is rejected and the game is unchanged

### Requirement: Scores accumulate across rounds
A team's score SHALL be the sum of its points from every round played so far. The daily double wager range SHALL use that cumulative score.

#### Scenario: Score carried into round 2
- **WHEN** a team ends round 1 with 1200 and earns 400 in round 2
- **THEN** its score shows 1600

#### Scenario: Daily double in round 2
- **WHEN** a team with 1200 from round 1 and nothing yet in round 2 finds a daily double
- **THEN** its maximum wager is 1200

### Requirement: Clue values are the same in every round
Each clue SHALL be worth its row times the configured score tick in every round, on the board and when scored.

#### Scenario: Round 2 clue value
- **WHEN** the score tick is 200 and a team answers the row 3 clue of round 2 correctly
- **THEN** the board labels that clue 600 and the team gains 600

### Requirement: Finishing the last round ends the game
Finishing the only round of a one-round game, or round 2 of a two-round game, SHALL end the game as a one-round game ends today.

#### Scenario: End of round 2
- **WHEN** the host confirms finish during round 2 of a two-round game
- **THEN** the crowd screen shows the end-of-game message and the game is finished

### Requirement: Resume returns to the round just finished
Resuming SHALL return to the round that was last finished, with its board and scores as they were. Between rounds, that is round 1.

#### Scenario: Round 1 ended by mistake
- **WHEN** the host resumes between rounds
- **THEN** round 1 is in progress again with its answered clues and scores as they were

#### Scenario: Resume after round 2
- **WHEN** the host resumes a finished two-round game
- **THEN** round 2 is in progress again and scores still include round 1

### Requirement: A new game can be started between rounds
Starting a new game between rounds SHALL back up the current game and start a fresh one, as it does after a finished game.

#### Scenario: Abandon after round 1
- **WHEN** the host starts a new game between rounds
- **THEN** the current database is kept as a timestamped backup and the new game starts from round 1 with zero scores

### Requirement: Databases from other versions are moved aside
On startup, a game database written with any schema version other than the current one SHALL be renamed to a timestamped backup next to it, and a fresh database SHALL be created. The server SHALL report the backup's path. A current database SHALL be left as it is.

#### Scenario: Upgrade with an old database
- **WHEN** the server starts in a game directory whose `ceopardy.db` was written by an earlier version
- **THEN** that file is renamed to a timestamped backup, the backup path is printed, and the start screen shows no game to resume

#### Scenario: Current database
- **WHEN** the server restarts during round 2 of a two-round game
- **THEN** the game is still on round 2 with its scores
