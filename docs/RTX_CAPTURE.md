# RTX C1/C4 artifact and claim map

The archived qualification used the same instrumented worker and CUDA backend for one C1/C4 pair on the GeForce RTX 5070 Ti Laptop GPU. CodeContests/test/124 was fixed at 757 input tokens and P4 was off. The frozen manuscript evidence is HeteroSpec PR #309 at `fc32d1af7dc0eac36c8d6dfc5709b0daaf3fb077`. The public artifact baseline is `58697de93d86fc39c105bdfb8d8c0fd2949f192c`. The exact capture binary, backend and model identities are recorded with the [source and capture commands](../runtime/rtx/README.md).

## Claim map

| Paper location | Public or redacted-derived evidence | Local replay and private evidence |
| --- | --- | --- |
| Implementation, `sec:implementation`, q1 vs q4/q2 launch claim | C1 8,550 q1. C4 8,325 q4 plus 225 q2. Phase counts, observed build hashes, dispatch counters and correlation multiset hashes. | Build the collector and reacquire the fixed pair with local models and input. The CPU readers process decoded CUPTI records with request, API, phase and thread associations. Raw buffers, full event export and host scope files stay private. |
| Final device qualification, `tab:access` / `s08_access.tex` | For each arm, 75 intermediate active F16 KV objects, two terminal objects, one inactive draft marker, 174 independent q1 target F32 vectors and 37 own-successor links. Public rows carry sizes, canonical hashes, shape and comparison status. | Complete KV, F32, independent endpoint payloads and successor metadata remain local. The public reader uses local reference objects for exact byte, full-tensor and successor checks. |
| Numerical qualification supplement, `supp:access` | 246,252 associated kernels per arm with zero dropped or unassociated request records. Independent archive readback passes and is recorded separately from new device execution. | The archived event-level and full numerical objects remain on the original machine. Historical profiler and the previous run's 150 intermediate originals remain BLOCKED. |
| RTX confirmation supplement, `supp:rtx-confirmation` | The formal 864-request latency estimate remains in the existing [statistics artifact](../reproduce/README.md), with C1/B primary and C4/C1 and C4/B descriptive. | The capture pair supplies mechanism and numerical qualification. The fixed case has zero packed prefill admissions. The formal panel retains the separate q3 prefill-tail exposure. |

## Release inventory

| Class | Contents |
| --- | --- |
| Public source | Native worker, pinned upstream source recipe and patch, CUPTI collector/instrumenter, build scripts, local capture/review scripts, notices and synthetic CPU checks. |
| Public record | Platform and profile settings, fixed case identifier and input length, paper claim locations, command templates and release checks. |
| Redacted derived | SHA256 and sizes, aggregate dispatch and phase counts, checkpoint geometry, finite/byte-comparison status and successor generation counts. |
| Private | Benchmark question/answer and input IDs, output sequences, weights, compiled binaries, complete KV/F32 streams and references, raw CUPTI buffers and per-event records, credentials, host inventory and local paths. |

[Component manifest](../runtime/rtx/MANIFEST.json) · [Frozen summaries](../runtime/rtx/records/expected.json) · [Checkpoint rows](../runtime/rtx/records/kv-checkpoints.json) · [Release verification](../runtime/rtx/records/release-checks.json)
