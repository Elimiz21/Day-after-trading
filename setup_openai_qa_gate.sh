#!/usr/bin/env bash
set -euo pipefail

echo "==> Creating folders"
mkdir -p .github/workflows
mkdir -p config
mkdir -p docs/status_reports
mkdir -p docs/qa_bundle
mkdir -p docs
mkdir -p scripts
mkdir -p src/qa
mkdir -p data/exports/csv

backup_if_exists () {
  local f="$1"
  if [ -f "$f" ]; then
    echo "==> Backing up existing $f -> ${f}.bak"
    mv "$f" "${f}.bak"
  fi
}

echo "==> Backing up potentially conflicting files (if present)"
backup_if_exists "README.md"
backup_if_exists ".gitignore"
backup_if_exists "requirements.txt"
backup_if_exists "requirements-dev.txt"

echo "==> Writing .gitignore"
cat > .gitignore <<'EOF'
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
.Python
.venv/
venv/
ENV/

# Env / secrets
.env

# OS
.DS_Store

# Data (keep exports, ignore heavy intermediates)
data/raw/
data/processed/

# Notebooks
.ipynb_checkpoints/

# Build
dist/
build/
EOF

echo "==> Writing README.md"
cat > README.md <<'EOF'
# Day-after Trading (Earnings Reversal Research)

This repo is for researching and testing a post-earnings, day-after reversal strategy.

## Governance (Option B)
We use:
- **Claude Code** to build/run the project in this repo
- **GitHub Actions** to run QA + build a QA bundle
- **OpenAI API (Responses API)** to review the QA bundle and post a **GO/NO-GO** PR comment automatically

### Secrets required (GitHub → Settings → Secrets and variables → Actions)
- `FMP_API_KEY`
- `OPENAI_API_KEY`

Optional variable:
- `OPENAI_MODEL` (default: `gpt-5.2`)

## What exists now
This is scaffolding only:
- CI workflow that runs a basic QA gate
- QA bundle builder
- OpenAI PR reviewer script (Responses API)
- A master prompt for Claude Code in `docs/claude_master_prompt.md`

The full pipeline/backtester/dashboard will be implemented next by Claude Code.
EOF

echo "==> Writing requirements.txt"
cat > requirements.txt <<'EOF'
requests>=2.31.0
pandas>=2.2.0
pyyaml>=6.0.1
python-dotenv>=1.0.1

# (Claude will add more as the pipeline is implemented)
EOF

echo "==> Writing requirements-dev.txt"
cat > requirements-dev.txt <<'EOF'
requests>=2.31.0
pandas>=2.2.0
pyyaml>=6.0.1
EOF

echo "==> Writing config files"
cat > config/execution_costs.yaml <<'EOF'
# Execution cost scenarios (explicit assumptions; not empirical bid/ask)
# Costs are applied per side (entry + exit).

scenarios:
  low:
    spread_bps_each_side: 2
    slippage_bps_each_side: 2
    commission_bps_each_side: 0
  medium:
    spread_bps_each_side: 5
    slippage_bps_each_side: 5
    commission_bps_each_side: 0
  high:
    spread_bps_each_side: 10
    slippage_bps_each_side: 10
    commission_bps_each_side: 0
EOF

cat > config/significance.yaml <<'EOF'
# Significance scenario grid (to be expanded during implementation)

rolling_windows_days: [60]

zscore:
  enabled: true
  robust: true   # median/MAD preferred
  thresholds: [1.5, 2.0, 2.5, 3.0]

percentile_abs_r1:
  enabled: true
  thresholds: [90, 95, 97.5, 99]

atr_multiple:
  enabled: true
  thresholds: [1.25, 1.5, 2.0]

gap2_min_abs:
  enabled: true
  thresholds: [0.0025, 0.005, 0.01]  # 0.25%, 0.5%, 1.0%
EOF

cat > config/openai_qa_prompt.md <<'EOF'
# Quant Strategy QA Gate (PR Review)

You are the QA Lead and Quant PM for a research repo.
Your job is to decide GO / NO-GO for merging this PR based on:
- correctness of data logic
- prevention of lookahead bias
- earnings event -> trading day mapping accuracy
- signal rule correctness
- execution simulation correctness under daily OHLC assumptions
- reproducibility evidence
- missingness / coverage reporting
- cost model correctness (no double-counting; explicit assumptions only)
- documentation clarity (methodology + limitations)

