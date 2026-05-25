# Ceopardy
# https://github.com/obilodeau/ceopardy/
#
# Olivier Bilodeau <olivier@bottomlesspit.org>
# Copyright (C) 2026 Olivier Bilodeau
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
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
