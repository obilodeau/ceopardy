# Ceopardy
# https://github.com/obilodeau/ceopardy/
#
# Olivier Bilodeau <olivier@bottomlesspit.org>
# Copyright (C) 2026 Olivier Bilodeau
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
"""
REST + Socket.IO layer for the Vite + Vue front-end.

The original server used Jinja to render every page and relied on two Socket.IO
namespaces ("/host" and "/viewer") for realtime updates. The SPA version funnels
all actions through JSON endpoints here and listens on a single "/game"
namespace for broadcast events.
"""

import random

from flask import Blueprint, jsonify, request
from flask import current_app as app
from sqlalchemy.exc import NoResultFound

from ceopardy import utils
from ceopardy.config import config
from ceopardy.exceptions import (
    GamefileParsingError,
    GameProblem,
    InvalidQuestionId,
    QuestionParsingError,
    UnknownTeamError,
)

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

GAME_NS = "/game"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _controller():
    return app.controller


def _public_config():
    """Subset of config safe to expose to the front-end."""
    keys = (
        "NB_TEAMS",
        "VARIABLE_TEAMS",
        "CATEGORIES_PER_GAME",
        "QUESTIONS_PER_CATEGORY",
        "SCORE_TICK",
        "DAILYDOUBLE_WAIGER_MIN",
        "DAILYDOUBLE_WAIGER_MAX_MIN",
    )
    return {k: config[k] for k in keys if k in config}


def _teams_payload(controller):
    """List of {tid, name, score}, indexed in display order."""
    if not controller.is_game_initialized():
        # Pre-game: show the placeholder team names with a zero score.
        teams_map = controller.get_teams_for_form()
        return [{"tid": tid, "name": name, "score": 0} for tid, name in teams_map.items()]

    scores_by_tid = controller.get_teams_score_by_tid()
    teams_map = controller.get_teams_for_form()
    # Ordered by tid to match the template for-loop semantics.
    ordered = sorted(
        teams_map.items(),
        key=lambda kv: int("".join(c for c in kv[0] if c.isdigit()) or 0),
    )
    result = []
    for tid, name in ordered:
        result.append(
            {
                "tid": tid,
                "name": name,
                "score": int(scores_by_tid.get(tid, 0) or 0),
            }
        )
    return result


def _questions_payload(controller):
    """Per-question dict keyed by qid.

    Shape:
        { "c1q1": {"answered": True/False, "team_scores": {"team1": -100, ...}} }
    """
    viewer = controller.get_questions_status_for_viewer()
    host = controller.get_questions_status_for_host()
    out = {}
    for qid, answered in viewer.items():
        out[qid] = {
            "answered": bool(answered),
            "team_scores": host.get(qid, {}) or {},
        }
    return out


def _full_state_payload():
    controller = _controller()
    initialized = controller.is_game_initialized()
    in_progress = controller.is_game_in_progress()

    if initialized:
        from ceopardy.model import Game  # local import: model needs an app context

        game_state = Game.query.one().state.name
    else:
        game_state = "uninitialized"

    data = {
        "initialized": initialized,
        "in_progress": in_progress,
        "game_state": game_state,
        "config": _public_config(),
        "messages": config.get("MESSAGES", []),
    }

    if initialized:
        data["teams"] = _teams_payload(controller)
        data["categories"] = controller.get_categories()
        data["questions"] = _questions_payload(controller)
        data["state"] = controller.get_complete_state()
        data["active_question"] = controller.get_active_question()

        # Daily-double waiger range for the team currently in control (if any).
        # Always report a usable range so the host slider is interactive even
        # before any team has been put in control.
        state = controller.get_complete_state()
        _min = config.get("DAILYDOUBLE_WAIGER_MIN", 0)
        _max = config.get("DAILYDOUBLE_WAIGER_MAX_MIN", 0)
        if state.get("dailydouble") in ("enabled", "revealed"):
            try:
                ctrl_team = controller.get_team_in_control()
                _min, _max = controller.get_dailydouble_waiger_range(ctrl_team.tid)
            except NoResultFound:
                # No team in control yet: keep the config defaults.
                pass
        data["dailydouble_range"] = {"min": _min, "max": _max}
        wager = controller.get_dailydouble_wager()
        data["dailydouble_wager"] = {"team": wager[0], "amount": wager[1]} if wager else None
    else:
        data["teams"] = _teams_payload(controller)
        data["categories"] = []
        data["questions"] = {}
        data["state"] = controller.get_complete_state()
        data["active_question"] = {}
        data["dailydouble_range"] = {
            "min": config.get("DAILYDOUBLE_WAIGER_MIN", 0),
            "max": config.get("DAILYDOUBLE_WAIGER_MAX_MIN", 0),
        }
        data["dailydouble_wager"] = None

    return data


