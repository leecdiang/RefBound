# Scientific data: per-round values, roles and estimators

This index links the directly readable timing observations and derived scientific
summaries accompanying the reconstructed paper. All eligible observations are retained,
including unfavorable pairs, roots and time blocks. Original experiments remain
unchanged. Data from different studies are not pooled.

This ZIP contains directly readable scientific data and metadata. It does not
run experiments. Four source files were copied byte for byte from already
verified saved inputs; their exact hashes and original locations are in
[SOURCES.json](artifact/scientific_data/SOURCES.json). The other timing tables
and summaries are the saved outputs of the current CPU reconstructions. Full
reader source, larger evidence packets and detailed review receipts remain in
the companion paper artifact.

## Directly readable observations

|Study / scientific purpose|Every-round or every-block data|Rows and interpretation|
|---|---|---|
|RTX #269: scalar organization and compatible few-column execution|[NATIVE_FORMAL_TIMES.csv](statistics/rtx269_recomputed/NATIVE_FORMAL_TIMES.csv)|864 eligible arm observations: 24 roots × 12 rounds × B/C1/C4; service and every phase in seconds. `round` is 0–11, `time_block` 0–5, with two rounds per root/block.|
|RTX #269: full role/exclusion record|[RTX269_ALL_REQUESTS.csv](artifact/scientific_data/RTX269_ALL_REQUESTS.csv)|1,764 unchanged public rows, including warmups, qualification and 12 resource-excluded requests. This is an exact packet member, not a new experiment.|
|A5000 #266: LOCAL selected transaction and separate natural service|[INDEPENDENT_NATIVE_VALUES.csv](statistics/confirmation266_recomputed/INDEPENDENT_NATIVE_VALUES.csv)|96 formal arm values: 48 in Panel A and 48 in B. Columns are panel, block (1–12), case, arm and seconds. The pairing gives 48 candidate/control pairs.|
|A5000 #266: all pairs, roles and complete endpoint summaries|[confirmation266_data.json](statistics/confirmation266_recomputed/confirmation266_data.json)|`pairs` retains all 48 paired observations and request identities; `measured` retains formal records; `results` contains all six endpoints with block log ratios.|
|Earlier independent complete-request studies #247/#248/#251/#254/#255/#256/#257/#259|[paired_request_times.csv](statistics/prior_studies_recomputed/estimates/paired_request_times.csv)|1,134 **contrast-level** records across 27 direct comparisons. Fields retain study PR, contrast, root, domain, round, control seconds, candidate seconds and ratio. A request reused by several contrasts appears several times; these rows are not 1,134 independent requests.|
|Workload metadata for those request studies|[workload_roots.csv](statistics/prior_studies_recomputed/estimates/workload_roots.csv)|134 study/root entries with input length, output convention and recorded stop metadata. Repeated root names across studies do not merge their references or observations.|
|Original LOCAL #260: all first transactions and dependent successors|[all_point_estimates_and_intervals.json](statistics/prior_studies_recomputed/all_point_estimates_and_intervals.json), key `LOCAL`|Eight paired measurements: two histories × two repeats × first/successor. Each pair exposes both arm times in **milliseconds** and the ratio. Successors are dependent state evidence.|
|M1: all native session values and primer roles|[M1_NATIVE_REQUESTS.csv](artifact/scientific_data/M1_NATIVE_REQUESTS.csv)|288 unchanged rows: 256 measurements (16 roots × four sessions × four arms) and 32 primers. `kind=measurement` selects formal observations; service/request/reset fields are seconds.|
|Original natural RTX LOCAL/WHOLE panel|[all_point_estimates_and_intervals.json](statistics/prior_studies_recomputed/all_point_estimates_and_intervals.json), key `natural_service.historical_RTX.pairs`|Every one of the 12 pairs: four roots × three sessions, with LOCAL/WHOLE seconds and ratios.|
|Original natural A5000 8B two-turn panel|[NATURAL_8B_EPISODES.json](artifact/scientific_data/NATURAL_8B_EPISODES.json)|22 unchanged role-specific episodes; `stage=MEASURE` selects eight formal arm episodes (two conversations × two rounds × L/W). Complete controller response-plus-reset times and constituent phases remain in seconds.|
|Historical shared-preparation scalar S3|[S3_TIMING_ROWS.csv](artifact/scientific_data/S3_TIMING_ROWS.csv)|288 unchanged rows: 144 measured and 144 warm across R1/R2/H1; each panel keeps its root, round, arm, role and original timing fields.|

The complete RTX eligibility predicate is `included=True`, `stage=formal`,
`role=measured`. A qualification row can itself say `role=measured`; ignoring
`stage` would incorrectly include it. The two excluded RTX units each contain
six requests (one qualification unit and one formal root-round unit), retained
with their original technical replacement disposition. A5000 #266 has no
replacement or failure; its 12 qualifications, 96 warmups, 96 formal observations
and eight diagnostics remain distinct. Scientific eligibility, failure and stop
rules are also retained in Supplement Sections “Eligibility, technical failures
and scientific stops” and “RTX confirmation after shared activation preparation.”

## Effects, root/block summaries and statistical roles

