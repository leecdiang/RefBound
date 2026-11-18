# Table design and scientific reading cards

Numbering follows the manuscript, not filenames. Old/new comparisons record the inherited design choice. Baseline pages refer to the pinned #276 author PDF, not the integrated manuscript's current pages. For input fields, checks and transforms see [`table_ledger.json`](table_ledger.json).

## Table 1 · Target-projection dispatch in three RTX paths

`tables/t01_dispatch.tex` · `tab:dispatch` · baseline #276 PDF p. 6

**Lookup.** Compare invocations and columns per group for B, C1 and C4; the last row describes the shared preparation. Read across one MMVQ operation only.

**Unit, clock and method.** One examined MMVQ operation after identical Q8_1 activation preparation. The invocation counts describe dispatch organization, not a claimed count of physical GPU launches or request latency.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** Target-projection dispatch in the independent RTX B/C1/C4 studies. All three paths begin after the same Q8\_1 activation preparation; counts refer to one examined MMVQ operation.

## Table 2 · Numerical qualification of the bound CUDA paths

`tables/t02_qualification.tex` · `tab:qualification` · baseline #276 PDF p. 7

**Lookup.** Each row is a bound profile and the numerical objects actually exercised. The boundary column says what was not checked.

**Unit, clock and method.** Original-machine complete-object comparisons on the named CUDA profiles; saved public objects are a subset.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** Numerical qualification of the bound CUDA paths. These are original-machine complete-object checks; Table~\ref{tab:access} distinguishes the independently readable public subset.

## Table 3 · Deployment profiles for the principal studies

`tables/t03_deployments.tex` · `tab:deployments` · baseline #276 PDF p. 8

**Lookup.** Rows bind a study to target/draft models, backend and placement. Context and execution settings are part of the row.

**Unit, clock and method.** Deployment register values. Context is C1024 except the noted C4096 case; model identities include quantization.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** Deployment profiles for the principal studies. Context is C1024 except A5000 confirmation B (C4096). The artifact deployment register binds compiler, driver, placement and model identities.

## Table 4 · Sampling and workload boundaries by study

`tables/t04_studies.tex` · `tab:studies` · baseline #276 PDF p. 9

**Lookup.** Follow one study row: roots, repeats, arms, input/output units and the number of measured observations. Footnotes mark dependent successors and clocks.

**Unit, clock and method.** Prompt or selected history tokens in; generated tokens or requested rows out. Rounds stay within root and time block.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** Sampling and workloads by independent study. Inputs are prompt tokens or selected LOCAL history lengths; outputs are generated tokens or requested rows. Repeated rounds remain within their root and time block. NR denotes an unreported field in the earlier RTX normalized table.

## Table 5 · M1 native service and direct effects

`tables/t05_m1.tex` · `tab:m1` · baseline #276 PDF p. 14

**Lookup.** Each projection row reports WHOLE/LOCAL native-service totals, the direct LOCAL/WHOLE time reduction, and its 99% interval side by side.

**Unit, clock and method.** Sixteen roots, four sessions per root, 64 measured requests per cell. Effects use sums over the same roots and sessions.

**Reading and limits.** The 20 removed calls per 2,224 logical cycles describe a 0.90% opportunity frequency, not a service speedup. Direct effects use ratios of totals; the root-geometric interaction is a separate estimand.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** M1 factorial: 16 roots and four sessions per root, with 64 measured requests per cell. Each projection row reports native-service totals and its direct LOCAL/WHOLE time reduction. Intervals are 99% marginal members of the five-comparison Bonferroni family; Table~\ref{tab:m1-family} retains the complete family.

## Table 6 · Natural 8B confirmation: effects and blocks

`tables/t07_confirmation_natural.tex` · `tab:confirmation-natural` · baseline #276 PDF p. 14

**Lookup.** The primary row weights the two fixed conversations equally. C0/C1 rows show direct effects and outer physical target invocations per two-turn episode; the counts are not per-layer projections or GPU kernels.

