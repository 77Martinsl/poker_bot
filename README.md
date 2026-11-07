# Poker bot hackathon

Write a bot that plays no-limit Texas hold'em. Your bot is a `Model` in
`model.py`. It is pickled and submitted, and the organisers' engine plays it
against other teams' bots.

## 1. Fork and set up

1. **Fork this repo** on GitHub and clone your fork.
2. Create a virtual environment and install the dependencies (Python 3.10+):

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

Run everything with `.venv/bin/python` from the repo root (in VS Code, select
`.venv` as the interpreter). If `venv` is missing on Ubuntu:
`sudo apt install python3-venv python3-pip`.

## 2. Implement `model.py`

**`model.py` is the one file you must implement.** Add your own files next to
it if you need them. The template calls every hand, so fill in:

- `seed(hand, player_id)`: your two hole cards and your seat, once per hand.
  Store them.
- `run(actions, game_state)`: on each of your turns, return one
  `PlayerAction`: `fold`, `call` (also checks) or `raise_to`.
- `end_game(actions, game_state)` (optional): called after every hand. Learn
  from it, for example about opponents, using `game_state.teams`.

Rules that matter:

- Keep the model's attributes plain data (numbers, lists, dicts, numpy
  arrays, weights). No lambdas, open files, sockets or threads: the model is
  pickled. Load weights and data in `__init__`.
- Do not edit `card_utils.py`, `player_action.py`, `game_state.py` or
  `game_interface.py`. The organisers' copies are what play.
- Only use `GameStateView` names listed in [CLAUDE.md](CLAUDE.md): any other
  name raises `AttributeError`.

[CLAUDE.md](CLAUDE.md) has the full rules, the API tables and the common
mistakes. Read it before you start.

## 3. Check and measure your bot

```sh
# Is it a valid submission? (pickles, plays legally, no faults, in time)
.venv/bin/python -m pytest tests/test_model.py -q

# How strong is it? bb/100 against each dummy bot, with a 95% interval
.venv/bin/python -m evals
.venv/bin/python -m evals --opponents tight equity --deals 1000 --table
```

Beating the dummy bots shows your bot works, not that it will win the
tournament: that depends on the other teams. Results are only meaningful when
the interval does not include 0, so add `--deals` to narrow it.

## 4. Submit

Not decided yet: the organisers will say how to submit. The arena expects one
folder per team, with the pickle named after the team next to its code, for
example `bots/team_a/team_a.pkl` and `bots/team_a/model.py`.
