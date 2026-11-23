# A5000 LOCAL artifact

The component uses the two-history frontend from the A5000 confirmation study. The released source follows the SIMPLE and LOCAL execution choices through owned score rows, acceptance, trim/commit and each arm's own next transaction. See the [build and replay guide](../runtime/local/README.md) and [component manifest](../runtime/local/MANIFEST.json).

## Claim map

The manuscript source was checked at HeteroSpec #309 commit `fc32d1af7dc0eac36c8d6dfc5709b0daaf3fb077`. References to qualification commits bind archived evidence and do not grant access to private material.

| Manuscript anchor | Public evidence and check | Original evidence retained separately |
| --- | --- | --- |
| Implementation and `fig:construction` | [Diagnostic implementation](../runtime/local/src/local_replay.inc), [phase planner](../runtime/local/src/inherited/phase_plan.hpp), and [backend graph reuse guard](../runtime/backend/src/llama-graph.cpp) show ordered extents, ownership, trim, and reuse. The same maximum extent of 512 does not override an ordered vector change. The [two-history trace](../runtime/local/evidence/TWO_HISTORIES.json) and quick check cover both observed outcomes. | Full receipts and original dispatch capture, bound to the frozen source and binaries. |
| `tab:qualification-details` and `tab:access` | [Object index](../runtime/local/evidence/CROSSING_OBJECTS.json) gives shapes, finite-value status, per-object hashes, and comparisons across all five active-KV checkpoints. The checker can compare the full payloads and verify the own-successor chain when supplied the authorized original captures. | Complete F32 and F16 payloads, exact token inputs and oracle build identity. On the original A5000, the three-arm qualification covered 18 candidate/reference F32 pairs, 10 candidate/reference active KV pairs, 42 same-arm historical objects and 12 retained prefixes. All 82 were byte equal under the recorded comparisons. |
| `fig:local` and the original diagnostic `tab:local-pairs` | The two-history artifact explains the execution geometry and work accounting. The original two-repeat diagnostic measurements are supplied by the existing paper plotting inputs. | Original diagnostic capture and device traces. The diagnostic clocks belong to that two-repeat study. |
| `fig:confirmation`, `tab:confirmation-effects`, and `tab:confirmation-pairs` | [Public statistical reconstruction](../reproduce/README.md) recomputes the fixed-pair effects from 12 matched time blocks. The supporting crossing is **21.56%** [20.21%, 22.83%] and the primary noncrossing control is **0.43%** [−1.13%, 2.01%], both for verify through commit. | Full original service and capture records remain under their existing access. These fixed-transaction estimates do not include a complete serving request. |

## Data access

| Class | Included |
| --- | --- |
| Public source | Author's diagnostic frontend, unmodified saved CPU fixture sources, build/test scripts and local capture reader. The existing CUDA core is reused with its original notices. |
| Public record | Frozen profile, public benchmark identifier, source/model/binary identities and build validation. |
| Redacted derivative | Two-history receipts restricted to extents, geometry and work counters. Complete-object derivative restricted to shape, finite status, hashes and recorded comparisons. |
| Private | Raw benchmark text and token sequences, frozen proposal stream, full logits/KV, weights, original ELF and host logs, and raw profiler captures. |

The public quick route verifies the released metadata without a model. The private readback route independently checks saved bytes and the fixed consumer chain. The clean public-source build is a separate identity from the previously qualified ELF. It adds compilation and fixture evidence. The original A5000 numerical capture supports the fixed case under its recorded identities. The manuscript's timing claims use the previously frozen measurements.
