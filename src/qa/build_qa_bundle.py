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
