# Spec Delta

## Purpose

Plays the round file's final question as a Final Jeopardy round in online
games: teams wager and answer by hand, the host reveals and judges each team,
then the game ends.

## ADDED Requirements

### Requirement: Final round starts from "Finish the game" online
When the host finishes the game in online mode and the round file declares a
final question, the system SHALL enter the Final Jeopardy round in its
category phase instead of ending the game.

#### Scenario: Online game with a final question
- **WHEN** the server runs with `--online`, the round file has a `final: [Category] clue` line, and the host finishes the game
- **THEN** the game state becomes `in_final`, the phase becomes `category`, and the viewer shows "Final Jeopardy" with the category, without the clue

#### Scenario: Any open clue is cleared
- **WHEN** the final round starts while a clue, Daily Double, or open buzzers are active
- **THEN** the clue and Daily Double are cleared and the buzzers are closed

### Requirement: Finishing without a final round ends the game
When the game is not in online mode, or the round file has no final question,
finishing the game SHALL end it immediately.

#### Scenario: Offline game with a final question
- **WHEN** the server runs without `--online`, the round file has a final question, and the host finishes the game
- **THEN** the game state becomes `finished` and the viewer shows the end-of-game message

#### Scenario: Online game without a final question
- **WHEN** the server runs with `--online`, the round file has no final question, and the host finishes the game
- **THEN** the game state becomes `finished`

### Requirement: Host advances the phases in order
The final round SHALL move through the phases `category`, `clue`, `locked`
and `finished` only forward and only when the host asks. A request to move to
any phase other than the next one SHALL be rejected without changing state.

#### Scenario: Reveal the clue
- **WHEN** the phase is `category` and the host reveals the clue
- **THEN** the phase becomes `clue` and the viewer shows the final clue

#### Scenario: Lock the answers
- **WHEN** the phase is `clue` and the host locks the answers
- **THEN** the phase becomes `locked`

#### Scenario: Skipping a phase is rejected
- **WHEN** the phase is `category` and the host asks to lock the answers
- **THEN** the request fails with an error and the phase stays `category`

### Requirement: Buzzers stay closed during the final round
The buzzers SHALL stay closed for the whole final round. A request to open
them, and any buzz, SHALL be ignored.

#### Scenario: Host tries to open the buzzers
- **WHEN** the game is `in_final` and the host asks to open the buzzers
- **THEN** the request fails and the buzzers stay closed

### Requirement: Host reveals one team's drawings at a time
Once the phase is `locked`, the host SHALL be able to reveal any team. The
viewer then shows that team's name, wager drawing and answer drawing. Before a
team is revealed, its drawings SHALL NOT be sent to the viewer.

#### Scenario: Reveal a team
- **WHEN** the phase is `locked` and the host reveals Team 2
- **THEN** the viewer shows Team 2's name with its wager and answer drawings

#### Scenario: Reveal before answers are locked
- **WHEN** the phase is `clue` and the host asks to reveal a team
- **THEN** the request fails and nothing is sent to the viewer

#### Scenario: Unrevealed drawings stay off the viewer
- **WHEN** the phase is `locked` and only Team 1 has been revealed
- **THEN** no state or event the viewer receives contains Team 2's or Team 3's drawings

### Requirement: Host previews drawings before revealing them
From the `locked` phase on, the host SHALL see every team's wager and answer
drawings, so they can read them before revealing them.

#### Scenario: Host reads a wager ahead of the reveal
- **WHEN** the phase is `locked`
- **THEN** the host view shows each team's wager and answer drawings, whether or not the team has been revealed

### Requirement: Wager amount is bounded by the team's score
When judging a team, the host SHALL enter the wager amount read from its
drawing. The amount MUST be an integer from 0 to the team's score before
the final round. A team at zero or below can wager only 0.

#### Scenario: Wager within bounds
- **WHEN** Team 1 has 1200 points before the final and the host judges it with a wager of 1000
- **THEN** the judgment is accepted

#### Scenario: Wager above the score
- **WHEN** Team 1 has 1200 points before the final and the host judges it with a wager of 1500
- **THEN** the judgment is rejected with an error and no score changes

#### Scenario: Team with a negative score
- **WHEN** Team 3 has -200 points before the final
- **THEN** the only wager the host can enter for Team 3 is 0

### Requirement: Judgment adds or subtracts the wager
The host SHALL judge each team's final answer as right, wrong, or not
attempted. A right answer adds the wager to the team's score, a wrong one
subtracts it, and not attempted leaves the score unchanged. Judging a team
again SHALL replace its previous judgment.

#### Scenario: Right answer
- **WHEN** Team 1 has 1200 points and is judged right with a wager of 1000
- **THEN** Team 1's score becomes 2200 on the host and the viewer

#### Scenario: Re-judging corrects a mistake
- **WHEN** Team 1 was judged right with 1000, and the host then judges it wrong with 1000
- **THEN** Team 1's score becomes 200

### Requirement: Host ends the game after the final round
In the `locked` phase the host SHALL be able to end the game, whether or not
every team has been revealed or judged. The game state then becomes
`finished` and the viewer shows the final scores.

#### Scenario: End after judging
- **WHEN** every team is judged and the host ends the game
- **THEN** the game state becomes `finished` and the viewer shows each team's final score

### Requirement: Final round survives a reload
The host and viewer SHALL restore the current phase, the category, the clue
once revealed, the revealed team, and the judgments when they reload during
the final round.

#### Scenario: Viewer reloads mid-reveal
- **WHEN** Team 2 is revealed and the viewer page reloads
- **THEN** the viewer shows Team 2's drawings again

#### Scenario: Viewer reloads before the clue
- **WHEN** the phase is `category` and the viewer page reloads
- **THEN** the viewer shows the category and not the clue
