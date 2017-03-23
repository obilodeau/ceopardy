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
import functools
from threading import Lock

from ceopardy.game import Game, GameBoard, GameState


def get():
    return controller

def locked(f):
    @functools.wraps(f)
    def wrapped(self, *args, **kwargs):
        with self.lock:
            result = f(self, *args, **kwargs)
        return result
    return wrapped

class Controller():
    def __init__(self):
        self.g = Game()
        self.gb = GameBoard()
        # Merge various constants from model
        self.g.config.update(self.gb.config)
        self.lock = Lock()

    def is_game_ready(self):
        return self.g.state is GameState.started

    @locked
    def start_game(self):
        return self.g.start()

    def get_config(self):
        return self.g.config

    def get_nb_teams(self):
        return self.g.config["NB_TEAMS"]

    def get_question(self, column, row):
        return self.gb.questions[row - 1][column - 1]
    
    def get_question_solved(self, column, row):
        question = self.get_question(column, row)
        return question.solved

    @locked
    def set_question_solved(self, column, row, value):
        question = self.get_question(column, row)
        question.solved = value

    def dictionize_questions_solved(self):
        questions = self.gb.questions
        result = {}
        for row in range(len(questions)):
            for column in range(len(self.gb.questions[row])):
                question = self.gb.questions[row][column]
                name = "c{0}q{1}".format(column + 1, row + 1)
                result[name] = question.solved
        return result

# TODO: Change for a multiple import solution
global controller
controller = Controller()
