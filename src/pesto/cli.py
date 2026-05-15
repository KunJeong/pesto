import argparse
import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PATCHED_PYTHON = PROJECT_ROOT / "vendor" / "cpython" / "python.exe"


def cmd_trace(args: argparse.Namespace):
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

    traces = "\n".join(result.stderr.splitlines()[4366:])
    first_matching_block = pesto_block_re.findall(traces)[0]

    frames = []
    for frame_line in first_matching_block.strip().splitlines():
        _, _, _, function_name, *_ = frame_line.split()
        frames.append(function_name)

    print(f"{escaping_exception_type} | " + " ; ".join(frames[: args.sensitivity]))


def cmd_mutate(args: argparse.Namespace):
    from pesto.mutator import mutate_file

    out_dir = Path.cwd() / "pesto_mutation"
    out_dir.mkdir(exist_ok=True)

    runtime_written = False
    mutated_paths = []

    for c_file in args.c_files:
        mutated_code, runtime_code = mutate_file(
            c_file,
            include_paths=args.include or [],
        )
        stem = Path(c_file).stem
        mutated_path = out_dir / f"{stem}.c"
        mutated_path.write_text(mutated_code)
        mutated_paths.append(mutated_path)

        if not runtime_written:
            (out_dir / "pesto_runtime.c").write_text(runtime_code)
            runtime_written = True

    all_files = " ".join(str(p) for p in mutated_paths)
    print(f"Compile: gcc {all_files} {out_dir}/pesto_runtime.c -o mutant")
    print("Run:     echo <mutant_id> | ./mutant  (-1 = original)")


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    trace_p = subparsers.add_parser("trace")
    trace_p.add_argument("target")
    trace_p.add_argument("-s", "--sensitivity", type=int, default=1)
    trace_p.set_defaults(func=cmd_trace)

    mutate_p = subparsers.add_parser("mutate")
    mutate_p.add_argument("c_files", nargs='+')
    mutate_p.add_argument("-I", "--include", metavar="DIR", action="append")
    mutate_p.set_defaults(func=cmd_mutate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