def _broadcast_state():
    """Push a full state refresh on the /game namespace."""
    payload = _full_state_payload()
    app.socketio.emit("state", payload, namespace=GAME_NS)


def _broadcast_board_update():
    """Push just the board + team scores without disturbing active overlays."""
    controller = _controller()
    app.socketio.emit(
        "board-update",
        {
            "questions": _questions_payload(controller),
            "teams": _teams_payload(controller),
        },
        namespace=GAME_NS,
    )


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------
@api_bp.route("/state", methods=["GET"])
def get_state():
    return jsonify(_full_state_payload())


@api_bp.route("/roundfiles", methods=["GET"])
def list_roundfiles():
    return jsonify(utils.list_roundfiles())


# ---------------------------------------------------------------------------
# Game lifecycle
# ---------------------------------------------------------------------------
@api_bp.route("/init", methods=["POST"])
def init_game():
    controller = _controller()
    data = request.get_json(force=True, silent=True) or {}
    action = data.get("action")

    if action == "new":
        roundfile = data.get("name")
        if not roundfile:
            return jsonify(result="failure", error="Missing round file name"), 400
        app.logger.info("New game requested with round file: %s", roundfile)

        if controller.is_game_initialized():
            controller.db_backup_and_create_new()

        teamnames = {
            "team{}".format(i): "Team {}".format(i) for i in range(1, config["NB_TEAMS"] + 1)
        }
        try:
            controller.setup_teams(teamnames)
            controller.setup_questions(roundfile)
            controller.start_game()
        except (GameProblem, GamefileParsingError, QuestionParsingError):
            app.logger.exception("Initialization error!")
            return jsonify(result="failure", error="Initialization error!"), 500

    elif action == "resume":
        controller.resume_game()
    else:
        return jsonify(result="failure", error="Unknown action"), 400

    # Default overlay: show the "game starting" message.
    content = "<p>{}</p>".format(config["MESSAGES"][0]["text"])
    controller.set_state("message", "message1")
    controller.set_state("overlay-big", content)
    controller.set_state("question", "")
    controller.set_state("overlay-question", "")

    _broadcast_state()
    app.socketio.emit(
        "overlay-big",
        {"id": "message1", "html": content},
        namespace=GAME_NS,
    )

    return jsonify(result="success")


@api_bp.route("/finish", methods=["POST"])
def finish():
    controller = _controller()
    if controller.is_final_question():
        # TODO: final round is not implemented yet - keep parity with legacy behavior.
        pass
    else:
        text = "<p>That's all folks! Thanks for playing!</p>"
        # Clear any active question / DD before showing the end-of-game
        # overlay, otherwise stale ui_state can resurrect the DD card on the
        # viewer the next time it loads.
        controller.set_state("question", "")
        controller.end_dailydouble()
        controller.set_state("overlay-question", text)
        controller.set_state("overlay-big", text)
        controller.finish_game()
        app.socketio.emit("dailydouble-wager", {"team": None, "amount": None}, namespace=GAME_NS)
        app.socketio.emit("question-hide", {}, namespace=GAME_NS)
        app.socketio.emit("overlay-big", {"id": "final", "html": text}, namespace=GAME_NS)
    _broadcast_state()
    return jsonify(result="success")


# ---------------------------------------------------------------------------
# Team management
# ---------------------------------------------------------------------------
@api_bp.route("/teams", methods=["POST"])
def update_teams():
    controller = _controller()
    data = request.get_json(force=True, silent=True) or {}
    if not data:
        return jsonify(result="failure", error="No team names provided"), 400

    # Enforce uniqueness + required fields (server-side equivalent of the
    # old UniqueTeamName validator).
    names = list(data.values())
    if any(not n for n in names):
        return jsonify(result="failure", error="Team names cannot be empty"), 400
    if len(set(names)) != len(names):
        return jsonify(result="failure", error="Team names must be unique"), 400

    controller.update_teams(data)

    app.socketio.emit("team-names", {"names": data}, namespace=GAME_NS)
    _broadcast_state()
    return jsonify(result="success", teams=data)


