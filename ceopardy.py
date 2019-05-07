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
import logging
import random
import re
import sys

from flask import g, Flask, render_template, redirect, jsonify, request
from flask_socketio import SocketIO, emit, disconnect
from flask_sqlalchemy import SQLAlchemy

import utils
from config import config
from forms import TeamNamesForm, TEAM_FIELD_ID

VERSION = "0.1.0"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Alex Trebek forever!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + config['DATABASE_FILENAME']
# To supress warnings about a feature we don't use
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

socketio = SocketIO(app)
db = SQLAlchemy(app)


@app.context_processor
def inject_config():
    """Injects ceopardy configuration for the template system"""
    return config


@app.route('/')
@app.route('/viewer')
def viewer():
    controller = get_controller()
    scores = controller.get_teams_score()
    categories = controller.get_categories()
    questions = controller.get_questions_status_for_viewer()
    state = controller.get_complete_state()
    active_question = controller.get_active_question()
    return render_template('viewer.html', scores=scores, categories=categories,
                           questions=questions, state=state,
                           active_question=active_question)


# TODO we must kill all client-side state on server load.
# To reproduce: Not-reloading a host view and reloading server causes mismatch
# between client and server states. Client is out of sync.
# TODO add authentication here
@app.route('/host')
def host():
    controller = get_controller()

    if not controller.is_game_in_progress():
        must_init = controller.is_game_initialized() is False
        roundfiles = utils.list_roundfiles()
        return render_template('start.html', must_init=must_init,
                               roundfiles=roundfiles)

    # TODO these objects need a major clean up for improved consistency
    # and reduced overhead
    scores = controller.get_teams_score()
    teams = controller.get_teams_for_form()
    form = TeamNamesForm(data=teams)
    categories = controller.get_categories()
    questions = controller.get_questions_status_for_host()
    state = controller.get_complete_state()
    active_question = controller.get_active_question()

    return render_template('host.html', scores=scores, teams=teams, form=form,
                           categories=categories, questions=questions,
                           state=state, active_question=active_question,
                           config=config)


# For now, this will give un an initial state which will avoid complications when
# rendering the host board
@app.route('/init', methods=["POST"])
def init():
    """Init can resume a finished game or start a new one"""
    controller = get_controller()

    if request.form['action'] == "new":
        roundfile = request.form['name']
        app.logger.info("New game requested with round file: {}"
                        .format(roundfile))

        # We want to start a new game, is there already one in the db?
        if controller.is_game_initialized():
            controller.db_backup_and_create_new()

        # Let's start a game!
        teamnames = {}
        for i in range(1, config['NB_TEAMS'] + 1):
            teamnames['team{}'.format(i)] = 'Team {}'.format(i)
        try:
            controller.setup_teams(teamnames)
            controller.setup_questions(roundfile)
            controller.start_game()
        except:
            app.logger.exception("Initialization error!")
            return jsonify(result="failure", error="Initialization error!")

    elif request.form['action'] == "resume":
        controller.resume_game()

    # This is kind of dirty, not sure I like it
    content = "<p>{}</p>".format(config["MESSAGES"][0]["text"])
    controller.set_state("message", "message1")
    controller.set_state("overlay-big", content)
    emit("overlay", {"action": "show", "id": "big", "html": content},
         namespace='/viewer', broadcast=True)
    
    # Just to be on the safe side
    controller.set_state("question", "")
    controller.set_state("overlay-question", "")
    emit("overlay", {"action": "hide", "id": "question", "html": ""},
         namespace='/viewer', broadcast=True)
    
    # Also as a precaution, the initialization might have caused something
    # to change below the big overlay
    emit("redirect", {"url": "/"}, namespace='/viewer', broadcast=True)

    return jsonify(result="success")


@app.route('/setup', methods=["POST"])
def setup():
    controller = get_controller()
    form = TeamNamesForm()
    # TODO: [LOW] csrf token errors are not logged (and return 200 which contradicts docs)
    if not form.validate_on_submit():
        return jsonify(result="failure", errors=form.errors)
    teamnames = {field.id: field.data for field in form
                 if TEAM_FIELD_ID in field.flags}
    controller.update_teams(teamnames)
    emit("team", {"action": "name", "args": teamnames}, namespace='/viewer', broadcast=True)
    return jsonify(result="success", teams=teamnames)


@app.route('/answer', methods=["POST"])
def answer():
    # FIXME this form isn't CSRF protected
    app.logger.debug("Answer form has been submitted with: {}", request.form)
    data = request.form
    controller = get_controller()

    app.logger.debug('received data: {}'.format(data["id"]))
    try:
        col, row = utils.parse_question_id(data["id"])
    except utils.InvalidQuestionId:
        return jsonify(result="failure", error="Invalid category/question format!")

    # Send everything but qid as a dict
    answers = request.form.to_dict()
    answers.pop('id')
    if not controller.answer_normal(col, row, answers):
        return jsonify(result="failure", error="Answer submission failed!")

    # TODO this is grossly inefficient
    question_status = controller.get_questions_status_for_host()
    teams = controller.get_teams_score_by_tid()
    emit("team", {"action": "score", "args": teams}, namespace='/viewer', broadcast=True)

    # someone answered correctly? identify team in control
    ctl_team = controller.get_good_answer_team(col, row)
    # highlight team in control and persist that state
    controller.set_state("team", ctl_team)
    emit("team", {'action': 'select', 'args': ctl_team}, namespace='/viewer', broadcast=True)

    return jsonify(result="success", answers=question_status[data["id"]],
                   teams=teams, ctl_team=ctl_team)
    

