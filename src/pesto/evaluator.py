import json
import os
import random
import subprocess
import time
from collections import defaultdict
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


def run_evaluation(sample=None, seed=42, timeout=10.0):
    python_exe = str(LONGOBJECT_PYTHON)
    test_files = sorted(TESTS_DIR.glob("*.py"))
    if not test_files:
        raise ValueError(f"No .py files found in {TESTS_DIR}")

    meta_data = json.loads(LONGOBJECT_META.read_text())
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

    print("\n[Baseline] Running with PESTO_MUTANT_ID=-1 ...")
    baselines = {}
    for tf in test_files:
        result = run_test(python_exe, str(tf), -1, timeout)
        baselines[str(tf)] = result
        status = "TIMEOUT" if result["timed_out"] else f"exit={result['exit_code']}"
        print(f"  {tf.name}: {status}")

    print(f"\n[Mutations] Evaluating {len(sampled_ids)} mutations ...")
    killed, per_mutant = 0, {}
    start = time.monotonic()

    for i, mid in enumerate(sampled_ids):
        killing_tests = []
        for tf in test_files:
            result = run_test(python_exe, str(tf), mid, timeout)
            if is_killed(baselines[str(tf)], result):
                killing_tests.append(tf.name)
                break

        info = mutation_info.get(mid, {})
        if killing_tests:
            killed += 1
            per_mutant[mid] = {"status": "killed", "killed_by": killing_tests, **info}
        else:
            per_mutant[mid] = {"status": "survived", **info}

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
