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

config = {
    'NB_TEAMS': 3,
    'VARIABLE_TEAMS': False,
    'CATEGORIES_PER_GAME': 5,
    'QUESTIONS_PER_CATEGORY': 5,
    'QUESTIONS_FILENAME': 'data/Questions.cp',
    'SCORE_TICK': 100,
    'MESSAGES': [\
        {"title": "Game not started",
         "text": "Please wait while the game is being set up..."},
        {"title": "Technical difficulties",
         "text": "It seems we're having some trouble, hang in there!"},
        {"title": "Break",
         "text": "On a short break, we'll be right back after these messages."},
        {"title": "Custom",
         "text": ""},
    ],
    'BASE_DIR': os.path.dirname(__file__) + '/',
    'DATABASE_FILENAME': 'ceopardy.db'
}
