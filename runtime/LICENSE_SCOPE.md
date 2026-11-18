# License scope

The root LICENSE applies to the author's original additions and packaging code. It does not relicense third-party source.

`backend/` is a fixed, modified llama.cpp/ggml source subset. Its original license notices, embedded component notices and available standalone licenses are retained. The author modifications are represented by the recorded source identity and patches. `frontend/` preserves the author's archived P4 research implementation.

This candidate excludes CUDA Toolkit/CUPTI headers, NVIDIA binary libraries, model weights, input datasets, experiment payloads and original host inventories. Installing a dependency for private compilation does not make that dependency part of the redistributable source package.

Before a public release, keep the exact third-party notices with the code, review any newly added dependency and separately approve the release name and contents. This scope statement is not a legal/compliance certification.

## Excluded optional backends

`backend/ggml/src/ggml-sycl/` and `backend/ggml/src/ggml-openvino/` have been removed from this CPU/CUDA-only candidate. SYCL Apache-2.0 WITH LLVM-exception sources and OpenVINO Apache-2.0 sources are not distributed here. `EXCLUDED_BACKENDS.json` retains only their paths and source hashes for audit. Do not enable `GGML_SYCL` or `GGML_OPENVINO`; those backends are unsupported in this subset. Original source archives remain unchanged.

The retained nlohmann header includes an Apache-2.0 Abseil fallback. Its separate full license and notice are in `licenses/Apache-2.0.txt` and `licenses/Abseil-NOTICE.txt`; this package is not exclusively MIT.
