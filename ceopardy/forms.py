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

class TeamNamesForm(FlaskForm):
    # TODO align this with global NB_TEAMS
    # http://wtforms.readthedocs.io/en/latest/specific_problems.html#dynamic-form-composition
    team1 = StringField('TeamName1', validators=[DataRequired()])
    team2 = StringField('TeamName2', validators=[DataRequired()])
    team3 = StringField('TeamName3', validators=[DataRequired()])
