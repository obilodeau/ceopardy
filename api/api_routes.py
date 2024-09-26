# Ceopardy
# https://github.com/obilodeau/ceopardy/
#
# Olivier Bilodeau <olivier@bottomlesspit.org>
# Copyright (C) 2024 Olivier Bilodeau
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
from flask import Blueprint, current_app as app, jsonify

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/categories', methods=['GET'])
def get_categories():
    categories = app.controller.get_categories()
    return jsonify(categories)


@api_bp.route('/current_question', methods=['GET'])
def get_active_question():
    return jsonify(app.controller.get_active_question())


@api_bp.route('/questions/grid', methods=['GET'])
def get_game_grid():
    return jsonify(app.controller.get_questions_status_for_viewer())


@api_bp.route('/state', methods=['GET'])
def get_state():
    return jsonify(app.controller.get_complete_state())


@api_bp.route('/scores', methods=['GET'])
def get_scores():
    return jsonify(app.controller.get_teams_score())
