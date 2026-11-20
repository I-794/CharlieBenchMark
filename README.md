# Charlie Index

An independent benchmark for language models. It scores each model on five skills, combines them into one number (the Charlie Index), and also reports price and speed.

| Category | What it checks | How it is graded |
|---|---|---|
| Novel Reasoning | Made-up games and rules that cannot be memorized | Exact answer match |
| Honesty | Admitting "UNKNOWN" for things that do not exist, while still answering real questions | Exact answer match |
| Instruction Following | Obeying strict rules about length, letters, and format | Code checks each rule |
| Estimation | Fermi-style "roughly how many" questions | Answer must land in a range |
| Coding | Small Python functions | Hidden tests are run |

Everything is graded by code. The full rules are in [METHODOLOGY.md](METHODOLOGY.md).

## What you need

- Python 3.10 or newer. Nothing else to install.
- An [OpenRouter](https://openrouter.ai) API key for real runs. One key reaches almost every model.

## Try it with no API key

This uses pretend models so you can see the whole pipeline work.

```bash
python -m charlie validate        # checks the question files
python -m charlie run --mock      # pretend models answer the questions
python -m charlie score --mock    # grades the answers and builds the leaderboard
```

Then open `site/index.html` in a browser.

## Run it for real

1. Pick your models in `models.json`. Look up the exact ids at https://openrouter.ai/models, because ids change over time.

2. Set your key (this lasts until you close the terminal):

   ```bash
   export OPENROUTER_API_KEY="your-key-here"       # Mac or Linux
   $env:OPENROUTER_API_KEY="your-key-here"         # Windows PowerShell
   ```

3. Do a cheap test first: one model, 3 questions, asked once.

   ```bash
   python -m charlie run --only openai/gpt-6-luna --limit 3 --trials 1
   ```

4. Run the whole thing. Every model answers every question 3 times.

   ```bash
   python -m charlie run
   ```

   If it stops or some requests fail, run the same command again. It skips whatever is already saved.

5. Score it.

   ```bash
   python -m charlie score
   ```

   This prints the leaderboard, writes `results/leaderboard.json`, and updates the website data in `site/data.js`. Open `site/index.html` to see it.

Raw replies are saved in `results/raw/`, one file per model. Scoring always re-grades from those files, so if you fix a scorer you can run `score` again without paying for new answers.

## Tracking results in a spreadsheet

Every time you run `score`, three spreadsheet files are written to `results/`:

| File | What is in it |
|---|---|
| `leaderboard.csv` | The current leaderboard: one row per model with the index, every category, cost and speed |
| `question_scores.csv` | One row per question and one column per model, so you can see exactly what each model missed |
| `history.csv` | A running log. Each day you score adds new rows, so you can chart how scores change over time |

To open one in Google Sheets: go to sheets.google.com, start a blank sheet, then File, Import, Upload, and pick the file. For `history.csv`, re-import with "Replace current sheet" after each new run and any charts you made will update.

### Useful options

| Option | What it does |
|---|---|
| `--only MODEL_ID` | Run just one model from `models.json` |
| `--trials N` | How many times each question is asked (default 3) |
| `--limit N` | Only the first N questions |
| `--workers N` | How many requests go out at once (default 4) |
| `--max-tokens N` | Longest reply allowed (default 4000) |
| `--rpm N` | Send at most N requests per minute. Use this if a provider rate-limits you |

## Adding questions

Each file in `questions/` is one category. Add a new entry to its `questions` list, then run `python -m charlie validate`. Every question is worth one point and uses one of four scorers:

- `exact`: needs `answer` (a string, or a list of accepted strings)
- `numeric_range`: needs `low` and `high`
- `constraints`: needs a `constraints` list and a `reference` reply that obeys them
- `code`: needs `function`, `tests` (a list of `[arguments, expected]`) and a `reference` solution

`validate` grades each reference reply and complains if one does not get full marks, which catches broken answer keys.

### Keeping a hidden set

Questions posted publicly can end up in a model's training data. For a serious leaderboard, put most of your questions in a folder named `questions_private/` using the same file format. That folder is loaded automatically and is ignored by git, so it never gets published. Use a different `category` file name there only if you want a new category; otherwise reuse the same `category` and `name` values and give the questions new ids.

## Safety note

The Coding category runs the Python that models write, on your computer, in a separate process with a 10-second limit. That is not a real sandbox. Only benchmark models you are comfortable running code from, or run the benchmark inside a container or virtual machine.

## Publishing the site

The `site/` folder is a plain static site. To put it online, turn on GitHub Pages for the repository or upload the folder to any static host.
