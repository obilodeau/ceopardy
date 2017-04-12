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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Alex Trebek forever!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ceopardy.db'
socketio = SocketIO(app)
db = SQLAlchemy(app)


@app.context_processor
def inject_config():
    """Injects ceopardy configuration for the template system"""
    controller = get_controller()
    return controller.get_config()


@app.route('/')
def start():
    controller = get_controller()
    if controller.is_game_ready():
        # TODO eventually viewer should just become /?
        return render_template("viewer.html")
    else:
        return render_template('lobby.html')


# TODO we must kill all client-side state on server load.
# To reproduce: Not-reloading a host view and reloading server causes mismatch
# between client and server states. Client is out of sync.
# authentication related: commented for now
@app.route('/host')
def host():
    # Start the game if it's not already started
    controller = get_controller()
    if not controller.is_game_ready():
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
        controller.start_game(teamnames)

        # announce waiting room that game has started
        emit("start_game", namespace="/wait", broadcast=True)
        return redirect('/host')

    return render_template('host-setup.html', form=form)


# TODO eventually viewer should just become /?
@app.route('/viewer')
def viewer():
    controller = get_controller()
    team_stats = controller.get_team_stats()
    # FIXME crashes, need to store in global context?
    # See: http://flask.pocoo.org/docs/0.12/appcontext/
    return render_template('viewer.html', team_stats=team_stats)


@socketio.on('click', namespace='/host')
def handle_click(data):
    controller = get_controller()
    print('received data: ' + data["id"], file=sys.stderr)
    match = re.match("c([0-9]+)q([0-9]+)", data["id"])
    if match is not None:
        items = match.groups()
        column = int(items[0])
        row = int(items[1])
        controller.set_question_solved(column, row, True)
        state = controller.dictionize_questions_solved()
        emit("update-board", state, namespace='/viewer', broadcast=True)
        emit("show-overlay", "<p>Test!</p>", namespace='/viewer', broadcast=True)


@socketio.on('unclick', namespace='/host')
def handle_click(data):
    emit("hide-overlay", namespace='/viewer', broadcast=True)


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
    state = controller.dictionize_questions_solved()
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
