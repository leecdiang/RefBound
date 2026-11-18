#!/usr/bin/env python3
"""Rebuild the 27 editable table bodies from frozen inputs; no network or GPU."""

if not __debug__:
    raise SystemExit("Optimized Python is unsupported: verification must remain enabled.")

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "table_design"
sys.dont_write_bytecode = True
sys.path.insert(0, str(DESIGN))
from layouts import render
from audit import audit

COMMIT = "8224998c5aa3032476d669990e6ae20e10cd1fb0"
BASE = "papers/taco/20261118_visual_reconstruction/"
ZIP_SHA = "26a99d9a3638ead1a27cdd38d9363813e94bdbb178bf7696582b9bd3844c969f"
MAN_SHA = "0bdabcafd77f0839c7cc6f2cd442251a0826d733db1491e2986554e9ecfd6624"
EXTRAS = {
    "artifact/DEPLOYMENTS_AND_WORKLOADS.md": "0580dc5b400a49c872135eb3340095b47924a359ae2db1c526044fefd440dbe4",
    "statistics/confirmation266_recomputed/DISPATCH_AND_SUCCESSOR_AUDIT.json": "11e55d8a692617467f6b921ddfd67b3b6a0e78cf65d6954cf5f5f101f2722b79",
    "data/history/applications.json": "ab7e824107681bb7a1244dccca4d0c16e98d861d48b1752758b667a653b145af",
}
HASH = lambda b: hashlib.sha256(b).hexdigest()
PRIOR = "statistics/prior_studies_recomputed/all_point_estimates_and_intervals.json"
CONF = "statistics/confirmation266_recomputed/confirmation266_data.json"
RTX = "statistics/rtx269_recomputed/figure_data.json"
CN = "statistics/confirmation266_recomputed/INDEPENDENT_NATIVE_VALUES.csv"
RN = "statistics/rtx269_recomputed/NATIVE_FORMAL_TIMES.csv"
RA = "artifact/scientific_data/RTX269_ALL_REQUESTS.csv"
MN = "artifact/scientific_data/M1_NATIVE_REQUESTS.csv"
PLOT = "data/plot_data.json"
PAIRS = "statistics/prior_studies_recomputed/estimates/paired_request_times.csv"
HIST = "data/history/historical_evidence.json"
NAT = "artifact/scientific_data/NATURAL_8B_EPISODES.json"
DEP, DISPATCH, APPS = EXTRAS


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


class Inputs:
    def __init__(self, tex, data):
        if HASH(tex.read_bytes()) != ZIP_SHA:
            raise ValueError("The TeX ZIP does not match the fixed #276 archive.")
        self.z = ZipFile(tex)
        self.data = data
        b = (data / "MANIFEST.json").read_bytes()
        if HASH(b) != MAN_SHA:
            raise ValueError("The scientific-data manifest does not match #276.")
        self.man = {x["member"]: x for x in json.loads(b)["files"]}
        self.tm = {x["path"]: x["sha256"] for x in json.loads(self.z.read("MANIFEST.json"))["files"]}
        self.cache = {}
        self.records = {}
        self.alias = dict(prior=PRIOR, conf=CONF, cn=CN, rtx=RTX, rn=RN, ra=RA, mn=MN,
                          plot=PLOT, pairs=PAIRS, hist=HIST, nat=NAT, dep=DEP, dispatch=DISPATCH, apps=APPS,
                          work="statistics/prior_studies_recomputed/estimates/workload_roots.csv")

    def tex(self, p):
        b = self.z.read(p)
        assert HASH(b) == self.tm[p], p
        return b.decode()

    def get(self, name):
        p = self.alias[name]
        if p not in self.cache:
            if p in EXTRAS:
                local = DESIGN / "sources" / Path(p).name
                b = local.read_bytes()
                expected = EXTRAS[p]
                repository_path = BASE + p
                loc = "table_design/sources/" + local.name
            else:
                b = (self.data / p).read_bytes()
                expected = self.man[p]["sha256"]
                repository_path = BASE + self.man[p]["source_path"]
                loc = "inputs/scientific_data/" + p
            assert HASH(b) == expected, p
            self.records[p] = dict(commit=COMMIT, repository_path=repository_path,
                                   local=loc, sha256=expected)
            s = b.decode()
            self.cache[p] = (json.loads(s) if p.endswith(".json") else list(csv.DictReader(io.StringIO(s)))
                             if p.endswith(".csv") else s)
        return self.cache[p]


def arg(s, pos):
    assert s[pos] == "{", s[pos:pos+20]
    d = 1
    for i in range(pos+1, len(s)):
        if s[i] in "{}" and s[i-1] != "\\":
            d += 1 if s[i] == "{" else -1
            if not d:
                return s[pos+1:i], i+1
    raise ValueError("Unclosed TeX argument")


