#!/usr/bin/env python3

import argparse
import subprocess
import sys
import time
from pathlib import Path


def resolve_python(cpython_path: Path) -> Path:
    path = cpython_path.resolve()
    if not path.is_file():
        sys.exit(f"cpython executable not found: {path}")
    return path


def run_test(python: Path, test_file: Path, timeout: float | None):
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            [str(python), str(test_file)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
        elapsed = time.perf_counter() - start
        return elapsed, proc.returncode, False
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start
        return elapsed, None, True


def parse_args():
    parser = argparse.ArgumentParser(
        description="Measure a non-recursive .py test suite with CPython."
    )
    parser.add_argument(
        "cpython",
        type=Path,
        help="CPython executable.",
    )
    parser.add_argument(
        "tests_dir",
        type=Path,
        help="Directory containing .py test files. Subdirectories are ignored.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Per-test timeout in seconds. Use 0 to disable. Default: 10.0.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    python = resolve_python(args.cpython)
    tests_dir = args.tests_dir.resolve()
    timeout = None if args.timeout == 0 else args.timeout

    if not tests_dir.is_dir():
        sys.exit(f"test suite directory not found: {tests_dir}")

    test_files = sorted(path for path in tests_dir.glob("*.py") if path.is_file())
    if not test_files:
        sys.exit(f"no .py files found in: {tests_dir}")

    ok_exits = 0
    nonzero_exits = 0
    timeouts = 0
    sum_test_elapsed = 0.0

    suite_start = time.perf_counter()
    for test_file in test_files:
        elapsed, returncode, timed_out = run_test(python, test_file, timeout)
        sum_test_elapsed += elapsed
        if timed_out:
            timeouts += 1
        elif returncode == 0:
            ok_exits += 1
        else:
            nonzero_exits += 1
    suite_elapsed = time.perf_counter() - suite_start

    print(f"python: {python}")
    print(f"tests_dir: {tests_dir}")
    print(f"py_files: {len(test_files)}")
    print(f"timeout: {'disabled' if timeout is None else str(timeout) + 's'}")
    print(f"suite_time_s: {suite_elapsed:.6f}")
    print(f"sum_test_time_s: {sum_test_elapsed:.6f}")
    print(f"mean_test_time_s: {suite_elapsed / len(test_files):.6f}")
    print(f"ok_exits: {ok_exits}")
    print(f"nonzero_exits: {nonzero_exits}")
    print(f"timeouts: {timeouts}")

    return 1 if timeouts else 0


if __name__ == "__main__":
    raise SystemExit(main())
