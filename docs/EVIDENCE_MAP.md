# Evidence-to-output map

Follow a result from the bundled manuscript to its released inputs and reconstructed values. This map uses semantic LaTeX labels and source filenames, which remain useful when typesetting changes page or figure numbers.

[Artifact guide](README.md) · [Statistics](../reproduce/README.md) · [Figures and paper](../paper/README.md)

## Statistical reconstruction

Run `python3 reproduce/scripts/reproduce.py` from the repository root. All output fields below are in `reproduce/results/recomputed.json`; input paths are relative to `reproduce/`.

| Paper anchor / source | Released input | Recomputed output | Coverage |
| --- | --- | --- | --- |
| `fig:confirmation`, `f07_confirmation`; `tab:confirmation-effects`, `s14_confirmation_effects` | `data/a5000_confirmation.csv` | `a5000.negative`, `.positive`, `.interaction`, `.C0`, `.C1`, `.equal_conversation_overall` | All six point estimates and individual 95% intervals. The historical labels `negative` and `positive` mean the fixed noncrossing and crossing cases, respectively; they describe cases rather than outcome selection. |
| `fig:c4`; `tab:rtx269-effects`, `s18_rtx269_effects` | `data/rtx_confirmation.csv`, `data/rtx_bootstrap_indices.jsonl` | `rtx["C1/B"]`, `["C4/C1"]`, `["C4/B"]` | Aggregate complete-request ratios and crossed-bootstrap 95% intervals. The plotting package supplies the root and phase panels. |
| RTX request-role register and eligibility discussion | `data/rtx_request_roles.csv` | `rtx_roles` | The full released 1,764-row role register, including the 864 formal timing observations. |
| `tab:m1`, `t05_m1` | `data/m1_requests.csv` | `m1.arm_total_s`, `.contrasts`, `.interaction_ratio`, `.negative_root_counts` | Four-arm totals, direct total ratios and the separate root-geometric interaction. Historical simultaneous 99% intervals remain reference metadata. Printed physical-call counts use separate paper inputs. |
| Historical direct comparisons, including study #257 P4 results | `data/prior_pairs.csv` | `prior_contrasts`, `prior_root_estimates`, `prior_reference_checks` | 27 contrast and 474 root point estimates. Historical intervals remain reference metadata. The 1,134 contrast rows reuse requests; CodeContests/train/279's adverse SD_P4/TO_P4 result is retained. |

## Figures and manuscript inputs

The public [paper builder](../paper/README.md) regenerates all eight formal figures and 27 native tables from its included inputs. The [figure guide](../paper/figures/README.md) also covers the three editable alternatives. These inputs include frozen statistical sidecars as well as the scalar-reconstruction route above.

| Material | Public source and identity record |
| --- | --- |
| Plotting values, request derivatives and statistical sidecars | [`paper/figures/inputs/scientific_data/`](../paper/figures/inputs/scientific_data/) and its [`MANIFEST.json`](../paper/figures/inputs/scientific_data/MANIFEST.json) |
| Selected fields and transformations for the three native CSV derivatives | [`paper/DATA_MINIMIZATION.json`](../paper/DATA_MINIMIZATION.json) |
| Statistical derivative identities and estimator origins | [`reproduce/SOURCE_MAP.json`](../reproduce/SOURCE_MAP.json) |
| Figure outputs and recorded regeneration checks | [`paper/figures/proof/REBUILD_REPORT.json`](../paper/figures/proof/REBUILD_REPORT.json) |
| Bundled figure/manuscript files | [`paper/DELIVERY_MANIFEST.json`](../paper/DELIVERY_MANIFEST.json), also bound by the root [`RELEASE_MANIFEST.json`](../RELEASE_MANIFEST.json) |

## Read each result at its recorded scope

- `fig:constraints` and `fig:construction` explain mechanisms. Scalar statistics reconstruct timing results; full numerical-agreement records belong to the corresponding execution and qualification evidence.
- `fig:local` uses the original two-repeat LOCAL transactions. The later 12-block A5000 confirmation is a separate study.
- Figure regeneration uses the specified frozen inputs and checks the rendered values and encodings. Only the intervals identified in the statistics table above are recomputed by the scalar entry point.
- The released runtime implements the P4 application frontend. LOCAL's two-history diagnostic frontend has separate implementation and qualification records.

See the [artifact guide](README.md) for manuscript versions, historical provenance labels and the distinction between saved-artifact reconstruction and original model execution.
