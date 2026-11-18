#!/usr/bin/env python3
"""Draw Supplementary Fig. S1/S2 and Fig. 6 from frozen values.

The page geometry is 5.477 in wide, the actual acmart text width. All marks are
editable Matplotlib artists; every point carries its source key in the SVG.
"""

if not __debug__:
    raise SystemExit("Optimized Python is unsupported: verification must remain enabled.")

import csv
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
(ROOT/".build").mkdir(exist_ok=True)
_cache = tempfile.TemporaryDirectory(prefix=".mpl-tail-", dir=ROOT/".build")
os.environ["MPLCONFIGDIR"] = _cache.name
os.environ["SOURCE_DATE_EPOCH"] = "1794960000"
import matplotlib
matplotlib.use("Agg")
# Avoid a known empty macOS system-font plist on headless builds; only bundled
# DejaVu faces are used, and the font cache lives in the owned build directory.
_path = os.environ.get("PATH", "")
try:
    os.environ["PATH"] = _cache.name
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties
finally:
    os.environ["PATH"] = _path
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_agg import FigureCanvasAgg

matplotlib.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.2,
    "pdf.fonttype": 42, "svg.fonttype": "none", "svg.hashsalt": "hs-independent-tail-v1",
    "axes.unicode_minus": False, "figure.facecolor": "white", "savefig.facecolor": "white",
    "path.simplify": False})
W = 5.477 * 72
INK, GRAY, FAINT, GUIDE = "#1E303B", "#465965", "#82919A", "#CFD8DC"
BLUE, TEAL, RUST = "#254B70", "#087B70", "#A95524"
BPALE, TPALE, RPALE = "#EDF2F6", "#E8F3F0", "#F8EEE4"
STAMP = datetime(2026, 11, 18, tzinfo=timezone.utc)
CAPS = {}


def num(v, d=2):
    return f"{v:.{d}f}"


def pct(v, d=1):
    return f"{v:+.{d}f}%"


def load_tables():
    """Read values from the frozen manuscript archive itself."""
    with ZipFile(ROOT / "inputs/arxiv_source.zip") as z:
        a = z.read("tables/s01_local_pairs.tex").decode()
        b = z.read("tables/s02_diagnostics.tex").decode()
    pairs = []
    for line in a.splitlines():
        if line.strip().endswith(r"\\") and line.count("&") == 6 and "Geometry" not in line:
            c = [x.strip() for x in line[:-2].split("&")]
            if c[0] in ("Crossing", "Within block"):
                pairs.append(dict(geometry="Noncrossing" if c[0] == "Within block" else c[0],
                                  source_geometry=c[0], transaction=c[1], base=int(c[2]), repeat=int(c[3]),
                                  simple=float(c[4]), local=float(c[5]), ratio=float(c[6])))
    events = []
    for line in b.splitlines():
        if line.strip().endswith(r"\\") and line.count("&") == 4 and "Event" not in line:
            c = [x.strip() for x in line[:-2].split("&")]
            if c[0] in ("Projection (ms)", "Attention (ms)", "Joins (ms)"):
                events.append(dict(event=c[0].split(" (")[0], within_simple=float(c[1]),
                                   within_local=float(c[2]), crossing_simple=float(c[3]),
                                   crossing_local=float(c[4])))
    assert len([p for p in pairs if p["transaction"] == "First"]) == 4 and len(events) == 3
    return pairs, events


