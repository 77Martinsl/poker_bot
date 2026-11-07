# NOTE: DO NOT CHANGE THIS CODE

from collections import Counter
from collections.abc import Sequence
from itertools import combinations
from typing import Annotated

from pydantic import ConfigDict, Field, validate_call

from card import Card

# Hand categories, weakest first; a rank's first number indexes this.
CATEGORIES = [
    "high_card",
    "pair",
    "two_pair",
    "three_of_a_kind",
    "straight",
    "flush",
    "full_house",
    "four_of_a_kind",
    "straight_flush",
]


# Pydantic checks the cards against the type hint (strict: Cards only, any
# sequence of 5 to 7 of them) and raises ValidationError, a ValueError.
@validate_call(config=ConfigDict(strict=True))
def evaluate(
    cards: Annotated[Sequence[Card], Field(min_length=5, max_length=7)],
) -> tuple[int, ...]:
    """
    The rank of the best 5-card hand among 5 to 7 cards.

    Ranks compare with < and >: a higher rank wins, equal ranks split. The
    first number is the category (CATEGORIES[rank[0]] names it), the rest
    break ties, e.g. (1, 14, 13, 9, 4) is a pair of aces with K, 9, 4.

        evaluate(hand + list(game_state.board))
    """
    if len(set(cards)) != len(cards):
        raise ValueError(f"duplicate cards in {[str(c) for c in cards]}")
    return max(_rank_five(five) for five in combinations(cards, 5))


def category(rank: tuple[int, ...]) -> str:
    """The name of a rank's category, e.g. "full_house"."""
    return CATEGORIES[rank[0]]


def _rank_five(cards):
    values = sorted((card.value for card in cards), reverse=True)
    flush = len({card.suit for card in cards}) == 1
    straight_high = _straight_high(values)

    # Group by value, biggest groups first, higher values breaking ties:
    # a full house 7 7 7 K K gives counts (3, 2) and ranks (7, 13).
    groups = sorted(Counter(values).items(), key=lambda g: (g[1], g[0]),
                    reverse=True)
    counts = tuple(count for _, count in groups)
    ranks = tuple(value for value, _ in groups)

    if straight_high and flush:
        return (8, straight_high)
    if counts == (4, 1):
        return (7, *ranks)
    if counts == (3, 2):
        return (6, *ranks)
    if flush:
        return (5, *values)
    if straight_high:
        return (4, straight_high)
    if counts == (3, 1, 1):
        return (3, *ranks)
    if counts == (2, 2, 1):
        return (2, *ranks)
    if counts == (2, 1, 1, 1):
        return (1, *ranks)
    return (0, *values)


def _straight_high(values):
    """The top card of a straight in these 5 values, or None. The wheel
    A-2-3-4-5 counts as a 5-high straight."""
    if len(set(values)) != 5:
        return None
    if values[0] - values[4] == 4:
        return values[0]
    if values == [14, 5, 4, 3, 2]:
        return 5
    return None
