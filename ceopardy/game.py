
class Game():
    def __init__(self):
        self.config = {
            'NB_TEAMS': 3
        }

    # TODO randomly pick a team
    # TODO save a game in progress
    # TODO load a game in progress

class Team():
    def __init__(self, name):
        self.score = 0
        self.name = name


class GameBoard():
    def __init__(self):
        self.config = {
            'CATEGORIES_PER_GAME': 5,
            'QUESTIONS_PER_CATEGORY': 5
        }

class Question():
    pass
