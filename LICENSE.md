# RefBound licensing

Copyright (c) 2026 Chengzhan Li, for original author contributions.

- Original software and packaging scripts: [MIT](licenses/MIT.txt).
- Author-owned paper text, figures, tables, documentation and released measurements/data arrangement: [CC BY 4.0](licenses/CC-BY-4.0.txt). Attribute Chengzhan Li and the paper/project, and indicate modifications.
- This grant covers only rights held by the author. It does not relicense benchmark datasets (including MATH, CodeContests and OASST), model weights, cited publications, or third-party source. No benchmark question/answer text or model weights are bundled.
- llama.cpp/ggml and other third-party code retain their notices; consult runtime/THIRD_PARTY.md and runtime/LICENSE_SCOPE.md. This includes MIT, BSD-2-Clause and the retained Apache-2.0 Abseil portion.
- The ACM acmart class/source is LPPL 1.3 or later; ACM-Reference-Format.bst declares public domain. Their original notices and template source are retained in paper/. DejaVu font terms are retained in paper/figures/typography/LICENSE_DEJAVU.

No blanket MIT license applies to this repository. References to original private source identities are provenance, not grants of access or rights over those separate materials.

## Embedded source excerpts

Code excerpts embedded in `paper/figures/method/inputs/*.json` retain their source-code licenses; the JSON container does not relicense them as data. In particular, llama/ggml-derived excerpts from `llama-graph.cpp`, `mmvq.cu` and `ggml-cuda.cu` retain the upstream MIT notice in `runtime/backend/LICENSE`. Consult the adjacent source maps and `runtime/THIRD_PARTY.md` for origin and other exceptions. CC BY 4.0 applies to author-owned graphical metadata and results, not to upstream program text.
