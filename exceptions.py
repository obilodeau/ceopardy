"""Domain exceptions for ceopardy.

A leaf module so any other module (controller, utils, api/routes, tests…)
can import these without creating circular imports.
"""


class GameProblem(Exception):
    """Generic game-state / rules violation."""


class UnknownTeamError(GameProblem):
    """Raised when a team id is not present in the current game."""


class InvalidQuestionId(Exception):
    """Raised when a question id cannot be parsed into (col, row)."""


class QuestionParsingError(Exception):
    """Raised when the Questions file cannot be parsed."""


class GamefileParsingError(Exception):
    """Raised when a .round (game) file cannot be parsed."""
