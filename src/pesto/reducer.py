"""Perses-based reduction that preserves each program's crash signature."""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import paths, tracer

DEFAULT_TRACE_SENSITIVITY = 10
DEFAULT_REDUCER_JOBS = min(4, os.cpu_count() or 1)
PERSES_THREADS = "1"
SCRIPT_TIMEOUT_SECONDS = 600


def run_perses(*, input_file: str, results_dir: str, output_dir: str, sensitivity: int) -> None:
    os.makedirs(output_dir, exist_ok=True)

    # Compute the original program's summary once, then pass it to every Perses run.
    expected_summary = tracer.trace_summary(input_file, sensitivity)

    input_basename = os.path.basename(input_file)
    with tempfile.TemporaryDirectory(prefix=f"pesto-{os.path.splitext(input_basename)[0]}-") as work_dir:
        # Perses requires the input file and the test script to live together.
        staged_input = os.path.join(work_dir, input_basename)
        staged_script = os.path.join(work_dir, paths.TEST_SCRIPT.name)
        shutil.copy2(input_file, staged_input)
        shutil.copy2(str(paths.TEST_SCRIPT), staged_script)
        os.chmod(staged_script, 0o755)

        env = os.environ.copy()
        env.update(
            {
                "PESTO_PROJECT_ROOT": str(paths.PROJECT_ROOT),
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
            str(paths.PERSES_JAR),
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


def collect_inputs(inputs: str | None = None, input_dir: str | None = None) -> list[str]:
    if inputs:
        input_file = os.path.abspath(inputs)
        if not os.path.isfile(input_file):
            raise FileNotFoundError(f"input file not found: {input_file}")
        return [input_file]

    resolved_dir = os.path.abspath(input_dir or str(paths.DEFAULT_TESTS_DIR))
    if not os.path.isdir(resolved_dir):
        raise NotADirectoryError(f"input directory not found: {resolved_dir}")

    return sorted(glob.glob(os.path.join(resolved_dir, "*.py")))


def reduce_all(
    output: str,
    inputs: str | None = None,
    input_dir: str | None = None,
    sensitivity: int = DEFAULT_TRACE_SENSITIVITY,
    jobs: int = DEFAULT_REDUCER_JOBS,
) -> int:
    """Reduce inputs into ``output``. Returns a process-style exit code."""
    try:
        collected = collect_inputs(inputs, input_dir)
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"[PESTO] {exc}", file=sys.stderr)
        return 2

    if not paths.PERSES_JAR.is_file():
        print(f"Perses jar not found: {paths.PERSES_JAR}", file=sys.stderr)
        print("Run ./scripts/install-perses.sh first.", file=sys.stderr)
        return 2

    if not paths.TEST_SCRIPT.is_file():
        print(f"test script not found: {paths.TEST_SCRIPT}", file=sys.stderr)
        return 2

    results_dir = os.path.abspath(output)
    os.makedirs(results_dir, exist_ok=True)

    if not collected:
        print("[PESTO] no input files to reduce", file=sys.stderr)
        return 0

    parallel = min(jobs, len(collected))
    print(f"[PESTO] reducing {len(collected)} input(s) with {parallel} parallel job(s)", flush=True)

    failed = []
    with ThreadPoolExecutor(max_workers=parallel) as executor:
        future_to_input = {
            executor.submit(
                reduce_input,
                input_file=input_file,
                results_dir=results_dir,
                sensitivity=sensitivity,
            ): os.path.abspath(input_file)
            for input_file in collected
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
