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
from model import Game, Team, GameState, GameBoard, Question
from utils import parse_questions, parse_gamefile


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
    def is_game_initialized():
        game = Game.query.first()
        return game.state != GameState.uninitialized


    @staticmethod
    def is_game_started():
        game = Game.query.first()
        return game.state == GameState.started


    @staticmethod
    def setup_teams(teamnames):
        app.logger.info("Setup teams: {}".format(teamnames))
        game = Game.query.first()
        if game.state == GameState.uninitialized:
            for _tn in teamnames:
                team = Team(_tn)
                db.session.add(team)
            db.session.commit()
        else:
            raise GameProblem("Trying to setup a game that is already started")
        return True


    @staticmethod
    def setup_questions(q_file=config['QUESTIONS_FILENAME']):
        app.logger.info("Setup questions from file: {}".format(q_file))
        game = Game.query.first()
        if game.state == GameState.uninitialized:

            # TODO need to be able to specify given game
            gamefile, final = parse_gamefile('data/1st.round')
            questions = parse_questions(q_file)

            # TODO do some validation based on config constants
            for _col, _cat in enumerate(gamefile, start=1):
                for _row, _q in enumerate(questions[_cat], start=1):
                    score = _row * config['SCORE_TICK']
                    question = Question(_q, score, _cat, _row, _col)
                    db.session.add(question)

            # add final question
            if final is not None:
                question = Question(final.question, 0, final.category, 0, 0, final=True)
                db.session.add(question)
            db.session.commit()

        else:
            raise GameProblem("Trying to setup a game that is already started")
        return True


    @staticmethod
    def start_game():
        app.logger.info("Starting the game. Good luck everyone!")
        # Are there teams and questions?
        if Team.query.all() and Question.query.all():

            # Yes, mark game as started
            game = Game.query.first()
            game.state = GameState.started
            db.session.commit()
            return True

        else:
            raise GameProblem("Trying to start a game that is not ready")


    @staticmethod
    def get_config():
        return config


    @staticmethod
    def get_teams():
        game = Game.query.first()
        if game.state == GameState.started:
            # TODO implement score
            return {team.name: 0 for team in Team.query.all()}
        else:
            return []


    @staticmethod
    def get_nb_teams():
        return config["NB_TEAMS"]

    @staticmethod
    def get_categories():
        return [_q.category for _q in
                db.session.query(Question.category).distinct()
                  .filter(Question.final == False)
                  .order_by(Question.col)]


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

    #def dictionize_questions_solved(self):
    #    # TODO migrate to db
    #    gb = GameBoard()
    #    questions = gb.questions
    #    result = {}
    #    for row in range(len(questions)):
    #        for column in range(len(gb.questions[row])):
    #            question = gb.questions[row][column]
    #            name = "c{0}q{1}".format(column + 1, row + 1)
    #            result[name] = question.solved
    #    return result


class GameProblem(Exception):
    pass
