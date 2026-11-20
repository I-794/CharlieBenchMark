"""Loading questions, talking to models, and recording raw replies."""

import glob
import hashlib
import json
import os
import random
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from . import VERSION
from .scorers import reference_response

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUESTION_DIRS = ["questions", "questions_private"]
API_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPTS = {
    "answer": (
        "You are taking a benchmark. Work through the problem, then end your reply "
        "with one final line in exactly this form:\nANSWER: <your answer>\n"
        "Put only the answer itself after 'ANSWER:', with no units and no explanation."
    ),
    "constraints": (
        "You are taking a benchmark. Follow the instructions exactly. Output only "
        "the requested text, with nothing before or after it."
    ),
    "code": (
        "You are taking a benchmark. Write a Python 3 function that uses only the "
        "standard library. Reply with a single ```python code block that contains "
        "the complete function and nothing else."
    ),
}

# Pretend models for trying the pipeline without an API key:
# (id, display name, skill 0-1, seconds per question, dollars per question)
MOCK_MODELS = [
    ("mock/atlas-large", "Atlas Large (sample)", 0.92, 6.0, 0.0090),
    ("mock/atlas-small", "Atlas Small (sample)", 0.74, 1.6, 0.0011),
    ("mock/birch-pro", "Birch Pro (sample)", 0.85, 3.8, 0.0042),
    ("mock/cedar-mini", "Cedar Mini (sample)", 0.58, 0.9, 0.0003),
    ("mock/delta-open", "Delta Open (sample)", 0.66, 2.4, 0.0006),
]


def load_questions():
    """Read every category file. Returns (categories, questions)."""
    categories, questions, seen = [], [], set()
    for folder in QUESTION_DIRS:
        for path in sorted(glob.glob(os.path.join(ROOT, folder, "*.json"))):
            with open(path) as handle:
                data = json.load(handle)
            if data["category"] not in [c["id"] for c in categories]:
                categories.append({"id": data["category"], "name": data["name"]})
            for question in data["questions"]:
                if question["id"] in seen:
                    raise ValueError(f"duplicate question id: {question['id']}")
                seen.add(question["id"])
                question["category"] = data["category"]
                question["instructions"] = data.get("instructions", "")
                questions.append(question)
    return categories, questions


def build_messages(question):
    kind = question["scorer"] if question["scorer"] in ("constraints", "code") else "answer"
    system = SYSTEM_PROMPTS[kind]
    if question["instructions"]:
        system += "\n\n" + question["instructions"]
    return [{"role": "system", "content": system}, {"role": "user", "content": question["prompt"]}]


MAX_TRIES = 12


class Throttle:
    """Spaces out requests, and holds every worker back after a rate-limit reply."""

    def __init__(self):
        self.lock = threading.Lock()
        self.gap = 0.0          # seconds between requests (0 = no limit)
        self.next_slot = 0.0    # earliest time the next request may start
        self.warned = 0.0

    def set_rpm(self, rpm):
        self.gap = 60.0 / rpm if rpm else 0.0

    def wait_turn(self):
        with self.lock:
            start = max(time.time(), self.next_slot)
            self.next_slot = start + self.gap
        time.sleep(max(0.0, start - time.time()))

    def pause(self, seconds):
        with self.lock:
            self.next_slot = max(self.next_slot, time.time() + seconds)
            if seconds >= 20 and time.time() - self.warned > 30:
                self.warned = time.time()
                print("  rate limited by the provider, waiting it out (this is normal)")
        time.sleep(seconds)


throttle = Throttle()


