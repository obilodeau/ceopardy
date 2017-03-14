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
from ceopardy.controller import Controller

app = Flask(__name__)

@app.context_processor
def inject_config():
    """Injects ceopardy configuration for the template system"""
    return Controller.get_gameboard_config()

@app.route('/')
def gameboard():
    return render_template("gameboard.html")


if __name__ == '__main__':
    app.run(debug=True)
