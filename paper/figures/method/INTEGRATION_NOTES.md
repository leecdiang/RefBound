# Method figures: accepted integration

These are localized edits of PR #277 at `8f6b37608ead243d7bc98599636fd96230aa1540`, following the review in PR #278. The previous candidate, its input records, and the manuscript baseline are not modified.

## Fig. 1: reference obligations

The accepted matrix, q8 grouping sketches, and committed-output tracks are retained. Panel titles now use regular 8.7 pt type rather than bold 9.4 pt; normal data text stays at 8–8.2 pt. The already-correct separation between output index range 0–127 and mismatch start 29 is preserved.

Panel (a) counts complete model/operator outputs: 16 objects for each measured width/recipe cell; packed q2/q4 remain explicitly not run. Panel (b) is a separate B570 experiment, with three inputs × 128 committed vocabulary vectors = 384 vectors per arm and 1,920 across five arms. Physical-view repair changes 198 unequal vectors to zero. The panels do not constitute one cumulative ablation or one failure-rate denominator.

The caption names both independent studies, the full-object and vector denominators, the unmeasured widths, the index interval, and the compound repair. The Description explains the visual structure and its principal comparisons without duplicating the caption sentence by sentence.

## Fig. 2: construction, ownership and successor

The accepted side-by-side SIMPLE/LOCAL flow remains the main figure. The three headings are **Local attention refinement**, **Owned row at rejection**, and **Successor view guard**, in regular 8.7 pt type. The layered alternative remains an editable attachment; it is not an extra numbered supplement.

Scientific encodings remain unchanged:

- SIMPLE uses q3+q1 whole-decoder subcalls; LOCAL uses q4 QKV and downstream projection/FFN groups with the same 3+1 attention views. QKV produces KV before attention, and the attention rows join before output projection and FFN.
- Boxes span query membership. Their dimensions do not encode elapsed time or memory size, and the two policy arms are alternatives rather than consecutive instants.
- Synchronized copying retains SIMPLE's first-subcall `z1` before native storage reuse. Rejection leaves KV 0–254 and a correction pending at position 255.
- The successor follows LOCAL's own commit at positions 255–258. The extent vector changes from `[256,256,256,512]` to `[256,512,512,512]`; unchanged q4, maximum 512 and reference policy do not permit reuse. The new views are 1+3. Owned `z3` supplies the bonus pending at 259, beyond retained KV 0–258.

The shorter caption retains this construction and state progression. Definitions of the owned-slot representation, extent, and reference-policy identifier belong in the manuscript method sections.

## Editable source and mapping

Run `python3 scripts/method_figures.py`. `evidence.py` reads the frozen receipts, output hashes, checker records and attention-view traces listed in `INPUTS.json`; it does not execute a model. `figure_marks.json` contains the derived scientific records. Each `f*_artist_ledger.json` binds the exported SVG IDs to text or vector geometry and points back to those scientific records. Tags distinguish widths, source subcalls, owned slots, changed extents, commit and pending state.

PDFs and SVGs are regenerated together with the caption/Description JSON and map. The PDFs remain 5.477 inches wide with embedded TrueType fonts. SVG text stays editable; `scripts/access.py --no-sim` embeds the font subsets after generation.

## Checks and limits

The current generator passed editable-label boundary and overlap checks. The bounded CPU check in `tail/check_mark_sources.py` verifies the Fig.1 denominators and the Fig.2 ownership/successor relationships against the retained derived records. The original evidence reader also checks underlying recorded receipts and byte hashes. New colored and grayscale renders of all three method outputs were visually inspected; there is no human accessibility certification or new GPU/model replay. Final manuscript float and page inspection remains a separate integration check.
