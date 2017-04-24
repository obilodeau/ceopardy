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

from config import config
from forms import TeamNamesForm, TEAM_FIELD_ID

VERSION = "0.1.0"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Alex Trebek forever!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ceopardy.db'
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
    categories = controller.get_categories()
    teams = controller.get_teams_score()
    initialized = controller.is_game_initialized()
    return render_template('viewer.html', teams=teams, categories=categories,
                           initialized=initialized)


# TODO we must kill all client-side state on server load.
# To reproduce: Not-reloading a host view and reloading server causes mismatch
# between client and server states. Client is out of sync.
# authentication related: commented for now
@app.route('/host')
def host():
    controller = get_controller()
    teams = {}
    if controller.is_game_started():
        teams = controller.get_teams_for_form()
        form = TeamNamesForm(data=teams)
        started = True
    # FIXME on a normal game flow (setup then play) the answer form is empty (no teams set)
    #       not sure what solution to this problem I prefer yet
    else:
        form = TeamNamesForm()
        started = False
    return render_template('host.html', form=form, started=started, teams=teams)


# TODO: kick-out if game is started
# TODO: we might be a little better if we split everything in individual REST APIs?
#       see http://stackoverflow.com/questions/3850742/flask-how-do-i-combine-flask-wtf-and-flask-sqlalchemy-to-edit-db-models
@app.route('/setup', methods=["POST"])
def setup():
    controller = get_controller()
    form = TeamNamesForm()
    # TODO: [LOW] csrf token errors are not logged (and return 200 which contradicts docs)
    if form.validate_on_submit():

        teamnames = {field.id: field.data for field in form
                     if TEAM_FIELD_ID in field.flags}

        # If teams exists, update them
        if controller.teams_exists():
            controller.update_teams(teamnames)

        # Otherwise create them
        else:
            controller.setup_teams(teamnames)
            # FIXME move lines below in another "feature" to allow retries w/o
            #       requiring a database reset
            controller.setup_questions()
            controller.start_game()

        emit("team", {"action": "name", "args": teamnames}, namespace='/viewer', broadcast=True)
        return jsonify(result="success")

    return jsonify(result="failure", errors=form.errors)


@app.route('/answer', methods=["POST"])
def answer():
    # TODO incomplete
    app.logger.debug("Answer form has been submitted with: {}", request.form)
    controller = get_controller()

    qid = request.form['qid']

    # send everything but qid as a dict
    answers = request.form.to_dict()
    answers.pop('qid')
    if controller.answer_normal(qid, answers):
        return jsonify(result="success")

    return jsonify(result="failure", error="Something went wrong")


@socketio.on('click', namespace='/host')
def handle_click(data):
    controller = get_controller()
    app.logger.debug('received data: {}'.format(data["id"]))
    match = re.match("c([0-9]+)q([0-9]+)", data["id"])
    if match is not None:
        col, row = match.groups()
        qid, question_text = controller.get_question(col, row)
        #state = controller.dictionize_questions_solved()
        #emit("update-board", state, namespace='/viewer', broadcast=True)
        emit("overlay", {"action": "show", "id": "small", "html": question_text},
             namespace='/viewer', broadcast=True)
        emit("test2", {"action": "show_answer_ui", "qid": qid,
                      "q_text": question_text}, namespace='/host')


@socketio.on('unclick', namespace='/host')
def handle_click(data):
    emit("overlay", {"action": "hide", "id": "small", "html": ""}, namespace='/viewer', broadcast=True)


@socketio.on('message', namespace='/host')
def handle_message(data):
    # FIXME Temporary XSS!!!
    if data["action"] == "show":
        emit("overlay", {"action": "show", "id": "big", "html": "<p>{0}</p>".format(data["text"])}, namespace='/viewer', broadcast=True)
    else:
        emit("overlay", {"action": "hide", "id": "big", "html": ""}, namespace='/viewer', broadcast=True)


@socketio.on('roulette', namespace='/host')
def handle_roulette():
    controller = get_controller()
    nb = controller.get_nb_teams()
    l = []
    team = "team" + str(random.randrange(1, nb + 1))
    for i in range(12):
        l.append("team" + str(i % nb + 1))
    l.append(team)
    app.logger.debug(l)
    emit("team", {"action": "roulette", "args": l}, namespace='/viewer', broadcast=True)


@socketio.on('refresh', namespace='/viewer')
def handle_refresh():
    controller = get_controller()
    # FIXME
    #state = controller.dictionize_questions_solved()
    state = {}
    emit("update-board", state)


if __name__ == '__main__':

    # logging
    file_handler = logging.FileHandler('ceopardy.log')
    #file_handler.setLevel(logging.INFO)
    file_handler.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        '{asctime} {levelname}: {message} [in {pathname}:{lineno}]', style='{')
    file_handler.setFormatter(fmt)
    app.logger.addHandler(file_handler)

    # cleaner controller access
    # unsure if required once we have a db back-end
    with app.app_context():

        from controller import Controller
        def get_controller():
            _ctl = getattr(g, '_ctl', None)
            if _ctl is None:
                _ctl = g._ctl = Controller()
            return _ctl

        @app.teardown_appcontext
        def teardown_controller(exception):
            app.logger.debug("Controller teardown requested")
            _ctl = getattr(g, '_ctl', None)
            if _ctl is not None:
                _ctl = None

    socketio.run(app, host="0.0.0.0", debug=True)
