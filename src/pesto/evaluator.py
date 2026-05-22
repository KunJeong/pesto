import json
import os
import random
import subprocess
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LONGOBJECT_META = PROJECT_ROOT / "vendor" / "cpython" / "pesto.json"


def _exception_type(stderr):
    for line in reversed(stderr.splitlines()):
        line = line.strip()
        if line and not line.startswith(" ") and not line.startswith("^"):
            return line.split(":")[0]
    return None


def run_test(python_exe, test_file, mutant_id, timeout):
    env = {**os.environ, "PESTO_MUTANT_ID": str(mutant_id)}
    try:
        r = subprocess.run(
            [python_exe, test_file],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, env=env,
        )
        return {
            "exit_code": r.returncode,
            "stdout": r.stdout,
            "exception_type": _exception_type(r.stderr),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": None, "stdout": "", "exception_type": None, "timed_out": True}


def is_killed(baseline, result):
    if baseline["timed_out"] != result["timed_out"]:
        return True
    if result["timed_out"]:
        return False
    if result["exit_code"] in (134, -6, 6):
        return True
    if baseline["exit_code"] != result["exit_code"]:
        return True
    if baseline["stdout"] != result["stdout"]:
        return True
    if baseline["exception_type"] != result["exception_type"]:
        return True
    return False


LONGOBJECT_PYTHON = PROJECT_ROOT / "vendor" / "cpython" / "python"
TESTS_DIR = PROJECT_ROOT / "tests"


def _evaluate_mutant(python_exe, test_files, baselines, mutation_info, mid, timeout):
    killing_tests = []
    for tf in test_files:
        result = run_test(python_exe, str(tf), mid, timeout)
        if is_killed(baselines[str(tf)], result):
            killing_tests.append(tf.name)
            break
    info = mutation_info.get(mid, {})
    if killing_tests:
        return mid, {"status": "killed", "killed_by": killing_tests, **info}
    return mid, {"status": "survived", **info}


def run_evaluation(sample=None, seed=42, timeout=10.0, tests_dir=None, binary=None, meta=None):
    python_exe = binary or str(LONGOBJECT_PYTHON)
    _meta = Path(meta) if meta else LONGOBJECT_META
    _tests_dir = Path(tests_dir) if tests_dir else TESTS_DIR
    test_files = sorted(_tests_dir.glob("*.py"))
    if not test_files:
        raise ValueError(f"No .py files found in {_tests_dir}")

    meta_data = json.loads(_meta.read_text())
    mutation_count = meta_data["mutation_count"]
    mutation_info = {m["id"]: m for m in meta_data.get("mutations", [])}

    all_ids = list(range(mutation_count))
    if sample and sample < mutation_count:
        rng = random.Random(seed)
        sampled_ids = sorted(rng.sample(all_ids, sample))
        print(f"Sampled {len(sampled_ids)} of {mutation_count} mutations (seed={seed})")
    else:
        sampled_ids = all_ids
        print(f"Evaluating all {mutation_count} mutations")

    print(f"{len(test_files)} test files | timeout={timeout}s")

    n_workers = os.cpu_count() or 4

    print("\n[Baseline] Running with PESTO_MUTANT_ID=-1 ...")
    baselines = {}
    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        future_to_tf = {executor.submit(run_test, python_exe, str(tf), -1, timeout): tf for tf in test_files}
        for future in as_completed(future_to_tf):
            tf = future_to_tf[future]
            result = future.result()
            baselines[str(tf)] = result
            status = "TIMEOUT" if result["timed_out"] else f"exit={result['exit_code']}"
            print(f"  {tf.name}: {status}")

    print(f"\n[Mutations] Evaluating {len(sampled_ids)} mutations (workers={n_workers}) ...")
    killed, per_mutant = 0, {}
    start = time.monotonic()

    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = {
            executor.submit(_evaluate_mutant, python_exe, test_files, baselines, mutation_info, mid, timeout): mid
            for mid in sampled_ids
        }
        for i, future in enumerate(as_completed(futures)):
            mid, result = future.result()
            per_mutant[mid] = result
            if result["status"] == "killed":
                killed += 1
            if (i + 1) % 50 == 0 or (i + 1) == len(sampled_ids):
                elapsed = time.monotonic() - start
                print(f"  [{i+1}/{len(sampled_ids)}] killed={killed} "
                      f"score={killed/(i+1):.1%} elapsed={elapsed:.1f}s", flush=True)

    total_evaluated = len(sampled_ids)
    score = killed / total_evaluated if total_evaluated else 0.0

    print(f"\n{'='*60}")
    print(f"MUTATION SCORE: {killed}/{total_evaluated} = {score:.1%}")
    if sample and sample < mutation_count:
        print(f"(sampled {total_evaluated} of {mutation_count} total mutations)")

    type_stats = defaultdict(lambda: {"killed": 0, "survived": 0})
    for m in per_mutant.values():
        type_stats[m.get("type", "unknown")][m["status"]] += 1
    print("\nBy mutation type:")
    for t, s in sorted(type_stats.items()):
        total_t = s["killed"] + s["survived"]
        print(f"  {t:8s}: {s['killed']}/{total_t} killed ({s['killed']/total_t:.1%})")

    results = {
        "mutation_count_total": mutation_count,
        "mutation_count_evaluated": total_evaluated,
        "sample_seed": seed if (sample and sample < mutation_count) else None,
        "killed": killed,
        "survived": total_evaluated - killed,
        "mutation_score": score,
        "type_stats": type_stats,
        "per_mutant": {str(k): v for k, v in per_mutant.items()},
    }

    output = PROJECT_ROOT / "result.json"
    output.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved to {output}")

    return results