def call_openrouter(model_id, messages, max_tokens, timeout=180):
    """Send one request. Returns (text, usage dict, seconds). Retries rate limits and server errors."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("Set OPENROUTER_API_KEY first (or use --mock to try it without a key).")
    body = json.dumps({
        "model": model_id, "messages": messages, "max_tokens": max_tokens,
        "usage": {"include": True},
    }).encode()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    for attempt in range(MAX_TRIES):
        wait = min(2 ** attempt, 30)
        try:
            throttle.wait_turn()
            start = time.time()
            request = urllib.request.Request(API_URL, data=body, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as reply:
                data = json.load(reply)
            if "error" in data:
                raise RuntimeError(str(data["error"])[:300])
            # time only the request that worked, not the waiting before it
            return (data["choices"][0]["message"].get("content") or "", data.get("usage") or {},
                    time.time() - start)
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:300]
            if error.code not in (408, 429) and error.code < 500:
                raise RuntimeError(f"HTTP {error.code}: {detail}")
            last = f"HTTP {error.code}: {detail}"
            if error.code == 429:
                wait = 20  # rate limits reset each minute, so wait it out
        except (urllib.error.URLError, TimeoutError, RuntimeError, KeyError, ValueError) as error:
            last = str(error)
        throttle.pause(wait)
    raise RuntimeError(f"gave up after {MAX_TRIES} tries: {last}")


def mock_reply(model, question, trial):
    """Fake a reply: the reference answer with probability `skill`, otherwise a miss."""
    model_id, _, skill, seconds, dollars = model
    seed = int(hashlib.sha256(f"{model_id}|{question['id']}|{trial}".encode()).hexdigest(), 16)
    rng = random.Random(seed)
    lean = random.Random(f"{model_id}|{question['category']}").uniform(-0.12, 0.08)
    correct = rng.random() < skill + lean
    text = reference_response(question) if correct else "I am not sure.\nANSWER: 0"
    latency = seconds * rng.uniform(0.6, 1.5)
    usage = {"prompt_tokens": 180, "completion_tokens": int(latency * rng.uniform(55, 75)),
             "cost": dollars * rng.uniform(0.7, 1.3)}
    return text, usage, latency


def raw_path(results_dir, model_id):
    return os.path.join(results_dir, "raw", model_id.replace("/", "__") + ".jsonl")


def read_records(path):
    if not os.path.exists(path):
        return []
    with open(path) as handle:
        return [json.loads(line) for line in handle if line.strip()]


def run_benchmark(models, results_dir, trials=3, workers=4, max_tokens=4000, mock=False, limit=None,
                  rpm=None):
    """Ask every model every question `trials` times and append replies to disk.

    Safe to stop and restart: questions that already have a saved reply are skipped,
    and questions that failed with an API error are tried again.
    """
    throttle.set_rpm(rpm)
    _, questions = load_questions()
    if limit:
        questions = questions[:limit]
    os.makedirs(os.path.join(results_dir, "raw"), exist_ok=True)
    lock = threading.Lock()

    for model in models:
        model_id = model[0] if mock else model["id"]
        path = raw_path(results_dir, model_id)
        done = {(r["qid"], r["trial"]) for r in read_records(path)}
        todo = [(q, t) for t in range(trials) for q in questions if (q["id"], t) not in done]
        print(f"{model_id}: {len(todo)} to run, {len(done)} already saved")
        counts = {"ok": 0, "failed": 0}

        def ask(job):
            question, trial = job
            try:
                if mock:
                    text, usage, latency = mock_reply(model, question, trial)
                else:
                    text, usage, latency = call_openrouter(model_id, build_messages(question), max_tokens)
            except RuntimeError as error:
                with lock:
                    counts["failed"] += 1
                    print(f"  failed {question['id']} trial {trial}: {error}")
                return
            record = {
                "model": model_id, "qid": question["id"], "category": question["category"],
                "trial": trial, "response": text, "latency_s": round(latency, 3),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "cost_usd": usage.get("cost"), "benchmark_version": VERSION,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            with lock:
                with open(path, "a") as handle:
                    handle.write(json.dumps(record) + "\n")
                counts["ok"] += 1
                if counts["ok"] % 25 == 0:
                    print(f"  {counts['ok']}/{len(todo)}")

        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(ask, todo))
        print(f"  finished: {counts['ok']} saved, {counts['failed']} failed")
        if counts["failed"]:
            print("  run the same command again to retry the failed ones")