class Page:
    def __init__(self, h, name):
        self.h, self.name = h, name
        self.fig = Figure(figsize=(W / 72, h / 72), dpi=144, facecolor="white")
        self.ax = self.fig.add_axes([0, 0, 1, 1], xlim=(0, W), ylim=(h, 0), frameon=False)
        self.ax.axis("off")
        self.texts, self.recs, self._n = [], [], 0

    def gid(self, tag):
        self._n += 1
        return f"{self.name}-{tag}-{self._n:04d}"

    def text(self, x, y, s, c=INK, fs=8.2, ha="left", bold=False, tag="label", z=6):
        f = Path(matplotlib.get_data_path()) / "fonts/ttf" / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
        props = FontProperties(family="DejaVu Sans", fname=str(f), size=fs, weight="bold" if bold else "normal")
        o = self.ax.text(x, y, str(s), fontproperties=props, ha=ha, va="center", color=c,
                         clip_on=False, zorder=z, gid=self.gid(tag))
        self.texts.append(o)
        return o

    def line(self, pts, c=GUIDE, lw=.65, ls="-", tag="line", z=2):
        gid = self.gid(tag)
        self.ax.add_line(Line2D(*zip(*pts), linewidth=lw, color=c, linestyle=ls,
                                solid_capstyle="butt", solid_joinstyle="round", zorder=z, gid=gid))
        return gid

    def interval(self, xlo, xhi, y, c, *, key, limits):
        gid=self.line([(xlo,y),(xhi,y)],c,1.15,tag="interval")
        for x in (xlo,xhi):
            self.line([(x,y-2.4),(x,y+2.4)],c,.75,tag="interval-cap")
        self.recs.append(dict(gid=gid,kind="interval",x=xlo,y=y,x_hi=xhi,key=key,
                              shape="capped-line",value=list(limits)))

    def mark(self, x, y, shape, size, c, fill="white", lw=.6, tag="point", z=4,
             key=None, value=None, kind="point"):
        gid=self.gid(tag)
        self.ax.plot([x], [y], linestyle="none", marker=shape, markersize=size, markeredgewidth=lw,
                     markeredgecolor=c, markerfacecolor=fill, zorder=z, gid=gid)
        self.recs.append(dict(gid=gid,kind=kind,x=x,y=y,key=key or tag,shape=shape,
                              value=value,fill=fill))

    def bar(self, x0, y0, x1, y1, c, fill="white", lw=.7, tag="bar", z=3):
        self.ax.add_patch(Rectangle((x0, min(y0, y1)), x1 - x0, abs(y1 - y0), facecolor=fill,
                                    edgecolor=c, linewidth=lw, zorder=z, gid=self.gid(tag)))

    def head(self, y, letter, title, aside=None):
        self.text(3, y, f"({letter})", BLUE, 8.7, bold=True, tag="panel")
        self.text(22, y, title, INK, 8.7, bold=False, tag="panel-title")
        if aside:
            self.text(W - 3, y, aside, GRAY, 8.0, "right", tag="aside")

    def rule(self, y):
        self.line([(3, y), (W - 3, y)], GUIDE, .7, tag="rule")

    def save(self, sub):
        out = ROOT / sub
        out.mkdir(parents=True, exist_ok=True)
        canvas = FigureCanvasAgg(self.fig)
        canvas.draw()
        width, height = canvas.get_width_height()
        rend = canvas.get_renderer()
        boxes = [s.get_window_extent(rend) for s in self.texts]
        for s, b in zip(self.texts, boxes):
            assert b.x0 >= -0.4 and b.x1 <= width + .4 and b.y0 >= -0.4 and b.y1 <= height + .4, \
                f"{self.name}: out of bounds {s.get_text()!r} {list(b.extents)}"
        for i, (a, ba) in enumerate(zip(self.texts, boxes)):
            for bb, b in zip(self.texts[i + 1:], boxes[i + 1:]):
                dx, dy = min(ba.x1, b.x1) - max(ba.x0, b.x0), min(ba.y1, b.y1) - max(ba.y0, b.y0)
                if dx > 1.5 and dy > 2.0:
                    raise ValueError(f"{self.name}: text collision {a.get_text()!r} / {bb.get_text()!r}")
        desc = CAPS[self.name]["description"]
        self.fig.savefig(out / (self.name + ".pdf"), metadata={"Creator": "HeteroSpec independent atelier",
                        "Title": self.name, "Subject": desc, "CreationDate": STAMP, "ModDate": STAMP})
        self.fig.savefig(out / (self.name + ".svg"), metadata={"Creator": "HeteroSpec independent atelier",
                        "Title": self.name, "Description": desc, "Date": "2026-11-18"})
        CAPS[self.name]["size_pt"] = [W, self.h]
        CAPS[self.name]["editable_labels"] = len(self.texts)
        CAPS[self.name]["ordinary_type_pt"] = 8.2
        with (ROOT / "results" / (self.name + "_marks.csv")).open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["svg_id", "kind", "text", "x_pt", "y_pt", "data_key", "shape", "font_pt", "value", "fill"])
            for s in self.texts:
                w.writerow([s.get_gid(), "text", s.get_text(), round(s.get_position()[0], 3),
                            round(s.get_position()[1], 3), "", "", s.get_fontsize(), "", ""])
            for r in self.recs:
                w.writerow([r["gid"], r["kind"], "", round(r["x"], 3), round(r["y"], 3), r["key"],
                            r.get("shape", ""), "",r.get("value",""),r.get("fill","")])
        (ROOT/"tail"/(self.name+"_data_map.json")).write_text(json.dumps({
            "layout_coordinates":"PostScript points measured from top left",
            "source_notes":"INTEGRATION_NOTES.md", "marks":self.recs},indent=2,ensure_ascii=False)+"\n")
        return dict(stem=self.name, width_pt=W, height_pt=self.h,
                    min_font_pt=min(t.get_fontsize() for t in self.texts),
                    editable_text_labels=len(self.texts), marks=len(self.recs))


