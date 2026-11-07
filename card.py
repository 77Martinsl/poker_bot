# DO NOT CHANGE THIS CODE

from dataclasses import dataclass

RANKS = "23456789TJQKA"
SUITS = "CDHS"


@dataclass(frozen=True)
class Card:
    """A playing card, e.g. Card("A", "S") or Card.parse("AS")."""

    rank: str  # one of RANKS
    suit: str  # one of SUITS

    def __post_init__(self):
        # Type and length first: `in` on a non-str raises TypeError, and ""
        # is in every string.
        if not (isinstance(self.rank, str) and len(self.rank) == 1
                and self.rank in RANKS):
            raise ValueError(f"unknown rank {self.rank!r}")
        if not (isinstance(self.suit, str) and len(self.suit) == 1
                and self.suit in SUITS):
            raise ValueError(f"unknown suit {self.suit!r}")

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