**Unit, clock and method.** Two fixed conversations and 12 paired time blocks. The complete two-turn response-plus-reset clock includes common consumer work. Native dispatch physical_calls and width histograms give C0 263/263 calls and 508/508 rows, C1 273/272 calls and 809/809 rows.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** Natural 8B target-only confirmation: effects and individual 95% whole-time-block intervals over two fixed conversations and 12 paired blocks. The primary estimate weights conversations equally within each block. All block values and direction counts remain in Section~\ref{supp:confirmation}.

## Table 7 · Reference selection and state handoff in related systems

`tables/t06_neighbors.tex` · `tab:neighbors` · baseline #276 PDF p. 16

**Lookup.** Read horizontally: what each system fixes, what it still lets vary, and where state passes to the consumer. This is a design comparison, not a measured ranking.

**Unit, clock and method.** Invariants and handoff contracts stated by the cited systems. No new measurement is introduced.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection keeps the original four-column design comparison and only repairs the citation wrap.

**Integrated caption.** Reference selection, retained execution freedom, and state handoff in the closest systems.

## Table S1 · Every original LOCAL pair, including successors

`tables/s01_local_pairs.tex` · `tab:local-pairs` · baseline #276 PDF p. 21

**Lookup.** Rows are clean verify-through-commit milliseconds; ratio is LOCAL/SIMPLE. A successor starts from its own arm’s commit and is not an independent repeat.

**Unit, clock and method.** One root, two histories and two paired repeats supply four first-transaction pairs; successors depend on their own first commit.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** Every original LOCAL pair, including successors from each arm's own committed state.

## Table S2 · Independent device-event diagnostics

`tables/s02_diagnostics.tex` · `tab:diagnostics` · baseline #276 PDF p. 21

**Lookup.** Each column is a separate profiler run. Event counts and event-clock milliseconds are not added to the wall clock.

**Unit, clock and method.** Independent profiler output for both selected first-transaction histories, Noncrossing (base 137) and Crossing (base 253); event counts and durations retain their own instrumentation clock.

**Reading and limits.** The profiler clock is not the transaction wall clock. Counts locate work; they do not apportion complete-request time.

**Old → new (Keep the values; tighten the lookup.).** Event counts and event-clock times remain separate; no wall-clock total is implied.

**Integrated caption.** Independent device-event diagnostics for the two first-transaction histories. Times and counts use the profiler's own clock.

## Table S3 · All six A5000 confirmation endpoints

`tables/s14_confirmation_effects.tex` · `tab:confirmation-effects` · baseline #276 PDF p. 22

**Lookup.** Six prespecified endpoints on the A5000 confirmation alone. The interaction is a ratio of ratios, not a time difference.

**Unit, clock and method.** A5000 confirmation: 12 joint time blocks, six endpoints, whole-block bootstrap intervals.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** All six A5000 confirmation endpoints and their prespecified roles. The interaction is a ratio of ratios.

## Table S4 · Every 32B confirmation pair

`tables/s15_confirmation_A.tex` · `tab:confirmation-a-pairs` · baseline #276 PDF p. 22

**Lookup.** Twelve paired time blocks for each 32B history. Times are milliseconds; ratios above one mean LOCAL took longer.

**Unit, clock and method.** Verification through trim/commit and synchronization with C4 on, P4 off and frozen proposals.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** Every 32B confirmation pair: first-transaction verification-through-commit milliseconds. Noncrossing is primary and crossing supporting.

## Table S5 · Every natural 8B confirmation pair

`tables/s16_confirmation_B.tex` · `tab:confirmation-b-pairs` · baseline #276 PDF p. 23

**Lookup.** Twelve paired blocks for each fixed conversation. Times are seconds; ratios above one mean LOCAL took longer.

**Unit, clock and method.** Two-turn response plus reset, including common CPU sampling and control.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** Every 8B confirmation pair: complete two-turn response-plus-reset seconds. C0/C1 identify conversations in this panel.

## Table S6 · Phase account within the 8B confirmation clock

`tables/s17_confirmation_costs.tex` · `tab:confirmation-costs` · baseline #276 PDF p. 23

