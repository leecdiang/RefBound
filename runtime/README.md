# P4 runtime source

This package contains the P4 numerical core and four-arm application frontend used in the archived A5000 study. The included workflow builds the CPU core, compiles the real P4 frontend to objects and checks state logic. CUDA execution follows the deployment-specific build and qualification stages in [CUDA_BUILD.md](CUDA_BUILD.md).

[Repository home](../README.md) · [Artifact guide](../docs/README.md) · [Provenance](PROVENANCE.json) · [Recorded validation](VALIDATION.json)

The numerical source was reconstructed by replaying the fixed loop4 → Q32 → strong REF1 → native4 → P4 transformations. The four resulting core files match the archived P4 source hashes. `PROVENANCE.json` binds included files and original source identities. The patch series records numerical changes and a separate build-only removal of unrelated historical Windows tools.

## What is included

- `backend/`: fixed llama/ggml-based numerical source, including actual P4 dispatch.
- `frontend/`: unchanged four-arm resident application frontend, state reader, transaction and draft-work tests.
- `scripts/build_cpu.py`: source integrity checks, fresh CPU build, real frontend object compilation and model-free CPU tests.
- `patches/`: auditable source transformations; not replacements for the complete included source tree.
- Third-party license files retained in their original directories.

No model weights, experiment prompts/payloads, host inventories, NVIDIA SDK headers, CUDA libraries or historical executable archives are included.

## CPU validation

Requirements: Python 3, CMake, Ninja, a C++17 GNU-compatible compiler and OpenMP development support. From the repository root, run:

```sh
python3 runtime/scripts/build_cpu.py --out /absolute/path/to/new-cpu-build --jobs 2
```

The output directory must be new and outside the repository. Outputs include commands, logs and a result record. This model-free workflow checks buildability and state logic; GPU arithmetic is checked by deployment-specific numerical qualification. The CPU workflow compiles frontend objects, while the complete P4 worker obtains its capability exports from the CUDA backend.

The preserved [validation record](VALIDATION.json) reports 216 CPU build steps, frontend object compilation, transaction checks and 257,082 draft-work cases. Its candidate-stage status fields, and those in `PROVENANCE.json`, describe the original validation snapshot. See the [artifact guide](../docs/README.md#reading-the-provenance-records) for their relation to this public repository.

## CUDA build and qualification

The native P4 core exports `hs_prefill_pack4_capability_v1` and `hs_prefill_pack4_audit` from the CUDA MMVQ translation unit. Do not substitute stubs for these capabilities. A complete worker requires a user-installed CUDA Toolkit, CUDA numerical backend, work-count object and CUDA runtime linking.

See [CUDA_BUILD.md](CUDA_BUILD.md) for the source-build stages and validation scope. The frontend retains the original fixed-profile study contract, including GPU visibility, graph-policy and numerical-reference checks. A new deployment binds and qualifies that profile on its own toolchain and device.

## Scope and portability

The preserved state reader currently loads `/usr/lib/x86_64-linux-gnu/libcrypto.so.3`. This is an explicit Linux platform dependency, not a bundled library. The included frontend is the P4 application frontend, not the later LOCAL two-history diagnostic frontend. A reusable runtime should add a separate validated user-facing configuration layer rather than deleting scientific guards.

Historical measurements describe the archived deployment. Newly compiled binaries have not inherited those measurements or numerical qualification.

## Licenses

Original author additions use the repository's MIT license. Upstream and vendored components retain their own copyrights and licenses. `THIRD_PARTY.md` identifies the main included components. The root MIT file does not replace third-party terms. NVIDIA SDK components must be obtained separately under NVIDIA's terms.

## Excluded optional backends

`backend/ggml/src/ggml-sycl/` and `backend/ggml/src/ggml-openvino/` have been removed from this CPU/CUDA-only distribution. SYCL Apache-2.0 WITH LLVM-exception sources and OpenVINO Apache-2.0 sources are not distributed here. `EXCLUDED_BACKENDS.json` retains only their paths and source hashes for audit. Do not enable `GGML_SYCL` or `GGML_OPENVINO`; those backends are unsupported in this subset. Original source archives remain unchanged.
