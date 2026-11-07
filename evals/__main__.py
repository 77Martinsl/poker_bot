"""
Measures your model against the baseline bots.

    python -m evals                      # heads-up against every baseline
    python -m evals --opponents tight equity --deals 500 --rounds 3
    python -m evals --table              # also one table with all of them

Run from the repo root. bb/100 is big blinds won per 100 hands, with its
95% confidence interval: a result is only meaningful when the interval
does not straddle 0. Beating the sanity bots shows your bot works, not that
it will win: the real field is other teams' bots.
"""

import argparse
import importlib
import pickle

from evals.baselines import BASELINES
from evals.match import MatchResult, play_match

TIME_LIMIT = 10.0  # seconds per move, as the arena enforces it


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(prog="python -m evals")
    parser.add_argument(
        "--model", default="model:Model",
        help="your model as module:Class (default model:Model)",
    )
    parser.add_argument("--name", default="you", help="your team name")
    parser.add_argument(
        "--opponents", nargs="+", choices=list(BASELINES),
        default=list(BASELINES), help="baselines to play (default all)",
    )
    parser.add_argument(
        "--table", action="store_true",
        help="also play one table with you and every opponent",
    )
    parser.add_argument("--deals", type=int, default=100)
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    module, _, attribute = args.model.partition(":")
    model_class = getattr(importlib.import_module(module), attribute)
    # Pickled once, like a submission; every rotation unpickles a fresh one.
    blob = pickle.dumps(model_class())
    you = {args.name: lambda: pickle.loads(blob)}
    opponents = {name: BASELINES[name] for name in args.opponents}

    print(f"{'opponents':<40} {'your bb/100':>18} {'hands':>7} "
          f"{'faults':>6} {'slowest':>8}")
    for name, factory in opponents.items():
        result = play_match(you | {name: factory}, args.deals, args.rounds,
                            args.seed)
        _report(name, result)
    if args.table and len(opponents) > 1:
        result = play_match(you | opponents, args.deals, args.rounds,
                            args.seed)
        _report(f"table of {len(result.names)}", result)


def _report(label: str, result: MatchResult):
    """One row for the first model (yours), then its first fault if any."""
    print(f"{label:<40} {result.bb_per_100[0]:>+9.1f} ± "
          f"{result.ci95[0]:<6.1f} {result.hands:>7} {result.faults[0]:>6} "
          f"{result.max_move_seconds[0]:>7.2f}s")
    if result.first_faults[0] is not None:
        print(f"    first fault: {result.first_faults[0]}")
    if result.max_move_seconds[0] > TIME_LIMIT:
        print(f"    slower than the {TIME_LIMIT:.0f}s limit per move")


if __name__ == "__main__":
    main()
