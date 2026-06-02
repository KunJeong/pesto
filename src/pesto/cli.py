"""Unified command-line interface for the PESTO toolchain."""

import argparse
import json
import sys
from pathlib import Path

# Allow running as ``python src/pesto/cli.py`` by putting src/ on the path.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pesto import (
    cpython_build,
    dedup,
    evaluator,
    fuzzer,
    mutator,
    pipeline,
    reducer,
    summarize,
    tracer,
)


def _parse_mutations(numbers):
    result = []
    for n in numbers:
        if not (1 <= n <= len(mutator.ALL_MUTATION_TYPES)):
            raise SystemExit(
                f"Invalid mutation number {n}. Valid: 1–{len(mutator.ALL_MUTATION_TYPES)} "
                f"({', '.join(f'{i+1}={t}' for i, t in enumerate(mutator.ALL_MUTATION_TYPES))})"
            )
        result.append(mutator.ALL_MUTATION_TYPES[n - 1])
    return result


def _validate_smtc_limit(value):
    if value is not None and value < 0:
        raise SystemExit(f"--smtc-limit must be >= 0 (got {value})")


def cmd_trace(args):
    print(tracer.trace_summary(args.target, args.sensitivity))


def cmd_fuzz_proc(args):
    fuzzer.process_grammar()


def cmd_fuzz(args):
    outdir, kept = fuzzer.generate(
        n=args.n, rounds=args.rounds, outdir=args.outdir, seed=args.seed
    )
    print(f"kept {kept} crashing program(s) in {outdir}")
    return 0 if kept else 1


def cmd_reduce(args):
    return reducer.reduce_all(
        output=args.output,
        inputs=args.input,
        input_dir=args.input_dir,
        sensitivity=args.sensitivity,
        jobs=args.jobs,
    )


def cmd_dedup(args):
    return dedup.dedup(args.input_dir, args.output_dir)


def cmd_summarize(args):
    return summarize.summarize_errors(args.input_dir, out_dir=args.out_dir)


def _load_config(config_path):
    with open(config_path) as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise SystemExit("Config must be a JSON object mapping file paths to function lists.")
    return raw


