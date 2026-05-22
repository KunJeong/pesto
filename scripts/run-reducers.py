#!/usr/bin/env python3

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
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
DEFAULT_INPUT_DIR = os.path.join(ROOT, "tests")
DEFAULT_TRACE_SENSITIVITY = 10
DEFAULT_REDUCER_JOBS = min(4, os.cpu_count() or 1)
PERSES_THREADS = "1"
SCRIPT_TIMEOUT_SECONDS = 60

# casting string to int and validating that input sensitivity is a non-negative integer
def trace_sensitivity(value: str) -> int:
    sensitivity = int(value)
    if sensitivity < 0:
        raise argparse.ArgumentTypeError("trace sensitivity must be non-negative")
    return sensitivity

def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return number

# Run the pesto CLI on the input file to get the expected stderr summary, which is used as the oracle for reducers.
def compute_summary(input_file: str, sensitivity: int) -> str:
    result = subprocess.run(
        [
            sys.executable,
            os.path.join(ROOT, "src", "pesto", "cli.py"),
            "trace",
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


def reduce_input(input_file: str, results_dir: str, sensitivity: int) -> str:
    input_file = os.path.abspath(input_file)
    input_basename = os.path.basename(input_file)
    output_dir = os.path.join(results_dir, os.path.splitext(input_basename)[0])

    print(f"[PESTO] reducing {input_file}", flush=True)
    run_perses(
        input_file=input_file,
        results_dir=results_dir,
        output_dir=output_dir,
        sensitivity=sensitivity,
    )
    return os.path.join(results_dir, input_basename)


def collect_inputs(args: argparse.Namespace) -> list[str]:
    if args.inputs:
        input_file = os.path.abspath(args.inputs)
        if not os.path.isfile(input_file):
            raise FileNotFoundError(f"input file not found: {input_file}")
        return [input_file]

    input_dir = os.path.abspath(args.input_dir or DEFAULT_INPUT_DIR)
    if not os.path.isdir(input_dir):
        raise NotADirectoryError(f"input directory not found: {input_dir}")

    return sorted(glob.glob(os.path.join(input_dir, "*.py")))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate reduced Python programs using trace-sensitivity")
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("-i", "--inputs", metavar="INPUT_FILE", help="Single Python test file to reduce.",)
    input_group.add_argument("-d", "--dir", dest="input_dir", metavar="INPUT_DIR", help="Directory containing Python test files to reduce. Defaults to tests/.",)
    parser.add_argument("-o", "--output", required=True, help="Directory where final reduced programs are collected.",)
    parser.add_argument("-ts", "--trace-sensitivity", type=trace_sensitivity, default=DEFAULT_TRACE_SENSITIVITY, help=f"Number of trace frames to keep in summaries. Defaults to {DEFAULT_TRACE_SENSITIVITY}.",)
    parser.add_argument("-j", "--jobs", type=positive_int, default=DEFAULT_REDUCER_JOBS, help=f"Number of input files to reduce in parallel. Defaults to {DEFAULT_REDUCER_JOBS}.",)
    return parser.parse_args()

def main():
    args = parse_args()
    sensitivity = args.trace_sensitivity
    try:
        inputs = collect_inputs(args)
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"[PESTO] {exc}", file=sys.stderr)
        return 2

    if not os.path.isfile(PERSES_JAR):
        print(f"Perses jar not found: {PERSES_JAR}", file=sys.stderr)
        print("Run ./scripts/install-perses.sh first.", file=sys.stderr)
        return 2

    if not os.path.isfile(TEST_SCRIPT):
        print(f"test script not found: {TEST_SCRIPT}", file=sys.stderr)
        return 2

    results_dir = os.path.abspath(args.output)
    os.makedirs(results_dir, exist_ok=True)

    if not inputs:
        print("[PESTO] no input files to reduce", file=sys.stderr)
        return 0

    jobs = min(args.jobs, len(inputs))
    print(f"[PESTO] reducing {len(inputs)} input(s) with {jobs} parallel job(s)", flush=True)

    failed = []
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        future_to_input = {
            executor.submit(
                reduce_input,
                input_file=input_file,
                results_dir=results_dir,
                sensitivity=sensitivity,
            ): os.path.abspath(input_file)
            for input_file in inputs
        }

        for future in as_completed(future_to_input):
            input_file = future_to_input[future]
            input_basename = os.path.basename(input_file)
            try:
                output_file = future.result()
            except Exception as exc:
                failed.append((input_file, str(exc)))
                print(f"[PESTO] failed {input_basename}: {exc}", file=sys.stderr, flush=True)
            else:
                print(f"[PESTO] wrote {output_file}", flush=True)

    if failed:
        print("\n[PESTO] failures:", file=sys.stderr)
        for input_file, message in failed:
            print(f"  {input_file}: {message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
