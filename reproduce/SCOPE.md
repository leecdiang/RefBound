# Statistical reconstruction scope

[Statistics guide](README.md) · [Artifact guide](../docs/README.md) · [Evidence map](../docs/EVIDENCE_MAP.md)

## Included and tested

The local-source map binds five CSV datasets and one bootstrap draw file to frozen original member hashes. All selected rows are retained; only explicitly enumerated nonessential columns were removed. Complete A5000 case outcomes, RTX request roles/exclusion reason, M1 primers and prior negative effects are retained. Verification includes reference equality at 2e-10 tolerance, grouping/cardinality assertions and retained adverse cells. All 27 historical contrast point estimates and all 474 root estimates are additionally checked against the independently frozen historical reference. The observed maximum discrepancy is recorded in validation/AUDIT.json.

## Not included or not newly validated

1. Original model/GPU experiments and full numerical-state equality. Exact models, runtimes and large captured states are not in this release.
2. Full historical raw-request and failure archives. The published RTX role register retains every row and exclusion; M1 retains primers. This does not claim comprehensive public raw records for every historical study.
3. Independent re-bootstrap of M1 simultaneous 99% intervals or all prior-study intervals.
4. This statistics component does not generate graphics or rebuild the decoder. Separately reviewed `../paper/` and `../runtime/` provide those workflows, with their own explicit verification scope.
5. Repository source hashes identify origins in the research archive. Included data are available without access to that archive. The public implementation's source/build register, toolchain instructions and licenses are in `../runtime/`; its validation scope is separate from statistical reconstruction.

## Data transformations

A5000 scalar table, RTX formal timings and historical pairs retain every original column. M1 omits native receipt hash and reference identity. RTX all-request register retains grouping/roles/order/exclusion and basic timing/work fields, but omits request scheduling identifiers, private core identity, prompt fingerprints and auxiliary phase fields already represented in the formal timing table. SOURCE_MAP.json lists exact retained and removed columns; original member hashes identify the untouched original inputs.

No model data or prompt text were used to construct this package. No conclusion, sign, root or eligible numerical observation was selected for publication based on whether it was favorable.