## Project context
Universe: S&P 500 only
Data: FMP API only
Horizon: 15 years
Strategy:
- T0 = earnings event date
- T1 = next trading day after T0
- T2 = next trading day after T1
- Significant move on T1 (scenario grid)
- If T2 opens opposite direction vs T1 close:
  - If R1 > 0 and Gap2 < 0 => long at Open(T2)
  - If R1 < 0 and Gap2 > 0 => short at Open(T2)
- Target: Close(T1)
- Hit logic (daily OHLC):
  - long hit if High(T2) >= Close(T1)
  - short hit if Low(T2) <= Close(T1)
Exit variants must be explicit & tested.

## Inputs you will receive
1) A QA bundle manifest with coverage stats, file lists, row counts, config snapshots, and key summaries.
2) A PR diff summary.

## Output format (MANDATORY)
Return Markdown with these sections:

### ✅ Verdict: GO or ❌ NO-GO
One sentence rationale.

### Blockers (must fix before merge)
Bullet list. If none, write "None".

### High priority fixes
Bullet list.

### Medium/Low improvements
Bullet list.

### Quant sanity checks
- Lookahead bias: PASS/FAIL + evidence
- Earnings mapping: PASS/FAIL + evidence
- Split/adjustment handling: PASS/FAIL + evidence
- Missingness transparency: PASS/FAIL + evidence
- Signal correctness: PASS/FAIL + evidence
- Cost model: PASS/FAIL + evidence
- Reproducibility: PASS/FAIL + evidence

### Suggested next step
One paragraph.

Be tough and specific. Cite evidence from the provided bundle and diff.
EOF

echo "==> Writing Claude master prompt"
cat > docs/claude_master_prompt.md <<'EOF'
# Claude Code Master Prompt (Builder)

You are the BUILDER agent operating inside this repo.

Goal:
Implement the full earnings-reversal backtest pipeline using ONLY FMP API data for S&P 500, 15 years, with CSV outputs, Streamlit dashboard, and strict QA.

You MUST:
1) Implement the research pipeline phase-by-phase (Phase 1..6).
2) After each phase, write:
   - docs/status_reports/phase_<N>.md
   - docs/status_reports/latest.md (copy of current phase report)
   - docs/qa_bundle/latest/{qa_manifest.md,status_report.md,summaries.md}
3) Ensure `python -m src.qa.run_qa --mode local` passes before moving to next phase.

OpenAI QA:
GitHub Actions will run and post a PR comment with GO/NO-GO and fixes. You must read that comment and implement fixes.

Hard constraints:
- Data: ONLY FMP API
- Universe: S&P 500 only
- Real data only; log exclusions
- No lookahead: rolling features only pre-event
- Costs are scenario assumptions (explicit), not empirical spreads
- Daily OHLC target-hit rules are used (unless intraday is added legally/available)

Start with Phase 1 smoke test (5 tickers, ~20 events).
EOF

echo "==> Writing docs/status_reports/latest.md"
cat > docs/status_reports/latest.md <<'EOF'
# Status Report (latest)

This file is updated each phase by the builder agent.

## Next
- Implement Phase 1 (repo scaffold + smoke test)
EOF

echo "==> Writing src package markers"
cat > src/__init__.py <<'EOF'
# Package marker
EOF

cat > src/qa/__init__.py <<'EOF'
# QA subpackage
EOF

