# HeteroSpec: CPU Reproducibility Companion

Reconstruct the saved-measurement results for **Recovering Parallelism under Fixed Numerical References in Quantized LLM Decoders**. This independent, self-contained companion does not require access to the private research repository.

## Quick start

Python 3.12 and NumPy 2.3.5 were tested. Install `requirements.txt` in your own environment before going offline, then run:

```sh
python scripts/reproduce.py
```

The command reads only local files, validates the pinned input hashes, writes `results/recomputed.json`, and fails if reconstructed reference values differ beyond the documented tolerance. No model download, accelerator, external service, shell command or private repository access is used. The checked package contains all data used by this command.

## Results and units

- A5000 confirmation: 96 scalar arm values, 48 matched pairs, 12 time blocks. Reconstructs four case effects, the crossing/noncrossing interaction, and the equal-conversation 8B effect; 10,000 whole-block bootstrap samples, seed 20261117.
- RTX confirmation: 864 formal observations (24 roots × 12 rounds × three arms). Reconstructs C1/B, C4/C1 and C4/B using equal-root/equal-block log ratios and the 10,000 frozen crossed-bootstrap root/block index draws. The separate 1,764-row role register retains exclusions and nonformal roles; they are not silently mixed into timing estimates.
- Prior studies: all 1,134 contrast-level paired rows retained, including negative roots. Reconstructs and checks all 474 per-root and all 27 equal-root geometric contrast point estimates against the frozen historical reference. These rows reuse requests across contrasts and are not 1,134 independent requests. Historical confidence intervals are not newly bootstrapped by this release.
- M1: all 256 measured requests plus 32 excluded primers retained. Reconstructs four arm totals, original direct ratios of totals and the root-geometric interaction. Its historical simultaneous 99% intervals are retained in `expected.json` as reference metadata, not independently regenerated here.

A timing ratio below one means less time for the candidate. Reduction is `100 × (1 − ratio)`, not throughput speedup. Timing values are seconds. Within-study sampling units are preserved. Do not add improvements from different studies into a cumulative speedup claim.

## Evidence levels

This release reproduces arithmetic and specified confidence intervals **from saved scalar measurements**. The immutable raw source-archive digest and per-file mappings are in `SOURCE_MAP.json`; the necessary released derivatives are included locally. Private source commit identifiers are provenance labels, not public access links.

It does **not** perform a new GPU run, validate a newly compiled decoder, compare full vocabulary/KV payloads, or recover an entire original machine. Model weights, binaries, full KV/vector archives, native source capsules, original prompt/question text, generated token sequences, private paths and machine/context identifiers are not distributed. A researcher cannot recreate the full GPU experiment from this package alone. The original implementation/source-build mapping register is not independently reproducible from this statistics-only release.

The paper's complete graphics and manuscript build are not included in this minimal release. Their separate internal clean-build checks do not substitute for a public, standalone graphics release. This package is deliberately a statistics companion, not a claim that every artifact promised in the manuscript is already publicly available. See `SCOPE.md` for remaining work.

## Licensing and attribution

Author-owned reconstruction code: MIT (`LICENSE`). Author-owned measurements, bootstrap index arrays and derived statistics: CC BY 4.0 (`licenses/CC-BY-4.0.txt`). Attribute Chengzhan Li, HeteroSpec (2026), retain study identifiers and describe modifications. Third-party model, benchmark and runtime licenses are not overridden. Only benchmark identifiers are included, not benchmark question text or solutions. NumPy is an external dependency, not vendored here.

This release is a documented derivative of frozen author records. It removes nonessential identity columns but changes no retained measurement or unfavorable observation. Original frozen records are not rewritten. No publication acceptance or peer review is implied.

### Python optimization safety

Run the reconstruction without `-O`, `-OO`, or `PYTHONOPTIMIZE`. The entry point explicitly rejects optimized Python before reading data or producing results, because its integrity and scientific-reference checks use assertions.
