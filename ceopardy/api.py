import flask
from flask import Blueprint, request
from flask_socketio import SocketIO, send, emit
import ceopardy.controller as controller
import random
#import flask_login


api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/', defaults={'path': 'debug'})
@api.route('/<path:path>', methods=['GET', 'PUT', 'POST', 'DELETE'])
#@flask_login.login_required
def dispatcher(path):
    parts = path.split("/")
    handler = parts.pop(0)
    #if len(parts) > 0 and len(parts[-1]) == 0:
    #    parts.pop()
    if len(parts) == 0:
        # Request should have ended with a / but we fix it anyway...
        parts.append("")
    # Get rid of file inclusion and directory traversal crap right away!
    if "." in parts or ".." in parts:
        return flask.jsonify({"result": "Fuck off!"})
    method = request.method.lower()
    if request.method == "GET":
        data = request.args
    elif request.method == "POST" or request.method == "PUT": 
        data = request.form
    else:
        data = None
    function = None
    try:
        function = getattr(Handlers, method + "_" + handler)
    except AttributeError:
        # Fallback...for debug purposes!
        if handler == "debug":
            success, variable = Handlers.debug
    if function is not None:
        try:
            success, variable = function(parts, data)
        except:
            success = False
            result = {}
            variable = "Server-side failure!"
        if success is None:
            return variable
        if success:
            result = variable
            result["result"] = "ok"
        else:
            result = {}
            result["result"] = variable
    else:
        result = {}
        result["result"] = "Operation not supported!"
    return flask.jsonify(**result)


class Handlers:
    '''
    Operations handlers, REST style where a request like:
        VERB /operation/something/item
    Will end up calling the method verb_something(item, data) where item is the rest of the path 
    as a list split by "/" and data is the data that comes with the request.
    On success, methods return True with a dictionnary of results.
    On failure, methods return False with a message.
    '''
    def debug(parts, data):
        '''
        The name says it all...
        '''
        print("debug", file=sys.stderr)
        return True, {"debug": "debug"}

    def post_roulette(parts, data):
        '''
        '''
        if len(parts[-1]) == 0:
            pass
        else:
            pass
        nb = controller.get().get_nb_teams()
        #nb = 3
        l = []
        team = "t" + str(random.randrange(1, nb + 1))
        for i in range(12):
            l.append("t" + str(i % nb + 1))
        l.append(team)
        emit("roulette-team", l, broadcast=True, namespace="/viewer")
        return True, {}
    '''
    # Not supported
    def post_roulette(parts, data):
    def put_roulette(parts, data):
    def delete_roulette(parts, data):
    '''

