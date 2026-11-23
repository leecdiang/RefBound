#!/usr/bin/env bash
set -euo pipefail
if [[ $# != 1 ]]; then printf 'Usage: bash test_cpu.sh NEW_OUTPUT_DIR\n' >&2; exit 2; fi
component="$(cd "$(dirname "$0")" && pwd)"
mkdir -- "$1"
out="$(cd "$1" && pwd)"
python3 -B "$component/check.py" --quick
for test in test_transaction test_draft_work; do
    "${CXX:-g++-11}" -std=c++17 -O2 -I"$component/src" "$component/src/$test.cpp" -o "$out/$test"
    "$out/$test"
done