echo "==> Writing QA scripts"
cat > src/qa/run_qa.py <<'EOF'
import argparse
from pathlib import Path
import sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["ci", "local"], default="local")
    _ = ap.parse_args()

    required = [
        Path("config/significance.yaml"),
        Path("config/execution_costs.yaml"),
        Path("config/openai_qa_prompt.md"),
        Path("docs/status_reports/latest.md"),
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        print("QA FAIL: missing required project files:")
        for m in missing:
            print(" -", m)
        sys.exit(1)

    print("QA PASS (basic). Expand QA checks in src/qa/run_qa.py as pipeline is implemented.")
    sys.exit(0)

if __name__ == "__main__":
    main()
EOF

cat > src/qa/build_qa_bundle.py <<'EOF'
import argparse
from pathlib import Path
import subprocess
import datetime

def run(cmd):
    return subprocess.check_output(cmd, text=True).strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    commit = run(["git", "rev-parse", "HEAD"])
    now = datetime.datetime.utcnow().isoformat() + "Z"

    status_report_src = Path("docs/status_reports/latest.md")
    if status_report_src.exists():
        (out / "status_report.md").write_text(status_report_src.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        (out / "status_report.md").write_text("(missing docs/status_reports/latest.md)\n", encoding="utf-8")

    manifest = f"""# QA Manifest (latest)

- timestamp_utc: {now}
- git_commit: {commit}

## Reproduce
- Commands:
  - python -m src.qa.run_qa --mode local
  - python -m src.qa.build_qa_bundle --out docs/qa_bundle/latest

## Coverage
(TODO: once pipeline exists, include tickers/events/missingness stats.)

## Exports
(TODO: once pipeline exists, list data/exports/csv/*.csv with row counts.)
"""
    (out / "qa_manifest.md").write_text(manifest, encoding="utf-8")

    summaries = """# Summaries
(TODO: once pipeline exists, add compact summaries: counts, key metrics tables.)
"""
    (out / "summaries.md").write_text(summaries, encoding="utf-8")

    print(f"Wrote QA bundle to {out}")

if __name__ == "__main__":
    main()
EOF

echo "==> Writing OpenAI PR QA reviewer script"
cat > scripts/openai_pr_qa_review.py <<'EOF'
import argparse
import json
import os
from pathlib import Path
import subprocess
import textwrap
import requests

OPENAI_URL = "https://api.openai.com/v1/responses"

def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()

def get_pr_diff_summary() -> str:
    try:
        base = os.environ.get("GITHUB_BASE_REF")
        if base:
            run(["git", "fetch", "origin", base, "--depth=1"])
            diff = run(["git", "diff", f"origin/{base}...HEAD", "--stat"])
        else:
            diff = run(["git", "diff", "HEAD~1...HEAD", "--stat"])
        return diff[:8000]
    except Exception as e:
        return f"(diff summary unavailable: {e})"

def load_text(path: Path, max_chars: int = 120000) -> str:
    if not path.exists():
        return f"(missing: {path})"
    txt = path.read_text(encoding="utf-8", errors="replace")
    if len(txt) > max_chars:
        return txt[:max_chars] + "\n\n(TRUNCATED)"
    return txt

def call_openai(prompt: str, model: str) -> str:
    key = os.environ["OPENAI_API_KEY"]
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": prompt,
    }
    r = requests.post(OPENAI_URL, headers=headers, json=payload, timeout=180)
    r.raise_for_status()
    data = r.json()

    out_text = []
    for item in data.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    out_text.append(c.get("text", ""))
    return "\n".join(out_text).strip() or json.dumps(data)[:2000]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    bundle = Path(args.bundle)
    prompt_file = Path(args.prompt)
    out_file = Path(args.out)

    model = os.environ.get("OPENAI_MODEL", "gpt-5.2")

    manifest = load_text(bundle / "qa_manifest.md")
    status = load_text(bundle / "status_report.md")
    summaries = load_text(bundle / "summaries.md")
    qa_prompt = load_text(prompt_file)
    diff_summary = get_pr_diff_summary()

    full_prompt = f"""{qa_prompt}

## QA Bundle Manifest
{manifest}

## Status report
{status}

## Summaries
{summaries}

## PR Diff summary
{diff_summary}
"""
    review = call_openai(full_prompt, model=model)

    header = textwrap.dedent(f"""\
    <!-- OPENAI_QA_REVIEW -->
    (Model: `{model}`)
    """)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(header + "\n" + review + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
EOF

echo "==> Writing GitHub Action workflow"
cat > .github/workflows/quant_qa.yml <<'EOF'
name: Quant QA Gate (OpenAI)

on:
  pull_request:
    types: [opened, synchronize, reopened]
  workflow_dispatch: {}

permissions:
  contents: read
  pull-requests: write

jobs:
  qa:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run local QA checks (fast)
        run: |
          python -m src.qa.run_qa --mode ci

      - name: Build QA bundle for OpenAI review
        env:
          FMP_API_KEY: ${{ secrets.FMP_API_KEY }}
        run: |
          python -m src.qa.build_qa_bundle --out docs/qa_bundle/latest

      - name: OpenAI QA review (Responses API)
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          OPENAI_MODEL: ${{ vars.OPENAI_MODEL }}
        run: |
          python scripts/openai_pr_qa_review.py \
            --bundle docs/qa_bundle/latest \
            --prompt config/openai_qa_prompt.md \
            --out docs/qa_bundle/latest/openai_review.md

      - name: Post (or update) PR comment with QA verdict
        uses: peter-evans/create-or-update-comment@v4
        with:
          issue-number: ${{ github.event.pull_request.number }}
          body-file: docs/qa_bundle/latest/openai_review.md
          edit-mode: replace
EOF

echo "==> Done. Next:"
echo "  1) git add -A && git commit -m 'Add OpenAI QA gate workflow + QA bundle scaffolding'"
echo "  2) git push -u origin setup/openai-qa-gate"
echo "  3) Open PR, then add secrets: FMP_API_KEY + OPENAI_API_KEY"

