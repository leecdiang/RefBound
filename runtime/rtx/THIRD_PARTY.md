# Third-party dependencies

The author's worker and packaging source retain the [MIT notice](LICENSE). The four-file native patch includes llama.cpp and ggml context and retains the [upstream MIT notice](LICENSE-LLAMA.txt). The pinned upstream source archive is downloaded separately. Its original license files and embedded notices remain in that archive and the materialized source tree.

The worker uses nlohmann JSON from the pinned upstream archive. See the [nlohmann notice](LICENSE-JSONHPP.txt), [Apache-2.0 license](licenses/Apache-2.0.txt) and [Abseil notice](licenses/Abseil-NOTICE.txt) for its retained fallback.

MSVC, the Windows SDK, CMake, Ninja, Git, Python, NumPy, CUDA and CUPTI are separate dependencies. This component distributes source and evidence records. It contains no SDK, compiler, binary dependency, model or dataset. The author-owned documentation and released measurement derivatives use the repository's [documentation and data license](../../LICENSE.md).
