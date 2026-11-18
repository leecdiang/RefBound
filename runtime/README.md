# Reference-preserving P4 research source

This package contains the actual P4 numerical core and four-arm application frontend used in the archived A5000 study. It is research source; new-deployment CUDA/GPU qualification remains outstanding.

The numerical source was reconstructed by replaying the fixed loop4 → Q32 → strong REF1 → native4 → P4 transformations. The four resulting core files match the archived P4 source hashes. `PROVENANCE.json` binds included files and original source identities. The patch series records numerical changes and a separate build-only removal of unrelated historical Windows tools.

## What is included

- `backend/`: fixed llama/ggml-based numerical source, including actual P4 dispatch.
- `frontend/`: unchanged four-arm resident application frontend, state reader, transaction and draft-work tests.
- `scripts/build_cpu.py`: source integrity checks, fresh CPU build, real frontend object compilation and model-free CPU tests.
- `patches/`: auditable source transformations; not replacements for the complete included source tree.
- Third-party license files retained in their original directories.

No model weights, experiment prompts/payloads, host inventories, NVIDIA SDK headers, CUDA libraries or historical executable archives are included.

## CPU validation

Requirements: Python 3, CMake, Ninja, a C++17 GNU-compatible compiler and OpenMP development support. From the package root, run:

```sh
python3 scripts/build_cpu.py --out /path/to/new-build --jobs 2
```

The output directory must not already exist and must be outside this package. No download, model loading, inference, GPU initialization or experiment run is performed. Outputs include actual commands/logs and a result record. The CPU core is a build diagnostic, **not** an oracle for the paper's GPU arithmetic. The P4 worker is not linked by this CPU workflow because its capabilities are supplied by the real CUDA backend.

## CUDA build and qualification remaining

The native P4 core exports `hs_prefill_pack4_capability_v1` and `hs_prefill_pack4_audit` from the CUDA MMVQ translation unit. Do not substitute stubs for these capabilities. A complete worker requires a user-installed CUDA Toolkit, CUDA numerical backend, work-count object and CUDA runtime linking.

See `CUDA_BUILD.md` for the exact source-build stages and remaining validation. This package has not been advertised as a generic concurrent serving runtime. The frontend retains the original fixed-profile study contract, including GPU visibility, graph-policy and numerical-reference checks; new deployments require fresh qualification.

## Scope and portability

The preserved state reader currently loads `/usr/lib/x86_64-linux-gnu/libcrypto.so.3`. This is an explicit Linux platform dependency, not a bundled library. The included frontend is the P4 application frontend, not the later LOCAL two-history diagnostic frontend. A reusable runtime should add a separate validated user-facing configuration layer rather than deleting scientific guards.

Historical measurements describe the archived deployment. Newly compiled binaries have not inherited those measurements or numerical qualification.

## Licenses

Original author additions use the repository's MIT license. Upstream and vendored components retain their own copyrights and licenses. `THIRD_PARTY.md` identifies the main included components. The root MIT file does not replace third-party terms. NVIDIA SDK components must be obtained separately under NVIDIA's terms.

## Excluded optional backends

`backend/ggml/src/ggml-sycl/` and `backend/ggml/src/ggml-openvino/` have been removed from this CPU/CUDA-only candidate. SYCL Apache-2.0 WITH LLVM-exception sources and OpenVINO Apache-2.0 sources are not distributed here. `EXCLUDED_BACKENDS.json` retains only their paths and source hashes for audit. Do not enable `GGML_SYCL` or `GGML_OPENVINO`; those backends are unsupported in this subset. Original source archives remain unchanged.
