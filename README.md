# Usage-to-Invoice Exception Agent

An agent that reviews monthly usage against contracts and invoices, finds
exceptions with SQL, has Claude explain each one, and checks the explanations
before anyone relies on them.

All data in this repo is synthetic. It is modeled on a usage-to-invoice review
workflow, with eight problems planted on purpose so the agent can be tested
against a known answer.

## How it works

1. SQL finds and calculates. `checks.sql` runs 7 checks (CTEs, window
   functions, joins) and writes `data/exceptions.csv`. Every number comes from SQL.
2. Claude explains. `explain_exceptions.py` sends the contracts and exceptions
   to Claude with a prompt and gets back one block per exception.
3. A checker validates. It confirms every exception is covered and that the
   answer contains no number that is not in the source data.

## Files

- `generate_data.py`: creates synthetic contracts, usage events and invoices
- `checks.sql`: the 7 exception checks
- `run_checks.py`: loads the CSVs into SQLite, runs the checks, writes exceptions
- `explain_exceptions.py`: calls Claude, then runs the checker
- `prompt_v1.md`: first prompt
- `prompt_v2.md`: improved prompt
- `ITERATIONS.md`: what failed, what changed, what happened
- `data/`: input data, `ANSWER_KEY.txt`, and the saved v1 and v2 outputs

## Run it

```
python3 generate_data.py
python3 run_checks.py
python3 explain_exceptions.py --cli --prompt prompt_v2.md
```

`--cli` calls Claude through the Claude Code command line using your Claude
login, so no API key is stored in this project. Other modes:

- `--mock` tests the checker offline with a deliberately flawed answer
- `--answer-file path` checks an answer you saved from any source
- no flag: calls the Anthropic API (needs ANTHROPIC_API_KEY)

## Built with

Claude was used to help write the starter code and data generator. I ran,
tested and revised everything, and the iteration notes show what I observed.
