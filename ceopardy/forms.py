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
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired

from ceopardy.controller import controller

# NOTE: Be careful with this form. team names input entries are dynamic based on the number of teams
#       don't add a team<something> field or it will mangle with it.
class TeamNamesForm(FlaskForm):
    pass

for _i in range(1, controller.get_nb_teams() + 1):
    _i = str(_i)
    setattr(TeamNamesForm, "team" + _i,
            StringField(label="Team {}'s Name".format(_i), validators=[DataRequired()]))