|Study|Summary file / key|Estimator and role|
|---|---|---|
|RTX #269|[figure_data.json](statistics/rtx269_recomputed/figure_data.json): `estimates`, `roots`, `blocks`, `dispatch`|C1/B is the **sole prespecified primary**; C4/C1 and C4/B are prespecified descriptive secondary comparisons. Average the two paired log ratios within a root/block, then give 24 roots and six blocks equal weight. The 10,000 frozen draws independently resample code/math-stratified roots and whole time blocks. Crossed 95% intervals are primary; root-only intervals condition on the six observed blocks.|
|A5000 #266 A|[confirmation266_data.json](statistics/confirmation266_recomputed/confirmation266_data.json): `results.A`|Noncrossing is primary; crossing and interaction supporting. Direct effects average paired log ratios over 12 blocks. Interaction averages crossing-minus-noncrossing log ratios; it is a ratio of ratios.|
|A5000 #266 B|Same file, `results.B`|Equal-conversation overall is primary; C0 and C1 supporting. Within each block, give the two fixed conversations equal log weight, then average blocks. Ten thousand joint whole-block draws, seed 20261117, individual 95% percentile intervals.|
|Earlier modern C4/P4/B570 studies|[all_point_estimates_and_intervals.json](statistics/prior_studies_recomputed/all_point_estimates_and_intervals.json): `modern_effects`|Average paired log ratios over rounds within a root, then give roots equal weight. Ten thousand whole-root bootstrap draws within code/math strata; individual 95% intervals. Seeds are 20261117 for A5000 C4 and 20261116 for the other modern panels. Two-root pilot/selected-transaction panels retain their descriptive roles.|
|M1|Same file, `M1.contrasts`, `M1.interaction`, `M1.census`|Direct effects are ratios of service totals, retaining all four sessions within each root. The interaction is the geometric mean of per-root ratios of ratios. Ten thousand paired-root draws, seed 19720261107, with 99% marginal intervals in the five-comparison Bonferroni family.|
|Original natural panels|Same file, `natural_service`|Historical RTX: geometric mean of balanced paired native-service ratios. Historical A5000 8B: ratio of total controller response-plus-reset time. These are not additional samples for #266 or selected 32B LOCAL.|

For a candidate/control time ratio `r`, time reduction is `100 × (1 − r)` percent.
A positive reduction means lower candidate time. Transform a ratio interval
`[lo, hi]` into `[100(1 − hi), 100(1 − lo)]`; the endpoint order reverses.
Arithmetic phase differences have a different estimand from geometric effects
and are not added to percentages. Table 6 uses this same
reduction convention and preserves all block directions in the pair file.

## Clock and treatment bindings

- **LOCAL #260 and #266 A:** selected 32B verification through trim/commit and
  synchronization, including owned-row copies and decisions; C4 on, P4 off,
  frozen proposals. History preparation and live drafting are outside that clock.
- **RTX #269 and independent CUDA C4/P4 requests:** complete resident request,
  including reset, prefill, target work, live drafting when present, output
  handling, decisions, commit and final synchronization. Loading/context-pool
  setup and post-clock exports are excluded. B/C1/C4 use SIMPLE and P4 off.
- **A5000 #266 B:** two-turn target-only response plus reset, including common
  CPU sampling and control; two fixed 8B conversations at C4096, cap128 per turn.
- **M1:** original native-service clock and historical WHOLE/LOCAL × loop4/packed
  names. These factors are not relabeled modern C4/P4.
- **B570 formal:** compute plus normal teardown, with intervening endpoint
  export/hash excluded; CPU draft. The Vulkan-draft placement pilot is separate.

RTX C4 also has a q3 prefill tail: 2,652 prefill admissions accompany 2,273,400
verification admissions. A5000 P4's 232 P4-entering application calls are q32 in
one physical extent. Separate q16/q24 qualification is numerical coverage, not
additional application timing. These bindings prevent a C4→P4→LOCAL cumulative
interpretation or strict verifier-only attribution.

## Diagnostics and earlier historical summaries

[plot_data.json](data/plot_data.json) retains the original LOCAL device-event
diagnostics, initial two-repeat arm times, same-study stage costs and associated
role counts. Its device-event clock is separate from clean LOCAL transaction
wall time.

[historical_evidence.json](data/history/historical_evidence.json) and its
[SOURCE_MANIFEST.json](data/history/SOURCE_MANIFEST.json) retain the earlier
geometry, application, natural and worker-lifetime register, including slower
LOCAL cells and adverse application/worker results. These older register entries
retain their original summary and source-binding granularity. This visual-reconstruction
revision does not claim to reconstruct every individual native receipt behind
those additional historical summaries. The original sources remain linked; no
new values are invented to fill an unreported field.

## Package verification and scope

`MANIFEST.json` lists every data/document payload, its byte size, SHA-256 and ZIP
CRC-32. The manifest excludes itself. The separately delivered
`SCIENTIFIC_DATA_MANIFEST.json` additionally identifies the complete ZIP and
its internal manifest. ZIP timestamps and file modes are fixed so the packaging
script can reproduce identical bytes from identical saved sources.

All local links in this README resolve within this ZIP. The full artifact keeps
this package builder in `scripts/package_scientific_data.py`. No statistical
estimator, bootstrap, model or GPU is executed by packaging. Existing source
records and output summaries are not altered.

The sidecar preserves every measured direction and repeated timing observation
in the reconstructed studies, including M1 sessions, original LOCAL dependent
successors and excluded RTX role records. Older additional historical entries
retain their available source-bound summary granularity as described above.
Reproducing all bootstrap draws requires the frozen index files and source
packets in the full artifact; this data sidecar is not a full numerical-tensor
backup or model replay package.
