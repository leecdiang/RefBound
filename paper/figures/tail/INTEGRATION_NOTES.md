# Tail figures: accepted integration

These files implement localized PR #278 decisions on the accepted PR #277 figure source. All measurements, intervals, study identities and input archives are retained. No GPU/model execution or new confidence interval is introduced.

## Fig. 6: three complete-service comparison rows

The former separate root-strip and summary panels have been combined into three rows. Each row contains all 24 root-geometric ratios, the equal-root diamond, its actual 95% stratified-root interval, and one exact numerical ratio/interval cell. The three rows reuse the same 24 roots: 72 effect marks, not 72 independent inputs.

The full comparison labels are grouped/scalar under target-only, grouped/scalar under speculation, and grouped speculation/grouped target-only. The estimates and displayed limits remain:

| Comparison | Ratio [95% CI] |
|---|---|
| Grouped/scalar under target-only | 0.783 [0.770, 0.797] |
| Grouped/scalar under speculation | 0.872 [0.870, 0.874] |
| Grouped speculation/grouped target-only | 2.512 [2.486, 2.539] |

Every horizontal coordinate uses one continuous logarithmic scale over 0.72–2.75, including all observed root ratios. Equal time is the dashed line at one. The interval endpoints are drawn at their true coordinates without widening; the numeric column makes narrow limits readable. The space between approximately 0.87 and 2.51 is the actual ratio distance. The final comparison is slower: 2.512 times the grouped target-only control time. This formal clock includes CPU drafting and normal teardown. The two-root Vulkan draft-placement pilot is a separate study.

The figure is 208 pt high instead of 284 pt. Data type remains 8–8.2 pt; the title is regular 8.7 pt. Filled circles, open diamonds, full row labels and the dashed equal-time line keep meaning available without color. The caption removes unused-marker design commentary and states the 72/24 sample identity and full service cost.

## Fig. S1: first transactions and separate event clocks

The upper panel is explicitly four first-transaction pairs: two fixed histories × two paired repeats. The displayed term is Noncrossing at base 137, matching the supplement tables; the frozen input's historical `Within block` label remains recorded as `source_geometry` in the reader. The adverse noncrossing repeat remains visible at LOCAL/SIMPLE 1.013.

The lower panel retains separately clocked projection and attention observations for both histories. Its event times are not added to transaction wall-clock time. Four dependent successor pairs remain in Table S1. Numerical event labels were raised from 7.2 to 7.6 pt and the event axis endpoint was moved left to keep the 80-ms grid line clear of those labels. No data coordinate was dropped or changed.

## Fig. S2: two independent initial studies

Panel (a) uses complete-request seconds for 12 A5000 root pairs; panel (b) uses ratios for all 24 initial RTX roots in each direct contrast. Each study has two rounds and remains separate from the later 12-round RTX confirmation. The caption uses (a)/(b), not left/right, and seconds only applies to (a).

The initial C1/B estimate remains 1.008 [0.994, 1.022]. The summaries retain their independent controls and individual 95% stratified-root intervals. Small ratio text was raised from 7.2 to 7.7 pt. No cross-deployment pairing or causal ranking is implied.

## Source, mappings and verification

Run `python3 scripts/tail_figures.py`, then `python3 tail/check_mark_sources.py`. The input binding and layout definitions are in `TAIL_FIGURE_MAP.json`. Fig. S1 reads the frozen table values in `inputs/arxiv_source.zip`; Figs.6/S2 read the retained scientific sidecar and paired request seconds. The generator emits PDF, SVG, captions/Descriptions, `*_data_map.json`, and `results/*_marks.csv` together.

The inherited tail ledger had text records but never appended its actual point records. This integration repairs that mapping omission. The new ledgers retain numeric values, root/study/contrast identifiers, marker identities and coordinates; true interval endpoints are included. A bounded independent scalar check verifies every displayed root ratio against the two saved rounds and binds the corresponding SVG marker to its ledger coordinates. It also checks the Fig.1/2 invariants. See `MARK_SOURCE_CHECK.json` for executed results.

Generator boundary/overlap checks and PDF font/vector checks passed. New colored and grayscale renders were inspected at the 5.477-inch PDF dimensions; the last Fig.S1 spacing adjustment was re-rendered and rechecked. The PDF/true-text SVG checks are in `METHOD_TAIL_VECTOR_QA.json`. SVG subsets can be refreshed with `scripts/access.py --no-sim` after any redraw. These are AI/contextual visual checks and saved-data CPU checks, not human blind review, accessibility certification, complete native-archive reanalysis or GPU reproduction.