**Lookup.** Mean component differences LOCAL minus SIMPLE within the response-plus-reset clock; negative values save time.

**Unit, clock and method.** The same B confirmation episodes as the endpoint table; component means close to the service difference before rounding.

**Reading and limits.** Retain all signed LOCAL-minus-SIMPLE arithmetic phase differences and residuals. They are not a strict decomposition of geometric endpoint effects.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** Arithmetic mean LOCAL-minus-SIMPLE phase differences in milliseconds within the registered response-plus-reset clock.

## Table S7 · RTX confirmation effects and roles

`tables/s18_rtx269_effects.tex` · `tab:rtx269-effects` · baseline #276 PDF p. 24

**Lookup.** Three RTX contrasts with their roles. Intervals are crossed root/time-block intervals from 10,000 draws.

**Unit, clock and method.** 864 formal measured requests; two log ratios averaged within each root/block, 10,000 crossed draws.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** RTX confirmation primary and descriptive complete-request estimates, with crossed root/time-block intervals.

## Table S8 · All six RTX time blocks in execution order

`tables/s19_rtx269_blocks.tex` · `tab:rtx269-blocks` · baseline #276 PDF p. 25

**Lookup.** Columns are time blocks in execution order; rows are contrasts. Cells are within-block geometric ratios from the same formal measured requests, not six new input samples.

**Unit, clock and method.** Equal root weight and equal log weight to the two paired rounds inside each block.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The six temporal summaries are labelled as summaries of the same 864 requests, not as replication.

**Integrated caption.** All six RTX time blocks in execution order: within-block geometric time ratios.

## Table S9 · All 24 RTX roots

`tables/s20_rtx269_roots.tex` · `tab:rtx269-roots` · baseline #276 PDF p. 25

**Lookup.** Two lists of twelve roots retain their IDs, domain membership, and all twelve rounds. Adjacent rows in the code and math lists are not paired inputs.

**Unit, clock and method.** Root geometric ratio over 12 rounds; code and math roots are stratified, not ranked.

**Reading and limits.** Each root appears once per contrast. Repeated roots and negative values are retained; no root is dropped.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** All 24 RTX roots: per-root geometric time ratios over 12 rounds.

## Table S10 · RTX arithmetic phase differences

`tables/s21_rtx269_phases.tex` · `tab:rtx269-phases` · baseline #276 PDF p. 26

**Lookup.** Mean paired phase differences in milliseconds for each RTX contrast; positive values add time to the candidate.

**Unit, clock and method.** Nonoverlapping arithmetic phases from the complete resident-request ledger.

**Reading and limits.** All phase, reset, synchronization and residual costs remain. The C1-minus-B column has the opposite sign to Figure~\ref{fig:c4}(c), whose arithmetic savings are B minus C1. Neither account strictly decomposes the geometric percentage.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** RTX confirmation arithmetic phase differences, candidate minus control, within the complete resident-request clock.

## Table S11 · All direct modern request effects

`tables/s11_direct_effects.tex` · `tab:direct-effects` · baseline #276 PDF p. 27

**Lookup.** Every direct modern effect with its own study, control and interval. Do not pool rows across deployments.

**Unit, clock and method.** Equal-root geometric paired effects; each row keeps its contemporaneous denominator and 95% interval.

**Reading and limits.** Rows come from different deployments. The table is an inventory of direct effects, not a meta-analysis.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** All direct modern request effects, retaining each independent study and its contemporaneous control.

## Table S12 · Signed arithmetic phase costs

`tables/s03_phase_costs.tex` · `tab:phase-costs` · baseline #276 PDF p. 28

**Lookup.** Each column is one same-study SD/SD comparison. Negative values mean the candidate phase is shorter.

**Unit, clock and method.** Arithmetic phase means within each named study; target decode is zero in these SD/SD comparisons.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** Signed arithmetic mean phase differences in milliseconds. Each column is one same-study SD/SD comparison.

## Table S13 · M1 five-comparison family

