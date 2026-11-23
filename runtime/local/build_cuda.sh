#!/usr/bin/env bash
set -euo pipefail
if [[ $# != 1 || "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
    printf 'Usage on Linux x86-64: bash build_cuda.sh NEW_OUTPUT_DIR\n' >&2
    exit 2
fi
component="$(cd "$(dirname "$0")" && pwd)"
cuda="${CUDA_ROOT:-/usr/local/cuda-12.5}"
ccdir="${GCC_BIN_DIR:-/usr/bin}"
test "$("$ccdir/g++-11" -dumpfullversion)" = 11.4.0
"$cuda/bin/nvcc" --version | grep -F 'V12.5.40'
test -r /usr/lib/x86_64-linux-gnu/libcrypto.so.3
mkdir -- "$1"
out="$(cd "$1" && pwd)"
flags=(
    -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
    "-DCMAKE_C_COMPILER=$ccdir/gcc-11" "-DCMAKE_CXX_COMPILER=$ccdir/g++-11"
    "-DCMAKE_CUDA_COMPILER=$cuda/bin/nvcc" "-DCMAKE_CUDA_HOST_COMPILER=$ccdir/g++-11"
    -DCMAKE_CUDA_ARCHITECTURES=86 -DBUILD_SHARED_LIBS=OFF -DGGML_CPU=ON -DGGML_CUDA=ON
    -DGGML_NATIVE=OFF -DGGML_CCACHE=OFF
    -DLLAMA_BUILD_NUMBER=10839 -DLLAMA_BUILD_COMMIT=0cae43063
    -DLLAMA_BUILD_COMMON=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF
    -DLLAMA_BUILD_TOOLS=OFF -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BUILD_APP=OFF
    -DLLAMA_BUILD_MTMD=OFF -DLLAMA_OPENSSL=OFF -DLLAMA_BUILD_UI=OFF
    -DLLAMA_USE_PREBUILT_UI=OFF
)
export CUDA_VISIBLE_DEVICES=
cmake -S "$component" -B "$out/build" "${flags[@]}" > "$out/configure.log" 2>&1
nice -n 10 cmake --build "$out/build" --target refbound-local --parallel 2 --verbose > "$out/build.log" 2>&1
worker="$out/build/refbound-local"
ninja -C "$out/build" -t commands refbound-local | tail -1 > "$out/link.command"
ldd "$worker" > "$out/dependencies.log"
if grep -q 'not found' "$out/dependencies.log"; then exit 1; fi
nm --defined-only "$worker" > "$out/symbols.log"
for symbol in hs_a5000_native4_capability_v1 hs_prefill_pack4_capability_v1 hs_prefill_pack4_audit; do
    grep -E " [Tt] ${symbol}$" "$out/symbols.log"
done
grep -m1 'ggml-cuda/.*mmvq' "$out/build/local-link.map"
"$worker" --cpu-fixtures
for arm in SIMPLE LOCAL; do
    HS_LOCAL_LOWERING="$arm" HS_PREFILL_PACK4=0 "$worker" --local-profile-cpu "$arm"
done
if HS_LOCAL_LOWERING=LOCAL HS_PREFILL_PACK4=1 "$worker" --local-profile-cpu LOCAL > "$out/refusal.log" 2>&1; then
    printf 'CPU fixture unexpectedly admitted P4 in LOCAL\n' >&2
    exit 1
fi
grep -F 'P4 OFF' "$out/refusal.log"
sha256sum "$worker"
