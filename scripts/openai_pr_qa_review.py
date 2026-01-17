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
