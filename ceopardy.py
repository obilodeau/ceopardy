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

from flask import g, Flask, render_template, redirect
from flask_socketio import SocketIO, emit, disconnect
from flask_sqlalchemy import SQLAlchemy

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
    controller = get_controller()
    return controller.get_config()


@app.route('/')
def slash():
    controller = get_controller()
    if controller.is_game_started():
        categories = controller.get_categories()
        team_stats = controller.get_team_stats()
        return render_template('viewer.html', categories=categories,
                               team_stats=team_stats)
    else:
        return render_template('lobby.html')


# TODO eventually viewer should just become /?
@app.route('/viewer')
def viewer():
    controller = get_controller()
    teams = controller.get_teams()
    print(teams, file=sys.stderr)
    # FIXME crashes, needs a database
    # See: http://flask.pocoo.org/docs/0.12/appcontext/
    return render_template('viewer.html', teams=teams)


# TODO we must kill all client-side state on server load.
# To reproduce: Not-reloading a host view and reloading server causes mismatch
# between client and server states. Client is out of sync.
# authentication related: commented for now
@app.route('/host')
def host():
    # Start the game if it's not already started
    controller = get_controller()
    if not controller.is_game_started():
        form = TeamNamesForm()
        return render_template('host-setup.html', form=form)

    return render_template('host.html')


# TODO: kick-out if game is started
@app.route('/setup', methods=["GET", "POST"])
def setup():
    controller = get_controller()
    form = TeamNamesForm()
    # TODO: [LOW] csrf token errors are not logged (and return 200 which contradicts docs)
    if form.validate_on_submit():

        teamnames = [field.data for field in form if TEAM_FIELD_ID in field.flags]
        controller.setup_teams(teamnames)
        controller.setup_questions()
        controller.start_game()

        # announce waiting room that game has started
        emit("start_game", namespace="/wait", broadcast=True)
        return redirect('/host')

    return render_template('host-setup.html', form=form)


@socketio.on('click', namespace='/host')
def handle_click(data):
    controller = get_controller()
    print('received data: ' + data["id"], file=sys.stderr)
    match = re.match("c([0-9]+)q([0-9]+)", data["id"])
    if match is not None:
        items = match.groups()
        column = int(items[0])
        row = int(items[1])
        #controller.set_question_solved(column, row, True)
        #state = controller.dictionize_questions_solved()
        #emit("update-board", state, namespace='/viewer', broadcast=True)
        emit("overlay", {"action": "show", "id": "small", "html": "<p>Test!</p>"}, namespace='/viewer', broadcast=True)


@socketio.on('unclick', namespace='/host')
def handle_click(data):
    emit("overlay", {"action": "hide", "id": "small", "html": ""}, namespace='/viewer', broadcast=True)


@socketio.on('message', namespace='/host')
def handle_message(data):
    # Temporary XSS!!!
    if data["action"] == "show":
        emit("overlay", {"action": "show", "id": "big", "html": "<p>{0}</p>".format(data["text"])}, namespace='/viewer', broadcast=True)
    else:
        emit("overlay", {"action": "hide", "id": "big", "html": ""}, namespace='/viewer', broadcast=True)


@socketio.on('roulette', namespace='/host')
def handle_roulette():
    controller = get_controller()
    nb = controller.get_nb_teams()
    l = []
    team = "t" + str(random.randrange(1, nb + 1))
    for i in range(12):
        l.append("t" + str(i % nb + 1))
    l.append(team)
    emit("roulette-team", l, namespace='/viewer', broadcast=True)


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
