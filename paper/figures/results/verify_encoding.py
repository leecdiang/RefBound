"""CPU-only checks of the integrated result figures' actual mark ledgers.

Run after the result generators and SVG font embedding. Checks graphic/sample
identities and signed displayed values, not new experimental observations.
"""

if not __debug__:
    raise SystemExit("Optimized Python is unsupported: verification must remain enabled.")

import csv
import hashlib
import json
import platform
from collections import Counter
from pathlib import Path

import fitz
import matplotlib
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def read(name):
    with (RESULTS / name).open() as stream:
        return list(csv.DictReader(stream))


def points(rows):
    return [r for r in rows if r["kind"] == "point" and r["data_key"]]


def main():
    f3 = read("f07_confirmation_marks.csv")
    f4 = read("f04_few_column_marks.csv")
    f5 = read("f05_prefill_marks.csv")
    assert len(points(f3)) == 60
    assert len([r for r in f3 if r["kind"] == "line" and
                ("negative+positive" in r["data_key"] or "C0+C1" in r["data_key"])]) == 24
    assert len(points(f4)) == 75
    assert len(points(f5)) == 114
    roots = read("f05_root_effects.csv")
    assert len(roots) == 108
    assert len(set((r["study_pr"], r["root"]) for r in roots)) == 36
    assert set(Counter((r["study_pr"], r["root"]) for r in roots).values()) == {3}
    adverse = [r for r in roots if float(r["reduction_pct"]) < 0]
    assert len(adverse) == 1 and adverse[0]["root"] == "CodeContests/train/279"
    assert round(float(adverse[0]["reduction_pct"]), 2) == -0.33
    key = "257:SD_P4/TO_P4:rank=12:root=CodeContests/train/279"
    mark = next(r for r in f5 if r["data_key"] == key)
    assert mark["shape"] == "D" and mark["fill"] == "#FFFFFF"
    evidence = json.loads((RESULTS / "frozen_evidence.json").read_text())
    assert evidence["fig4"]["estimators"]["C1/B"]["role"] == "prespecified primary"
    assert all(evidence["fig4"]["estimators"][k]["role"] == "prespecified descriptive secondary"
               for k in ("C4/C1", "C4/B"))
    water = evidence["fig4"]["estimators"]["C1/B"]["candidate_minus_control_ms"]
    texts = [r["text"] for r in f4 if r["data_key"].startswith("269:C1/B:arithmetic_ms_saved=")]
    assert texts == ["+100.43", "−173.57", "−7.43", "+0.06", "−80.52"]
    assert abs(sum(water[k] for k in ("verify", "prefill", "draft", "remaining")) - water["service"]) < 1e-9
    files = {}
    for folder, stem in [("figures", "f07_confirmation"), ("figures", "f04_few_column"),
                         ("figures", "f05_prefill"), ("alternatives", "f03_alternate"),
                         ("alternatives", "f05_prompt_length")]:
        path = ROOT / folder / (stem + ".pdf")
        with fitz.open(path) as doc:
            spans = [s for b in doc[0].get_text("dict")["blocks"] if "lines" in b
                     for line in b["lines"] for s in line["spans"]]
            files[stem] = {"width_pt": doc[0].rect.width, "height_pt": doc[0].rect.height,
                           "font_sizes_pt": sorted(set(round(s["size"], 3) for s in spans)),
                           "pdf_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                           "svg_sha256": hashlib.sha256(path.with_suffix(".svg").read_bytes()).hexdigest()}
    report = {
        "scope": "CPU checks of saved-value graphic encoding, not a GPU/model experiment or laboratory reproduction",
        "figure3": {"effect_points": 60, "same_block_pair_lines": 24, "blocks": 12,
                    "histories": 2, "conversations": 2, "ci_encoding": "printed numbers, no CI bars"},
        "figure4": {"root_effects": 72, "distinct_roots": 24, "summary_diamonds": 3,
                    "primary": "C1/B", "waterfall_labels_ms": texts,
                    "unrounded_net_saved_ms": -water["service"], "rounded_label_sum_not_asserted": True},
        "figure5": {"study_specific_roots": 36, "effect_marks": 108, "summary_diamonds": 6,
                    "adverse_mark": adverse[0],
                    "rank_axis_explicit": any(r["text"] == "Root rank (prompt-length order)" for r in f5)},
        "files": files,
        "runtime": {"python": platform.python_version(), "numpy": np.__version__,
                    "matplotlib": matplotlib.__version__},
        "font_measurement_note": "PyMuPDF span sizes are actual font sizes. pdfminer LTChar height on a rotated label can be below the font size."
    }
    (RESULTS / "INTEGRATION_ENCODING_CHECK.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: 60 confirmation points, 72 RTX root effects, 108 P4 effects / 36 study-specific roots, signed waterfall labels.")


if __name__ == "__main__":
    main()
