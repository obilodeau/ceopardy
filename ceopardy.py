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
import flask
from flask import Flask, render_template
from flask_socketio import SocketIO, send, emit
from ceopardy.controller import controller
from ceopardy.api import api
import sys
import re
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Alex Trebek forever!'
# API - RESTful
app.register_blueprint(api, url_prefix='/api')
socketio = SocketIO(app)

@app.context_processor
def inject_config():
    """Injects ceopardy configuration for the template system"""
    return controller.get_config()


@app.route('/')
def start():
    if controller.is_game_ready():
        # TODO eventually viewer should just become /?
        return render_template("viewer.html")
    else:
        return render_template('wait.html')

# TODO we must kill all client-side state on server load.
# To reproduce: Not-reloading a host view and reloading server causes mismatch
# between client and server states. Client is out of sync.
@app.route('/host')
def host():
    # Start the game if it's not already started
    if not controller.is_game_ready():
        return render_template('setup.html')

    return render_template('host.html')

@app.route('/setup')
def setup():

    # TODO missing input validation (and form doesn't even submit here, lol)
    controller.start_game()

    # announce waiting room that game has started
    emit("start_game", namespace="/wait", broadcast=True)
    return render_template('host.html')


# TODO eventually viewer should just become /?
@app.route('/viewer')
def viewer():
    return render_template('viewer.html')

@socketio.on('click')
def handle_click(data):
    print('received data: ' + data["id"], file=sys.stderr)
    match = re.match("c([0-9]+)q([0-9]+)", data["id"])
    if match is not None:
        items = match.groups()
        column = int(items[0])
        row = int(items[1])
        controller.set_question_solved(column, row, True)
        state = controller.dictionize_questions_solved()
        emit("update-board", state, broadcast=True)
        emit("show-overlay", "<p>Test!</p>", broadcast=True)

@socketio.on('unclick')
def handle_click(data):
    emit("hide-overlay", broadcast=True)

@socketio.on('roulette')
def handle_roulette():
    nb = controller.get_nb_teams()
    l = []
    team = "t" + str(random.randrange(1, nb + 1))
    for i in range(12):
        l.append("t" + str(i % nb + 1))
    l.append(team)
    emit("roulette-team", l, broadcast=True)


@socketio.on('refresh')
def handle_refresh():
    state = controller.dictionize_questions_solved()
    emit("update-board", state)

if __name__ == '__main__':
    socketio.run(app, debug=True)
