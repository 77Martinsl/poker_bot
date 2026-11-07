# Poker bot arena

No-limit Texas hold'em for bots. A team writes a `Model` in `model.py`; the
model object is pickled and submitted, and the organiser's engine plays it
against other teams' models.

This file has two sections. **Default to "For bot authors"**: almost everyone
working in this repo is writing a bot. Use "For maintainers" only when the
user says they maintain the engine.

## For bot authors

### Setup

Python 3.10+ and Pydantic, pinned in `requirements.txt` (the engine uses the
same version, so keep the pin). From the repo root:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Run everything with `.venv/bin/python` (in VS Code, select `.venv` as the
interpreter): the system `python3` cannot import the code without Pydantic.
On Ubuntu, if `venv` or `pip` is missing: `sudo apt install python3-venv
python3-pip`.

### Rules for Claude

- Edit only `model.py` and new files you add next to it. Never edit a file
  headed `DO NOT CHANGE THIS CODE` (`card.py`, `player_action.py`,
  `game_state.py`, `game_interface.py`, `hand_eval.py`): the organiser's
  copies are what play, so local changes only make your tests lie.
- The model is pickled. Keep its attributes plain data (numbers, lists,
  dicts, numpy arrays, model weights). No lambdas, open files, sockets,
  threads or generators as attributes. Load weights and data in `__init__`.
- Imports are flat (`from card import Card`): run code from the repo root,
  with `.venv/bin/python`.
- Never guess a `GameStateView` name: use only those listed below. Editors
  cannot autocomplete them, and any other name raises `AttributeError`.

### How a bot is run

1. `Model()` is constructed and pickled once.
2. Each hand, the engine builds `GameInterface(model, game_state, player_id,
   hand)`, which calls `model.seed(hand, player_id)` once. Store both:
   `run` is not given them again.
3. On each of your turns, `model.run(actions, game_state)` is called:
   - `actions`: every `PlayerAction` since your last turn this hand, oldest
     first, your own previous move and the dealer's cards included.
   - `game_state`: a read-only `GameStateView` of the hand, already updated
     with `actions`.
4. `run` returns one `PlayerAction` with your own `player_id`. A non-
   `PlayerAction`, someone else's id or an illegal move raises
   `InvalidAction`.

### Errors

Two kinds, both subclasses of `ValueError`:

- `pydantic.ValidationError`: a value has the wrong type or range, e.g.
  `Card("1", "S")`, `PlayerAction.raise_to(0, 2.5)`, `evaluate` on 4 cards.
  Checks are strict: no coercion, so `"5"` and `True` are not numbers. For
  positional arguments the message names the argument by position from
  `0`, counting `self` in methods: `PlayerAction / 0 / Input should be a
  valid integer` means `player_id`, `GameState.set_stack / 2 / ...` means
  `chips`.
- `InvalidAction` (`game_state.py`): the move breaks the rules of the hand,
  e.g. out of turn or a raise outside `raise_range`.

The horizon is one hand: a fresh `GameInterface` (and `seed`) every hand.

### Game rules as implemented

- Players are numbered `0..n-1`; every per-player tuple is indexed by id.
  The dealer is player `-1` (`player_action.DEALER`).
- Blinds are posted automatically (default 10/20, stacks 500). Heads-up, the
  button posts the small blind and acts first preflop; after the flop the
  first player after the button acts first.
- The dealer turns board cards over one at a time (`kind == "reveal_card"`):
  the 3rd, 4th and 5th card open the flop, turn and river.
- `raise_to(total)` names your **total bet this street**, not the increment.
  Legal totals are `min_raise_to..max_raise_to` (`raise_range`).
- A raise must be at least the last full raise (`last_raise`). An all-in
  smaller than that does not reopen betting for players who already acted.
- Fold and call are always legal on your turn. `call` checks when nothing is
  owed and calls all-in for less when your stack is short.

### API

`PlayerAction` (`player_action.py`), always built with a constructor:

| Constructor | Meaning |
|---|---|
| `PlayerAction.fold(player_id)` | fold |
| `PlayerAction.call(player_id)` | call, or check when `call_amount == 0` |
| `PlayerAction.raise_to(player_id, total)` | raise to a street total |

