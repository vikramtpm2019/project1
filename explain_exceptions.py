# Step 2 of the agent: ask Claude to explain each SQL-found exception, then
# check the answer. SQL finds and calculates; the model only explains.

import argparse
import csv
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")


def read(path):
    with open(path) as f:
        return f.read()


def build_message(prompt_path):
    prompt = read(prompt_path)
    # Support both the {{...}} placeholders and a plain prompt with none.
    prompt = prompt.replace("{{contracts}}", read(f"{DATA}/contracts.csv"))
    prompt = prompt.replace("{{exceptions}}", read(f"{DATA}/exceptions.csv"))
    return prompt


def call_claude(message):
    import anthropic  # imported here so --mock works without the package

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
    resp = client.messages.create(
        model=model,
        max_tokens=3000,
        messages=[{"role": "user", "content": message}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def call_claude_cli(message):
    """Use the Claude Code CLI (claude -p) with your plan login. No API key.

    ANTHROPIC_API_KEY is removed from the environment on purpose: if it is set,
    Claude Code uses it and bills API credits instead of your plan.
    """
    import subprocess

    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    try:
        r = subprocess.run(["claude", "-p", message], capture_output=True,
                           text=True, env=env, timeout=300)
    except FileNotFoundError:
        sys.exit("The 'claude' command was not found. Install Claude Code and run 'claude login' first.")
    if r.returncode != 0:
        sys.exit(f"claude -p failed: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout


def mock_answer():
    """A deliberately flawed answer, to prove the checker catches problems."""
    rows = list(csv.DictReader(open(f"{DATA}/exceptions.csv")))
    out = []
    for r in rows[:-1]:  # skip the last one: a missed exception
        out.append(f"{r['customer_id']}: {r['detail']}. Likely cause: data error.")
    out.append("C001: invoice is off by about $1,234.56, likely a rate error.")  # invented number
    return "\n".join(out)


NUM = re.compile(r"\d[\d,]*\.?\d*")


def numbers(text):
    vals = set()
    for m in NUM.findall(text):
        m = m.rstrip(".").replace(",", "")
        try:
            v = float(m)
        except ValueError:
            continue
        if v >= 100 or "." in m:  # ignore list numbers and day-of-month noise
            vals.add(v)
    return vals


def check(answer):
    rows = list(csv.DictReader(open(f"{DATA}/exceptions.csv")))
    # CSV commas are separators, not thousands marks: blank them so numbers
    # in neighbouring columns are not glued together.
    source = (read(f"{DATA}/exceptions.csv") + read(f"{DATA}/contracts.csv")).replace(",", " ")
    allowed = numbers(source)

    problems = []
    # 1. Coverage: every exception's customer must be addressed
    for r in rows:
        if r["customer_id"] not in answer:
            problems.append(f"MISSED: no mention of {r['customer_id']} ({r['check_name']})")
    # 2. Invented numbers: any figure not in the source data
    for v in sorted(numbers(answer) - allowed):
        problems.append(f"INVENTED NUMBER: {v:g} is not in the source data")
    return rows, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default=os.path.join(BASE, "prompt_v1.md"))
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--answer-file", help="check an answer already written to a file (no API call)")
    ap.add_argument("--cli", action="store_true", help="call Claude through the Claude Code CLI using your plan login")
    args = ap.parse_args()

    if args.mock:
        answer = mock_answer()
    elif args.answer_file:
        answer = read(args.answer_file)
    elif args.cli:
        answer = call_claude_cli(build_message(args.prompt))
    else:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            sys.exit("Set ANTHROPIC_API_KEY first (or use --mock to test the checker).")
        answer = call_claude(build_message(args.prompt))

    print(answer)
    rows, problems = check(answer)

    name = os.path.splitext(os.path.basename(args.prompt))[0]
    out_path = os.path.join(DATA, f"output_{name}{'_mock' if args.mock else ''}.txt")
    with open(out_path, "w") as f:
        f.write(answer)

    print("\n--- CHECK ---")
    print(f"exceptions in: {len(rows)}")
    if problems:
        for p in problems:
            print(" ", p)
    else:
        print("  all exceptions covered, no invented numbers")
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
