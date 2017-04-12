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
from wtforms.validators import InputRequired, ValidationError

from config import NB_TEAMS

# this id is used to flag team name input entries so that we can dynamically
# generate form because the number of team is configurable
TEAM_FIELD_ID = 'teamname'

class TeamNamesForm(FlaskForm):
    pass

class UniqueTeamName():
    """A validator that ensures that each field of a given field set is unique."""
    # we are using WTForms' flags to identify team name entries so that they can be dynamic
    field_flags = (TEAM_FIELD_ID,)

    def __call__(self, form, field):
        for otherfield in form._fields.values():
            # filter only team name fields (and not myself)
            if TEAM_FIELD_ID in field.flags and field is not otherfield:
                # raise error if name not unique
                if field.data == otherfield.data:
                    raise ValidationError('Team name must be unique per game!')

for _i in range(1, NB_TEAMS + 1):
    _i = str(_i)
    setattr(TeamNamesForm, "team" + _i,
            StringField(label="Team {}'s Name".format(_i),
                        validators=[InputRequired('A team name must be provided!'),
                                    UniqueTeamName()]))