@socketio.on('question', namespace='/host')
def handle_question(data):
    controller = get_controller()
    if data["action"] == "select":
        col, row = utils.parse_question_id(data["id"])
        question = controller.get_question(col, row)
        answer = controller.get_answer(col, row)

        # Daily Double animation
        if question['double'] is True:
            emit("question", {"action": "hide", "id": "question", "content": "",
                              "category": ""},
                 namespace='/viewer', broadcast=True)
            emit("dailydouble", {"qid": data['id']}, namespace="/viewer",
                 broadcast=True)
            controller.set_state("question", data["id"])
            controller.set_state("dailydouble", "enabled")
            return {"question": config.get("DAILYDOUBLE_HOST_TEXT")}

        # Regular question
        emit("question", {"action": "show", "id": "question",
                          "content": question['text'],
                          "category": question['category']},
             namespace='/viewer', broadcast=True)
        controller.set_state("question", data["id"])
        controller.set_state("dailydouble", "")
        return {"question": question['text'], "answer": answer}

    # Return to board
    elif data["action"] == "deselect":
        state = controller.get_questions_status_for_viewer()
        emit("update-board", state, namespace='/viewer', broadcast=True)
        emit("question", {"action": "hide", "id": "question", "content": "",
                          "category": ""},
             namespace='/viewer', broadcast=True)
        controller.set_state("question", "")
        controller.set_state("dailydouble", "")
        return {}


@socketio.on('message', namespace='/host')
def handle_message(data):
    controller = get_controller()
    # FIXME Temporary XSS!!!
    if data["action"] == "show":
        content = "<p>{0}</p>".format(data["text"])
        mid = data["id"]
        emit("overlay", {"action": "show", "id": "big", "html": content}, 
            namespace='/viewer', broadcast=True)
    else:
        content = ""
        mid = ""
        emit("overlay", {"action": "hide", "id": "big", "html": ""}, 
            namespace='/viewer', broadcast=True)
    controller.set_state("message", mid)
    controller.set_state("overlay-big", content)


@socketio.on('team', namespace='/host')
def handle_team(data):
    controller = get_controller()
    if data["action"] == "select":
        team = data["id"]
        data["args"] = team
        controller.set_state("team", team)
    elif data["action"] == "roulette":
        nb = controller.get_nb_teams()
        l = []
        team = "team" + str(random.randrange(1, nb + 1))
        for i in range(12):
            l.append("team" + str(i % nb + 1))
        l.append(team)
        data["args"] = l
        controller.set_state("team", team)
    else:
        return ""
    emit("team", data, namespace='/viewer', broadcast=True)
    return team


@socketio.on('slider', namespace='/host')
def handle_slider(data):
    controller = get_controller()
    controller.set_state(data["id"], data["value"])


@socketio.on('final', namespace='/host')
def move_to_final_round(data):
    controller = get_controller()
    if controller.is_final_question():
        # TODO implement
        pass
    else:
        # TODO better highlight winner
        text = "<p>That's all folks! Thanks for playing!</p>"
        controller.set_state("overlay-question", text)
        controller.finish_game()
        emit("overlay", {"action": "show", "id": "question", "html": text},
             namespace='/viewer', broadcast=True)


@socketio.on('refresh', namespace='/viewer')
def handle_refresh():
    controller = get_controller()
    # FIXME
    #state = controller.dictionize_questions_solved()
    state = {}
    emit("update-board", state)


if __name__ == '__main__':

    # Logging
    file_handler = logging.FileHandler('ceopardy.log')
    #file_handler.setLevel(logging.INFO)
    file_handler.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        '{asctime} {levelname}: {message} [in {pathname}:{lineno}]', style='{')
    file_handler.setFormatter(fmt)
    app.logger.addHandler(file_handler)

    # Cleaner controller access
    # Unsure if required once we have a db back-end
    with app.app_context():

        from controller import Controller
        def get_controller():
            _ctl = getattr(g, '_ctl', None)
            if _ctl is None:
                _ctl = g._ctl = Controller()
            return _ctl

        @app.teardown_appcontext
        def teardown_controller(exception):
            #app.logger.debug("Controller teardown requested")
            _ctl = getattr(g, '_ctl', None)
            if _ctl is not None:
                _ctl = None

    # WARNING: This app is not ready to be exposed on the network.
    #          Game host interface would be exposed.
    socketio.run(app, host="127.0.0.1", debug=True)
