
from ceopardy.game import GameBoard

class Controller():

    @staticmethod
    def get_gameboard_config():
        gb = GameBoard()
        return gb.config