def transaction():
    pairs, events = load_tables()
    p = Page(276, "f03_transaction")
    p.head(9, "a", "Four first-transaction pairs")
    p.text(4, 24, "Clean verify-through-commit · C4 on · P4 off", GRAY, 8.0)
    # local x scale and axis
    x0, x1 = 128, 286
    lo, hi = 70, 105
    X = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
    for tick in (70, 80, 90, 100):
        xx = X(tick)
        p.line([(xx, 34), (xx, 125)], FAINT, .5, tag="grid")
        p.text(xx, 133, str(tick), GRAY, 8.0, "center")
    p.text((x0 + x1) / 2, 146, "Complete verify-through-commit time (ms)", GRAY, 8.0, "center")
    rows = [("Crossing", 1), ("Crossing", 2), ("Noncrossing", 1), ("Noncrossing", 2)]
    ys = {("Crossing", 1): 52, ("Crossing", 2): 74, ("Noncrossing", 1): 98, ("Noncrossing", 2): 120}
    for geo, rep in rows:
        r = next(x for x in pairs if x["geometry"] == geo and x["transaction"] == "First" and x["repeat"] == rep)
        y = ys[geo, rep]
        name = geo + f" · r{rep} ({r['base']})"
        p.text(4, y, name, INK, 8.1)
        p.line([(X(r["simple"]), y), (X(r["local"]), y)], GRAY, .8, tag="paired-segment")
        p.mark(X(r["simple"]), y, "s", 4.1, GRAY, "white", .8, tag="SIMPLE",
               key=f"first/{geo}/repeat{rep}/SIMPLE_ms",value=r["simple"],kind="first_pair_arm")
        p.mark(X(r["local"]), y, "o", 4.4, TEAL, TEAL, .55, tag="LOCAL",
               key=f"first/{geo}/repeat{rep}/LOCAL_ms",value=r["local"],kind="first_pair_arm")
        p.text(294, y, f"{r['simple']:.2f} → {r['local']:.2f}", INK, 8.0)
        p.text(392, y, f"{r['ratio']:.3f}", TEAL if r["ratio"] < 1 else RUST, 8.0, "right", bold=True)
    p.text(294, 133, "SIMPLE → LOCAL", GRAY, 7.8)
    p.text(392, 133, "L/S", GRAY, 7.8, "right")
    p.text(392, 32, "Parentheses: query position", GRAY, 7.8, "right")
    p.rule(157)
    p.head(170, "b", "Separate device-event diagnostic", "Own profiler clock")
    p.text(4, 185, "Open square SIMPLE; filled circle LOCAL. Event time is not added to the wall clock.",
           GRAY, 7.9)
    e0, e1 = 152, 330
    E = lambda v: e0 + v / 80 * (e1 - e0)
    for tick in (0, 20, 40, 60, 80):
        p.line([(E(tick), 196), (E(tick), 250)], FAINT, .48, tag="grid")
        p.text(E(tick), 256, str(tick), GRAY, 7.8, "center")
    lanes = [("Projection · noncrossing", events[0], "within", BLUE),
             ("Projection · crossing", events[0], "crossing", TEAL),
             ("Attention · noncrossing", events[1], "within", BLUE),
             ("Attention · crossing", events[1], "crossing", TEAL)]
    for i, (label, e, case, col) in enumerate(lanes):
        y = 204 + i * 14
        a, b = e[case + "_simple"], e[case + "_local"]
        p.text(4, y, label, INK, 8.0)
        p.line([(E(a), y-1.2), (E(b), y+1.2)], col, .85, tag=case + "-segment")
        p.mark(E(a), y-1.2, "s", 3.7, col, "white", .7, tag=case + "-SIMPLE",
               key=f"device_event/{case}/{e['event']}/SIMPLE_ms",value=a,kind="event_arm")
        p.mark(E(b), y+1.2, "o", 3.9, col, col, .5, tag=case + "-LOCAL",
               key=f"device_event/{case}/{e['event']}/LOCAL_ms",value=b,kind="event_arm")
        p.text(392, y, f"{a:.2f}→{b:.2f}", GRAY, 7.6, "right")
    p.text(4, 268, "Noncrossing: base 137. Four dependent successor pairs are retained in Table S1.", GRAY, 7.6)
    return p.save("figures")


