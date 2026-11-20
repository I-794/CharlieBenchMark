"""Command line: python -m charlie [validate | run | score]"""

import argparse
import json
import os
import sys

from .core import MOCK_MODELS, ROOT, run_benchmark
from .report import build_leaderboard, print_leaderboard, validate_questions


def load_models(path):
    with open(path) as handle:
        return json.load(handle)["models"]


def main():
    parser = argparse.ArgumentParser(prog="charlie", description="Run and score the Charlie Index.")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("validate", help="check that the question files are well formed")

    run = commands.add_parser("run", help="ask the models every question and save the replies")
    run.add_argument("--models", default=os.path.join(ROOT, "models.json"))
    run.add_argument("--only", help="run just this one model id from the models file")
    run.add_argument("--trials", type=int, default=3, help="times each question is asked (default 3)")
    run.add_argument("--workers", type=int, default=4, help="requests sent at once (default 4)")
    run.add_argument("--max-tokens", type=int, default=4000)
    run.add_argument("--limit", type=int, help="only the first N questions, for a cheap test")
    run.add_argument("--mock", action="store_true", help="use pretend models, no API key needed")

    score = commands.add_parser("score", help="score saved replies and build the leaderboard")
    score.add_argument("--models", default=os.path.join(ROOT, "models.json"))
    score.add_argument("--mock", action="store_true", help="score the pretend-model results")

    args = parser.parse_args()
    results_dir = os.path.join(ROOT, "results", "mock") if getattr(args, "mock", False) \
        else os.path.join(ROOT, "results")

    if args.command == "validate":
        sys.exit(0 if validate_questions() else 1)

    if args.command == "run":
        if args.mock:
            models = MOCK_MODELS
        else:
            models = load_models(args.models)
            if args.only:
                models = [m for m in models if m["id"] == args.only]
                if not models:
                    sys.exit(f"{args.only} is not in {args.models}")
        run_benchmark(models, results_dir, trials=args.trials, workers=args.workers,
                      max_tokens=args.max_tokens, mock=args.mock, limit=args.limit)
        print("Next: python -m charlie score" + (" --mock" if args.mock else ""))

    if args.command == "score":
        if args.mock:
            names = {m[0]: m[1] for m in MOCK_MODELS}
        else:
            names = {m["id"]: m.get("name", m["id"]) for m in load_models(args.models)}
        board = build_leaderboard(results_dir, names, mock=args.mock)
        if not board["models"]:
            sys.exit("No saved replies found. Run `python -m charlie run` first.")
        print_leaderboard(board)
        where = os.path.relpath(results_dir, ROOT)
        print(f"Website: open site/index.html")
        print(f"Spreadsheets: {where}/leaderboard.csv, {where}/question_scores.csv, {where}/history.csv")


if __name__ == "__main__":
    main()
