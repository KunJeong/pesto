#!/usr/bin/env python3

from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile


# Paths and constants
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
PERSES_JAR = os.path.join(ROOT, "perses", "perses_deploy.jar")
TEST_SCRIPT = os.path.join(ROOT, "scripts", "test-script.sh")
DEFAULT_TRACE_SENSITIVITY = 10
PERSES_THREADS = "1"
SCRIPT_TIMEOUT_SECONDS = 60

# casting string to int and validating that input sensitivity is a non-negative integer
def trace_sensitivity(value: str) -> int:
    sensitivity = int(value)
    if sensitivity < 0:
        raise argparse.ArgumentTypeError("trace sensitivity must be non-negative")
    return sensitivity

# Run the pesto CLI on the input file to get the expected stderr summary, which is used as the oracle for reducers.
def compute_summary(input_file: str, sensitivity: int) -> str:
    result = subprocess.run(
        [
            sys.executable,
            os.path.join(ROOT, "src", "pesto", "cli.py"),
            input_file,
            "-s",
            str(sensitivity),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"failed to compute oracle summary for {input_file}\n{result.stderr}"
        )
    return result.stdout.strip()


def run_perses(
    *,
    input_file: str,
    results_dir: str,
    output_dir: str,
    sensitivity: int,
) -> None:
    os.makedirs(output_dir, exist_ok=True)

    # Compute the original program's summary once, then pass it to every Perses test run.
    expected_summary = compute_summary(input_file, sensitivity)

    input_basename = os.path.basename(input_file)
    with tempfile.TemporaryDirectory(prefix=f"pesto-{os.path.splitext(input_basename)[0]}-") as work_dir:
        # Perses requires the input file and the test script to live in the same directory.
        staged_input = os.path.join(work_dir, input_basename)
        staged_script = os.path.join(work_dir, os.path.basename(TEST_SCRIPT))
        shutil.copy2(input_file, staged_input)
        shutil.copy2(TEST_SCRIPT, staged_script)
        os.chmod(staged_script, 0o755)

        # Set up environment variables for the test script
        env = os.environ.copy()
        env.update(
            {
                "PESTO_PROJECT_ROOT": ROOT,
                "PESTO_ORIGINAL_INPUT": input_file,
                "PESTO_PYTHON": sys.executable,
                "PESTO_TRACE_SENSITIVITY": str(sensitivity),
                "PESTO_TARGET_BASENAME": input_basename,
                "PESTO_EXPECTED_SUMMARY": expected_summary,
            }
        )

        cmd = [
            "java",
            "-jar",
            PERSES_JAR,
            "--test-script",
            staged_script,
            "--input-file",
            staged_input,
            "--output-dir",
            output_dir,
            "--threads",
            PERSES_THREADS,
            "--script-execution-timeout-in-seconds",
            str(SCRIPT_TIMEOUT_SECONDS),
        ]
        subprocess.run(cmd, cwd=work_dir, env=env, check=True)

    reduced_file = os.path.join(output_dir, input_basename)
    if not os.path.isfile(reduced_file):
        raise FileNotFoundError(f"Perses did not write expected output: {reduced_file}")

    shutil.copy2(reduced_file, os.path.join(results_dir, input_basename))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate reduced Python programs using trace-sensitivity")
    parser.add_argument("-i", "--inputs", nargs="+", help="Python test files to reduce. Defaults to tests/*.py.",)
    parser.add_argument("-o", "--output", required=True, help="Directory where final reduced programs are collected.",)
    parser.add_argument("-ts", "--trace-sensitivity", type=trace_sensitivity, default=DEFAULT_TRACE_SENSITIVITY, help=f"Number of trace frames to keep in summaries. Defaults to {DEFAULT_TRACE_SENSITIVITY}.",)
    return parser.parse_args()

def main():
    args = parse_args()
    sensitivity = args.trace_sensitivity
    inputs = args.inputs or sorted(glob.glob(os.path.join(ROOT, "tests", "*.py")))

    if not os.path.isfile(PERSES_JAR):
        print(f"Perses jar not found: {PERSES_JAR}", file=sys.stderr)
        print("Run ./scripts/install-perses.sh first.", file=sys.stderr)
        return 2

    if not os.path.isfile(TEST_SCRIPT):
        print(f"test script not found: {TEST_SCRIPT}", file=sys.stderr)
        return 2

    results_dir = os.path.abspath(args.output)
    os.makedirs(results_dir, exist_ok=True)

    failed = []
    # Run reducer on each input file
    for input_file in inputs:
        input_file = os.path.abspath(input_file)
        input_basename = os.path.basename(input_file)
        output_dir = os.path.join(results_dir, os.path.splitext(input_basename)[0])
        print(f"[PESTO] reducing {input_file}", flush=True)
        try:
            run_perses(
                input_file=input_file,
                results_dir=results_dir,
                output_dir=output_dir,
                sensitivity=sensitivity,
            )
        except Exception as exc:
            failed.append((input_file, str(exc)))
            print(f"[PESTO] failed {input_basename}: {exc}", file=sys.stderr, flush=True)
        else:
            print(f"[PESTO] wrote {os.path.join(results_dir, input_basename)}", flush=True)

    if failed:
        print("\n[PESTO] failures:", file=sys.stderr)
        for input_file, message in failed:
            print(f"  {input_file}: {message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
