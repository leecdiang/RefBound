# CUDA reconstruction stages

This is an engineering recipe for a future build, not a record of a successful CUDA build.

1. Verify `PROVENANCE.json`, preserve the original source package, and use a new output directory.
2. Install a compatible Linux x86-64 compiler, CMake, Ninja and complete CUDA Toolkit in the user's own environment. The original A5000 deployment recorded GCC 11.4 and CUDA 12.5.40; this source package does not redistribute those tools or promise bit-identical output with newer versions.
3. Configure `backend/` using the same disabled extra targets as `scripts/build_cpu.py`, but set `GGML_CUDA=ON` and an explicit architecture (A5000: 86). Keep `BUILD_SHARED_LIBS=OFF`. Record CMake cache, compiler versions, flags and all source/dependency hashes.
4. Build actual `llama`, `ggml`, `ggml-base`, `ggml-cpu`, and `ggml-cuda` targets. Do not copy an unrelated installed ggml or old archive into the new build.
5. Compile `frontend/native.cpp` with the included backend include/src/ggml/include/ggml/src/common/vendor directories. Compile `frontend/work_counts.cpp` with those includes and the installed CUDA Toolkit headers.
6. Link the real objects and archives, CUDA runtime, cuBLAS/cuBLASLt and all other dependencies selected by the actual CUDA CMake target, plus system threading/dynamic-loader/OpenMP libraries. Use CMake's generated target/link metadata rather than treating this list as an exhaustive hand-written linker command. Preserve the `--wrap` functions actually implemented in work_counts.cpp: cudaLaunchKernel, cudaLaunchKernelExC, cudaMemcpyAsync, cudaMemcpy, cudaMemcpy2DAsync, cudaMalloc, cudaMallocAsync, cudaStreamSynchronize, cudaDeviceSynchronize. Capture full link command/map and unresolved-symbol report. A successful target name alone is insufficient.
7. Before any GPU execution, inspect binary module dependencies and required P4 capability exports. Model-free `--cpu-fixtures` must pass without entering backend/model initialization.
8. GPU/model testing is a distinct, explicitly budgeted step. Use a new independent reference on the same deployment, verify complete outputs, active KV/state, continuation/rollback, actual dispatch and end-to-end timings. Preserve failures. This candidate package does not authorize or run those tests.

Known diagnostic result: CPU core archives and the real P4 frontend objects build. Linking against the CPU-only core leaves the two P4 capability/audit symbols unresolved, as expected; the missing symbols must come from actual CUDA MMVQ compilation. CUDA configuration on the audit machine fails because nvcc is not installed.
