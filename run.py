from ceopardy import app, create_app, socketio

create_app()

if __name__ == "__main__":
    # WARNING: This app is not ready to be exposed on the network.
    #          Game host interface would be exposed.
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
