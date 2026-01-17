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
