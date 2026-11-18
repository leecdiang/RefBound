# Third-party source and licenses

This is an engineering license inventory, not legal advice or a blanket redistribution clearance.

- llama.cpp / ggml: MIT; `backend/LICENSE`, fixed source based on upstream commit `0cae43063cf15170e91a2ff4d034da0ecef4a1b2` plus the recorded author modifications.
- nlohmann/json: retain `backend/licenses/LICENSE-jsonhpp` and the notices in its source/header.
- xxHash: BSD-2-Clause; `backend/vendor/hash/xxhash/LICENSE`.
- rotate-bits: MIT; retain `backend/vendor/hash/rotate-bits/LICENSE.md`.
- SHA256: public-domain notice; retain `backend/vendor/hash/sha256/LICENSE`.
- cpp-httplib: MIT; `backend/vendor/cpp-httplib/LICENSE` (not used by the minimal CPU build).
- miniaudio: dual public-domain / MIT No Attribution notices retained in `backend/vendor/miniaudio/miniaudio.h`.
- stb: dual MIT / public-domain notices retained in its headers, including `backend/vendor/stb/stb_image.h`.
- sheredom/subprocess: Unlicense/public-domain dedication retained in `backend/vendor/sheredom/subprocess.h`.
- Other vendored/embedded components: original notices remain in their files; review them before selecting or modifying a release subset.

No NVIDIA headers/libraries are included. Do not copy audit-machine SDK files into a public package. System OpenMP, libcrypto and CUDA dependencies remain separately installed dependencies with their respective terms.

## Excluded optional backends

`backend/ggml/src/ggml-sycl/` and `backend/ggml/src/ggml-openvino/` have been removed from this CPU/CUDA-only candidate. SYCL Apache-2.0 WITH LLVM-exception sources and OpenVINO Apache-2.0 sources are not distributed here. `EXCLUDED_BACKENDS.json` retains only their paths and source hashes for audit. Do not enable `GGML_SYCL` or `GGML_OPENVINO`; those backends are unsupported in this subset. Original source archives remain unchanged.

- Embedded Abseil C++11 integer-sequence fallback in `backend/vendor/nlohmann/json.hpp`, between its explicit Google Abseil markers: Apache-2.0, Copyright 2017 The Abseil Authors. Fixed upstream source is `abseil/abseil-cpp@10cb35e459f5ecca5b2ff107635da0bfa41011b4:absl/utility/utility.h`. Full license `licenses/Apache-2.0.txt`; component notice `licenses/Abseil-NOTICE.txt`. This obligation remains for source distribution even when the C++17 build excludes that fallback. The full standard license text was copied from the audit host's common-licenses Apache-2.0 file, not from an SDK.
