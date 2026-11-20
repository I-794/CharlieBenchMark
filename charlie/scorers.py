"""Scoring functions. Every scorer returns a float from 0.0 (wrong) to 1.0 (right).

Scoring is fully automatic: no human or model judges an answer.
"""

import json
import math
import os
import re
import subprocess
import sys
import tempfile

ANSWER_RE = re.compile(r"ANSWER\s*:\s*(.+)", re.IGNORECASE)
NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?(?:e[+-]?\d+)?", re.IGNORECASE)
SCI_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*[x*]\s*10\s*\^?\s*\{?\s*(-?\d+)")
MULTIPLIERS = {"thousand": 1e3, "k": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}


def extract_answer(text):
    """Return whatever follows the last 'ANSWER:' in the reply, or None."""
    found = ANSWER_RE.findall(text or "")
    return found[-1].strip() if found else None


def normalize(text):
    text = re.sub(r"[*_`\"'“”‘’]", "", text.strip().lower())
    return re.sub(r"\s+", " ", text).strip(" .!,;:")


def parse_number(text):
    """Read a number out of text like '2,900,000', '2.9e9', '3 billion' or '3 x 10^9'."""
    text = text.replace(",", "").replace("×", "x")
    sci = SCI_RE.search(text)
    if sci:
        return float(sci.group(1)) * 10 ** int(sci.group(2))
    match = NUMBER_RE.search(text)
    if not match:
        return None
    value = float(match.group(0))
    word = re.match(r"\s*([a-z]+)", text[match.end():].lower())
    if word and word.group(1) in MULTIPLIERS:
        value *= MULTIPLIERS[word.group(1)]
    return value


def score_exact(question, response):
    """Right if the final answer matches one of the accepted answers."""
    answer = extract_answer(response)
    if answer is None:
        return 0.0
    accepted = question["answer"]
    if not isinstance(accepted, list):
        accepted = [accepted]
    for expected in accepted:
        expected = str(expected)
        if normalize(answer) == normalize(expected):
            return 1.0
        if NUMBER_RE.fullmatch(expected.strip()):
            got = parse_number(answer)
            if got is not None and math.isclose(got, float(expected)):
                return 1.0
    return 0.0


def score_numeric_range(question, response):
    """Full credit inside [low, high]. Outside it, credit falls off with distance
    on a log scale and reaches zero when the answer is off by a factor of 10."""
    answer = extract_answer(response)
    value = parse_number(answer) if answer else None
    if value is None or value <= 0:
        return 0.0
    low, high = question["low"], question["high"]
    if low <= value <= high:
        return 1.0
    ratio = low / value if value < low else value / high
    return max(0.0, 1.0 - math.log10(ratio))


def _lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def _load_json(text):
    try:
        return json.loads(text)
    except ValueError:
        return None


def check_constraint(constraint, text):
    kind, value = constraint["type"], constraint.get("value")
    if kind == "word_count":
        return len(re.findall(r"[A-Za-z0-9'’-]+", text)) == value
    if kind == "sentence_count":
        return len([part for part in re.split(r"[.!?]+", text) if part.strip()]) == value
    if kind == "line_count":
        return len(_lines(text)) == value
    if kind == "forbid_letter":
        return value.lower() not in text.lower()
    if kind == "forbid_words":
        return not any(re.search(rf"\b{re.escape(w)}\b", text, re.IGNORECASE) for w in value)
    if kind == "contains":
        return value.lower() in text.lower()
    if kind == "lowercase":
        return text == text.lower()
    if kind == "ends_with":
        return text.rstrip(" .!?\n").lower().endswith(value.lower())
    if kind == "acrostic":
        return "".join(line[0] for line in _lines(text)).upper() == value.upper()
    if kind == "sorted_lines":
        lines = [line.lower() for line in _lines(text)]
        return lines == sorted(lines)
    if kind == "no_bullets":
        return not any(re.match(r"([-*•]|\d+[.)])", line) for line in _lines(text))
    if kind == "json_keys":
        data = _load_json(text)
        return isinstance(data, dict) and set(data) == set(value)
    if kind == "json_array_len":
        data = _load_json(text)
        item = data.get(constraint["key"]) if isinstance(data, dict) else None
        return isinstance(item, list) and len(item) == value
    if kind == "json_int":
        data = _load_json(text)
        item = data.get(constraint["key"]) if isinstance(data, dict) else None
        return isinstance(item, int) and not isinstance(item, bool)
    raise ValueError(f"unknown constraint type: {kind}")


def score_constraints(question, response):
    """Fraction of the listed rules that the whole reply obeys."""
    text = (response or "").strip()
    if not text:
        return 0.0
    rules = question["constraints"]
    return sum(check_constraint(rule, text) for rule in rules) / len(rules)


HARNESS = """
import json, sys
namespace = {}
exec(open(sys.argv[1]).read(), namespace)
function = namespace[sys.argv[2]]
tests = json.load(open(sys.argv[3]))
passed = 0
for args, expected in tests:
    try:
        passed += json.loads(json.dumps(function(*args))) == expected
    except Exception:
        pass
print("CHARLIE_RESULT", passed, len(tests))
"""


def extract_code(response):
    blocks = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", response or "", re.DOTALL)
    return blocks[-1] if blocks else (response or "")


def score_code(question, response, timeout=10):
    """Fraction of hidden tests the submitted function passes.

    The code runs in a separate Python process with a time limit. It is not a
    real sandbox, so only run models you are comfortable running code from.
    """
    code = extract_code(response)
    if not code.strip():
        return 0.0
    with tempfile.TemporaryDirectory() as folder:
        paths = {name: os.path.join(folder, name) for name in ("harness.py", "solution.py", "tests.json")}
        with open(paths["harness.py"], "w") as handle:
            handle.write(HARNESS)
        with open(paths["solution.py"], "w") as handle:
            handle.write(code)
        with open(paths["tests.json"], "w") as handle:
            json.dump(question["tests"], handle)
        try:
            result = subprocess.run(
                [sys.executable, "-I", paths["harness.py"], paths["solution.py"],
                 question["function"], paths["tests.json"]],
                cwd=folder, capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return 0.0
    found = re.findall(r"CHARLIE_RESULT (\d+) (\d+)", result.stdout)
    if not found:
        return 0.0
    passed, total = map(int, found[-1])
    return passed / total if total else 0.0


SCORERS = {
    "exact": score_exact,
    "numeric_range": score_numeric_range,
    "constraints": score_constraints,
    "code": score_code,
}


def score(question, response):
    return float(SCORERS[question["scorer"]](question, response))


def reference_response(question):
    """A reply that should earn full marks. Used by `validate` and by mock runs."""
    if "reference" in question:
        return question["reference"]
    if question["scorer"] == "exact":
        answer = question["answer"]
        return f"ANSWER: {answer[0] if isinstance(answer, list) else answer}"
    if question["scorer"] == "numeric_range":
        return f"ANSWER: {math.sqrt(question['low'] * question['high']):.0f}"
    raise ValueError(f"question {question['id']} needs a 'reference' reply")
