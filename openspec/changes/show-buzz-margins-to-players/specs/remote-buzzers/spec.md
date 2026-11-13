# Spec Delta

## MODIFIED Requirements

### Requirement: The buzzer page sees only its own team
The buzzer page SHALL receive only: its team's name (on connect and on rename), buzzers opening with a race number, buzzers closing with whether its team won, its team's place and margin in a race it entered, being excluded as a locked-out team, latency pings, and link revocation. It SHALL NOT receive scores, other teams' names or reactions, questions, answers, the board or game broadcasts.

#### Scenario: Rename
- **WHEN** the host renames team 1
- **THEN** team 1's buzzer pages show the new name and no other page receives it

#### Scenario: Question selected
- **WHEN** the host selects a question
- **THEN** the buzzer page learns only that buzzers are open, not the question text

#### Scenario: Race decided
- **WHEN** team 2 beats team 1 by 8 ms
- **THEN** team 1's pages learn they were second by 8 ms, but not team 2's name or reaction

## ADDED Requirements

### Requirement: Buzzer page shows how close the race was
When told its team's standing, the buzzer page SHALL show the margin in whole milliseconds under the won or lost message: `8 ms ahead` for the first place, and the place with the margin behind the winner, such as `2nd · +8 ms`, for any other. The line SHALL clear when buzzers open again, when the team is excluded, or when the host closes the buzzers without a winner.

#### Scenario: Winner
- **WHEN** the player's team wins by 8 ms over the runner-up
- **THEN** the page reads "You're in! Answer now." and `8 ms ahead`

#### Scenario: Runner-up
- **WHEN** the player's team finishes second, 8 ms behind the winner
- **THEN** the page reads "Another team was faster." and `2nd · +8 ms`

#### Scenario: Buzzing after the decision
- **WHEN** the page shows "Another team was faster." with no margin and the player then buzzes
- **THEN** the page adds its team's place and margin, such as `3rd · +640 ms`

#### Scenario: No margin to show
- **WHEN** the player's team won alone with nobody buzzing after, or never buzzed
- **THEN** the page shows its won or lost message with no margin line

#### Scenario: Next question
- **WHEN** buzzers open for the next question
- **THEN** the margin line is gone
