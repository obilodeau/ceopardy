# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: A keyboard buzz in offline mode is awarded at once`
- TO: `### Requirement: Keyboard buzzes go through the race in both modes`

## MODIFIED Requirements

### Requirement: A keyboard buzz is judged by the server
A keypress on the host for team N (keys 1 to the number of teams) SHALL be sent to the server, whether or not the buzzers are open. The server SHALL accept it while buzzers are open and the team is not locked out. After a race is decided, it SHALL accept the first keypress of each team not yet in the race, for the result only. Otherwise it is ignored. An unknown team SHALL be rejected.

#### Scenario: Buzz while open
- **WHEN** buzzers are open and the host machine receives key `2`
- **THEN** team 2 buzzes in

#### Scenario: Buzz while closed
- **WHEN** buzzers are closed with no race decided since they last opened, and the host machine receives key `2`
- **THEN** nothing happens

#### Scenario: Buzz after the decision
- **WHEN** team 1 was awarded the buzz and the host machine then receives key `2`
- **THEN** team 1 keeps the buzz and team 2 is added to the race result

#### Scenario: Two windows, one keypress
- **WHEN** two host windows each forward the same keypress
- **THEN** the buzz is awarded at most once

### Requirement: Keyboard buzzes go through the race in both modes
In both modes, an accepted keyboard buzz SHALL enter the buzzer race, judged on its arrival, so the race result and margins cover keyboard buzzers too. When no web player is in the race, which is always the case offline, the race SHALL be decided on the first buzz, without a collection window.

#### Scenario: Offline keypress
- **WHEN** buzzers are open in offline mode and key `1` is pressed
- **THEN** team 1 is awarded the buzz straight away

#### Scenario: Offline result
- **WHEN** buzzers are open in offline mode, key `1` is pressed, then key `3`
- **THEN** team 1 is awarded the buzz and the host's result line shows team 1 first and team 3 second with its margin

#### Scenario: Hybrid event
- **WHEN** buzzers are open in online mode and key `3` is pressed while remote players also buzz
- **THEN** the winner is decided by the buzzer race rules, with team 3 as one of the entrants

## REMOVED Requirements

### Requirement: A keyboard buzz in online mode races web buzzers
**Reason**: Keyboard buzzes now race in both modes; "Keyboard buzzes go through the race in both modes" covers the online case.
**Migration**: None. Online behavior is unchanged: a keyboard buzz still enters the same race as web buzzes.
