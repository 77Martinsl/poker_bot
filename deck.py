from card import RANKS, SUITS, Card


def full_deck() -> list[Card]:
    """
    All 52 cards in a fixed order: by rank, lowest first, then by suit.

    A new list every call. Shuffle a copy for each hand, e.g.
    random.Random(seed).shuffle(deck).
    """
    return [Card(rank, suit) for rank in RANKS for suit in SUITS]