Fields: `player_id`, `kind` (`"fold"`, `"call"`, `"raise"`, `"reveal_card"`),
`amount` (raise total), `card` (for `reveal_card`).

`Card` (`card.py`): `Card.parse("AS")`, `card.rank` (`"2".."9"`, `"T"`, `"J"`,
`"Q"`, `"K"`, `"A"`), `card.suit` (`"C"`, `"D"`, `"H"`, `"S"`), `card.value`
(2 to 14, ace high), `str(card) == "AS"`. Compare ranks with `.value`, never
with the rank strings.

`GameStateView` (`game_state.py`): every name you can read. Lists come back as
tuples.

| The table | |
|---|---|
| `button`, `small_blind`, `big_blind` | player id; chips; chips |
| `stacks`, `bets`, `folded`, `acted` | per player: chips behind, chips bet this street, bools |
| `teams` | per player: team name. Seats change between hands, names do not: your team is `teams[self.player_id]`, a team's seat is `teams.index(name)` |
| `board` | Cards dealt so far |
| `street` | `"preflop"`, `"flop"`, `"turn"`, `"river"` |
| `pot` | every chip put in this hand, this street's bets included |
| `last_raise` | size of the last full raise this street |
| `to_act` | player id to act, `None` when the street is closed |
| `num_players`, `players_in_hand`, `active_players` | count; ids not folded; ids not folded and not all-in |
| `is_street_closed`, `is_hand_over` | bools |
| `current_bet` | the street total everyone must reach |

| Any player (methods) | |
|---|---|
| `status(player_id)` | `"active"`, `"folded"` or `"all_in"` |
| `effective_stack(player_id)` | their chips behind, capped by the biggest other stack still in (chips already bet excluded) |
| `spr(player_id)` | `effective_stack / pot` |

| The player to act (you, inside `run`) | |
|---|---|
| `call_amount` | chips a call adds (0 = check) |
| `min_raise_to`, `max_raise_to`, `raise_range` | legal raise totals; `raise_range` is `None` when you cannot raise |
| `can_raise` | bool |
| `legal_actions` | property, no `()`: e.g. `("fold", "call", "raise")` |
| `pot_odds` | `call_amount / (pot + call_amount)`, `0.0` when checking |
| `validate_action(action)` | raises `InvalidAction` if `action` is illegal |

`hand_eval.py`: `evaluate(cards)` takes 5 to 7 Cards (a list or tuple) and returns a tuple that
compares with `<`/`>` (higher wins, equal splits); `category(rank)` names it,
e.g. `"full_house"`. `rank[0]` indexes `CATEGORIES`, from `0` (high card) to
`8` (straight flush). Typical use: `evaluate(self.hand + list(game_state.board))`.

### Example bot

```python
from hand_eval import evaluate
from player_action import PlayerAction


class Model:
    def __init__(self):
        self.hand = []
        self.player_id = None

    def seed(self, hand, player_id):
        self.hand = hand
        self.player_id = player_id

    def run(self, actions, game_state):
        me = self.player_id
        if len(game_state.board) >= 3:
            # Two pair or better (see hand_eval.CATEGORIES).
            strong = evaluate(self.hand + list(game_state.board))[0] >= 2
        else:
            high, low = sorted(card.value for card in self.hand)[::-1]
            strong = high == low or low >= 10  # a pair, or two high cards
        if strong and "raise" in game_state.legal_actions:
            low, high = game_state.raise_range
            # Raise to about the pot, kept within the legal range.
            return PlayerAction.raise_to(me, min(high, max(low, game_state.pot)))
        if game_state.call_amount == 0 or game_state.pot_odds < 0.25:
            return PlayerAction.call(me)
        return PlayerAction.fold(me)
```

### Testing locally

`engine.play_hand` plays one hand exactly as the organiser's engine does and
pays out the pot. From the repo root:

```python
import random
from deck import full_deck
from engine import play_hand
from model import Model

deck = full_deck()
random.Random(1).shuffle(deck)  # same seed, same cards
result = play_hand([Model(), Model()], deck, stacks=[500, 500])
print(result.net, [str(c) for c in result.board], result.faults)
```