@api_bp.route("/team/select", methods=["POST"])
def team_select():
    controller = _controller()
    data = request.get_json(force=True, silent=True) or {}
    tid = data.get("tid") or ""
    controller.set_state("team", tid)
    # If we're mid-DD and control is reassigned, drop the previous team's
    # wager (a new one is needed) and re-broadcast the wager range computed
    # for the new controlling team — the host's slider min/max must follow.
    state = controller.get_complete_state()
    if state.get("dailydouble") == "enabled" and tid:
        controller.clear_dailydouble_wager()
        app.socketio.emit("dailydouble-wager", {"team": None, "amount": None}, namespace=GAME_NS)
        try:
            dbl_min, dbl_max = controller.get_dailydouble_waiger_range(tid)
            app.socketio.emit(
                "dailydouble-range",
                {"team": tid, "range": {"min": dbl_min, "max": dbl_max}},
                namespace=GAME_NS,
            )
        except UnknownTeamError:
            app.logger.warning(
                "DD range recompute skipped: unknown team %s; "
                "client keeps its previous slider range",
                tid,
            )
    app.socketio.emit("team-select", {"tid": tid or None}, namespace=GAME_NS)
    return jsonify(result="success", tid=tid)


@api_bp.route("/team/roulette", methods=["POST"])
def team_roulette():
    controller = _controller()
    nb = controller.get_nb_teams()
    winner = "team{}".format(random.randrange(1, nb + 1))
    sequence = ["team{}".format(i % nb + 1) for i in range(12)]
    sequence.append(winner)
    controller.set_state("team", winner)
    app.socketio.emit("team-roulette", {"sequence": sequence, "winner": winner}, namespace=GAME_NS)
    return jsonify(result="success", winner=winner)


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------
@api_bp.route("/question/select", methods=["POST"])
def question_select():
    controller = _controller()
    data = request.get_json(force=True, silent=True) or {}
    qid = data.get("id")
    try:
        col, row = utils.parse_question_id(qid)
    except InvalidQuestionId:
        return jsonify(result="failure", error="Invalid qid"), 400

    question = controller.get_question(col, row)
    answer = controller.get_answer(col, row)

    if question["dailydouble"] is True:
        # A Daily Double normally requires a team to be in control (they had
        # to pick the clue to trigger it). If that invariant is broken — most
        # likely because the operator forgot to use the roulette — fall back
        # to team1 and log loudly so it's noticed.
        try:
            ctrl_team = controller.get_team_in_control()
        except NoResultFound:
            app.logger.warning(
                "Daily Double selected with no team in control; falling back to team1. "
                "Normally, you should use the roulette to assign control before picking a clue."
            )
            controller.set_state("team", "team1")
            ctrl_team = controller.get_team_in_control()
        dbl_min, dbl_max = controller.get_dailydouble_waiger_range(ctrl_team.tid)

        controller.set_state("question", qid)
        controller.set_state("dailydouble", "enabled")

        # Hide any previous question overlay, show the daily-double animation.
        app.socketio.emit("question-hide", {}, namespace=GAME_NS)
        app.socketio.emit(
            "dailydouble",
            {
                "qid": qid,
                "category": question["category"],
                "team": ctrl_team.tid,
                "range": {"min": dbl_min, "max": dbl_max},
            },
            namespace=GAME_NS,
        )
        return jsonify(
            result="success",
            dailydouble=True,
            team=ctrl_team.tid,
            dailydouble_range={"min": dbl_min, "max": dbl_max},
            question=config.get("DAILYDOUBLE_HOST_TEXT"),
        )

    controller.set_state("question", qid)
    controller.end_dailydouble()
    app.socketio.emit(
        "question-show",
        {
            "qid": qid,
            "text": question["text"],
            "category": question["category"],
            "dailydouble": False,
        },
        namespace=GAME_NS,
    )
    return jsonify(
        result="success",
        dailydouble=False,
        question=question["text"],
        answer=answer,
    )


@api_bp.route("/dailydouble/reveal", methods=["POST"])
def dailydouble_reveal():
    """Reveal the DD clue: flip state to 'revealed' and broadcast the text."""
    controller = _controller()
    state = controller.get_complete_state()
    if state.get("dailydouble") != "enabled":
        return jsonify(result="failure", error="Daily Double not active or already revealed"), 400
    qid = state.get("question") or ""
    try:
        col, row = utils.parse_question_id(qid)
    except InvalidQuestionId:
        return jsonify(result="failure", error="No active DD question"), 400
    question = controller.get_question(col, row)
    controller.set_state("dailydouble", "revealed")
    app.socketio.emit(
        "dailydouble-reveal",
        {"qid": qid, "text": question["text"], "category": question["category"]},
        namespace=GAME_NS,
    )
    return jsonify(result="success")


