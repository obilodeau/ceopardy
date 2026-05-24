from ceopardy import app, create_app, socketio


def main():
    # WARNING: This app is not ready to be exposed on the network.
    #          Game host interface would be exposed.
    create_app()
    socketio.run(app, host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
