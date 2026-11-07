# DO NOT CHANGE THIS CODE

from dataclasses import dataclass
from typing import Literal

from card import Card

DEALER = -1  # the dealer's player id


@dataclass(frozen=True)
class PlayerAction:
    """
    One move at the table, by a player or by the dealer.

    Your model returns one each turn: build it with
    PlayerAction.fold(player_id), PlayerAction.call(player_id) (checks when
    nothing is owed) or PlayerAction.raise_to(player_id, total), where total
    is the total you want to have bet this street.

    The dealer (player id DEALER) turns over board cards with
    PlayerAction.reveal_card(card).
    """

    player_id: int  # who acted; DEALER for the dealer
    kind: Literal["fold", "call", "raise", "reveal_card"]
    amount: int = 0  # raise total
    card: Card | None = None  # the card revealed

    def __post_init__(self):
        # Checks the action on its own (not against the game state yet)
        if self.kind not in ("fold", "call", "raise", "reveal_card"):
            raise ValueError(f"unknown action {self.kind!r}")
        if type(self.player_id) is not int:
            raise ValueError(
                f"player_id must be an int, not {self.player_id!r}"
            )
        if self.kind == "reveal_card":
            if self.player_id != DEALER:
                raise ValueError("only the dealer reveals cards")
            if not isinstance(self.card, Card):
                raise ValueError(
                    f"reveal_card needs a Card, not {self.card!r}"
                )
        else:
            if self.player_id == DEALER:
                raise ValueError(f"the dealer cannot {self.kind}")
            if self.card is not None:
                raise ValueError(f"{self.kind} takes no card")
        if self.kind == "raise":
            if type(self.amount) is not int or self.amount <= 0:
                raise ValueError(
                    f"raise needs a whole number of chips, not {self.amount!r}"
                )
        elif self.amount != 0:
            raise ValueError(f"{self.kind} takes no amount")

    # Use these constructors rather than PlayerAction(...) directly.

    @classmethod
    def fold(cls, player_id):
        return cls(player_id, "fold")

    @classmethod
    def call(cls, player_id):
        return cls(player_id, "call")

    @classmethod
    def raise_to(cls, player_id, total):
        return cls(player_id, "raise", total)

    @classmethod
    def reveal_card(cls, card):
        return cls(DEALER, "reveal_card", card=card)

    # Example, inside your Model.run(actions, game_state):
    #
    #     me = self.player_id  # stored by your seed()
    #     if game_state.can_raise:
    #         return PlayerAction.raise_to(me, game_state.min_raise_to)
    #     if game_state.call_amount == 0:
    #         return PlayerAction.call(me)  # nothing owed: this checks
    #     return PlayerAction.fold(me)
