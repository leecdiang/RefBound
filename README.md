# RefBound

**Research software and reproducibility artifacts for [Recovering Parallelism under Fixed Numerical References in Quantized LLM Decoders](https://arxiv.org/abs/2610.03228).**

RefBound collects reference-preserving P4 source, saved-measurement statistical reconstruction, and the editable figures and manuscript. It makes the numerical source and the evidence behind the paper inspectable, while keeping model weights and original prompt/state payloads out of the distribution.

## Start here

| Workflow | Command from repository root | Result |
|---|---|---|
| Reconstruct reported statistics | `python reproduce/scripts/reproduce.py` | `reproduce/results/recomputed.json` |
| Rebuild the CPU core and test state logic | `python runtime/scripts/build_cpu.py --out /absolute/new-cpu-build --jobs 2` | Static libraries, actual P4 frontend objects, test logs |
| Rebuild figures and paper | `python paper/build.py --output /absolute/new-paper-build` | 8 formal figures, 27 tables and a 33-page paper |
| Verify distributed files | `python verify.py` | Complete release manifest verification |

Use new output directories outside the repository. Install the dependencies described in each component first: NumPy for statistics; CMake, Ninja, C++17 and OpenMP for the CPU build; the pinned figure dependencies, pypdf and a full TeX Live/acmart font environment for the paper. Commands do not download models or initialize a GPU. Optimized Python (`-O`/`-OO`) is rejected by scientific verification entry points.

## Verified capabilities

- **Statistics:** reconstruct saved A5000/RTX estimates and intervals, M1 point estimates, and 27 historical contrast / 474 root estimates. Adverse outcomes and excluded request roles are retained. See [scope](reproduce/SCOPE.md).
- **Source:** the recovered numerical transformation chain matches four archived P4 core-file hashes. A clean CPU build completed all 216 build steps; the real P4 frontend compiled to objects; transaction and 257,082 draft-work tests passed.
- **Graphics and manuscript:** the full entry point regenerates 8 formal PDFs and 27 native TeX tables byte-for-byte against the frozen author manuscript, then builds its 33-page PDF. The checked rendering matches all frozen author pages at 144 DPI; this is not a PDF byte-identity claim.

### Validation boundary

CUDA compilation, the complete worker link and GPU numerical qualification have **not** been completed for a new deployment. This is a research source and reproducibility release, not a validated general-purpose inference server or an install-and-run GPU runtime. Archived timings are not performance measurements of a newly compiled binary. Reconstructing saved statistics/figures does not rerun the original model experiments; the figure generator also uses frozen statistical sidecars. Historical M1 99% intervals are not independently re-bootstrapped by the statistics script.

## Contents

- [runtime/](runtime/): recovered P4 implementation, numerical patches, model-free tests, CPU build and CUDA remaining steps.
- [reproduce/](reproduce/): minimized scalar measurements, frozen bootstrap draws, estimators and reference checks.
- [paper/](paper/): frozen author manuscript, editable plotting scripts, native tables, template sources, and isolated full-chain builder.
- [Evidence map](docs/EVIDENCE_MAP.md): paper anchors, statistics outputs and their exact scope.
- [Licensing](LICENSE.md): MIT author software; CC BY 4.0 author text/figures/data; third-party exceptions preserved.

## Provenance and citation

This release is based on frozen research artifacts. Original-source hashes remain distinct from public derived-file hashes. Some historical links inside the frozen manuscript and provenance point to the original private HeteroSpec repository; all required inputs for the workflows above are included here. Those links are historical identifiers, not required downloads. The submitted arXiv manuscript is not changed by this software release.

Please cite Chengzhan Li, *Recovering Parallelism under Fixed Numerical References in Quantized LLM Decoders*, arXiv:2610.03228, and identify the RefBound commit used. No journal acceptance or DOI is implied.
