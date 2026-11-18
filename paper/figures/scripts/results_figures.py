"""Draw main Figures 3–5 and the native-pair Figure 3 alternative. CPU/offline.

Run: python3 scripts/results_figures.py
Requires Python 3.9+, NumPy, Matplotlib (the bundled DejaVu Sans font).
Input paths are relative to this project. No manuscript or input file is edited.
The artist ledger uses physical PostScript points, with (0,0) at page top left.
"""

if not __debug__:
    raise SystemExit("Optimized Python is unsupported: verification must remain enabled.")

import csv
import hashlib
import json
import math
import os
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "inputs"
DATA = INPUT / "scientific_data"
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)

BASE = "8224998c5aa3032476d669990e6ae20e10cd1fb0"
A266 = "0cac675cc757f195b74893da53af2161c2599c97"
R269 = "3ed4671c21291f0ed0012fd61cc992558fdb024d"
P4_SHAS = {257: "7deb9aa28a934878837d3d74be8ed14bc374809a",
           255: "1f75de3433d4121f916bee81ca5fc5a1b848e7c6"}
ZIP_SHA = "d437b1f2c758f0593651af5441ef8d09183a5bcf31f0a55df4ec74efd0300568"
MAN_SHA = "0bdabcafd77f0839c7cc6f2cd442251a0826d733db1491e2986554e9ecfd6624"
DRAW_SHA = "fba8f39df16e8efeb045e78585a3715189ba75872c14952a89775c8e211972b2"
CA = "statistics/confirmation266_recomputed/"
CR = "statistics/rtx269_recomputed/"
CP = "statistics/prior_studies_recomputed/"
F3, ALT, F4, F5 = "f07_confirmation", "f03_alternate", "f04_few_column", "f05_prefill"
R_KEYS = ("C1/B", "C4/C1", "C4/B")
P_KEYS = ("TO_P4/TO_C4", "SD_P4/SD_C4", "SD_P4/TO_P4")
E_NAMES = {"negative": "Noncrossing", "positive": "Crossing", "interaction": "Crossing / noncrossing",
           "C0": "Conversation 0", "C1": "Conversation 1", "equal_conversation_overall": "Equal weight"}
ALL8 = "equal_conversation_overall"
STAGES = {"verify": ["target_verify"], "prefill": ["target_prefill"],
          "draft": ["draft_prefill", "draft_sync", "draft_propose"],
          "remaining": ["context", "target_decode", "decision_commit", "terminal_sync", "other_host"]}
PHASE = ["service"] + [s for subset in STAGES.values() for s in subset]
W = 5.477 * 72
INK, MUTED, GRID, LIGHT = "#24313B", "#505F69", "#D2DADC", "#E5EAEB"
NAVY, TEAL, RUST = "#254B70", "#087B70", "#A95524"
WHITE = "#FFFFFF"
FS, HEAD = 8.2, 8.7
STAMP = datetime(2026, 11, 18, tzinfo=timezone.utc)
mpl.rcParams.update({"font.family": "DejaVu Sans", "font.size": FS, "text.usetex": False,
                     "svg.fonttype": "none", "svg.hashsalt": "taco-atelier-results-20261118",
                     "pdf.fonttype": 42, "ps.fonttype": 42, "pdf.use14corefonts": False,
                     "savefig.facecolor": WHITE, "savefig.transparent": False,
                     "path.simplify": False, "lines.solid_capstyle": "butt"})


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False,
                                        allow_nan=False) + "\n", encoding="utf-8")


def write_csv(name, records):
    with (OUT / name).open("w", encoding="utf-8", newline="") as file:
        fields = list(dict.fromkeys(k for rec in records for k in rec))
        wr = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
        wr.writeheader()
        wr.writerows(records)


def native_rows(relative):
    with (DATA / relative).open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def frozen(relative):
    return json.loads((DATA / relative).read_text(encoding="utf-8"))


def same(a, b):
    np.testing.assert_allclose(a, b, rtol=0, atol=3e-10)


def reduction(ratio):
    return 100 * (1 - ratio)


def stats(logs, resampled_logs):
    r = float(np.exp(np.mean(logs)))
    lo, hi = (float(v) for v in np.percentile(np.exp(resampled_logs), [2.5, 97.5]))
    return {"ratio": r, "ratio_lo": lo, "ratio_hi": hi, "pct": reduction(r),
            "lo": reduction(hi), "hi": reduction(lo), "draws": 10000}


def fmt(x, digits=2, plus=False):
    return format(x, ("+" if plus else "") + f".{digits}f").replace("-", "−")


def pci(s, digits=2, unit=""):
    return f"{fmt(s['pct'], digits)} [{fmt(s['lo'], digits)}, {fmt(s['hi'], digits)}]{unit}"


def rci(s):
    return f"{fmt(s['ratio'],3)} [{fmt(s['ratio_lo'],3)}, {fmt(s['ratio_hi'],3)}]"


