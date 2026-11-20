"""Turn raw replies into scores, a leaderboard file, and data for the website."""

import csv
import glob
import json
import os
import statistics
import time

from . import BENCHMARK_NAME, VERSION
from .core import ROOT, load_questions, read_records
from .scorers import reference_response, score


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def score_model(records, categories, questions):
    """Score one model's replies. Returns (leaderboard row, average score per question)."""
    by_id = {q["id"]: q for q in questions}
    records = [r for r in records if r["qid"] in by_id]
    trials = sorted({r["trial"] for r in records})

    # points[trial][category] = list of question scores
    points = {t: {c["id"]: [] for c in categories} for t in trials}
    per_question = {}
    for record in records:
        value = score(by_id[record["qid"]], record["response"])
        points[record["trial"]][record["category"]].append(value)
        per_question.setdefault(record["qid"], []).append(value)

    per_trial_index, category_scores = [], {}
    for trial in trials:
        per_trial_index.append(100 * mean(mean(points[trial][c["id"]]) for c in categories))
    for category in categories:
        category_scores[category["id"]] = round(
            100 * mean(mean(points[t][category["id"]]) for t in trials), 1)

    ci95 = None
    if len(per_trial_index) > 1:
        ci95 = round(1.96 * statistics.stdev(per_trial_index) / len(per_trial_index) ** 0.5, 1)

    latencies = [r["latency_s"] for r in records if r.get("latency_s")]
    out_tokens = sum(r.get("completion_tokens") or 0 for r in records)
    costs = [r["cost_usd"] for r in records if r.get("cost_usd") is not None]
    expected = len(questions) * len(trials)
    row = {
        "index": round(mean(per_trial_index), 1),
        "ci95": ci95,
        "categories": category_scores,
        "trials": len(trials),
        "coverage": round(len(records) / expected, 3) if expected else 0,
        "median_latency_s": round(statistics.median(latencies), 2) if latencies else None,
        "tokens_per_second": round(out_tokens / sum(latencies), 1) if latencies and out_tokens else None,
        "cost_per_run_usd": round(sum(costs) / len(trials), 4) if costs and trials else None,
    }
    return row, {qid: round(mean(values), 3) for qid, values in per_question.items()}


def write_csv(path, header, rows):
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def export_spreadsheets(results_dir, board, question_scores, questions):
    """Write CSV files that open directly in Google Sheets or Excel."""
    categories = board["categories"]
    header = (["rank", "model", "model_id", "charlie_index", "plus_minus_95"]
              + [c["name"] for c in categories]
              + ["cost_per_run_usd", "median_seconds", "tokens_per_second", "trials", "answered"])

    def cells(row):
        return ([row["name"], row["id"], row["index"], row["ci95"]]
                + [row["categories"][c["id"]] for c in categories]
                + [row["cost_per_run_usd"], row["median_latency_s"], row["tokens_per_second"],
                   row["trials"], row["coverage"]])

    write_csv(os.path.join(results_dir, "leaderboard.csv"), header,
              [[rank] + cells(row) for rank, row in enumerate(board["models"], 1)])

    # One row per question, one column per model: shows exactly what each model missed.
    models = board["models"]
    write_csv(os.path.join(results_dir, "question_scores.csv"),
              ["question", "category"] + [m["name"] for m in models],
              [[q["id"], q["category"]] + [question_scores[m["id"]].get(q["id"], "") for m in models]
               for q in questions])

    # Running log: every scoring day adds rows, so you can track scores over time.
    history_path = os.path.join(results_dir, "history.csv")
    history_header = ["date", "version", "questions"] + header[1:]
    old = []
    if os.path.exists(history_path):
        with open(history_path, newline="") as handle:
            rows = list(csv.reader(handle))
        if rows and rows[0] == history_header:
            old = [r for r in rows[1:] if not (r[0] == board["generated"] and r[1] == board["version"])]
        elif rows:
            os.replace(history_path, history_path.replace(".csv", f"-before-{board['generated']}.csv"))
    new = [[board["generated"], board["version"], board["question_count"]] + cells(row) for row in models]
    write_csv(history_path, history_header, old + new)


def build_leaderboard(results_dir, model_names, mock=False):
    categories, questions = load_questions()
    rows, question_scores = [], {}
    for path in sorted(glob.glob(os.path.join(results_dir, "raw", "*.jsonl"))):
        records = read_records(path)
        if not records:
            continue
        model_id = records[0]["model"]
        row = {"id": model_id, "name": model_names.get(model_id, model_id)}
        scores, question_scores[model_id] = score_model(records, categories, questions)
        row.update(scores)
        rows.append(row)
    rows.sort(key=lambda row: -row["index"])

    board = {
        "benchmark": BENCHMARK_NAME, "version": VERSION, "mock": mock,
        "generated": time.strftime("%Y-%m-%d", time.gmtime()),
        "question_count": len(questions),
        "categories": [dict(c, questions=sum(q["category"] == c["id"] for q in questions))
                       for c in categories],
        "models": rows,
    }
    with open(os.path.join(results_dir, "leaderboard.json"), "w") as handle:
        json.dump(board, handle, indent=2)
    with open(os.path.join(ROOT, "site", "data.js"), "w") as handle:
        handle.write("window.CHARLIE_DATA = " + json.dumps(board, indent=2) + ";\n")
    export_spreadsheets(results_dir, board, question_scores, questions)
    return board


def print_leaderboard(board):
    categories = board["categories"]
    header = f"{'#':>2}  {'Model':<28} {'Index':>6} {'+/-':>5}  " + " ".join(
        f"{c['name'][:10]:>10}" for c in categories) + f"  {'$/run':>8} {'sec':>6}"
    print(f"\n{board['benchmark']} v{board['version']}  ({board['question_count']} questions)")
    print(header)
    print("-" * len(header))
    for rank, row in enumerate(board["models"], 1):
        cells = " ".join(f"{row['categories'][c['id']]:>10.1f}" for c in categories)
        ci = f"{row['ci95']:.1f}" if row["ci95"] is not None else "-"
        cost = f"{row['cost_per_run_usd']:.4f}" if row["cost_per_run_usd"] is not None else "-"
        secs = f"{row['median_latency_s']:.1f}" if row["median_latency_s"] is not None else "-"
        flag = "" if row["coverage"] >= 1 else f"  (only {row['coverage']:.0%} answered)"
        print(f"{rank:>2}  {row['name'][:28]:<28} {row['index']:>6.1f} {ci:>5}  {cells}  {cost:>8} {secs:>6}{flag}")
    print()


def validate_questions():
    """Check that every question's reference reply earns full marks."""
    categories, questions = load_questions()
    problems = 0
    for question in questions:
        try:
            got = score(question, reference_response(question))
        except Exception as error:  # a broken question should be reported, not crash the check
            got, error_text = None, str(error)
        if got != 1.0:
            problems += 1
            print(f"PROBLEM {question['id']}: reference scored {got if got is not None else error_text}")
    for category in categories:
        count = sum(q["category"] == category["id"] for q in questions)
        print(f"{category['name']:<24} {count} questions")
    print(f"{len(questions)} questions total, {problems} problems")
    return problems == 0
