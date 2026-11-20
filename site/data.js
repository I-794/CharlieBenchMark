window.CHARLIE_DATA = {
  "benchmark": "Charlie Index",
  "version": "1.0",
  "mock": true,
  "generated": "2026-11-20",
  "question_count": 32,
  "categories": [
    {
      "id": "coding",
      "name": "Coding",
      "questions": 6
    },
    {
      "id": "estimation",
      "name": "Estimation",
      "questions": 6
    },
    {
      "id": "honesty",
      "name": "Honesty",
      "questions": 8
    },
    {
      "id": "instruction_following",
      "name": "Instruction Following",
      "questions": 6
    },
    {
      "id": "novel_reasoning",
      "name": "Novel Reasoning",
      "questions": 6
    }
  ],
  "models": [
    {
      "id": "mock/atlas-large",
      "name": "Atlas Large (sample)",
      "index": 88.1,
      "ci95": 7.3,
      "categories": {
        "coding": 83.3,
        "estimation": 83.3,
        "honesty": 95.8,
        "instruction_following": 94.4,
        "novel_reasoning": 83.3
      },
      "trials": 3,
      "coverage": 1.0,
      "median_latency_s": 6.36,
      "tokens_per_second": 64.9,
      "cost_per_run_usd": 0.2859
    },
    {
      "id": "mock/birch-pro",
      "name": "Birch Pro (sample)",
      "index": 85.4,
      "ci95": 9.0,
      "categories": {
        "coding": 72.2,
        "estimation": 72.2,
        "honesty": 91.7,
        "instruction_following": 90.7,
        "novel_reasoning": 100.0
      },
      "trials": 3,
      "coverage": 1.0,
      "median_latency_s": 3.9,
      "tokens_per_second": 65.1,
      "cost_per_run_usd": 0.1294
    },
    {
      "id": "mock/atlas-small",
      "name": "Atlas Small (sample)",
      "index": 68.7,
      "ci95": 11.5,
      "categories": {
        "coding": 66.7,
        "estimation": 66.7,
        "honesty": 75.0,
        "instruction_following": 68.5,
        "novel_reasoning": 66.7
      },
      "trials": 3,
      "coverage": 1.0,
      "median_latency_s": 1.64,
      "tokens_per_second": 64.2,
      "cost_per_run_usd": 0.0351
    },
    {
      "id": "mock/cedar-mini",
      "name": "Cedar Mini (sample)",
      "index": 59.9,
      "ci95": 6.8,
      "categories": {
        "coding": 61.1,
        "estimation": 77.8,
        "honesty": 45.8,
        "instruction_following": 70.4,
        "novel_reasoning": 44.4
      },
      "trials": 3,
      "coverage": 1.0,
      "median_latency_s": 0.97,
      "tokens_per_second": 63.4,
      "cost_per_run_usd": 0.0095
    },
    {
      "id": "mock/delta-open",
      "name": "Delta Open (sample)",
      "index": 49.4,
      "ci95": 3.2,
      "categories": {
        "coding": 27.8,
        "estimation": 50.0,
        "honesty": 70.8,
        "instruction_following": 48.1,
        "novel_reasoning": 50.0
      },
      "trials": 3,
      "coverage": 1.0,
      "median_latency_s": 2.36,
      "tokens_per_second": 65.5,
      "cost_per_run_usd": 0.0195
    }
  ]
};