@api_bp.route("/dailydouble/wager", methods=["POST"])
def dailydouble_wager():
    """Persist + broadcast the controlling team's live DD wager."""
    controller = _controller()
    data = request.get_json(force=True, silent=True) or {}
    try:
        amount = int(data.get("amount"))
    except (TypeError, ValueError):
        return jsonify(result="failure", error="Invalid amount"), 400
    try:
        ctrl_team = controller.get_team_in_control()
    except NoResultFound:
        return jsonify(result="failure", error="No team in control"), 400
    try:
        tid, amount = controller.set_dailydouble_wager(ctrl_team.tid, amount)
    except GameProblem as e:
        return jsonify(result="failure", error=str(e)), 400
    app.socketio.emit(
        "dailydouble-wager",
        {"team": tid, "amount": amount},
        namespace=GAME_NS,
    )
    return jsonify(result="success", team=tid, amount=amount)


@api_bp.route("/question/deselect", methods=["POST"])
def question_deselect():
    controller = _controller()
    controller.set_state("question", "")
    controller.end_dailydouble()
    app.socketio.emit("question-hide", {}, namespace=GAME_NS)
    _broadcast_board_update()
    return jsonify(result="success")


@api_bp.route("/answer", methods=["POST"])
def submit_answer():
    controller = _controller()
    data = request.get_json(force=True, silent=True) or {}
    qid = data.get("id")
    answers = data.get("answers") or {}
    try:
        col, row = utils.parse_question_id(qid)
    except InvalidQuestionId:
        return jsonify(result="failure", error="Invalid qid"), 400

    question = controller.get_question(col, row)
    if question["dailydouble"] is False:
        # Normal questions: one -1/0/1 score per team.
        normal = {
            tid: int(val)
            for tid, val in answers.items()
            if "-" not in tid  # filter helpers
        }
        if not controller.answer_normal(col, row, normal):
            return jsonify(result="failure", error="Answer submission failed"), 500
    else:
        team = controller.get_team_in_control()
        tid = team.tid
        answer = answers.get(f"{tid}-dailydouble", -1)
        waiger = answers.get(f"{tid}-waiger-dailydouble", 0)
        if not controller.answer_dailydouble(col, row, team, answer, waiger):
            return jsonify(result="failure", error="Answer submission failed"), 500
        controller.end_dailydouble()
        app.socketio.emit("dailydouble-wager", {"team": None, "amount": None}, namespace=GAME_NS)

    # Team that ultimately "won" this question stays in control.
    ctl_team = controller.get_good_answer_team(col, row)
    controller.set_state("team", ctl_team or "")

    app.socketio.emit("team-select", {"tid": ctl_team or None}, namespace=GAME_NS)
    _broadcast_board_update()
    return jsonify(result="success", ctl_team=ctl_team)


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------
@api_bp.route("/message/show", methods=["POST"])
def message_show():
    controller = _controller()
    data = request.get_json(force=True, silent=True) or {}
    mid = data.get("id") or ""
    text = data.get("text") or ""
    html = "<p>{0}</p>".format(text)

    controller.set_state("message", mid)
    controller.set_state("overlay-big", html)

    app.socketio.emit("overlay-big", {"id": mid, "html": html}, namespace=GAME_NS)
    return jsonify(result="success")


@api_bp.route("/message/hide", methods=["POST"])
def message_hide():
    controller = _controller()
    controller.set_state("message", "")
    controller.set_state("overlay-big", "")
    app.socketio.emit("overlay-big", {"id": "", "html": ""}, namespace=GAME_NS)
    return jsonify(result="success")


# ---------------------------------------------------------------------------
# Misc host state (drawer positions etc.)
# ---------------------------------------------------------------------------
@api_bp.route("/slider", methods=["POST"])
def slider():
    controller = _controller()
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("id")
    value = data.get("value", "")
    if not name:
        return jsonify(result="failure", error="Missing slider id"), 400
    controller.set_state(name, value)
    app.socketio.emit("slider", {"id": name, "value": value}, namespace=GAME_NS)
    return jsonify(result="success")
