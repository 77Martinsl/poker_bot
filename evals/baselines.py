"""
Sparring bots to measure your model against.

Sanity bots (FoldBot, CallBot, RandomBot, ShoveBot) are easy to beat: losing
to them means a bug. The sparring bots (TightBot, EquityBot) play simple but
sensible poker. Each is a plain Model: seed() then run() every turn.
"""

import random

from card import Card
from deck import full_deck
from hand_eval import evaluate
from player_action import PlayerAction


class _Bot:
    """Stores the hand and seat, as every model must."""

    def __init__(self):
        self.hand: list[Card] = []
        self.player_id = None

    def seed(self, hand, player_id):
        self.hand = hand
        self.player_id = player_id

    def _check_or_fold(self, game_state):
        if game_state.call_amount == 0:
            return PlayerAction.call(self.player_id)
        return PlayerAction.fold(self.player_id)

    def _raise_to(self, game_state, total):
        """A raise to total, kept within the legal range; a call if a raise
        is not allowed."""
        if not game_state.can_raise:
            return PlayerAction.call(self.player_id)
        low, high = game_state.raise_range
        total = min(high, max(low, total))
        return PlayerAction.raise_to(self.player_id, total)


class FoldBot(_Bot):
    """Checks when it is free, otherwise folds."""

    def run(self, actions, game_state):
        return self._check_or_fold(game_state)


class CallBot(_Bot):
    """Checks or calls everything: the classic calling station."""

    def run(self, actions, game_state):
        return PlayerAction.call(self.player_id)


class ShoveBot(_Bot):
    """Goes all-in whenever it can, otherwise calls."""

    def run(self, actions, game_state):
        return self._raise_to(game_state, game_state.max_raise_to)


class RandomBot(_Bot):
    """Picks a legal move at random: raises a random amount 30% of the
    time, folds (when it costs something) 20%, otherwise calls."""

    def __init__(self, seed: int | None = None):
        super().__init__()
        self.rng = random.Random(seed)

    def run(self, actions, game_state):
        roll = self.rng.random()
        if roll < 0.3 and game_state.can_raise:
            low, high = game_state.raise_range
            return PlayerAction.raise_to(
                self.player_id, self.rng.randint(low, high)
            )
        if roll < 0.5:
            return self._check_or_fold(game_state)
        return PlayerAction.call(self.player_id)


class TightBot(_Bot):
    """
    Plays strong starting hands only, then bets made hands.

    Preflop: raises to about three big blinds (or the pot when facing a
    raise) with a pair of 8s or better, or two cards ten or higher with an
    ace or king; otherwise checks or folds. After the flop: bets the pot
    with two pair or better, calls cheap bets with a pair, else checks or
    folds.
    """

    def run(self, actions, game_state):
        if game_state.street == "preflop":
            low, high = sorted(card.value for card in self.hand)
            if (high == low and high >= 8) or (low >= 10 and high >= 13):
                total = max(3 * game_state.big_blind, game_state.pot)
                return self._raise_to(game_state, total)
            return self._check_or_fold(game_state)
        category = evaluate(self.hand + list(game_state.board))[0]
        if category >= 2:  # two pair or better
            return self._raise_to(game_state, game_state.pot)
        if category == 1 and game_state.pot_odds < 0.3:
            return PlayerAction.call(self.player_id)
        return self._check_or_fold(game_state)


class EquityBot(_Bot):
    """
    Plays by its chance of winning, estimated by dealing out random
    opponent hands and boards `samples` times.

    Raises the pot when that chance is well above a fair share of the pot,
    calls when it beats the pot odds, otherwise checks or folds.
    """

    def __init__(self, samples: int = 100, seed: int | None = None):
        super().__init__()
        self.samples = samples
        self.rng = random.Random(seed)

    def run(self, actions, game_state):
        opponents = len(game_state.players_in_hand) - 1
        equity = self.equity(list(game_state.board), opponents)
        # A fair share of the pot is 1 / players; raise well above it.
        if equity > 1.5 / (opponents + 1) and equity > 0.5:
            return self._raise_to(game_state, game_state.pot)
        if equity > game_state.pot_odds:
            return PlayerAction.call(self.player_id)
        return self._check_or_fold(game_state)

    def equity(self, board: list[Card], opponents: int) -> float:
        """Share of the pot won against random hands: ties count split."""
        unseen = [c for c in full_deck() if c not in self.hand + board]
        missing = 5 - len(board)
        won = 0.0
        for _ in range(self.samples):
            cards = self.rng.sample(unseen, missing + 2 * opponents)
            full_board = board + cards[:missing]
            mine = evaluate(self.hand + full_board)
            holes = cards[missing:]
            theirs = [
                evaluate(holes[2 * i:2 * i + 2] + full_board)
                for i in range(opponents)
            ]
            best = max(theirs, default=mine)
            if mine > best:
                won += 1
            elif mine == best:
                won += 1 / (1 + theirs.count(best))
        return won / self.samples


SANITY = {
    "fold": FoldBot,
    "call": CallBot,
    "random": RandomBot,
    "shove": ShoveBot,
}
SPARRING = {
    "tight": TightBot,
    "equity": EquityBot,
}
BASELINES = SANITY | SPARRING