def cmd_mutate(args):
    if args.config and args.c_files:
        raise SystemExit("error: --config and positional c_files are mutually exclusive")
    if not args.config and not args.c_files:
        raise SystemExit("error: provide either c_files or --config")

    enabled = _parse_mutations(args.mutations) if args.mutations else None
    _validate_smtc_limit(args.smtc_limit)
    targets = _load_config(args.config) if args.config else {f: None for f in args.c_files}

    out_dir = Path.cwd() / "pesto_mutation"
    out_dir.mkdir(exist_ok=True)

    runtime_written = False
    mutated_paths = []
    all_mutations = []
    file_entries = []
    id_offset = 0

    for c_file, func_list in targets.items():
        mutated_code, runtime_code, mutation_count, mutations = mutator.mutate_file(
            c_file,
            include_paths=args.include or [],
            enabled_mutations=enabled,
            target_functions=func_list,
            id_offset=id_offset,
            smtc_limit=args.smtc_limit,
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

        file_entries.append({
            "file": c_file,
            "mutation_count": mutation_count,
            "id_range": [id_offset, id_offset + mutation_count - 1] if mutation_count else [],
        })
        all_mutations.extend(mutations)
        id_offset += mutation_count

    unified_meta = {"mutation_count": id_offset, "mutations": all_mutations, "files": file_entries}
    (out_dir / "pesto.json").write_text(json.dumps(unified_meta, indent=2))

    print(f"Compile: gcc {' '.join(str(p) for p in mutated_paths)} {out_dir}/pesto_runtime.c -o mutant")
    print("Run:     PESTO_MUTANT_ID=<id> ./mutant  (-1 = original)")


def cmd_mutate_cpython(args):
    if args.config and args.file:
        raise SystemExit("error: --config and positional file are mutually exclusive")

    enabled = _parse_mutations(args.mutations) if args.mutations else None
    _validate_smtc_limit(args.smtc_limit)
    targets = _load_config(args.config) if args.config else None
    built = cpython_build.build_mutated_cpython(
        file=args.file or "Objects/longobject.c", mutations=enabled, targets=targets,
        smtc_limit=args.smtc_limit,
    )
    return 0 if built else 1


def cmd_evaluate(args):
    evaluator.run_evaluation(
        sample=args.sample,
        seed=args.seed,
        timeout=args.timeout,
        tests_dir=args.tests_dir,
        binary=args.binary,
        meta=args.meta,
    )


def cmd_pipeline(args):
    return pipeline.run_pipeline(
        args.workdir,
        n=args.n,
        rounds=args.rounds,
        seed=args.seed,
        sensitivity=args.sensitivity,
        jobs=args.jobs,
        sample=args.sample,
        eval_seed=args.eval_seed,
        timeout=args.timeout,
        skip_fuzz=args.skip_fuzz,
        skip_reduce=args.skip_reduce,
        skip_dedup=args.skip_dedup,
        skip_evaluate=args.skip_evaluate,
    )


def build_parser():
    parser = argparse.ArgumentParser(prog="pesto", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("trace", help="print the crash signature of a Python program")
    p.add_argument("target")
    p.add_argument("-s", "--sensitivity", type=int, default=1)
    p.set_defaults(func=cmd_trace)

    p = sub.add_parser("fuzz-proc", help="compile the fuzzing grammar")
    p.set_defaults(func=cmd_fuzz_proc)

    p = sub.add_parser("fuzz", help="generate crashing Python programs")
    p.add_argument("-n", type=int, default=20)
    p.add_argument("--rounds", type=int, default=100)
    p.add_argument("-o", "--outdir", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.set_defaults(func=cmd_fuzz)

    p = sub.add_parser("reduce", help="reduce crashing programs with Perses")
    p.add_argument("-o", "--output", required=True, metavar="DIR")
    p.add_argument("-i", "--input", default=None, metavar="FILE")
    p.add_argument("--input-dir", default=None, metavar="DIR")
    p.add_argument("-s", "--sensitivity", type=int, default=reducer.DEFAULT_TRACE_SENSITIVITY)
    p.add_argument("-j", "--jobs", type=int, default=reducer.DEFAULT_REDUCER_JOBS)
    p.set_defaults(func=cmd_reduce)

    p = sub.add_parser("dedup", help="keep one program per unique AST")
    p.add_argument("input_dir")
    p.add_argument("output_dir")
    p.set_defaults(func=cmd_dedup)

    p = sub.add_parser("summarize", help="summarize exceptions from fuzzer .err logs")
    p.add_argument("input_dir")
    p.add_argument(
        "-o",
        "--out-dir",
        help="copy .py files whose .err final exception class is TypeError",
    )
    p.set_defaults(func=cmd_summarize)

    p = sub.add_parser("mutate", help="mutate plain C files and emit a compile recipe")
    p.add_argument("c_files", nargs="*")
    p.add_argument("--config", metavar="JSON", help="JSON map of file -> function list (null = all)")
    p.add_argument("-I", "--include", metavar="DIR", action="append")
    p.add_argument("-m", "--mutations", nargs="+", type=int, metavar="N")
    p.add_argument("--smtc-limit", type=int, metavar="N")
    p.set_defaults(func=cmd_mutate)

    p = sub.add_parser("mutate-cpython", help="mutate CPython source file(s) and rebuild")
    p.add_argument("file", nargs="?", default=None)
    p.add_argument("--config", metavar="JSON", help="JSON map of cpython-relative file -> function list (null = all)")
    p.add_argument("-m", "--mutations", nargs="+", type=int, metavar="N")
    p.add_argument("--smtc-limit", type=int, metavar="N")
    p.set_defaults(func=cmd_mutate_cpython)

    p = sub.add_parser("evaluate", help="compute the mutation score of a test suite")
    p.add_argument("--sample", type=int, default=None)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--timeout", type=float, default=10.0)
    p.add_argument("--tests-dir", default=None, metavar="DIR")
    p.add_argument("--binary", default=None, metavar="PATH")
    p.add_argument("--meta", default=None, metavar="PATH")
    p.set_defaults(func=cmd_evaluate)

    p = sub.add_parser("pipeline", help="run the full fuzz->reduce->dedup->evaluate flow")
    p.add_argument("workdir", nargs="?", default=None)
    p.add_argument("-n", type=int, default=20)
    p.add_argument("--rounds", type=int, default=100)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("-s", "--sensitivity", type=int, default=reducer.DEFAULT_TRACE_SENSITIVITY)
    p.add_argument("-j", "--jobs", type=int, default=reducer.DEFAULT_REDUCER_JOBS)
    p.add_argument("--sample", type=int, default=None)
    p.add_argument("--eval-seed", type=int, default=42)
    p.add_argument("--timeout", type=float, default=10.0)
    p.add_argument("--skip-fuzz", action="store_true")
    p.add_argument("--skip-reduce", action="store_true")
    p.add_argument("--skip-dedup", action="store_true")
    p.add_argument("--skip-evaluate", action="store_true")
    p.set_defaults(func=cmd_pipeline)

    return parser


def main():
    args = build_parser().parse_args()
    rc = args.func(args)
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
