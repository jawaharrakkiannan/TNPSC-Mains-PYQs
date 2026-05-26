#!/usr/bin/env python3
"""
TNPSC PYQ Pipeline runner.

Steps (automated):
  1 - extract_syllabus.py     -> data/syllabus_themes.json
  2 - extract_questions.py    -> data/questions_raw.json
  3 - tag_questions.py        -> data/questions_tagged.json
  4 - generate_html.py        -> output/viewer.html

Manual step between 2 and 3:
  python run_pipeline.py --review    (launches Flask review server)
  Edits saved to data/questions_corrected.json, used automatically by step 3.

Usage:
  python run_pipeline.py                    # run steps 1,2,3,4
  python run_pipeline.py --steps 1,2        # run specific steps
  python run_pipeline.py --review           # launch review server
  python run_pipeline.py --steps 2 --extract-review  # step 2 with noise flag dump
"""
import argparse
import os
import subprocess
import sys
import time


def run_script(name: str, extra: list[str] | None = None) -> bool:
    cmd = [sys.executable, os.path.join("scripts", name)] + (extra or [])
    print(f"\n{'='*56}\nRunning: {' '.join(cmd)}\n{'='*56}", flush=True)
    start = time.time()
    rc = subprocess.run(cmd).returncode
    elapsed = time.time() - start
    label = "OK" if rc == 0 else "FAILED"
    print(f"[{label}] {name} ({elapsed:.1f}s)", flush=True)
    return rc == 0


def main() -> None:
    p = argparse.ArgumentParser(description="TNPSC PYQ Pipeline")
    p.add_argument("--steps", default="1,2,3,4")
    p.add_argument("--review", action="store_true",
                   help="Launch Flask review server")
    p.add_argument("--extract-review", action="store_true",
                   help="Pass --review flag to step 2 (dump noise-flagged questions)")
    args = p.parse_args()

    if args.review:
        run_script("review_server.py")
        return

    steps = {s.strip() for s in args.steps.split(",")}
    ok = True
    if "1" in steps:
        ok &= run_script("extract_syllabus.py")
    if "2" in steps:
        extra = ["--review"] if args.extract_review else []
        ok &= run_script("extract_questions.py", extra)
    if "3" in steps:
        ok &= run_script("tag_questions.py")
    if "4" in steps:
        ok &= run_script("generate_html.py")

    print(f"\n{'='*56}", flush=True)
    print("Pipeline complete." if ok else "Pipeline finished with errors.", flush=True)
    if "4" in steps and ok:
        print("Open: output/viewer.html", flush=True)


if __name__ == "__main__":
    main()
