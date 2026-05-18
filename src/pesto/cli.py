import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PATCHED_CPYTHON_ROOT = PROJECT_ROOT / "vendor" / "cpython"
TESTS_DIR = PROJECT_ROOT / "tests"

_TRACE_SKIP = 4366



def cmd_trace(args: argparse.Namespace):
    result = subprocess.run(
        [str(PATCHED_CPYTHON_ROOT / "python"), args.target],
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

    traces = "\n".join(result.stderr.splitlines()[_TRACE_SKIP:])
    first_matching_block = pesto_block_re.findall(traces)[0]

    frames = [line.split()[3] for line in first_matching_block.strip().splitlines()]

    print(f"{escaping_exception_type} | " + " ; ".join(frames[: args.sensitivity]))


def _parse_mutations(numbers):
    from pesto.mutator import ALL_MUTATION_TYPES
    result = []
    for n in numbers:
        if not (1 <= n <= len(ALL_MUTATION_TYPES)):
            raise SystemExit(
                f"Invalid mutation number {n}. Valid: 1–{len(ALL_MUTATION_TYPES)} "
                f"({', '.join(f'{i+1}={t}' for i, t in enumerate(ALL_MUTATION_TYPES))})"
            )
        result.append(ALL_MUTATION_TYPES[n - 1])
    return result


def cmd_mutate(args: argparse.Namespace):
    from pesto.mutator import mutate_file

    enabled = _parse_mutations(args.mutations) if args.mutations else None

    out_dir = Path.cwd() / "pesto_mutation"
    out_dir.mkdir(exist_ok=True)

    runtime_written = False
    mutated_paths = []

    for c_file in args.c_files:
        mutated_code, runtime_code, mutation_count, mutations = mutate_file(
            c_file,
            include_paths=args.include or [],
            enabled_mutations=enabled,
        )
        stem = Path(c_file).stem
        mutated_path = out_dir / f"{stem}.c"
        mutated_path.write_text(mutated_code)
        mutated_paths.append(mutated_path)

        meta = {"file": c_file, "mutation_count": mutation_count, "mutations": mutations}
        (out_dir / f"{stem}.meta.json").write_text(json.dumps(meta, indent=2))

        if not runtime_written:
            (out_dir / "pesto_runtime.c").write_text(runtime_code)
            runtime_written = True

    print(f"Compile: gcc {' '.join(str(p) for p in mutated_paths)} {out_dir}/pesto_runtime.c -o mutant")
    print("Run:     PESTO_MUTANT_ID=<id> ./mutant  (-1 = original)")


def cmd_mutate_cpython(args: argparse.Namespace):
    from pesto.mutator import mutate_file, CPYTHON_DEFINES, CPYTHON_HEADERS

    sys.setrecursionlimit(50000)

    if not PATCHED_CPYTHON_ROOT.exists():
        sys.exit(f"Patched CPython not found. Run: scripts/build-patched-cpython.sh")

    include_paths = [
        str(CPYTHON_HEADERS),
        str(PATCHED_CPYTHON_ROOT),
        str(PATCHED_CPYTHON_ROOT / "Include"),
        str(PATCHED_CPYTHON_ROOT / "Include" / "cpython"),
        str(PATCHED_CPYTHON_ROOT / "Include" / "internal"),
    ]

    enabled = _parse_mutations(args.mutations) if args.mutations else None

    meta_path = PATCHED_CPYTHON_ROOT / "pesto.json"
    target = PATCHED_CPYTHON_ROOT / args.file

    if meta_path.exists():
        print("Already mutated, skipping mutation step.")
    else:
        print(f"Mutating {args.file} ...")
        try:
            mutated_code, runtime_code, mutation_count, mutations = mutate_file(
                str(target),
                cpp_args=CPYTHON_DEFINES,
                include_paths=include_paths,
                enabled_mutations=enabled,
            )
            target.write_text(mutated_code)
            (target.parent / "pesto_runtime.c").write_text(runtime_code)

            meta = {"file": str(target), "mutation_count": mutation_count, "mutations": mutations}
            meta_path.write_text(json.dumps(meta, indent=2))
            print(f"Done: {mutation_count} mutations in {args.file}")
        except Exception as e:
            msg = str(e).splitlines()[0][:80]
            print(f"Failed [{type(e).__name__}] {msg}")
            return

    rel = target.parent.relative_to(PATCHED_CPYTHON_ROOT)
    runtime_obj = f"{rel}/pesto_runtime.o"
    runtime_src = f"{rel}/pesto_runtime.c"

    makefile = PATCHED_CPYTHON_ROOT / "Makefile"
    content = makefile.read_text()
    if "# PESTO additions" not in content:
        makefile.write_text(content + (
            f"\n# PESTO additions\n"
            f"OBJECT_OBJS += {runtime_obj}\n\n"
            f"{runtime_obj}: {runtime_src}\n"
            f"\t$(CC) -c -O2 -o $@ $<\n"
        ))
        print("Patched Makefile.")

    subprocess.run(
        ["make", "-C", str(PATCHED_CPYTHON_ROOT), runtime_obj],
        check=True,
        capture_output=True,
    )

    print(f"Building mutated CPython ...")
    result = subprocess.run(
        ["make", "-C", str(PATCHED_CPYTHON_ROOT), f"-j{os.cpu_count() or 4}", "python"],
    )
    if result.returncode == 0:
        print(f"\nBuild complete: {PATCHED_CPYTHON_ROOT}/python")
        print(f"Evaluate: pesto evaluate")
    else:
        print(f"\nBuild failed.")


def cmd_evaluate(args: argparse.Namespace):
    from pesto.evaluator import run_evaluation

    run_evaluation(
        sample=args.sample,
        seed=args.seed,
        timeout=args.timeout,
    )


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
    mutate_p.add_argument("-m", "--mutations", nargs="+", type=int, metavar="N")
    mutate_p.set_defaults(func=cmd_mutate)

    mutate_cpython_p = subparsers.add_parser("mutate-cpython")
    mutate_cpython_p.add_argument("file", nargs="?", default="Objects/longobject.c")
    mutate_cpython_p.add_argument("-m", "--mutations", nargs="+", type=int, metavar="N")
    mutate_cpython_p.set_defaults(func=cmd_mutate_cpython)

    eval_p = subparsers.add_parser("evaluate")
    eval_p.add_argument("--sample", type=int, default=None)
    eval_p.add_argument("--seed", type=int, default=42)
    eval_p.add_argument("--timeout", type=float, default=10.0)
    eval_p.set_defaults(func=cmd_evaluate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