`tables/s06_m1_family.tex` · `tab:m1-family` · baseline #276 PDF p. 28

**Lookup.** Four direct contrasts plus the interaction. Older tables gave only marginal intervals; all five are retained here.

**Unit, clock and method.** Four ratios of native-service totals and a separate root-geometric interaction; 99% marginal intervals are members of the five-comparison Bonferroni family.

**Reading and limits.** The interaction is on a ratio scale and can exceed one even when both direct ratios are below one.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** M1's five-comparison family. Direct contrasts use ratios of totals; interaction uses root-geometric ratios.

## Table S14 · Every M1 paired root

`tables/s07_m1_roots.tex` · `tab:m1-roots` · baseline #276 PDF p. 29

**Lookup.** Times sum four sessions per root. Ratios use unrounded totals and both cut policies are shown.

**Unit, clock and method.** Four sessions summed per root; the five-comparison family lives in the adjacent table.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** Every M1 paired root. Times sum four sessions in seconds; each row gives its direct cut-policy ratios.

## Table S15 · Other historical natural panels

`tables/s05_natural.tex` · `tab:natural` · baseline #276 PDF p. 29

**Lookup.** Each panel keeps its original unit, clock and estimator. The rows are not interchangeable.

**Unit, clock and method.** Historical natural panels with their original units, clocks and estimators.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** Other historical natural LOCAL/WHOLE panels with their original units, clocks and estimators.

## Table S16 · Request-role accounting

`tables/s04_ledger.tex` · `tab:ledger` · baseline #276 PDF p. 30

**Lookup.** Ledger rows count scheduled work; measured and warm-up roles are separate. Timing tables cover only measured requests.

**Unit, clock and method.** Scheduled rows by measured, warm-up, qualification and resource roles.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** Ledger roles are separated so a scheduled row cannot be mistaken for a measured timing observation.

**Integrated caption.** Request-role accounting. Timing-table scope and full-campaign completion are distinct.

## Table S17 · Numerical evidence scope

`tables/s08_access.tex` · `tab:access` · baseline #276 PDF p. 31

**Lookup.** Original-machine checks cover more objects than the independently readable saved subset. Read the coverage column literally.

**Unit, clock and method.** Complete numerical objects on the original machine versus the saved, independently readable subset.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** Numerical evidence scope: original-machine comparisons and the independently readable saved-object subset.

## Table S18 · The separate B570 repair pilot

`tables/s09_pilot.tex` · `tab:pilot` · baseline #276 PDF p. 31

**Lookup.** Two roots, one measured round and a predeclared stop. No population interval is assigned.

**Unit, clock and method.** Two roots, one measured round, complete service including normal teardown.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** The separate B570 draft-placement pilot: two roots, one round and a predeclared complete-service stop.

## Table S19 · Earlier Vulkan geometry observations

`tables/s12_historical_geometry.tex` · `tab:historical-geometry` · baseline #276 PDF p. 32

**Lookup.** Historical Vulkan fixed-cell summaries. Ratios are inverted from the original W/L direction; values above one favor the control.

**Unit, clock and method.** Earlier Vulkan observations and their original fixed-cell summaries, including slower LOCAL cells.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** Earlier Vulkan geometry observations, including slower LOCAL cells and their original fixed-cell summaries.

## Table S20 · Historical resident effects and worker lifetime

`tables/s13_historical_applications.tex` · `tab:historical-applications` · baseline #276 PDF p. 32

**Lookup.** Resident ratios compare the composite with the fastest measured target-only control in the same study; worker totals are a different clock.

**Unit, clock and method.** Resident effects and worker lifetime are separate clocks and are not added.

**Reading and limits.** Values, signs, units and original scope are retained. Do not infer a new endpoint, a pooled sample or a between-deployment ranking.

**Old → new (Keep the values; tighten the lookup.).** The projection preserves every source value and row; grouping and rules move units and scope into the table itself.

**Integrated caption.** Historical resident effects and the separate worker lifetime. Fastest resident and worker controls are selected within their own measured configurations.
