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