def order(src):
    """Follow actual TeX inputs (including nested RTX supplement), ignoring floats in comments."""
    result = []
    counters = dict(main=0, supplement=0)
    state = ["main"]
    pat = re.compile(r"\\input\{(sections/[^}]+)\}|\\setcounter\{table\}\{0\}|"
                     r"\\papertable(?:\[[^]]+\])?(?=\{)")

    def walk(path):
        s = re.sub(r"(?m)(?<!\\)%[^\n]*", "", src.tex(path))
        for x in pat.finditer(s):
            if x[1]:
                walk(x[1]+".tex")
            elif x[0].startswith(r"\setcounter"):
                state[0] = "supplement"
            else:
                name, k = arg(s, x.end())
                cap, k = arg(s, k)
                label, k = arg(s, k)
                counters[state[0]] += 1
                n = ("S" if state[0]=="supplement" else "") + str(counters[state[0]])
                result.append((n, name, cap, label, path, s.count("\n", 0, x.start())+1))
    walk("main.tex")
    files = {p[7:-4] for p in src.tm if p.startswith("tables/") and p.endswith(".tex")}
    assert counters == {"main": 7, "supplement": 20} and len(files) == len(result) == 27
    assert {v[1] for v in result} == files
    return result


class Body:
    """Baseline body rows, by their original order/line; never OCR or rekey a cell."""
    def __init__(self, s):
        self.source = s
        self.rows = []
        self.lines = []
        on = False
        for i, line in enumerate(s.splitlines(), 1):
            t = line.strip()
            if t == r"\bottomrule":
                break
            if t == r"\midrule":
                on = True
                continue
            if on and t.endswith(r"\\"):
                if t.startswith(r"\multicolumn"):  # panel heading in the B570 pilot
                    continue
                self.rows.append([v.strip() for v in t[:-2].split("&")])
                self.lines.append(i)
        self.note = (s.partition(r"\footnotesize\raggedright ")[2]).strip()
        assert self.rows


def build(src):
    mapping = order(src)
    cards = json.loads((DESIGN / "briefs.json").read_text())
    assert set(cards) == {r[0] for r in mapping}
    (ROOT / "tables").mkdir(exist_ok=True)
    entries, captions, pages = [], {}, []
    for n, stem, oldcap, label, section, line in mapping:
        p = "tables/" + stem + ".tex"
        b = Body(src.tex(p))
        card = cards[n]
        # The checks also furnish the few additional fields projected onto the table.
        extra, checks = audit(n, b, src)
        text, transform = render(n, b, extra)
        header = f"% Table {n} | {label} | editable body generated by scripts/build_tables.py\n"
        (ROOT / p).write_text(header+text)
        cap = card["caption"]
        if "{" in cap:
            try:
                cap = cap.format_map(extra)
            except (KeyError, ValueError):
                pass  # LaTeX braces are ordinary caption text, not placeholders.
        cap = re.sub(r"(?<!\\)([%_])", r"\\\1", cap)
        captions[stem] = cap
        native = []
        for alias, field, how in checks:
            src.get(alias)
            native.append(dict(source=src.alias[alias], fields=field, transformation=how))
        entries.append(dict(
            table=n, label=label, output=p, sha256=HASH((header+text).encode()),
            display_order_source=dict(commit=COMMIT, path=BASE+section, line=line),
            baseline=dict(commit=COMMIT, path=BASE+p, archive_member=p, sha256=src.tm[p],
                          first_rule_through_last_data="row lines below; full-precision and sign retained at source display precision",
                          row_lines=b.lines, rows=b.rows, note=b.note, original_caption=oldcap),
            projected_fields=transform, data_bindings=native, original_pdf_page=card["page"],
        ))
        pages.extend([f"## Table {n} · {card['title']}", "",
                      f"`{p}` · `{label}` · baseline #276 PDF p. {card['page']}", "",
                      f"**Lookup.** {card['lookup']}", "", f"**Unit, clock and method.** {card['method']}", "",
                      f"**Reading and limits.** {card['reading']}", "", f"**Old → new ({card['verdict']}).** {card['comparison']}",
                      "", f"**Integrated caption.** {cap.replace(chr(92)+'%', '%')}", ""])
    dump(DESIGN / "table_ledger.json", dict(freeze=COMMIT, arxiv_source_sha256=ZIP_SHA,
         scientific_manifest_sha256=MAN_SHA,
         conventions="Numbered by recursive main/section inputs, not lexical filenames. Baseline rows are cell-level "
                     "source locators, not additional output observations. Numeric alignments preserve signed zero "
                     "and precision. Exact saved scalar intervals are validated, not re-bootstrapped here.",
         sources=src.records, tables=entries))
    dump(DESIGN / "captions.json", captions)
    (DESIGN / "TABLE_CARDS.md").write_text("# Table design and scientific reading cards\n\n"
         "Numbering follows the manuscript, not filenames. Old/new comparisons record the inherited design choice. "
         "Baseline pages refer to the pinned #276 author PDF, not the integrated manuscript's current pages. "
         "For input fields, checks and transforms see [`table_ledger.json`](table_ledger.json).\n\n"+"\n".join(pages))
    return mapping, captions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tex-zip", type=Path, default=ROOT/"inputs/arxiv_source.zip")
    parser.add_argument("--data-dir", type=Path, default=ROOT/"inputs/scientific_data")
    parser.add_argument("--proof", action="store_true", help="also build baseline/redesign PDF proofs with CPU pdfLaTeX")
    a = parser.parse_args()
    src = Inputs(a.tex_zip, a.data_dir)
    mapping, caps = build(src)
    if a.proof:
        from table_proof import prove
        prove(ROOT, src, mapping, caps)
    print("Rebuilt 7 main + 20 supplemental native tables, verified bindings, ledger and captions.")


if __name__ == "__main__":
    main()
