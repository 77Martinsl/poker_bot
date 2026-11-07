# NOTE: DO NOT CHANGE THIS CODE

from typing import Literal, get_args

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

Rank = Literal["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
Suit = Literal["C", "D", "H", "S"]

RANKS = "".join(get_args(Rank))  # "23456789TJQKA", lowest first
SUITS = "".join(get_args(Suit))  # "CDHS"


# Pydantic checks the fields against their types on construction and raises
# ValidationError (a ValueError) if they don't match. strict: no coercion.
@dataclass(frozen=True, config=ConfigDict(strict=True))
class Card:
    """A playing card, e.g. Card("A", "S") or Card.parse("AS")."""

    rank: Rank
    suit: Suit

    @classmethod
    def parse(cls, text):
        """Rank then suit: "AS", "TD", "7H", "2C"."""
        if len(text) != 2:
            raise ValueError(f"a card is two characters, not {text!r}")
        return cls(text[0], text[1])

    @property
    def value(self):
        """The rank as a number, 2 to 14 (ace high), for comparing cards:
        Card.parse("AS").value > Card.parse("KD").value."""
        return RANKS.index(self.rank) + 2

    def __str__(self):
        return self.rank + self.suit
