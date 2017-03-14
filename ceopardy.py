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
from flask import Flask, render_template
from flask_socketio import SocketIO, send, emit
from ceopardy.controller import Controller
import sys

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Alex Trebek forever!'
socketio = SocketIO(app)

@app.context_processor
def inject_config():
    """Injects ceopardy configuration for the template system"""
    return Controller.get_config()

@app.route('/')
def start():
    return render_template("startup.html")

@app.route('/game')
def gameboard():
    return render_template("gameboard.html")

@app.route('/host')
def host():
    return render_template('host.html')

@app.route('/player')
def player():
    return render_template('player.html')

@app.route('/viewer')
def viewer():
    return render_template('viewer.html')

@socketio.on('click')
def handle_message(data):
    print('received data: ' + data["button"], file=sys.stderr)
    emit("change", data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
