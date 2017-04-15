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
import functools
from threading import Lock

from flask import current_app as app

from config import config
from ceopardy import db
from model import Game, Team, GameState, GameBoard


# TODO consider for removal now that we use a database: make sure to use transactions properly!
def locked(f):
    @functools.wraps(f)
    def wrapped(self, *args, **kwargs):
        with self.lock:
            result = f(self, *args, **kwargs)
        return result
    return wrapped


class Controller():
    def __init__(self):
        app.logger.debug("Controller initialized")
        self.lock = Lock()

        # if there's not a game state, create one
        if Game.query.first() is None:
            game = Game()
            db.session.add(game)
            db.session.commit()


    @staticmethod
    def is_game_ready():
        game = Game.query.first()
        return game.state == GameState.started

    @staticmethod
    def start_game(teamnames):
        app.logger.info("Starting game with teams: {}".format(teamnames))
        game = Game.query.first()
        if game.state == GameState.uninitialized:
            for _tn in teamnames:
                team = Team(_tn)
                db.session.add(team)
            game.state = GameState.started
            db.session.commit()
        else:
            raise GameProblem("Trying to setup a game that is already started")

        return True


    @staticmethod
    def get_config():
        return config


    @staticmethod
    def get_team_stats():
        game = Game.query.first()
        if game.state == GameState.started:
            # TODO implement score
            return {team.name: 0 for team in Team.query.all()}
        else:
            return None


    @staticmethod
    def get_nb_teams():
        return config["NB_TEAMS"]

    def get_question(self, column, row):
        # TODO migrate to db
        gb = GameBoard()
        return gb.questions[row - 1][column - 1]
    
    def get_question_solved(self, column, row):
        question = self.get_question(column, row)
        return question.solved

    @locked
    def set_question_solved(self, column, row, value):
        question = self.get_question(column, row)
        question.solved = value

    def dictionize_questions_solved(self):
        # TODO migrate to db
        gb = GameBoard()
        questions = gb.questions
        result = {}
        for row in range(len(questions)):
            for column in range(len(gb.questions[row])):
                question = gb.questions[row][column]
                name = "c{0}q{1}".format(column + 1, row + 1)
                result[name] = question.solved
        return result


class GameProblem(Exception):
    pass
