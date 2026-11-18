# Integrated result figures: selected structures and exact boundaries

These edits adopt the Fig. 3/4/5 structures in PR #277 at
`8f6b37608ead243d7bc98599636fd96230aa1540`, following the decisions in PR #278.
They change headings, explanatory identities, caption/Description text and metadata.
They do not change measured observations, point positions, estimators, confidence
intervals, or the selected six-cell rank layout. All edits are confined to the
new integration directory.

## Fig. 3 — paired confirmation blocks

- Two panels retain all twelve numbered time blocks. Lines connect cases **within
  the same block**; they do not connect successive blocks into a trend. The old
  generic description “unconnected blocks” does not describe this selected figure.
- The left panel has two fixed 32B histories of one root, C4 on, P4 off and frozen
  proposals. Its clock is verification through commit. Noncrossing is primary;
  crossing and the crossing/noncrossing ratio-of-ratios are supporting.
- The right panel explicitly says **8B target-only service**. It separately
  analyzes two fixed conversations from response through reset. Its diamond gives
  equal log weight within each time block. Twelve blocks are not twelve new inputs.
- The individual 95% joint whole-block confidence limits are **printed numbers**;
  this figure has no CI bars. The interaction null is one. The two primary
  intervals span zero; this is not confirmation of no effect.
- The existing 8.7 pt panel headings keep their size and use regular weight.
  Ordinary 8–8.2 pt labels and all sixty effect points are retained.

## Fig. 4 — independent resident-request treatment

- Shorter regular-weight headings read “Dispatch controls”, “Complete-request
  reduction (%)” and “Arithmetic mean savings (ms)”. Same binary, shared
  activation preparation, SIMPLE fixed, P4 off, and reset-through-final-sync
  clock remain explicit.
- All 24 roots per contrast remain visible, with three summary diamonds and real
  CIs. C1/B is the sole primary contrast. Both C4 labels now explicitly say
  **descriptive**. C4 includes observed q3 prefill-tail work.
- C1/B is −0.90 [−2.19, 0.48]%; C4/C1 is 15.80 [13.07, 18.30]%;
  C4/B is 15.04 [12.40, 17.49]%.
- The separate arithmetic waterfall is B minus C1. Its printed stages are
  +100.43, −173.57, −7.43 and +0.06 ms; the unrounded values produce −80.52 ms
  net savings (a cost). No strict equality is asserted for the rounded stage
  labels, and the millisecond values are not a decomposition of the geometric
  percentage. All negative points, signs and zero lines remain.

## Fig. 5 — six direct contrasts on a rank axis

- The shared horizontal label is exactly **Root rank (prompt-length order)**.
  Equally spaced positions are ranks within each study, not proportional token
  distances and not evidence for a causal prompt-length trend. Sparse tick labels
  were optional in the handover and were not added to the already dense plot.
- The studies have 12 and 24 roots. Each root recurs in three contrasts: **36
  study-specific root entries and 108 effect marks**, plus six summary diamonds.
  The deployments are unpaired; no cross-model/platform causal ranking is implied.
- Three rows remain direct comparisons: target-only P4/C4, speculative P4/C4,
  and speculation/target-only at fixed P4. They are not a chain of LOCAL gains.
- The caption retains reset-through-final-synchronization, SIMPLE fixed,
  candidate/control direction and individual 95% code/math-stratified root CIs.
  A5000 exposure remains q32-only; RTX has q32 plus admitted tails, recorded in
  `frozen_evidence.json` and the manuscript's treatment definition.
- The negative A5000 `CodeContests/train/279` effect remains at its exact source
  coordinates as an open diamond: −0.33480777022760755%, printed −0.33%.

## Diagnostic alternatives

`f03_alternate` retains 48 native matched pairs, with separate 32B millisecond
and 8B target-only second clocks. `f05_prompt_length` retains the same 108 effects
on actual prompt-token positions; overlapping equal/similar lengths are expected.
Both remain editable diagnostic attachments, with no added formal figure numbers.
The alternate length mapping is now emitted to
`results/f05_prompt_length_mapping.json`; its authored caption/Description is in
`results/captions.json` alongside the other result captions.

## Actual checks and scope

1. Ran both CPU generators. They verified the frozen data-member hashes, 96 saved
   confirmation times, 864 selected RTX requests and 108 P4 root effects against
   the supplied saved-value estimators. No model or GPU execution occurred.
2. Eight numerical CSVs were compared cell by cell against the verified #277
   source. Source IDs and counts are unchanged; minor CPU floating-point
   last-digit differences are measured rather than hidden by forcing byte
   equality. All 345 keyed point identities, shapes, sizes and fill values in
   the three main figures and raw-time alternative are identical; coordinate
   differences are below 1e-10 pt. See `BASELINE_VALUE_PRESERVATION.json` for
   exact per-file byte status and maximum numeric differences.
3. `verify_encoding.py` checks actual artist ledgers: 60 confirmation effect
   points and 24 within-block pair lines; 72 RTX root effects plus 3 summaries;
   108 P4 effects on 36 study-specific roots plus 6 summaries; the negative open
   diamond and signed waterfall labels. See `INTEGRATION_ENCODING_CHECK.json`.
4. Five PDF/SVG pairs are vectors, have embedded PDF fonts and editable SVG text,
   and contain no raster image assets. SVG font subsets were embedded through the
   inherited `access.embed_svg_text_fonts` helper. Parent build may rerun that
   helper for all eleven exports. See `INTEGRATION_VECTOR_CHECK.json`.
5. Rendered and viewed all five color/grayscale proofs at 144 dpi, each panel
   5.477 inches wide. No clipping, label overlap or lost negative point was
   observed. Main-figure heights remain 274, 286 and 299 pt. Headings remain
   8.7 pt. All other figure text is 8–8.2 pt except the retained 7.6 pt F3 block
   numerals. The true-length alternative uses 8–8.5 pt text; pdfminer's 2.2 pt
   transformed glyph height for rotated text is not its font size.

This is contextual AI verification of saved data and graphics, not human blind
review, accessibility certification, complete native-archive reconstruction,
arXiv production validation or a new experimental result. Final manuscript-page
layout is reviewed separately by the integration lead.
