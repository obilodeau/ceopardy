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
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, send, emit, disconnect
import flask_login
import ceopardy.controller as controller
import ceopardy.login as login
from ceopardy.api import api
import sys
import re
import random
import functools


app = Flask(__name__)
app.config['SECRET_KEY'] = 'Alex Trebek forever!'
app.add_url_rule('/login', view_func=login.login, methods=['GET', 'POST'])
app.add_url_rule('/logout', view_func=login.logout, methods=['GET', 'POST'])
# API - RESTful
app.register_blueprint(api, url_prefix='/api')
socketio = SocketIO(app)
login.init_app(app)
controller.init()

def authenticated_only(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not flask_login.current_user.is_authenticated:
            disconnect()
        else:
            return f(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_config():
    """Injects ceopardy configuration for the template system"""
    return controller.get().get_config()

@app.route('/')
def start():
    return render_template("startup.html")

@app.route('/game')
def gameboard():
    return render_template("gameboard.html")

@app.route('/host')
#@flask_login.login_required
def host():
    return render_template('host.html')

@app.route('/player')
def player():
    return render_template('player.html')

@app.route('/viewer')
def viewer():
    return render_template('viewer.html')

@socketio.on('click', namespace='/host')
def handle_click(data):
    print('received data: ' + data["id"], file=sys.stderr)
    match = re.match("c([0-9]+)q([0-9]+)", data["id"])
    if match is not None:
        items = match.groups()
        column = int(items[0])
        row = int(items[1])
        controller.get().set_question_solved(column, row, True)
        state = controller.get().dictionize_questions_solved()
        emit("update-board", state, namespace='/viewer', broadcast=True)
        emit("show-overlay", "Test!", namespace='/viewer', broadcast=True)

@socketio.on('unclick', namespace='/host')
def handle_click(data):
    emit("hide-overlay", namespace='/viewer', broadcast=True)

@socketio.on('roulette', namespace='/host')
#@authenticated_only
def handle_roulette():
    nb = controller.get().get_nb_teams()
    l = []
    team = "t" + str(random.randrange(1, nb + 1))
    for i in range(12):
        l.append("t" + str(i % nb + 1))
    l.append(team)
    emit("roulette-team", l, namespace='/viewer', broadcast=True)

@socketio.on('refresh', namespace='/viewer')
def handle_refresh():
    state = controller.get().dictionize_questions_solved()
    emit("update-board", state)

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", debug=True)