def b570():
    data = json.loads((ROOT / "inputs/scientific_data/data/plot_data.json").read_text())
    rows = ["TO_C/TO_A", "SD_C/SD_A", "SD_C/TO_C"]
    labels = [("Grouped/scalar", "under target-only"),
              ("Grouped/scalar", "under speculation"),
              ("Grouped speculation/", "grouped target-only")]
    by = {r["contrast"]: r for r in data["modern"] if r["pr"] == 247}
    for k in rows:
        assert len(by[k]["root_effects"]) == 24
    p = Page(208, "f06_b570")
    p.text(4, 9, "B570 complete service", INK, 8.7, tag="panel-title")
    p.text(392, 9, "24 roots · two rounds each", GRAY, 8.0, "right", tag="study")
    p.text(4, 29, "Direct comparison", GRAY, 8.0)
    p.text(210, 29, "Time ratio (log scale)", GRAY, 8.0, "center")
    p.text(392, 29, "Estimate [95% CI]", GRAY, 8.0, "right")
    x0, x1 = 142, 277
    lo, hi = .72, 2.75
    LX = lambda v: x0 + (math.log(v) - math.log(lo)) / (math.log(hi) - math.log(lo)) * (x1 - x0)
    for tick in (.75, 1, 1.5, 2, 2.5):
        p.line([(LX(tick), 39), (LX(tick), 164)], GUIDE if tick == 1 else FAINT,
               .8 if tick == 1 else .45, ls=(0, (2, 2)) if tick == 1 else "-", tag="equal-time" if tick == 1 else "grid")
        p.text(LX(tick), 177, f"{tick:g}×", GRAY, 7.9, "center")
    for j, (k, lab) in enumerate(zip(rows, labels)):
        y = 55 + j * 44
        col = BLUE if j < 2 else RUST
        p.text(4, y-3, lab[0], INK, 8.2)
        p.text(4, y+9, lab[1], INK, 8.0)
        s = by[k]
        # Stagger only vertically; every horizontal coordinate is the measured
        # root-geometric ratio on the same continuous logarithmic scale.
        for i, e in enumerate(sorted(s["root_effects"], key=lambda z: (z["ratio"], z["root"]))):
            dy = ((i % 5) - 2) * 2.1
            assert lo <= e["ratio"] <= hi
            p.mark(LX(e["ratio"]), y+dy, "o", 2.5, col, col, .35,
                   tag=f"root:{k}:{e['root']}", key=f"247/{k}/{e['root']}/ratio",
                   value=e["ratio"], kind="root_ratio")
        # The equal-root summary stays inside the same comparison row, below
        # the root swarm so a narrow CI cannot erase individual root marks.
        yy = y+11
        p.interval(LX(s["ci95_ratio"][0]), LX(s["ci95_ratio"][1]), yy, col,
                   key=f"247/{k}/ci95_ratio", limits=s["ci95_ratio"])
        p.mark(LX(s["ratio"]), yy, "D", 4.2, col, "white", .9,
               tag="estimate:"+k, key=f"247/{k}/ratio", value=s["ratio"], kind="summary")
        p.text(392, y+4, f"{s['ratio']:.3f} [{s['ci95_ratio'][0]:.3f}, {s['ci95_ratio'][1]:.3f}]",
               col if j == 2 else INK, 8.0, "right", tag="exact-ratio-ci")
    p.mark(7, 195, "o", 2.5, GRAY, GRAY, .35, tag="root-legend", kind="legend")
    p.text(14, 195, "Root ratios", GRAY, 8.0)
    p.mark(91, 195, "D", 4.2, GRAY, "white", .9, tag="summary-legend", kind="legend")
    p.text(99, 195, "Equal-root summary", GRAY, 8.0)
    p.text(392, 195, "Above 1: candidate slower", GRAY, 8.0, "right")
    assert sum(r["kind"] == "root_ratio" for r in p.recs) == 72
    assert sum(r["kind"] == "summary" for r in p.recs) == 3
    return p.save("figures")