def freeze_inputs():
    man = DATA / "MANIFEST.json"
    assert sha(man) == MAN_SHA
    rows = json.loads(man.read_bytes())["files"]
    for f in rows:
        assert sha(DATA / f["member"]) == f["sha256"], f["member"]
    assert sha(INPUT / "rtx269-frozen-draws.jsonl") == DRAW_SHA
    if (INPUT / "scientific_data.zip").exists():
        assert sha(INPUT / "scientific_data.zip") == ZIP_SHA
    sources = {CA+"INDEPENDENT_NATIVE_VALUES.csv": "Fig 3 and alternate: 96 native seconds",
               CA+"confirmation266_data.json": "Fig 3: pair/receipt IDs and independent check of six estimates and every interval",
               "artifact/scientific_data/RTX269_ALL_REQUESTS.csv": "Fig 4: field-minimized role/timing derivative with public row IDs",
               CR+"NATIVE_FORMAL_TIMES.csv": "Fig 4: independent cross-check of all selected arm and phase times",
               CR+"figure_data.json": "Fig 4: independent estimate/interval and dispatch check",
               CP+"estimates/paired_request_times.csv": "Fig 5: native candidate/control seconds by round",
               CP+"estimates/workload_roots.csv": "Fig 5: root domain and prompt/output lengths",
               CP+"all_point_estimates_and_intervals.json": "Fig 5: independent interval and all-root estimate check",
               "data/plot_data.json": "Fig 5: underlying study heads and request counts"}
    return dict(manuscript_head=BASE, confirmation266_head=A266, rtx269_head=R269,
                p4_heads=P4_SHAS, zip_sha256=ZIP_SHA, zip_member_manifest_sha256=MAN_SHA,
                all_16_data_zip_members_verified=True, frozen_rtx_draws_sha256=DRAW_SHA,
                input_members=[dict(path="inputs/scientific_data/"+f["member"], bytes=f["bytes"],
                                    sha256=f["sha256"], use=sources[f["member"]])
                               for f in rows if f["member"] in sources],
                gpu_host_identity={"study": 255, "head": P4_SHAS[255],
                         "path": "benchmarks/three_platform_closeout_20261116/prefill_p4/results/rtx5070ti_20261116/formal_packet/HOST.json",
                         "git_blob": "0b9d1c1c611af190dae1b5cd37b23b120eadeef0",
                         "reported_gpu": "NVIDIA GeForce RTX 5070 Ti Laptop GPU"},
                ci_percentiles=[2.5,97.5], percentile_interpolation="linear, on ratios; reversed for reductions",
                cpu_only=True, controlled_runtimes="No fitting, simulations of timings, or model executions.")


def confirmation():
    times = {(r["panel"], r["case"], int(r["block"]), r["arm"]): float(r["value_s"])
             for r in native_rows(CA + "INDEPENDENT_NATIVE_VALUES.csv")}
    meta = frozen(CA + "confirmation266_data.json")
    assert len(times) == 96 and meta["head"] == A266
    assert meta["primary_endpoints"] == ["A/negative", "B/equal_conversation_overall"]
    cases = [("A","negative"), ("A","positive"), ("B","C0"), ("B","C1")]
    pair_index = {(p["panel"],p["case"],p["block"]): p for p in meta["pairs"]}
    pairs, series, sums = [], {}, {}
    for panel, case in cases:
        ratios = []
        for block in range(1,13):
            base, cand = (times[panel,case,block,k] for k in ["SIMPLE","LOCAL"])
            p = pair_index[panel,case,block]
            same([base,cand], [p["SIMPLE_s"],p["LOCAL_s"]])
            ratios.append(cand/base)
            pairs.append(dict(panel=panel, case=case, block=block, SIMPLE_s=base, LOCAL_s=cand,
                              SIMPLE_request=p["SIMPLE_request"], LOCAL_request=p["LOCAL_request"],
                              ratio=cand/base, reduction_pct=reduction(cand/base)))
        series[case] = np.log(ratios)
    series["interaction"] = series["positive"] - series["negative"]
    series[ALL8] = (series["C0"] + series["C1"]) / 2
    rng = random.Random(20261117)
    draws = np.array([[rng.randrange(12) for _ in range(12)] for _ in range(10000)])
    for case, logs in series.items():
        panel = "A" if case in ("negative","positive","interaction") else "B"
        official = meta["results"][panel][case]
        s = stats(logs, logs[draws].mean(axis=1))
        same(logs, official["block_log_ratios"])
        same([s["ratio"],s["lo"],s["hi"]], [official["ratio"]]+official["reduction_percent_CI95"])
        sums[case] = dict(s, role="primary" if panel+"/"+case in meta["primary_endpoints"] else "supporting",
                          clock="selected 32B verify-through-commit" if panel=="A" else "8B two-turn response plus reset",
                          estimand="ratio of LOCAL/SIMPLE ratios" if case=="interaction" else "geometric LOCAL/SIMPLE time ratio",
                          blocks=12, blocks_ratio_below_one=int((logs<0).sum()))
    write_csv("f03_native_pairs.csv", pairs)
    write_csv("f03_block_effects.csv", [dict(endpoint=k,block=i+1,log_ratio=v,ratio=np.exp(v),
              reduction_pct="" if k=="interaction" else reduction(np.exp(v)),
              clock=sums[k]["clock"],role=sums[k]["role"])
             for k,z in series.items() for i,v in enumerate(z)])
    return dict(times=times,pairs=pairs,series=series,sums=sums)


