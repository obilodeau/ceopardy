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
import os
from collections import OrderedDict
from datetime import datetime

from flask import current_app as app
from sqlalchemy import and_

from ceopardy import db
from config import config
from model import Answer, Game, Team, GameState, Question, Response, State, \
    FinalQuestion
from utils import parse_question_id, parse_questions, parse_gamefile, \
    question_to_html


class Controller():
    def __init__(self):
        Controller._init()

    @staticmethod
    def _init():
        """
        This was extracted away from __init__ because it is called on a game
        reset which happens in a static method.
        """

        # If there's not a game state, create one
        if Game.query.one_or_none() is None:
            game = Game()
            db.session.add(game)
            # Default overlay state for a new game
            db.session.add(State("overlay-small", ""))
            db.session.add(State("overlay-big", "<p>There is currently no host running the show!</p>"))
            # No question is selected, the game hasn't started
            db.session.add(State("question", ""))
            db.session.add(State("container-header", "slide-down"))
            db.session.add(State("container-footer", "slide-up"))
            db.session.commit()


    @staticmethod
    def is_game_in_progress():
        game = Game.query.one()
        return game.state == GameState.in_round \
            or game.state == GameState.in_final


    @staticmethod
    def is_game_initialized():
        game = Game.query.one()
        return game.state != GameState.uninitialized


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
    def setup_questions(round_file, q_file=config['QUESTIONS_FILENAME']):
        app.logger.info("Setup questions from file: {}".format(q_file))
        game = Game.query.one()
        if game.state == GameState.uninitialized:

            gamefile, final = parse_gamefile(config['BASE_DIR'] + 'data/' + round_file)
            questions = parse_questions(config['BASE_DIR'] + q_file)

            # TODO do some validation based on config constants
            for _col, _cat in enumerate(gamefile, start=1):
                for _row, _q in enumerate(questions[_cat], start=1):
                    score = _row * config['SCORE_TICK']

                    daily_double = False
                    if _q.startswith('[dbl]'):
                        _q = _q.lstrip('[dbl]').lstrip()
                        daily_double = True

                    question = Question(_q, score, _cat, _row, _col,
                                        double = daily_double)
                    db.session.add(question)

            # Add final question
            if final is not None:
                final = FinalQuestion(**final)
                question = Question(final.question, 0, final.category, 0, 0, final=True)
                db.session.add(question)

            # Once everything loaded successfully, identify round file and commit
            game.round_filename = round_file
            db.session.add(game)
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
            game.state = GameState.in_round
            db.session.commit()
            return True

        else:
            raise GameProblem("Trying to start a game that is not ready")


    @staticmethod
    def finish_game():
        scores = Controller.get_teams_score()
        app.logger.info("Game is finished. Teams / Scores: {}".format(scores))

        # Mark as finished
        game = Game.query.one()
        game.state = GameState.finished
        db.session.commit()
        return True


    @staticmethod
    def resume_game():
        """Resuming a game is simply allowing to start over a finished game.
        
        Sometimes people click on finish by mistake or mess-up the score
        in the final round. Resuming a game enables to fix that.
        """
        if Controller.is_game_initialized() is False:
            app.logger.warn("Attempting to resume an uninitialized game...")
            return False

        game = Game.query.one()
        game.state = GameState.in_round
        db.session.commit()
        scores = Controller.get_teams_score()
        app.logger.info("A game has been resumed. Current teams / scores: {}"
                        .format(scores))
        return True


    @staticmethod
    def get_config():
        return config


    @staticmethod
    def get_teams_score():
        if Controller.is_game_initialized():
            answers = db.session.query(Team.id, Team.name, Answer.response,
                                       Answer.score_attributed)\
                                .join(Answer).order_by(Team.id).all()

            results = OrderedDict()
            # Handle case when there are no answers: names with 0 score
            if not answers:
                for _team in db.session.query(Team).order_by(Team.id).all():
                    results[_team.name] = 0
                return results

            # Sum all answers with negative scoring handled for bad answers
            for answer in answers:
                _id, _name, _response, _score = answer
                # Not already defined? initialize
                if not results.get(_name):
                    results[_name] = 0

                # bad: -1, nop: 0 and good: 1 multiplied with score gives result
                results[_name] += _response.value * _score
            return results

        else:
            # Return names with a 0 score
            return {name: 0
                    for tid, name in Controller.get_teams_for_form().items()}


    # TODO remove
    # Temporary fix, find a way to merge with the function above!
    @staticmethod
    def get_teams_score_by_tid():
        answers = db.session.query(Team.id, Team.tid, Answer.response,
                                   Answer.score_attributed)\
                            .join(Answer).order_by(Team.id).all()

        results = OrderedDict()
        # Handle case when there are no answers: names with 0 score
        if not answers:
            for _team in db.session.query(Team).order_by(Team.id).all():
                results[_team.tid] = 0
            return results

        # Sum all answers with negative scoring handled for bad answers
        for answer in answers:
            _id, _tid, _response, _score = answer
            # Not already defined? initialize
            if not results.get(_tid):
                results[_tid] = 0

            # bad: -1, nop: 0 and good: 1 multiplied with score gives result
            results[_tid] += _response.value * _score
        return results


    @staticmethod
    def get_good_answer_team(col, row):
        """
        Returns the team id of the team who correctly answered the specified question
        """
        team = db.session.query(Team).join(Answer, Question).filter(
            and_(Question.col == col, Question.row == row,
                 Answer.response == Response.good)).first()
        if team:
            return team.tid
        else:
            None


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
    def get_team_in_control():
        return Team.query.filter(Team.tid == Controller.get_state("team")).one()


    @staticmethod
    def get_dailydouble_waiger_range(team_id):
        _min = config.get('DAILYDOUBLE_WAIGER_MIN')
        scores = Controller.get_teams_score_by_tid()
        _max = scores[team_id]
        if _max < config.get('DAILYDOUBLE_WAIGER_MAX_MIN'):
            _max = config.get('DAILYDOUBLE_WAIGER_MAX_MIN')
        return (_min, _max)


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
        return { "text": question_to_html(_q.text), "category": _q.category, "dailydouble": _q.double }


    @staticmethod
    def get_active_question():
        _q = {}
        qid = Controller.get_complete_state().get('question', '')
        if qid != '':
            col, row = parse_question_id(qid)
            _q = Controller.get_question(col, row)
        return _q


    @staticmethod
    def is_final_question():
        """Is there a final question for this game?"""
        return Question.query.filter(Question.final == True).one_or_none() is not None


    @staticmethod
    def get_answer(column, row):
        app.logger.info(
            "Answer requested for row: {} and col: {}".format(row, column))

        condition = and_(Question.row == row, Question.col == column)
        _q = Question.query.filter(condition).one()
        _a = Answer.query.filter(Answer.question_id==_q.id).all()
        if len(_a) == 0:
            return {}
        answer = {}
        for a in _a:
            answer[a.team.tid] = a.response.value
        return answer


    @staticmethod
    def get_question_viewid_from_dbid(question_id):
        # Sorry for the ugly name but it says it all
        question = Question.query.get(question_id)
        qid = "c{}q{}".format(question.col, question.row)
        return qid


    @staticmethod
    def answer_normal(column, row, answers):
        app.logger.info("Answers submitted for question ({}, {}): {}"
                        .format(column, row, answers))
        # Answers looks like: ('team1', '-1'), ('team2', '1'), ('team3', '0')]

        condition = and_(Question.row == row, Question.col == column)
        _q = Question.query.filter(condition).one()
        
        # Is there already an answer? If so update answers
        prev_answers = Answer.query.filter(Answer.question_id == _q.id).all()
        if prev_answers:
            for _answer in prev_answers:
                _answer.response = Response(int(answers[_answer.team.tid]))
                db.session.add(_answer)

        # Otherwise create new ones
        else:
            for tid, points in answers.items():
                team = Team.query.filter(Team.tid == tid).one()
                question = Question.query.get(_q.id)
                response = Response(int(points))
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
        {c1q3: {'team1': '-300' , 'team2': '500', ...}
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
            tid = 'team{}'.format(_answer.team_id)
            results[qid][tid] = points

        return results


    @staticmethod
    def get_state(name):
        result = State.query.filter_by(name=name).one_or_none()
        if result is not None:
            return result.value
        else:
            return ""


    @staticmethod
    def get_complete_state():
        state = {}
        for s in State.query.all():
            state[s.name] = s.value
        return state


    @staticmethod
    def set_state(name, value):
        result = State.query.filter_by(name=name).one_or_none()
        if result is not None:
            if value is None:
                result.value = ''
            else:
                result.value = value
        else:
            db.session.add(State(name, value))
        db.session.commit()


    @staticmethod
    def db_backup_and_create_new():
        """
        Drop db connections, move file, create new db connection 
        and re-init empty db
        """
        # TODO we might need to lock this thing to avoid state issues with viewers
        previous_roundfile = Game.query.one().round_filename
        _bkp = 'ceopardy_{}_{}.db'.format(datetime.now().strftime('%Y-%m-%d_%H%M'),
                                          previous_roundfile)
        app.logger.info('Backing up current game to {}'.format(_bkp))
        db.engine.dispose()
        os.rename(config['BASE_DIR'] + config['DATABASE_FILENAME'],
                  config['BASE_DIR'] + _bkp)
        db.session = db.create_scoped_session()
        db.create_all()
        Controller._init()
        app.logger.info('SQL Engine reconnected, empty database recreated.' +
                        'We are ready to go!')


class GameProblem(Exception):
    pass
