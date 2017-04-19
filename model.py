# Ceopardy
# https://github.com/obilodeau/ceopardy/
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
import collections
from enum import Enum

from flask import current_app as app

from ceopardy import db, VERSION
from config import config


SCHEMA_VERSION = 1
# TODO save a game in progress
# TODO load a game in progress
# TODO refactor to GameModel?
class old_Game():
    def __init__(self):
        self.state = GameState.uninitialized
        self.teams = []




    def start(self):
        if self.state is GameState.setup:
            self.state = GameState.started
            return True
        else:
            raise GameProblem("Trying to start a game that isn't ready to start")


    def get_team_stats(self):
        return [{team.name: team.score} for team in self.teams]

    # TODO randomly pick a team


# TODO remove
class GameState(Enum):
    uninitialized = 0
    setup = 1
    started = 2


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.Enum(GameState))
    ceopardy_version = db.Column(db.String(16))
    schema_version = db.Column(db.Integer)

    def __init__(self):
        self.state = 'uninitialized'
        self.ceopardy_version = VERSION
        self.schema_version = SCHEMA_VERSION

    def __repr__(self):
        return '<Game in state %r>' % self.state


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tid = db.Column(db.String(7), unique=True)
    name = db.Column(db.String(80), unique=True)
    handicap = db.Column(db.Integer)

    def __init__(self, tid, name, handicap=0):
        self.tid = tid
        self.name = name
        self.handicap = handicap
        app.logger.debug("Team created: name is {}, handicap is {}"
                         .format(self.name, self.handicap))

    def __repr__(self):
        return '<Team %r>' % self.name


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255))
    score_original = db.Column(db.Integer)
    category = db.Column(db.String(80))
    final = db.Column(db.Boolean)
    double = db.Column(db.Boolean)
    row = db.Column(db.Integer)
    col = db.Column(db.Integer)

    def __init__(self, text, score_original, category, row, col, final=False,
                 double=False):
        self.text = text
        self.score_original = score_original
        self.category = category
        self.row = row
        self.col = col
        self.final = final
        self.double = double

    def __repr__(self):
        return '<Question {} for {} at col {} row {}>'\
            .format(self.category, self.score_original, self.col, self.row)

# For the database, a final question is just a flag on a regular question.
# This convenience object is created so that we manage it in a more OO-ish way
# after parsing and before database insertion.
FinalQuestion = collections.namedtuple('FinalQuestion', 'category question')

class GameBoard():
    def __init__(self):
        self.questions = []
        for column in range(config['CATEGORIES_PER_GAME']):
            l = []
            for row in range(config['QUESTIONS_PER_CATEGORY']):
                question = Question("Nothing!", (row + 1) * 100, [row + 1, column + 1])
                l.append(question)
            self.questions.append(l)
        self.categories = []
        for column in range(config['CATEGORIES_PER_GAME']):
            category = Category("This is C%d" % (column + 1), column + 1)
            self.categories.append(category)


class Category():
    def __init__(self, value, column):
        self.value = value
        self.column = column



# TODO consider for removal (duplicated in controller)
class GameProblem(Exception):
    pass

# this creates the database if it doesn't already exist
db.create_all()