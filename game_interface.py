# DO NOT CHANGE THIS CODE

from card import Card
from game_state import GameStateView, InvalidAction
from model import Model
from player_action import PlayerAction


class GameInterface:
    """Runs your model. The organiser's copy of this file is what plays.

    The engine keeps game_state up to date; this only reads it.
    """

    # DO NOT CHANGE THIS CODE
    def __init__(
        self,
        model: Model,
        game_state: GameStateView,
        player_id: int,
        hand: list[Card],
    ):
        if len(hand) != 2 or not all(isinstance(card, Card) for card in hand):
            raise ValueError(f"a hand is 2 Cards, not {hand!r}")
        self.model = model
        self.game_state = game_state
        self.player_id = player_id  # checked against every action returned
        self.model.seed(list(hand), player_id)

    # Gateway function that runs validation
    def process_action(self, actions: list[PlayerAction]) -> PlayerAction:
        """Takes the actions since your last turn and returns your move."""
        action = self.model.run(actions, self.game_state)
        # Type, then id, then the rules: each check relies on the one before.
        if not isinstance(action, PlayerAction):
            raise InvalidAction(
                "run() must return a PlayerAction, not "
                f"{type(action).__name__} ({action!r})"
            )
        if action.player_id != self.player_id:
            raise InvalidAction(
                f"your action has player_id {action.player_id}, "
                f"but you are player {self.player_id}"
            )
        self.game_state.validate_action(action)
        return action
