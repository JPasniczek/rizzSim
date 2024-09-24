# here implement class player
from typing import List, Tuple, Dict, Any

from clemgame.clemgame import Player


class Dater(Player):
    def __init__(self, model, player: str):
        super().__init__(model)
        self.player: str = player
        self.history: List = []

    # programmatic response
    def _custom_response(self, messages, turn_idx) -> str:
        return "nothing for now"