def initial_c4():
    data = json.loads((ROOT / "inputs/scientific_data/data/plot_data.json").read_text())
    pair = list(csv.DictReader((ROOT / "inputs/scientific_data/statistics/prior_studies_recomputed/estimates/paired_request_times.csv").open()))
    a = next(r for r in data["modern"] if r["pr"] == 259 and r["contrast"] == "C4/C1")
    rtx = {(r["contrast"]): r for r in data["modern"] if r["pr"] == 256}
    assert len(a["root_effects"]) == 12 and all(len(rtx[k]["root_effects"]) == 24 for k in rtx)
    # root-level geometric means from the paired seconds (two rounds per root)
    g = {}
    for r in pair:
        if r["study_pr"] in ("259", "256"):
            g.setdefault((r["study_pr"], r["contrast"], r["root"]), []).append(r)
    def gm(pr, contrast, root, arm):
        v = [float(x[arm]) for x in g[pr, contrast, root]]
        return math.exp(sum(map(math.log, v)) / len(v))
    p = Page(292, "f08_c4_initial")
    p.head(9, "a", "A5000 · 12 roots", "C4 / C1 · two rounds per root")
    p.text(4, 23, "Root geometric means in complete-request seconds; linked marks are the same root.", GRAY, 7.9)
    x0, x1 = 155, 372
    lo, hi = 4.6, 13.8
    X = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
    for tick in (5, 8, 11):
        p.line([(X(tick), 34), (X(tick), 152)], FAINT, .45)
        p.text(X(tick), 160, str(tick), GRAY, 7.8, "center")
    p.text((x0 + x1) / 2, 171, "Complete-request seconds (same root)", GRAY, 8.0, "center")
    for i, e in enumerate(sorted(a["root_effects"], key=lambda z: z["ratio"])):
        y = 42 + i * 8.8
        c = gm("259", "C4/C1", e["root"], "control_s")
        d = gm("259", "C4/C1", e["root"], "candidate_s")
        assert abs((d / c) - e["ratio"]) < 1e-9, (e["root"], d / c, e["ratio"])
        p.line([(X(c), y), (X(d), y)], GUIDE, .55)
        p.mark(X(c), y, "s", 2.5, GRAY, "white", .55, tag="C1:" + e["root"],
               key=f"259/C4_C1/{e['root']}/C1_geomean_s",value=c,kind="paired_root_seconds")
        p.mark(X(d), y, "o", 2.7, TEAL, TEAL, .4, tag="C4:" + e["root"],
               key=f"259/C4_C1/{e['root']}/C4_geomean_s",value=d,kind="paired_root_seconds")
    p.mark(7, 42, "s", 3.0, GRAY, "white", .55, kind="legend")
    p.text(14, 42, "C1 control", GRAY, 7.6)
    p.mark(7, 54, "o", 3.1, TEAL, TEAL, .4, kind="legend")
    p.text(14, 54, "C4", TEAL, 7.6)
    p.text(4, 72, "C4 / C1 estimate", GRAY, 7.6)
    p.text(4, 83, f"{a['ratio']:.3f}  [{a['ci95_ratio'][0]:.3f}, {a['ci95_ratio'][1]:.3f}]", TEAL, 7.7, bold=True)
    p.rule(179)
    p.head(192, "b", "Initial RTX · 24 roots", "C1 and C4 against B · two rounds per root")
    lo2, hi2 = .58, 1.12
    q0, q1 = 138, 336
    LX = lambda v: q0 + (math.log(v) - math.log(lo2)) / (math.log(hi2) - math.log(lo2)) * (q1 - q0)
    for tick in (.6, .8, 1):
        p.line([(LX(tick), 205), (LX(tick), 258)], GUIDE if tick == 1 else FAINT,
               .6 if tick == 1 else .45, ls=(0, (2, 2)) if tick == 1 else "-")
        p.text(LX(tick), 266, f"{tick:g}×", GRAY, 7.8, "center")
    for j, (k, lab) in enumerate([("C1/B", "C1 / B"), ("C4/B", "C4 / B"), ("C4/C1", "C4 / C1")]):
        y = 212 + j * 18
        s = rtx[k]
        col = BLUE if k == "C1/B" else TEAL if k == "C4/B" else RUST
        p.text(4, y, lab, INK, 8.0)
        p.text(46, y, f"{s['ratio']:.3f} [{s['ci95_ratio'][0]:.3f}, {s['ci95_ratio'][1]:.3f}]", col, 7.7)
        for i, e in enumerate(sorted(s["root_effects"], key=lambda z: z["ratio"])):
            dy = ((i % 5) - 2) * 1.55
            p.mark(LX(e["ratio"]), y + dy, "o", 2.3, col, col, .3, tag=f"{k}:{e['root']}",
                   key=f"256/{k}/{e['root']}/ratio",value=e["ratio"],kind="root_ratio")
        p.interval(LX(s["ci95_ratio"][0]), LX(s["ci95_ratio"][1]), y-5.8, col,
                   key=f"256/{k}/ci95_ratio",limits=s["ci95_ratio"])
        p.mark(LX(s["ratio"]), y - 5.8, "D", 4.0, col, "white", .85,
               key=f"256/{k}/ratio",value=s["ratio"],kind="summary")
    p.text(4, 282, "Ratios are root geometric means; 24 roots per comparison. The deployments are not paired.", GRAY, 7.6)
    return p.save("figures")


