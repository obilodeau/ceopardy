# Ceopardy
# <url>
#
# Olivier Bilodeau <olivier@bottomlesspit.org>
# Copyright (C) 2017 Olivier Bilodeau
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
class Game():
    def __init__(self):
        self.config = {
            'NB_TEAMS': 3
        }

    # TODO randomly pick a team
    # TODO save a game in progress
    # TODO load a game in progress

class Team():
    def __init__(self, name):
        self.score = 0
        self.name = name


class GameBoard():
    def __init__(self):
        self.config = {
            'CATEGORIES_PER_GAME': 5,
            'QUESTIONS_PER_CATEGORY': 5
        }

class Question():
    pass
