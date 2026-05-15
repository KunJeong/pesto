"""Run a target through patched python and print the escaping exception's c trace."""

import argparse
import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PATCHED_PYTHON = PROJECT_ROOT / "vendor" / "cpython" / "python.exe"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    parser.add_argument("-s", "--sensitivity", type=int, default=1)
    args = parser.parse_args()

    result = subprocess.run(
        [str(PATCHED_PYTHON), args.target],
        capture_output=True,
        text=True,
    )

    python_traceback_summary = next(
        line for line in reversed(result.stderr.splitlines()) if line.strip()
    )
    escaping_exception_type = python_traceback_summary.split(":", 1)[0].strip()

    pesto_block_re = re.compile(
        rf"\[PESTO-BEGIN type={re.escape(escaping_exception_type)}\](.*?)\[PESTO-END\]",
        re.DOTALL,
    )
    last_matching_block = pesto_block_re.findall(result.stderr)[-1]

    frames = []
    for frame_line in last_matching_block.strip().splitlines():
        _, _, _, function_name, *_ = frame_line.split()
        frames.append(function_name)

    print(f"{escaping_exception_type} | " + " ; ".join(frames[:args.sensitivity]))


if __name__ == "__main__":
    main()
