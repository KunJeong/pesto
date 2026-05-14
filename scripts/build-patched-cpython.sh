#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
git clone --depth 1 --branch v3.13.0 https://github.com/python/cpython.git vendor/cpython
git -C vendor/cpython apply "$ROOT/cpython-patch/instrumentation.patch"
cd vendor/cpython
./configure
make -j$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)
