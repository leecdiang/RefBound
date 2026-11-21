# Statistical reconstruction

Reconstruct the saved-measurement results for **Recovering Parallelism under Fixed Numerical References in Quantized LLM Decoders**. This component includes the scalar records, fixed bootstrap draws, estimators and reference values needed by its public entry point.

[Repository home](../README.md) · [Artifact guide](../docs/README.md) · [Evidence map](../docs/EVIDENCE_MAP.md) · [Detailed scope](SCOPE.md)

## Quick start

From the repository root, in your Python environment:

```sh
python -m pip install -r reproduce/requirements.txt
python reproduce/scripts/reproduce.py
```

Python **3.12** and NumPy **2.3.5** were tested. Install dependencies before running offline. Run without `-O`, `-OO` or `PYTHONOPTIMIZE`; the entry point rejects optimized Python because its integrity and scientific-reference checks use assertions.

## Outputs and checks

The script reads local files, validates pinned input hashes and writes `reproduce/results/recomputed.json`. It checks grouping and cardinality, retains adverse outcomes and excluded request roles, and fails if reconstructed reference values differ beyond the documented tolerance. A successful run prints `PASS` and the maximum reference error.

The output records point estimates, the specified recomputed intervals, counts, comparison checks, and Python/NumPy versions. No model or accelerator is required. The generated JSON is ignored by Git; the frozen inputs and expectations remain in place.

## Results and units

| Study | Released observations | Reconstructed result |
| --- | --- | --- |
| **A5000 confirmation** | 96 scalar arm values, 48 matched pairs, 12 time blocks | Four case effects, crossing/noncrossing interaction and equal-conversation 8B effect; 10,000 whole-block bootstrap draws, seed 20261117 |
| **RTX confirmation** | 864 formal observations: 24 roots × 12 rounds × 3 arms; separate 1,764-row role register | C1/B, C4/C1 and C4/B with equal-root/equal-block log ratios and 10,000 frozen crossed-bootstrap index draws |
| **Prior studies** | 1,134 contrast-level paired rows, including unfavorable roots | All 27 contrast and 474 per-root point estimates, checked against frozen historical references |
| **M1** | 256 measured requests and 32 excluded primers | Four arm totals, original direct ratios of totals and the separate root-geometric interaction |

A time ratio below one favors the candidate. Time reduction is `100 × (1 − ratio)`; timing values are seconds. Prior-study rows reuse requests across contrasts. Preserve each study's sampling unit and estimator when using these records.

A5000 and RTX intervals listed above are reconstructed. Prior-study intervals and M1's simultaneous 99% intervals remain frozen reference metadata in `data/expected.json`. [SCOPE.md](SCOPE.md) describes the distinction and the retained data fields.

## Related public components

- [`../paper/`](../paper/README.md) regenerates the editable graphics, native tables and bundled 33-page manuscript using its separately bound inputs and statistical sidecars.
- [`../runtime/`](../runtime/README.md) contains the P4 source, CPU build and state checks, plus CUDA build stages.
- [`../docs/EVIDENCE_MAP.md`](../docs/EVIDENCE_MAP.md) connects manuscript anchors to this script's JSON fields and the paper's plotting inputs.

This workflow reconstructs statistics from saved scalar measurements. Original model runs, full vocabulary/KV payloads and original-machine state are separate evidence. `SOURCE_MAP.json` binds the released derivatives to historical input identities; those private source identifiers are provenance labels, not required downloads.

## Licensing and attribution

Author reconstruction code uses MIT (`LICENSE`). Author measurements, bootstrap index arrays and derived statistics use CC BY 4.0 (`licenses/CC-BY-4.0.txt`). Attribute Chengzhan Li and the paper, retain study identifiers and describe modifications. Benchmark identifiers are included; benchmark question text and solutions are not. Third-party model, benchmark and runtime terms remain unchanged; NumPy is an external dependency. See the [repository license guide](../LICENSE.md).
