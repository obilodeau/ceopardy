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
from collections import OrderedDict

from flask import current_app as app
from sqlalchemy import and_

from ceopardy import db
from config import config
from model import Answer, Game, Team, GameState, Question, Response
from utils import parse_questions, parse_gamefile, question_to_html


class Controller():
    def __init__(self):
        app.logger.debug("Controller initialized")

        # if there's not a game state, create one
        if Game.query.one_or_none() is None:
            game = Game()
            db.session.add(game)
            db.session.commit()


    @staticmethod
    def is_game_initialized():
        game = Game.query.one()
        return game.state != GameState.uninitialized


    @staticmethod
    def is_game_started():
        game = Game.query.one()
        return game.state == GameState.started


    @staticmethod
    def setup_teams(teamnames):
        """Teamnames is {teamid: team_name} dict"""
        app.logger.info("Setup teams: {}".format(teamnames))
        game = Game.query.one()
        if game.state == GameState.uninitialized:
            for _tid, _tn in teamnames.items():
                team = Team(_tid, _tn)
                db.session.add(team)
            db.session.commit()
        else:
            raise GameProblem("Trying to setup a game that is already started")
        return True


    @staticmethod
    def update_teams(teamnames):
        """Teamnames is {teamid: team_name} dict"""
        app.logger.info("Update teams: {}".format(teamnames))
        for _id, _name in teamnames.items():
            db.session.query(Team).filter_by(tid=_id).update({"name": _name})
        db.session.commit()


    @staticmethod
    def setup_questions(q_file=config['QUESTIONS_FILENAME']):
        app.logger.info("Setup questions from file: {}".format(q_file))
        game = Game.query.one()
        if game.state == GameState.uninitialized:

            # TODO need to be able to specify given game
            gamefile, final = parse_gamefile(config['BASE_DIR'] + 'data/1st.round')
            questions = parse_questions(config['BASE_DIR'] + q_file)

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
            game = Game.query.one()
            game.state = GameState.started
            db.session.commit()
            return True

        else:
            raise GameProblem("Trying to start a game that is not ready")


    @staticmethod
    def get_config():
        return config


    @staticmethod
    def get_teams_score():
        if Controller.is_game_started():
            answers = db.session.query(Team.id, Team.name, Answer.response,
                                       Answer.score_attributed)\
                                .join(Answer).order_by(Team.id).all()

            results = OrderedDict()
            # handle case when there are no answers: names with 0 score
            if not answers:
                for _team in db.session.query(Team).order_by(Team.id).all():
                    results[_team.name] = 0
                return results

            # sum all answers with negative scoring handled for bad answers
            for answer in answers:
                _id, _name, _response, _score = answer
                # not already defined? initialize
                if not results.get(_name):
                    results[_name] = 0

                # bad: -1, nop: 0 and good: 1 multiplied with score gives result
                results[_name] += _response.value * _score
            return results

        else:
            # Return names with a 0 score
            return {name: 0
                    for tid, name in Controller.get_teams_for_form().items()}


    @staticmethod
    def get_teams_for_form():
        """Get list of teams
        If there are no teams, then return place holder teams. This is useful
        to render template for game setup."""
        if Team.query.first() is not None:
            return {team.tid: team.name for team in Team.query.all()}
        else:
            return {'team{}'.format(_i): 'Team {}'.format(_i)
                    for _i in range(1, config['NB_TEAMS'] + 1)}


    @staticmethod
    def teams_exists():
        if Team.query.all():
            return True
        return False


    @staticmethod
    def get_nb_teams():
        return config["NB_TEAMS"]


    @staticmethod
    def get_categories():
        return [_q.category for _q in
                db.session.query(Question.category).distinct()
                  .filter(Question.final == False)
                  .order_by(Question.col)]


    @staticmethod
    def get_question(column, row):
        app.logger.info(
            "Question requested for row: {} and col: {}".format(row, column))

        condition = and_(Question.row == row, Question.col == column)
        _q = Question.query.filter(condition).one()
        return _q.id, question_to_html(_q.text)


    @staticmethod
    def get_question_viewid_from_dbid(question_id):
        # sorry for the ugly name but it says it all
        question = Question.query.get(question_id)
        qid = "c{}q{}".format(question.col, question.row)
        return qid


    @staticmethod
    def answer_normal(question_id, answers):
        app.logger.info("Answers submitted for question {}: {}"
                        .format(question_id, answers))
        # answers looks like: ('team1', '-1'), ('team2', '1'), ('team3', '0')]

        # is there already an answer? If so update answers
        prev_answers = Answer.query.filter(Answer.question_id == question_id).all()
        if prev_answers:
            for _answer in prev_answers:
                _answer.response = Response(int(answers[_answer.team.tid]))
                db.session.add(_answer)

        # Otherwise create new ones
        else:
            for tid, response in answers.items():
                team = Team.query.filter(Team.tid == tid).one()
                question = Question.query.get(question_id)
                response = Response(int(response))
                db.session.add(Answer(response, team, question))

        db.session.commit()
        return True


    @staticmethod
    def _get_questions_status():
        """Full status about all questions"""
        questions = db.session.query(Question.row, Question.col, Answer)\
                                    .outerjoin(Answer).all()
        return questions


    @staticmethod
    def get_questions_status_for_viewer():
        """Limited status view about all questions: answered or not"""
        questions = Controller._get_questions_status()

        results = {}
        for question in questions:
            _row, _col, _answer = question
            qid = "c{}q{}".format(_col, _row)
            results[qid] = _answer is not None

        return results


    @staticmethod
    def get_questions_status_for_host():
        """Status view about all questions
        Format looks like:
        {c1q3: {'t1': '-300' , 't2': '500', ...}
        """
        questions = Controller._get_questions_status()

        results = {}
        for question in questions:
            _row, _col, _answer = question
            qid = "c{}q{}".format(_col, _row)
            # if new entry, add list
            if results.get(qid) is None:
                results[qid] = {}

            # skip empty answers
            if _answer is None:
                continue

            points = _answer.response.value * _answer.score_attributed
            '''
            status = "{}: {}, Points: {}".format(
                _answer.team_id, _answer.response.name, points)
            if _answer.response == Response.bad:
                status = '<span style="background: red;">' + status + '</span>'
            elif _answer.response == Response.good:
                status = '<span style="background: green;">' + status + '</span>'
            '''
            tid = 't{}'.format(_answer.team_id)
            results[qid][tid] = points

        return results



class GameProblem(Exception):
    pass