def main():
    CAPS.update({
        "f03_transaction": {
            "caption": r"Original LOCAL measurements for two fixed histories and two paired repeats (four first-transaction pairs), with C4 on, P4 off and frozen proposals. Open squares are SIMPLE; filled circles are LOCAL; segments join matched arms. (a) First-transaction verification-through-commit time. (b) Separately clocked projection and attention event time for each history; both panels use milliseconds. Device-event times are not added to the transaction clock. Four dependent successor pairs are retained in Table~\ref{tab:local-pairs}.",
            "description": "The upper panel shows four first-transaction pairs: two crossing repeats at base 253 and two noncrossing repeats at base 137. Open SIMPLE squares and filled LOCAL circles are connected within each pair, with milliseconds and LOCAL/SIMPLE ratios printed at right. The lower panel separately compares projection and attention event times for both histories. These device-event costs use their own clock; they are not components to add to the transaction wall clock."},
        "f06_b570": {
            "caption": r"Grouping and complete speculative service in the formal B570 CPU-draft study (24 roots, two rounds). Each comparison reuses the same roots (72 effect marks); open diamonds give equal-root estimates with individual 95\% stratified-root intervals printed at right. Ratios share a logarithmic axis: one means equal time, and lower values mean less candidate time. Service includes CPU drafting and normal teardown.",
            "description": "Three rows each retain 24 measured root ratios and an open-diamond equal-root summary on one continuous log axis. Grouped/scalar target-only execution is 0.783 with 95% interval 0.770 to 0.797; grouped/scalar speculation is 0.872 with interval 0.870 to 0.874. Grouped speculation versus grouped target-only is 2.512 with interval 2.486 to 2.539, to the right of the equal-time line at one and therefore slower. The 72 root marks reuse the same 24 roots across three contrasts. Numeric limits retain the narrow grouping intervals without changing their graphical extent."},
        "f08_c4_initial": {
            "caption": r"Initial C4 studies with SIMPLE fixed and P4 off, separate from the 12-round RTX confirmation. (a) Twelve A5000 roots: paired C1/C4 geometric complete-request seconds over two rounds. (b) Twenty-four initial RTX roots: geometric time ratios for C1/B, C4/B and C4/C1 over two rounds, with equal time at one. Summaries give equal-root estimates and individual 95\% stratified-root intervals. The two studies are unpaired.",
            "description": "The upper panel uses seconds and links the C1 open square to the C4 filled circle for each of 12 A5000 roots. The lower panel uses time ratios for 24 initial RTX roots in each of three direct comparisons. C1/B has an estimate of 1.008 and interval 0.994 to 1.022, crossing equal time; both C4 comparisons lie below one. Each initial study has two rounds and a separate control and interval; neither is pooled with the later RTX confirmation."},
    })
    fields = [transaction(), b570(), initial_c4()]
    out = {"input_binding": {
        "f03_transaction": "#276 arxiv_source.zip tables/s01_local_pairs.tex and tables/s02_diagnostics.tex; cell values read verbatim",
        "f06_b570": "#276 scientific_data.zip data/plot_data.json modern[pr=247] root_effects and ci95_ratio",
        "f08_c4_initial": "#276 scientific_data.zip data/plot_data.json modern[pr=259,256]; paired_request_times.csv for root means"},
        "figure_marks": ["results/f03_transaction_marks.csv", "results/f06_b570_marks.csv",
                         "results/f08_c4_initial_marks.csv"],
        "layout_notes": {"f03_transaction": "four first-transaction pairs (two histories by two repeats), plus independently clocked projection/attention events; four dependent successors stay in Table S1",
                         "f06_b570": "three comparison rows, each with 24 root ratios, an equal-root diamond, exact CI, and numeric limits on one continuous log scale",
                         "f08_c4_initial": "(a) 12 A5000 root pairs in seconds; (b) 24 initial RTX root ratios per contrast; each study has two rounds and remains separate"},
        "figures": fields}
    d = ROOT / "proof"; d.mkdir(exist_ok=True)
    (ROOT / "tail" / "TAIL_FIGURE_MAP.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    (ROOT / "tail").mkdir(exist_ok=True)
    (ROOT / "tail/captions.json").write_text(json.dumps(CAPS, indent=2, ensure_ascii=False) + "\n")
    print("Wrote Fig. 6, Fig. S1 and Fig. S2 (vector PDF + editable SVG).")
    _cache.cleanup()


if __name__ == "__main__":
    main()