def rtx():
    raw = native_rows("artifact/scientific_data/RTX269_ALL_REQUESTS.csv")
    formal = [r for r in raw if (r["included"],r["stage"],r["role"])==("True","formal","measured")]
    assert len(raw)==1764 and len(formal)==864
    ref = frozen(CR+"figure_data.json")
    assert ref["source_head"] == R269
    lookup = {(int(r["root_slot"]),int(r["round"]),r["study_variant"]):r for r in formal}
    assert len(lookup)==864 and all(int(r["time_block"])==int(r["round"])//2 for r in formal)
    for r in native_rows(CR+"NATIVE_FORMAL_TIMES.csv"):
        rr = lookup[int(r["root_slot"]),int(r["round"]),r["arm"]]
        same([float(r[k+"_s"]) for k in PHASE],[float(rr[k+"_s"]) for k in PHASE])
    with (INPUT/"rtx269-frozen-draws.jsonl").open() as file:
        draws = [json.loads(line) for line in file]
    ir, ib = (np.array([d[k] for d in draws]) for k in ("roots","blocks"))
    assert ir.shape==(10000,24) and ib.shape==(10000,6)
    assert np.all(ir[:,:12] < 12) and np.all(ir[:,12:] >= 12)
    assert np.all((0<=ib)&(ib<6)) and np.all((0<=ir)&(ir<24))
    cells, roots, blocks, all_phases, sums = [], [], [], [], {}
    for key in R_KEYS:
        a,b = key.split("/")
        logs = np.array([[math.log(float(lookup[i,j,a]["service_s"])/float(lookup[i,j,b]["service_s"]))
                          for j in range(12)] for i in range(24)])
        grid = logs.reshape(24,6,2).mean(axis=2)
        s = stats(grid, grid[ir[:,:,None],ib[:,None,:]].mean(axis=(1,2)))
        official = ref["estimates"][key]
        same([s["pct"],s["lo"],s["hi"]], [official["reduction_percent"]]+official["reduction_ci95"])
        for i in range(24):
            sample = lookup[i,0,a]
            refroot = next(r for r in ref["roots"] if r["root_slot"]==i)
            assert sample["root"]==refroot["root"] and sample["domain"]==("code" if i<12 else "math")
            rr = float(np.exp(grid[i].mean()))
            same(rr,refroot[key])
            roots.append(dict(contrast=key,slot=i,domain=sample["domain"],root=sample["root"],
                              ratio=rr,reduction_pct=reduction(rr)))
            for t in range(6):
                cells.append(dict(contrast=key,slot=i,root=sample["root"],time_block=t,
                            rounds=f"{2*t},{2*t+1}",log_ratio=grid[i,t],
                            candidate_ids=";".join(lookup[i,j,a]["request_id"] for j in (2*t,2*t+1)),
                            control_ids=";".join(lookup[i,j,b]["request_id"] for j in (2*t,2*t+1))))
        for t in range(6):
            rb = float(np.exp(grid[:,t].mean()))
            same(rb,ref["blocks"][t][key])
            blocks.append(dict(contrast=key,block=t,ratio=rb,reduction_pct=reduction(rb)))
        dm = {p:float(1000*np.mean([float(lookup[i,j,a][p+"_s"])-float(lookup[i,j,b][p+"_s"])
                       for i in range(24) for j in range(12)])) for p in PHASE}
        grouped = {k:sum(dm[p] for p in components) for k,components in STAGES.items()}
        same(sum(grouped.values()),dm["service"])
        for p in PHASE:
            same(dm[p],official["phase_ms"][p])
            all_phases.append(dict(contrast=key,level="native_phase",component=p,candidate_minus_control_ms=dm[p],
                                   control_minus_candidate_ms=-dm[p]))
        for p,v in grouped.items():
            all_phases.append(dict(contrast=key,level="group",component=p,candidate_minus_control_ms=v,
                                   control_minus_candidate_ms=-v))
        sums[key] = dict(s,role=official["role"],crossed_root_block=True,
                         roots_below_one=int((grid.mean(axis=1)<0).sum()),
                         blocks_below_one=int((grid.mean(axis=0)<0).sum()),
                         candidate_minus_control_ms=dict(grouped,service=dm["service"]))
    write_csv("f04_root_effects.csv",roots)
    write_csv("f04_block_effects.csv",blocks)
    write_csv("f04_root_block_cells.csv",cells)
    write_csv("f04_arithmetic_phases.csv",all_phases)
    return dict(roots=roots,sums=sums,dispatch=ref["dispatch"],counts=dict(Counter(
                f'{r["included"]}/{r["stage"]}/{r["role"]}' for r in raw)))


def ranks(v):
    _, inv, counts = np.unique(v,return_inverse=True,return_counts=True)
    return (np.cumsum(counts)-(counts-1)/2)[inv]


def prefill():
    paired = native_rows(CP+"estimates/paired_request_times.csv")
    workload = native_rows(CP+"estimates/workload_roots.csv")
    refs = {(r["study_pr"],r["contrast"]):r for r in frozen(CP+"all_point_estimates_and_intervals.json")["modern_effects"]}
    old = frozen("data/plot_data.json")
    roots, summaries, native, study = [], {}, [], {}
    for pr,nroots,nrounds in [(257,12,4),(255,24,2)]:
        profiles = {z["source_commit"] for z in old["modern"] if z["pr"]==pr}
        assert profiles=={P4_SHAS[pr]}
        meta = {r["root"]:r for r in workload if int(r["study_pr"])==pr}
        by_stratum = sorted(meta,key=lambda name:(meta[name]["domain"],name))
        by_length = sorted(meta,key=lambda name:(int(meta[name]["prompt_tokens"]),name))
        assert Counter(r["domain"] for r in meta.values())=={"code":nroots//2,"math":nroots//2}
        rng = random.Random(20261116)
        draws = np.array([[i+rng.randrange(nroots//2) for i in (0,nroots//2) for j in range(nroots//2)]
                          for d in range(10000)])
        distinct_arms = {}
        lengths = [int(meta[r]["prompt_tokens"]) for r in by_length]
        displayed = [int(meta[r]["display_tokens"]) for r in by_length]
        study[pr] = dict(n=nroots,rounds=nrounds,prompt_min=min(lengths),prompt_max=max(lengths),
                         display_min=min(displayed),display_max=max(displayed))
        summaries[pr] = {}
        for k in P_KEYS:
            cand,ctrl = k.split("/")
            sub = defaultdict(dict)
            for r in paired:
                if int(r["study_pr"])!=pr or r["contrast"]!=k:
                    continue
                root,j = r["root"],int(r["round"])
                ca,co = float(r["candidate_s"]),float(r["control_s"])
                assert j not in sub[root] and r["domain"]==meta[root]["domain"]
                same(ca/co,float(r["ratio"]))
                sub[root][j] = math.log(ca/co)
                for arm,time in [(cand,ca),(ctrl,co)]:
                    ix = root,j,arm
                    if ix in distinct_arms:
                        same(distinct_arms[ix],time)
                    distinct_arms[ix]=time
                native.append(dict(study_pr=pr,contrast=k,root=root,domain=r["domain"],round=j,
                                   control_s=co,candidate_s=ca,ratio=ca/co))
            assert set(sub)==set(by_stratum)
            assert all(set(z)==set(range(1,nrounds+1)) for z in sub.values())
            ls = np.array([np.mean([sub[root][j] for j in sorted(sub[root])]) for root in by_stratum])
            s = stats(ls,ls[draws].mean(axis=1))
            official = refs[pr,k]
            same([s["pct"],s["lo"],s["hi"]], [official["reduction_percent"]]+official["ci95_reduction_percent"])
            rr = {z["root"]:z for z in official["root_points"]}
            for rank,root in enumerate(by_length,1):
                ix=by_stratum.index(root)
                ratio=float(np.exp(ls[ix]))
                same(ratio,rr[root]["ratio"])
                roots.append(dict(study_pr=pr,contrast=k,root=root,domain=meta[root]["domain"],
                                  prompt_tokens=int(meta[root]["prompt_tokens"]),output_tokens=int(meta[root]["display_tokens"]),
                                  length_rank=rank,rounds=nrounds,ratio=ratio,reduction_pct=reduction(ratio)))
            sums = dict(s,nroots=nroots,rounds=nrounds,roots_below_one=int((ls<0).sum()))
            if k=="SD_P4/SD_C4":
                sums["exploratory_length_spearman"] = float(np.corrcoef(
                    ranks([int(meta[z]["prompt_tokens"]) for z in by_stratum]),ranks(reduction(np.exp(ls))))[0,1])
            summaries[pr][k] = sums
        assert len(distinct_arms) == nroots*nrounds*4 == 192
    assert len(roots)==108 and len(native)==288
    slower = [r for r in roots if r["ratio"]>1]
    assert [(r["study_pr"],r["root"],r["contrast"],r["length_rank"]) for r in slower]==[
           (257,"CodeContests/train/279","SD_P4/TO_P4",12)]
    write_csv("f05_root_effects.csv",roots)
    write_csv("f05_native_contrast_pairs.csv",native)
    return dict(roots=roots,sums=summaries,studies=study)


class Page:
    """Fixed physical layout; the same call draws and exports each artist."""
    def __init__(self,stem,height):
        self.stem,self.h = stem,height
        self.f = plt.figure(figsize=(W/72,height/72),dpi=144,facecolor=WHITE)
        self.ax = self.f.add_axes([0,0,1,1])
        self.ax.set(xlim=(0,W),ylim=(height,0))
        self.ax.set_axis_off()
        self.recs,self.texts = [],[]

    def put(self,artist,kind,x,y,key="",**data):
        gid=f"{self.stem}-{len(self.recs)+1:04d}"
        artist.set_gid(gid)
        self.recs.append(dict(svg_id=gid,kind=kind,x_pt=x,y_pt=y,data_key=key,**data))
        return artist

    def text(self,x,y,s,*,ha="left",size=FS,weight="normal",color=INK,key=""):
        t=self.ax.text(x,y,s,va="center",ha=ha,size=size,color=color,weight=weight,zorder=8)
        self.texts.append(t)
        return self.put(t,"text",x,y,key,text=s,font_pt=size,weight=weight,align=ha,color=color)

    def line(self,x,y,x2,y2,*,color=GRID,lw=.55,style="-",key="",z=2):
        line,=self.ax.plot([x,x2],[y,y2],color=color,lw=lw,ls=style,zorder=z)
        return self.put(line,"line",x,y,key,x2_pt=x2,y2_pt=y2,color=color,stroke_pt=lw,dash=str(style))

    def mark(self,x,y,shape,size,c,*,fill=None,lw=.7,key="",z=5):
        face=c if fill is None else fill
        line,=self.ax.plot([x],[y],linestyle="none",marker=shape,markersize=size,
                           markeredgewidth=lw,markeredgecolor=c,markerfacecolor=face,zorder=z)
        return self.put(line,"point",x,y,key,shape=shape,diameter_pt=size,stroke_pt=lw,color=c,fill=face)

    def bar(self,x1,ya,x2,yb,c,key,fill=None):
        y1,y2=sorted((ya,yb))
        p=Rectangle((x1,y1),x2-x1,y2-y1,edgecolor=c,facecolor=fill or c,
                    linewidth=.7,joinstyle="miter",zorder=3)
        self.ax.add_patch(p)
        return self.put(p,"rect",x1,y1,key,x2_pt=x2,y2_pt=y2,color=c,fill=fill or c)

    def whisker(self,x,point,lo,hi,c,*,key):
        self.line(x,lo,x,hi,color=c,lw=1.15,key=key+":interval",z=4)
        for py,which in [(lo,"lo"),(hi,"hi")]:
            self.line(x-2.6,py,x+2.6,py,color=c,lw=.85,key=key+":"+which,z=4)
        self.mark(x,point,"D",4.1,c,lw=.55,key=key+":estimate",z=6)

    def rule(self,y):
        self.line(4,y,W-4,y,color=GRID,lw=.65)

    def section(self,x,y,letter,label):
        self.text(x,y,letter,color=NAVY,weight="bold",size=HEAD)
        self.text(x+14,y,label,size=HEAD)

    def save(self):
        self.f.canvas.draw()
        rend=self.f.canvas.get_renderer()
        scale=72/self.f.dpi
        bbs=[s.get_window_extent(rend) for s in self.texts]
        # Check every editable label against the actual physical page and every other label.
        for i,(t,bb) in enumerate(zip(self.texts,bbs)):
            if min(bb.x0,bb.y0)<-.15 or bb.x1>W/scale+.15 or bb.y1>self.h/scale+.15:
                raise ValueError(f"{self.stem} out-of-bounds: {t.get_text()} {bb}")
            for j,other in enumerate(bbs[:i]):
                dx=min(other.x1,bb.x1)-max(other.x0,bb.x0)
                dy=min(other.y1,bb.y1)-max(other.y0,bb.y0)
                if dx*scale>.3 and dy*scale>.65:
                    raise ValueError(f"{self.stem} text collision: {self.texts[j].get_text()!r}, {t.get_text()!r} "
                                     f"({dx*scale:.2f} by {dy*scale:.2f} pt)")
        directory=ROOT/("alternatives" if self.stem==ALT else "figures")
        directory.mkdir(exist_ok=True)
        description=json.loads((OUT/"captions.json").read_text())[self.stem]["description"]
        self.f.savefig(directory/(self.stem+".pdf"),metadata={"Creator":"HeteroSpec independent atelier",
                       "Title":self.stem,"Subject":description,"CreationDate":STAMP,"ModDate":STAMP})
        self.f.savefig(directory/(self.stem+".svg"),metadata={"Creator":"HeteroSpec independent atelier",
                       "Title":self.stem,"Description":description,"Date":"2026-11-18"})
        write_csv(self.stem+"_marks.csv",self.recs)
        plt.close(self.f)
        return dict(stem=self.stem,width_pt=W,height_pt=self.h,min_font_pt=min(t.get_fontsize() for t in self.texts),
                    editable_text_labels=len(self.texts),artists=len(self.recs),corrected_label_collisions=0,
                    point_keys=sum(bool(r["data_key"]) and r["kind"]=="point" for r in self.recs))


def linear(value,lo,hi,x0,x1):
    return x0+(value-lo)/(hi-lo)*(x1-x0)


def legend_symbol(p,x,y,s,text,color,fill=None,size=4.0):
    p.mark(x,y,s,size,color,fill=fill)
    p.text(x+6,y,text)


def draw_confirmation(a):
    p=Page(F3,274)
    ss=a["sums"]
    p.section(4,8,"A","32B · two fixed histories")
    p.section(204,8,"B","8B · target-only service")
    p.text(4,21,"Selected verification through commit",color=MUTED)
    p.text(204,21,"Two conversations · response + reset",color=MUTED)
    legend_symbol(p,31,36,"o","Noncrossing",NAVY,WHITE)
    legend_symbol(p,109,36,"^","Crossing",TEAL)
    legend_symbol(p,224,36,"o","C0",MUTED,WHITE,3.6)
    legend_symbol(p,254,36,"s","C1",MUTED,WHITE,3.6)
    legend_symbol(p,284,36,"D","Equal weight",NAVY)
    p.text(4,50,"Block",size=8,color=MUTED)
    p.text(204,48,"Block",size=8,color=MUTED)
    xA=lambda q:linear(q,-6,27,31,186)
    xB=lambda q:linear(q,-6,27,218,389)
    def yy(i): return 59+9.1*i
    for xf in [xA,xB]:
        for tick in [-5,0,10,20]:
            xx=xf(tick)
            p.line(xx,51,xx,yy(11)+5,color=MUTED if tick==0 else LIGHT,lw=.7 if tick==0 else .5)
            p.text(xx,yy(11)+12,fmt(tick,0),ha="center",size=8,color=MUTED)
    for i in range(12):
        y=yy(i)
        p.text(20,y,str(i+1),ha="right",size=8,color=MUTED)
        p.text(208,y,str(i+1),ha="right",size=7.6,color=MUTED)
        vals={k:reduction(np.exp(a["series"][k][i])) for k in ("negative","positive",ALL8,"C0","C1")}
        key=lambda k:f"266:{k}:block={i+1}"
        p.line(xA(vals["negative"]),y,xA(vals["positive"]),y,color="#A2BDB9",lw=.75,
               key=key("negative+positive"))
        p.mark(xA(vals["negative"]),y,"o",3.9,NAVY,fill=WHITE,key=key("negative"))
        p.mark(xA(vals["positive"]),y,"^",4.5,TEAL,key=key("positive"))
        # Three rails make even a nearly identical C0/C1 block auditable.
        p.line(xB(vals["C0"]),y-2.7,xB(vals["C1"]),y+2.7,color="#A7B5BF",lw=.65,key=key("C0+C1"))
        p.mark(xB(vals["C0"]),y-2.7,"o",3.1,MUTED,fill=WHITE,lw=.65,key=key("C0"))
        p.mark(xB(vals["C1"]),y+2.7,"s",2.7,MUTED,fill=WHITE,lw=.6,key=key("C1"))
        p.mark(xB(vals[ALL8]),y,"D",3.6,NAVY,lw=.45,key=key(ALL8))
    p.text(W/2,184,"LOCAL time reduction (%)   ·   right of zero = less time",ha="center")
    p.rule(194)
    p.text(4,204,"Geometric reduction, % [95% CI]",weight="bold")
    p.text(204,204,"Geometric reduction, % [95% CI]",weight="bold")
    for k,y,x,xend in [("negative",218,4,191),("positive",230,4,191),
                       (ALL8,218,204,390),("C0",230,204,390),("C1",242,204,390)]:
        isprim=ss[k]["role"]=="primary"
        name={"negative":"Noncrossing","positive":"Crossing",ALL8:"Equal weight",
              "C0":"C0","C1":"C1"}[k]
        p.text(x,y,name+(" · primary" if isprim else " · supp."),size=8,weight="bold" if isprim else "normal")
        p.text(xend,y,pci(ss[k]),ha="right",size=8,color=NAVY if isprim else INK,key="266:"+k+":estimate_ci")
    p.rule(252)
    p.text(4,264,"32B paired interaction · crossing / noncrossing",weight="bold")
    p.text(390,264,rci(ss["interaction"]),ha="right",color=TEAL,weight="bold",key="266:interaction:ratio_ci")
    return p.save()


def draw_alternate(a):
    p=Page(ALT,294)
    p.text(4,8,"Paired arm times in execution order",weight="bold",size=HEAD)
    legend_symbol(p,280,8,"o","SIMPLE",MUTED,WHITE)
    legend_symbol(p,343,8,"s","LOCAL",TEAL)
    p.rule(18)
    p.section(4,29,"A","32B · selected verification through commit (ms)")
    p.section(4,159,"B","8B target-only · two-turn response plus reset (s)")
    for panel,case,title,left,top,low,high,ticks in [
        ("A","negative","Noncrossing · primary",0,56,69,105,[70,85,100]),
        ("A","positive","Crossing · supporting",201,56,69,105,[70,85,100]),
        ("B","C0","Conversation 0 · supporting",0,186,7.9,13.4,[8,10,12]),
        ("B","C1","Conversation 1 · supporting",201,186,7.9,13.4,[8,10,12])]:
        p.text(left+24,top-13,title,weight="bold")
        xx=lambda i:left+25+i*(158/11)
        yf=lambda v:linear(v,low,high,top+48,top)
        for tick in ticks:
            p.line(xx(0)-4,yf(tick),xx(11)+4,yf(tick),color=GRID,lw=.48)
            p.text(left+17,yf(tick),str(tick),ha="right",color=MUTED,size=8)
        for i in range(12):
            val={arm:a["times"][panel,case,i+1,arm]*(1000 if panel=="A" else 1) for arm in ("SIMPLE","LOCAL")}
            assert all(low<=v<=high for v in val.values()),val
            key=f"266:{case}:block={i+1}"
            x,y0,y1=xx(i),yf(val["SIMPLE"]),yf(val["LOCAL"])
            # Within-block offsets keep both native values visible even when their times tie.
            p.line(x-1.25,y0,x+1.25,y1,color="#9AADB0",lw=.74,key=key+":pair")
            p.mark(x-1.25,y0,"o",3.45,MUTED,fill=WHITE,lw=.7,key=key+":SIMPLE")
            p.mark(x+1.25,y1,"s",3.05,TEAL,lw=.5,key=key+":LOCAL")
        for i in [0,3,7,11]:
            p.text(xx(i),top+57,str(i+1),ha="center",color=MUTED,size=8)
        p.text(left+24,top+70,pci(a["sums"][case],unit="%"),color=TEAL,key="266:"+case+":estimate_ci")
    p.text(4,141,"Supporting 32B interaction (ratio of ratios)",weight="bold")
    p.text(390,141,rci(a["sums"]["interaction"]),ha="right",color=TEAL,key="266:interaction:ratio_ci")
    p.rule(150)
    p.text(4,273,"Primary 8B reduction · equal conversation weight",weight="bold")
    p.text(390,273,pci(a["sums"][ALL8],unit="%"),ha="right",color=NAVY,key="266:"+ALL8+":estimate_ci")
    p.text(4,287,"Horizontal positions: observed blocks 1–12. Brackets: individual 95% block intervals.",color=MUTED)
    return p.save()


def draw_rtx(a):
    p=Page(F4,286)
    p.section(4,8,"A","Dispatch controls")
    p.text(390,8,"Same binary · shared prep · SIMPLE fixed · P4 off",ha="right",size=8,color=MUTED)
    for x,arm,desc,org in [(5,"B","Scalar loop","q calls · 1 column/group"),(136,"C1","Scalar groups","1 call · 1 column/group"),
                           (267,"C4","Few-column arithmetic","1 call · q columns/group")]:
        p.text(x,25,arm,weight="bold",color=TEAL if arm=="C4" else NAVY)
        p.text(x+19,25,desc)
        p.text(x,38,org,color=MUTED)
    p.rule(48)
    p.section(4,60,"B","Complete-request reduction (%)")
    p.text(4,73,"Reset → final sync · 24 roots × 6 blocks × 2 rounds",color=MUTED)
    p.text(390,73,"Above zero = time saved",ha="right",color=MUTED)
    yf=lambda v:linear(v,-5,30,159,102)
    for j,(k,left) in enumerate(zip(R_KEYS,(29,151,273))):
        col=NAVY if j==0 else TEAL
        p.text(left,89,k+(" · primary" if j==0 else " · descriptive"),weight="bold" if j==0 else "normal",color=col)
        for t in [0,15,30]:
            y=yf(t)
            p.line(left-4,y,left+110,y,color=MUTED if t==0 else LIGHT,lw=.65 if t==0 else .5)
            if j==0:p.text(left-8,y,str(t),ha="right",size=8,color=MUTED)
        p.line(left+84,101,left+84,158,color=GRID,lw=.5,style=(0,(1.5,2)))
        for rec in [r for r in a["roots"] if r["contrast"]==k]:
            i=rec["slot"]
            xx=left+i*3.12+(4 if i>=12 else 0)
            p.mark(xx,yf(rec["reduction_pct"]),"o",2.7,col,fill=WHITE if i<12 else col,
                   lw=.58,key=f"269:{k}:slot={i}:root={rec['root']}")
        s=a["sums"][k]
        p.whisker(left+98,yf(s["pct"]),yf(s["lo"]),yf(s["hi"]),col,key=f"269:{k}:crossed")
        for dx,lab in [(17,"code"),(58,"math"),(98,"all")]:
            p.text(left+dx,167,lab,ha="center",size=8,color=MUTED)
        p.text(left+48,181,pci(s),ha="center",size=8,color=col,key=f"269:{k}:estimate_ci")
    p.rule(191)
    p.section(4,202,"C","Arithmetic mean savings (ms)")
    p.text(390,202,"B minus C1",ha="right",color=MUTED)
    yf=lambda v:linear(v,-103,125,257,215)
    cols=[49,122,195,268,341]
    full=a["sums"]["C1/B"]["candidate_minus_control_ms"]
    zero=yf(0)
    p.line(23,zero,381,zero,color=MUTED,lw=.65)
    p.text(16,zero,"0",ha="right",size=8,color=MUTED)
    running=0
    for i,(k,label,x) in enumerate(zip(["verify","prefill","draft","remaining","service"],
                                       ["Verification","Prefill","Draft","Residual","Net service"],cols)):
        saving=-full[k]
        old=running if i!=4 else 0
        new=old+saving
        clr=NAVY if i==4 else TEAL if saving>0 else RUST
        if i!=4:
            p.line(x+15,yf(new),cols[i+1]-15,yf(new),color=MUTED,lw=.6,style=(0,(2,1.6)),
                   key="269:C1/B:running_after="+k)
            running=new
        else:same(new,running)
        p.bar(x-15,yf(old),x+15,yf(new),clr,"269:C1/B:waterfall="+k,
              fill=WHITE if i==4 else clr)
        p.text(x,266,label,ha="center",size=8)
        p.text(x,278,fmt(saving,plus=True),ha="center",size=8.2,color=clr,weight="bold",
               key="269:C1/B:arithmetic_ms_saved="+k)
    return p.save()


def draw_prefill(a):
    p=Page(F5,299)
    for pr,x,letter,gpu,model in [(257,4,"A","RTX A5000","Qwen3-32B / Qwen3-0.6B"),
                                  (255,204,"B","GeForce RTX 5070 Ti Laptop","Llama-3.1-8B / Llama-3.2-1B")]:
        st=a["studies"][pr]
        p.section(x,8,letter,gpu)
        p.text(x,21,model)
        p.text(x,33,f"{st['n']} roots × {st['rounds']} rounds · {st['prompt_min']}–{st['prompt_max']} prompt tokens",
               size=8,color=MUTED)
    p.rule(43)
    for i,(k,title) in enumerate(zip(P_KEYS,["Target-only packing · P4 / C4","Speculative packing · P4 / C4",
                                            "Speculation at fixed P4 · speculative / target-only"])):
        y=54+i*72
        p.text(4,y,title)
        yf=lambda v:linear(v,-5,60,y+53,y+12)
        for pr,left,right,ag in [(257,27,150,182),(255,224,347,379)]:
            s=a["sums"][pr][k]
            n=s["nroots"]
            for t in (0,30,60):
                p.line(left-3,yf(t),ag+6,yf(t),color=MUTED if t==0 else LIGHT,lw=.63 if t==0 else .48)
                if pr==257:p.text(left-9,yf(t),str(t),ha="right",color=MUTED,size=8)
            p.line(ag-14,y+11,ag-14,y+53,color=GRID,lw=.5,style=(0,(1.5,2)))
            for rec in [r for r in a["roots"] if r["study_pr"]==pr and r["contrast"]==k]:
                rank=rec["length_rank"]
                xx=linear(rank,1,n,left,right)
                key=f"{pr}:{k}:rank={rank}:root={rec['root']}"
                isout=rec["root"]=="CodeContests/train/279" and k==P_KEYS[2]
                clr=RUST if isout else NAVY if pr==257 else TEAL
                if isout:
                    # The annotated diamond has exactly the same coordinates as its source root.
                    p.line(xx,yf(rec["reduction_pct"])-2.8,xx,yf(39),color=RUST,lw=.68,key=key+":leader")
                    p.line(xx,yf(39),xx-6,yf(39),color=RUST,lw=.68,key=key+":leader")
                    p.text(xx-8,yf(39),f"train/279 · {fmt(rec['reduction_pct'])}%",ha="right",
                           color=RUST,size=8,key=key+":annotation")
                p.mark(xx,yf(rec["reduction_pct"]),"D" if isout else "o",4.5 if isout else 3.0,
                       clr,fill=WHITE if isout else clr,lw=.75 if isout else .45,key=key)
            col=NAVY if pr==257 else TEAL
            p.whisker(ag,yf(s["pct"]),yf(s["lo"]),yf(s["hi"]),col,key=f"{pr}:{k}:stratified")
            p.text((left+ag)/2,y+62,pci(s,unit="%"),ha="center",size=8,color=col,key=f"{pr}:{k}:estimate_ci")
    p.rule(268)
    p.text(4,279,"Root rank (prompt-length order)")
    p.mark(247,279,"D",4.0,NAVY)
    p.text(255,279,"Estimate [95% interval]")
    p.text(4,291,"Resident-request reduction (%) · above zero = less candidate time",color=MUTED)
    return p.save()


def main():
    provenance=freeze_inputs()
    a,r,p=confirmation(),rtx(),prefill()
    fields=[draw_confirmation(a),draw_alternate(a),draw_rtx(r),draw_prefill(p)]
    emit("source_provenance.json",provenance)
    emit("frozen_evidence.json",{
        "fig3":{"source":"#266: 96 native values, 48 pairs", "whole_block_rng":"CPython random.Random(20261117), randrange(12), 10000 x 12; shared across six endpoints",
                "clock_A":"32B first transaction: verification through trim/commit and sync; owned-row copies and decisions included, no history preparation/live drafting",
                "clock_B":"8B target-only: complete two-turn controller response plus reset, including common CPU sampling/control",
                "conditioning":"same two selected histories of one root / two fixed conversations over 12 measured time blocks; blocks are not independent inputs",
                "mark_mapping":"Lines connect only case effects within the same block, not successive blocks. The left panel pairs noncrossing/crossing; the right panel pairs C0/C1 and adds their equal-log-weight diamond. Confidence intervals are printed numbers, not bars.",
                "estimators":a["sums"]},
        "fig4":{"source":"#269: complete ledger, intersect included=True,stage=formal,role=measured",
                "clock":"resident request: reset, prefill, target work, live drafting, outputs, decision/commit, terminal sync; no loading/context-pool setup/post-clock exports",
                "crossed_draws":"10000 frozen stratified root and independent whole-block index vectors; two log ratios averaged per root/block",
                "waterfall":"Arithmetic B minus C1 mean milliseconds; its net uses unrounded phase values, so no strict sum of the rounded labels is asserted. It is a separate estimand from the geometric percentage effects.",
                "roles":r["counts"],"dispatch":r["dispatch"],"estimators":r["sums"]},
        "fig5":{"source":"#257 and #255; 192 distinct eligible arm requests per deployment",
                "clock":"complete resident request with reset, prefill, target, live draft if applicable, decisions/commit and final sync; no loading/context-pool setup/post-clock exports",
                "geometry":"A5000: q32 physically contiguous exposures; RTX: q32 plus admitted tail widths",
                "sharing":"Within each deployment the same four arms and roots are reused across three direct paired contrasts. The two studies have 12 and 24 roots: 36 study-specific root entries and 108 effect marks. No platform pairing, pooled draws or hardware comparison.",
                "horizontal_axis":"Root rank (prompt-length order): equally spaced ranks within each deployment, not proportional token distances or a causal length trend.",
                "root_draws":"Separate CPython random.Random(20261116) per deployment, 10000 draws of whole roots within fixed code and math strata, sorted by full root ID. Observed rounds stay together.",
                "studies":p["studies"],"estimators":p["sums"]}})
    emit("render_receipt.json",{"units":"PostScript points (72/in), top-left origin", "figures":fields,
         "CI_and_mark_numbers_verified_against_frozen_data":True,
         "root_and_native_counts":{"fig3_native_seconds":96,"fig4_native_selected_requests":864,
                                   "fig4_root_effect_marks":len(r["roots"]),"fig4_distinct_roots":24,
                                   "fig5_root_effect_marks":len(p["roots"]),"fig5_study_specific_roots":36}})
    print("Wrote 4 vector figure pairs; validated 96 confirmation times, 864 RTX requests, and 108 P4 root effects.")


if __name__=="__main__":
    main()
