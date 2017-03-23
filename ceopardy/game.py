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

NB_TEAMS = 3
CATEGORIES_PER_GAME = 5
QUESTIONS_PER_CATEGORY = 5

# TODO save a game in progress
# TODO load a game in progress
class Game():
    def __init__(self):
        self.config = {
            'NB_TEAMS': NB_TEAMS
        }
        self.started = False


    def start(self):
        if not self.started:
            self.started = True
            return True
        else:
            raise GameProblem("Trying to start an already started game")
        # TODO randomly pick a team


class Team():
    def __init__(self, name):
        self.score = 0
        self.name = name


class GameBoard():
    def __init__(self):
        self.config = {
            'CATEGORIES_PER_GAME': CATEGORIES_PER_GAME,
            'QUESTIONS_PER_CATEGORY': QUESTIONS_PER_CATEGORY
        }
        self.questions = []
        for column in range(CATEGORIES_PER_GAME):
            l = []
            for row in range(QUESTIONS_PER_CATEGORY):
                question = Question("Nothing!", (row + 1) * 100, [row + 1, column + 1])
                l.append(question)
            self.questions.append(l)
        self.categories = []
        for column in range(CATEGORIES_PER_GAME):
            category = Category("This is C%d" % (column + 1), column + 1)
            self.categories.append(category)


class Category():
    def __init__(self, value, column):
        self.value = value
        self.column = column


class Question():
    def __init__(self, value, amount, coordinates):
        self.value = value
        self.amount = amount
        self.coordinates = coordinates
        self.solved = False


class GameProblem(Exception):
    pass

