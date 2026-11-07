from card import Card
from game_state import GameStateView
from player_action import PlayerAction


class Model:
    """
    Your bot: change anything in this file, and add files next to it.

    This object is what gets pickled, so load weights and data in __init__
    and keep them in plain attributes.
    """

    def __init__(self):
        self.hand = []
        self.player_id = None

    def seed(self, hand: list[Card], player_id: int):
        """
        Called once before the hand: your two hole cards and your id.

        Store them; run() is not given them again.
        """
        self.hand = hand
        self.player_id = player_id

    def run(
        self, actions: list[PlayerAction], game_state: GameStateView
    ) -> PlayerAction:
        """
        Called on your turn.

        actions: everything done since your last turn this hand, oldest
            first: player moves, your own previous move included, and the
            dealer's reveal_card.
        game_state: the public state of the hand, read-only, e.g.
            game_state.call_amount, game_state.status(self.player_id),
            game_state.min_raise_to.
        """
        return PlayerAction.call(self.player_id)