`result.net` is chips won or lost per seat. `result.faults` maps a seat to
why its move was replaced: an exception in `seed` or `run`, or an illegal
move, is not fatal; the engine checks (nothing owed) or folds for you
instead. An empty `faults` means your bot played legally.

Run the engine's own tests with `.venv/bin/pip install -r
requirements-dev.txt`, then `.venv/bin/python -m pytest -q`.

### Common mistakes

- Reading `call_amount`, `min_raise_to`, `can_raise`, `legal_actions`,
  `raise_range` or `pot_odds` outside your turn: they describe `to_act`.
- Calling `legal_actions()` with brackets: it is a property.
- Mutating `board` or `stacks`: they are tuples; copy with `list(...)`.
- Treating `raise_to(x)` as "raise by x".
- Forgetting to store `hand` and `player_id` in `seed`.
- Passing card strings where Cards are expected: use `Card.parse("AS")`.
- Running with the system `python3` instead of `.venv/bin/python`.

### Not decided yet

Do not assume an answer to these; ask the user, who can ask the organisers:
the match format (heads-up or more players, number of hands, duplicate
deals), what happens after an `InvalidAction` (the local engine checks or
folds for you), time limits per move, how to submit (pickle format, Python
version), and whether a big blind posted all-in for less still makes
others call the full big blind (currently they only call what was posted).

## For maintainers

- This repo is the source of truth for the arena. The older
  `poker_bot_infrastructure` repo is reference only: never port its live
  ladder, SQLite, results site or websocket code.
- Scope: pickled `Model` submissions, bot-vs-bot match evaluation, action
  validation. Simplicity over features. The tournament side is deferred.
- Architecture: one shared `GameState` per hand, owned by the engine
  (`engine.py`). Its `process_action` validates betting actions and
  `deal_card` before changing anything. Models only ever see a
  `GameStateView` of it; `GameStateView.PUBLIC` is the whitelist of what
  they may read. Private information (hole cards, player id) lives in
  `GameInterface` and the model, never in `GameState`.
- The view stops mistakes, not cheating. In the same process a model can
  change the shared state (`view._state`), rewrite `GameStateView.PUBLIC`,
  read every hole card and the deck through `sys._getframe` or `gc`, and
  edit Cards and actions with `object.__setattr__`. Per-seat copies would
  not fix this. Requirement for the organiser's engine: each model runs in
  its own sandboxed process (which also guards the OS and handles time
  limits, `sys.exit` and crashes). `engine.play_hand` is in-process and only
  for trusted, local play.
- `engine.play_hand` never trusts a returned action: anything not exactly a
  `PlayerAction` is a fault, and the rest is rebuilt from its fields and
  validated before it is applied or shown to other seats.
- The engine routes turns: `GameInterface` assumes it is only called when
  its player is `to_act`, and the engine applies the returned action.
  `engine.play_hand` is one hand only; match format (seating, button
  rotation, duplicate deals, carrying stacks) belongs to its caller.
- `engine.py` and `deck.py` are covered by `tests/` (pytest + Hypothesis,
  pinned in `requirements-dev.txt`). Keep them passing.
- A new `GameState` query must also be added to `GameStateView.PUBLIC` and
  to the API tables above.
- Validation uses Pydantic v2 in strict mode, and only at entry points:
  `Card` and `PlayerAction` are strict Pydantic dataclasses (not
  `BaseModel`, so positional construction keeps working), and
  `setup_hand`, `set_stack`, `deal_card`, `GameInterface.__init__` and
  `evaluate` use `@validate_call`. Types do per-argument checks; checks
  between arguments (button < players, small blind <= big blind, duplicate
  cards) stay hand-written. Never validate `process_action` or the queries:
  they are the hot path.
- `GameInterface` does not validate `model` (`SkipValidation`): any object
  with `seed` and `run` is a bot.
- Keep `pydantic` pinned exactly in `requirements.txt`: pickles of Pydantic
  objects are only guaranteed to load under the version that made them, and
  the engine and every team must match.
- The files marked `DO NOT CHANGE THIS CODE` are the public contract: any
  change to a name or signature in them breaks submitted bots, so call it
  out to the user before making it.
- Commit to `main` only when asked, using jj (the repo is colocated);
  never push unless asked.
