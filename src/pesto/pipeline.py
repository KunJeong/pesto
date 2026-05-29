"""End-to-end PESTO pipeline: fuzz -> reduce -> dedup -> evaluate.

Evaluation scores the generated suite against an already-built mutant set, so
``mutate-cpython`` must be run once beforehand to produce the mutated
interpreter and ``pesto.json``.
"""

from pathlib import Path

from . import dedup, evaluator, fuzzer, paths, reducer


def _banner(step: str, title: str) -> None:
    print(f"\n{'=' * 60}\n[{step}] {title}\n{'=' * 60}", flush=True)


def run_pipeline(
    workdir=None,
    *,
    n: int = 20,
    rounds: int = 100,
    seed: int | None = None,
    sensitivity: int = reducer.DEFAULT_TRACE_SENSITIVITY,
    jobs: int = reducer.DEFAULT_REDUCER_JOBS,
    sample: int | None = None,
    eval_seed: int = 42,
    timeout: float = 10.0,
    skip_fuzz: bool = False,
    skip_reduce: bool = False,
    skip_dedup: bool = False,
    skip_evaluate: bool = False,
) -> int:
    """Run the pipeline. Returns a process-style exit code (0 on success)."""
    workdir = Path(workdir) if workdir else paths.DEFAULT_PIPELINE_DIR
    generated_dir = workdir / "generated"
    reduced_dir = workdir / "reduced"
    dedup_dir = workdir / "dedup"
    workdir.mkdir(parents=True, exist_ok=True)
    print(f"[pipeline] workdir: {workdir}")

    if not skip_fuzz:
        _banner("1/4", "fuzz")
        _, kept = fuzzer.generate(n=n, rounds=rounds, outdir=generated_dir, seed=seed)
        if kept == 0:
            print("[pipeline] fuzzing produced no crashing programs; aborting.")
            return 1
    else:
        _banner("1/4", f"fuzz (skipped, using {generated_dir})")

    if not skip_reduce:
        _banner("2/4", "reduce")
        rc = reducer.reduce_all(
            output=str(reduced_dir),
            input_dir=str(generated_dir),
            sensitivity=sensitivity,
            jobs=jobs,
        )
        if rc != 0:
            print("[pipeline] reduction failed; aborting.")
            return rc
    else:
        _banner("2/4", f"reduce (skipped, using {reduced_dir})")

    if not skip_dedup:
        _banner("3/4", "dedup")
        rc = dedup.dedup(reduced_dir, dedup_dir)
        if rc != 0:
            print("[pipeline] dedup failed; aborting.")
            return rc
    else:
        _banner("3/4", f"dedup (skipped, using {dedup_dir})")

    if not skip_evaluate:
        _banner("4/4", "evaluate")
        if not paths.LONGOBJECT_META.exists():
            print(
                f"[pipeline] no mutants found ({paths.LONGOBJECT_META}); "
                "run `python src/pesto/cli.py mutate-cpython` first."
            )
            return 1
        evaluator.run_evaluation(
            sample=sample,
            seed=eval_seed,
            timeout=timeout,
            tests_dir=str(dedup_dir),
        )
    else:
        _banner("4/4", "evaluate (skipped)")

    print("\n[pipeline] done.")
    return 0
