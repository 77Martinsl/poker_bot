"""Scripted models, decks and invariant checks for the engine tests."""

from card import RANKS, SUITS, Card
from game_state import GameState
from player_action import PlayerAction


def std_deck():
    return [Card(r, s) for r in RANKS for s in SUITS]


def cards(text):
    return [Card.parse(t) for t in text.split()]


def deck_from(*hands, board=""):
    """Hole cards per seat (strings like "AS AH"), then the board, then every
    other card in standard order."""
    front = [c for h in hands for c in cards(h)] + cards(board)
    assert len(set(front)) == len(front)
    return front + [c for c in std_deck() if c not in front]


class Scripted:
    """Plays a script; afterwards plays `default`. Records everything.

    Items: "fold", "call", "allin", "minraise", ("raise", total),
    ("exc", exception), ("return", obj), ("id", other_seat),
    ("action", PlayerAction).
    """

    def __init__(self, script=(), default="call", log=None, mutate=False):
        self.script = list(script)
        self.default = default
        self.log = log
        self.mutate = mutate
        self.turn = 0
        self.seeds = []
        self.runs = []
        self.kept = []  # the raw lists received, by reference
        self.player_id = None

    def seed(self, hand, player_id):
        self.seeds.append((list(hand), player_id))
        self.player_id = player_id

    def run(self, actions, gs):
        snap = {
            "actions": list(actions),
            "to_act": gs.to_act,
            "button": gs.button,
            "small_blind": gs.small_blind,
            "big_blind": gs.big_blind,
            "teams": gs.teams,
            "stacks": gs.stacks,
            "bets": gs.bets,
            "board": gs.board,
            "street": gs.street,
            "call_amount": gs.call_amount,
            "view_type": type(gs),
        }
        self.runs.append(snap)
        self.kept.append(actions)
        if self.log is not None:
            self.log.append((self.player_id, gs.street))
        item = (
            self.script[self.turn] if self.turn < len(self.script)
            else self.default
        )
        self.turn += 1
        if self.mutate:
            actions.clear()
            actions.append("junk")
        me = self.player_id
        if item == "fold":
            return PlayerAction.fold(me)
        if item == "call":
            return PlayerAction.call(me)
        if item == "allin":
            return PlayerAction.raise_to(me, gs.max_raise_to)
        if item == "minraise":
            return PlayerAction.raise_to(me, gs.min_raise_to)
        kind, arg = item
        if kind == "raise":
            return PlayerAction.raise_to(me, arg)
        if kind == "exc":
            raise arg
        if kind == "return":
            return arg
        if kind == "id":
            return PlayerAction.call(arg)
        if kind == "action":
            return arg
        raise AssertionError(f"bad script item {item!r}")


class SeedRaiser:
    def __init__(self, exc=None):
        self.exc = exc if exc is not None else RuntimeError("seed failed")
        self.seed_calls = 0
        self.run_calls = 0

    def seed(self, hand, player_id):
        self.seed_calls += 1
        raise self.exc

    def run(self, actions, gs):
        self.run_calls += 1
        return PlayerAction.call(0)


class RandomBot:
    """Deterministic bot driven by a list of ints drawn up front.

    0 fold, 1-3 call, 4 min raise, 5 all-in, 6 raise an exception,
    7 return None, 8 another seat's id, 9 an illegal raise.
    """

    FAULTS = {6, 7, 8, 9}

    def __init__(self, choices, seed_fault=False):
        self.choices = list(choices)
        self.seed_fault = seed_fault
        self.player_id = None
        self.runs = []  # dicts: actions, call_amount, fault, returned

    def seed(self, hand, player_id):
        self.player_id = player_id
        if self.seed_fault:
            raise ValueError("seed fault")

    def run(self, actions, gs):
        c = self.choices[len(self.runs) % len(self.choices)]
        rec = {
            "actions": list(actions),
            "call_amount": gs.call_amount,
            "fault": c in self.FAULTS,
            "returned": None,
        }
        self.runs.append(rec)
        me = self.player_id
        if c == 0:
            act = PlayerAction.fold(me)
        elif c in (1, 2, 3):
            act = PlayerAction.call(me)
        elif c == 4:
            act = (PlayerAction.raise_to(me, gs.min_raise_to)
                   if gs.can_raise else PlayerAction.call(me))
        elif c == 5:
            act = (PlayerAction.raise_to(me, gs.max_raise_to)
                   if gs.can_raise else PlayerAction.call(me))
        elif c == 6:
            raise RuntimeError("run fault")
        elif c == 7:
            return None
        elif c == 8:
            return PlayerAction.call((me + 1) % gs.num_players)
        else:
            act = PlayerAction.raise_to(me, gs.max_raise_to + 1)
        rec["returned"] = act
        return act


def replay(result, stacks, button=0, small_blind=10, big_blind=20,
           teams=None):
    """Applies result.actions to a fresh GameState; checks the hand ends
    exactly at the last action. Returns (state, states_before) where
    states_before[i] is (to_act, call_amount) before action i."""
    state = GameState(list(stacks), teams=teams)
    state.setup_hand(list(stacks), button, small_blind, big_blind, teams)
    before = []
    for action in result.actions:
        assert not state.is_hand_over, "action recorded after the hand ended"
        if state.is_street_closed:
            before.append((None, None))
        else:
            before.append((state.to_act, state.call_amount))
        state.process_action(action)
    assert state.is_hand_over, "recorded actions do not finish the hand"
    return state, before


def check_result(result, deck, stacks, button=0, small_blind=10,
                 big_blind=20, teams=None):
    """Spec invariants every HandResult must satisfy."""
    from engine import payouts

    n = len(stacks)
    assert result.hands == [[deck[2 * i], deck[2 * i + 1]] for i in range(n)]
    assert result.board == deck[2 * n:2 * n + len(result.board)]
    reveals = [a.card for a in result.actions if a.kind == "reveal_card"]
    assert reveals == result.board
    state, _ = replay(result, stacks, button, small_blind, big_blind, teams)
    contributed = [stacks[i] - state.stacks[i] for i in range(n)]
    if len(state.players_in_hand) > 1:
        assert len(result.board) == 5
    pay = payouts(contributed, list(state.folded), result.hands,
                  result.board, button)
    assert result.net == [pay[i] - contributed[i] for i in range(n)]
    assert sum(result.net) == 0
    assert all(result.net[i] >= -stacks[i] for i in range(n))
    return state
