#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLEAN_ROOT="$ROOT/vendor_clean"
CPYTHON="$CLEAN_ROOT/cpython"
PYTHON="$CPYTHON/python"
LOG="$ROOT/results/measure.txt"
TIMEOUT="10"
DIRS=()

usage() {
    echo "usage: $0 [-o LOG] [--timeout SECONDS] DIR [DIR ...]"
}

build_cpython() {
    mkdir -p "$CLEAN_ROOT"
    if [ ! -d "$CPYTHON" ]; then
        git clone --depth 1 --branch v3.13.0 https://github.com/python/cpython.git "$CPYTHON" || exit $?
    fi
    cd "$CPYTHON" || exit $?
    ./configure || exit $?
    make -j"$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)" || exit $?
    cd "$ROOT" || exit $?
}

run_measure() {
    tests_dir="$1"

    {
        echo "===== $tests_dir ====="
        python3 "$ROOT/src/pesto/eval/measure.py" "$PYTHON" "$tests_dir" --timeout "$TIMEOUT"
        status=$?
        echo "measure_exit: $status"
        echo
    } >> "$LOG" 2>&1
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        -o|--output)
            shift
            if [ "$#" -eq 0 ]; then
                usage
                exit 2
            fi
            LOG="$1"
            ;;
        --timeout)
            shift
            if [ "$#" -eq 0 ]; then
                usage
                exit 2
            fi
            TIMEOUT="$1"
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            while [ "$#" -gt 0 ]; do
                DIRS+=("$1")
                shift
            done
            break
            ;;
        -*)
            echo "unknown option: $1" >&2
            usage
            exit 2
            ;;
        *)
            DIRS+=("$1")
            ;;
    esac
    shift
done

if [ "${#DIRS[@]}" -eq 0 ]; then
    usage
    exit 2
fi

if [ ! -x "$PYTHON" ]; then
    build_cpython
fi

mkdir -p "$(dirname "$LOG")"
: > "$LOG"

for tests_dir in "${DIRS[@]}"; do
    run_measure "$tests_dir"
done

echo "$LOG"
