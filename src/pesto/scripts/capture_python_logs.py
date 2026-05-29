#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Python files with vendor/cpython/python.exe and save logs."
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        required=True,
        type=Path,
        help="Directory containing .py files to execute.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        required=True,
        type=Path,
        help="Directory where .txt log files will be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[3]
    python = repo_root / "vendor" / "cpython" / "python.exe"
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not python.is_file():
        sys.exit(f"python executable not found: {python}")
    if not input_dir.is_dir():
        sys.exit(f"input directory not found: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    py_files = sorted(path for path in input_dir.glob("*.py") if path.is_file())
    nonzero_exits = 0

    for path in py_files:
        log_path = output_dir / f"{path.stem}.txt"
        with log_path.open("w", encoding="utf-8", errors="replace") as log_file:
            proc = subprocess.run(
                [str(python), str(path)],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=repo_root,
            )
        if proc.returncode != 0:
            nonzero_exits += 1

    print(f"input_dir: {input_dir}")
    print(f"output_dir: {output_dir}")
    print(f"py_files: {len(py_files)}")
    print(f"logs_written: {len(py_files)}")
    print(f"nonzero_exits: {nonzero_exits}")


if __name__ == "__main__":
    main()
