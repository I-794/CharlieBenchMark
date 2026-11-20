# Charlie Index methodology

Version 1.0

## What is measured

Five categories. Every question is worth between 0 and 1 point.

1. **Novel Reasoning.** Problems built on invented games and rules, so the answer cannot be recalled from training data. Graded by exact match.
2. **Honesty.** A mix of real factual questions and questions about things that do not exist. The model is told to answer `UNKNOWN` when the thing is not real or it is not confident. Fabricating an answer to a fake question scores 0, and so does answering `UNKNOWN` to a real one. Graded by exact match.
3. **Instruction Following.** Writing tasks with strict rules (word counts, banned letters, formats). The score is the fraction of rules the reply obeys.
4. **Estimation.** Order-of-magnitude questions. Full credit inside the accepted range. Outside it, credit drops along a log scale and reaches 0 when the answer is off by a factor of 10.
5. **Coding.** Short Python functions. The score is the fraction of hidden tests passed. A solution that crashes or runs longer than 10 seconds scores 0.

## How answers are collected

- Every model gets the same system prompt and the same question text. The prompts are in `charlie/core.py`.
- For answer-style questions the model may reason freely but must finish with a line `ANSWER: <answer>`. Only that final line is graded. A reply without it scores 0.
- Models run with their provider's default settings (no temperature override), through the OpenRouter API, with a reply limit of 4000 tokens.
- Each question is asked 3 times per model, as separate conversations.

## How scores are calculated

- **Category score** = the average of that category's question scores, times 100.
- **Charlie Index** = the plain average of the five category scores. Every category counts equally, no matter how many questions it has.
- The reported index is the average across the repeated runs. The **± value** is a 95% confidence interval: 1.96 times the standard deviation of the per-run index, divided by the square root of the number of runs. With only 3 runs this is a rough guide, not a precise figure.
- If two models' intervals overlap, treat them as tied.

## Price and speed

- **Cost per run** is what the provider charged, as reported by the API, for answering every question once.
- **Seconds** is the median wall-clock time for one question, including network time.
- **Tokens/sec** is total output tokens divided by total time.

Speed depends on the provider and the time of day, so treat it as a snapshot.

## Grading is automatic and repeatable

No human and no model judges any answer. All grading code is in `charlie/scorers.py`. Raw replies are stored in `results/raw/` and scores are always recomputed from them, so anyone with the raw files gets the same numbers.

## Known limits

- The public question set is small. A model can gain or lose several points from one question, which is why the confidence intervals are wide. More questions make the index more stable.
- Public questions can leak into training data. The hidden set in `questions_private/` exists to guard against this.
- Exact-match grading is strict. A correct answer in an unexpected format is marked wrong.
- The Honesty category rewards saying `UNKNOWN`, so it must always contain real questions too, or a model could score well by never answering.

## Versions

Scores are only comparable within the same version. Any change to questions, prompts, or scoring gets a new version number and an entry here.

- **1.0**: first release.
