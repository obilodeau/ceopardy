from flask import Flask, render_template

app = Flask(__name__)

@app.context_processor
def inject_config():
    """Injects ceopardy configuration for the template system"""
    return {
        "CATEGORIES_PER_GAME": 5,
        "QUESTIONS_PER_CATEGORY": 5
    }


@app.route('/')
def gameboard():
    return render_template("gameboard.html")


if __name__ == '__main__':
    app.run(debug=True)
