"""Diagnostic Fig.5 alternative: observed prompt length on an actual axis.

Retained as an editable review attachment, not a replacement for the selected
six-cell rank plot or an additional numbered supplementary figure.
"""

if not __debug__:
    raise SystemExit("Optimized Python is unsupported: verification must remain enabled.")

import csv
import json
import os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("SOURCE_DATE_EPOCH","1794960000")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT=Path(__file__).resolve().parents[1]
D=ROOT/"inputs/scientific_data/statistics/prior_studies_recomputed"
PANEL=[("257","RTX A5000","Qwen3-32B", [40,100,180],(32,194)),
       ("255","RTX 5070 Ti Laptop","Llama-3.1-8B",[150,450,750],(125,780))]
ROWS=[("TO_P4/TO_C4","Target-only: P4 / C4"),("SD_P4/SD_C4","Speculative: P4 / C4"),
      ("SD_P4/TO_P4","At fixed P4: speculative / target-only")]
BLUE="#254B70";TEAL="#087B70";OCHRE="#A95524";INK="#23303A";GRAY="#626D76"


def read(name):
    with (D/"estimates"/name).open() as f:return list(csv.DictReader(f))


def ranks(x):
    _, inv, counts=np.unique(x,return_inverse=True,return_counts=True)
    return (np.cumsum(counts)-(counts-1)*.5)[inv]


def main():
    raw=read("paired_request_times.csv")
    lengths={(r["study_pr"],r["root"]):int(r["prompt_tokens"]) for r in read("workload_roots.csv")}
    summary={(str(r["study_pr"]),r["contrast"]):r for r in json.loads((D/"all_point_estimates_and_intervals.json").read_text())["modern_effects"]}
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":8,"axes.labelsize":8,"axes.titlesize":8.4,
        "xtick.labelsize":8,"ytick.labelsize":8,"text.color":INK,"axes.edgecolor":GRAY,
        "xtick.color":GRAY,"ytick.color":GRAY,"axes.linewidth":.55,"xtick.major.width":.55,"ytick.major.width":.55,
        "xtick.major.size":2.4,"ytick.major.size":2.4,"svg.fonttype":"none","pdf.fonttype":42,
        "svg.hashsalt":"heterospec-length-panel","figure.facecolor":"white","savefig.facecolor":"white"})
    fig=plt.figure(figsize=(5.477,4.80));coords=[];rho={}
    for col,(pr,hardware,model,ticks,xrange) in enumerate(PANEL):
        left=.109+col*.492;width=.385
        fig.text(left,.966,hardware,fontsize=8.5,color=INK)
        fig.text(left,.932,f"{model}  ·  "+("12 roots × 4 rounds" if pr=="257" else "24 roots × 2 rounds"),color=GRAY)
        for row,(contrast,label) in enumerate(ROWS):
            bottom=.694-row*.266
            if col==0:fig.text(left,bottom+.184,label,color=TEAL if row==2 else BLUE,fontsize=8)
            ax=fig.add_axes([left,bottom,width,.161])
            g=defaultdict(list)
            for r in raw:
                if (r["study_pr"],r["contrast"])==(pr,contrast):
                    g[r["root"]].append((int(r["round"]), np.log(float(r["candidate_s"])/float(r["control_s"]))))
            dx=xrange[1]-xrange[0]; xpos=xrange[1]+.21*dx
            ax.set_xlim(xrange[0],xrange[1]+.31*dx);ax.set_ylim(-6,65)
            ax.axvline(xrange[1]+.082*dx,color="#C2C9CB",lw=.6)
            ax.axhline(0,color="#858B90",ls=(0,(2,2)),lw=.6,zorder=0)
            ax.set_yticks([0,30,60]);ax.set_xticks([*ticks,xpos],list(map(str,ticks))+["All"])
            if col==1: ax.tick_params(axis="y",labelleft=False)
            if row!=2:ax.tick_params(axis="x",labelbottom=False)
            for spine in ("top","right"):ax.spines[spine].set_visible(False)
            vals=[];xs=[];side=summary[pr,contrast]; exp_roots={r["root"]:r["ratio"] for r in side["root_points"]}
            for idx,(root,obs) in enumerate(sorted(g.items())):
                assert len(obs)==(4 if pr=="257" else 2)
                ratio=float(np.exp(np.mean([v for _,v in obs])))
                assert abs(ratio-exp_roots[root])<1e-12
                val=100*(1-ratio); length=lengths[pr,root];xs.append(length);vals.append(val)
                adverse=(pr=="257" and contrast==ROWS[2][0] and root=="CodeContests/train/279")
                artist=ax.scatter([length],[val],marker="D" if adverse else "o",s=13 if adverse else 10,
                    facecolors="white" if adverse else "#677989",edgecolors=OCHRE if adverse else "white",
                    lw=1 if adverse else .32,zorder=3 if adverse else 2)
                gid=f"r{pr}-{row}-{idx}";artist.set_gid(gid)
                coords.append({"gid":gid,"study_pr":int(pr),"contrast":contrast,"root":root,"rounds":[i for i,_ in sorted(obs)],
                    "prompt_tokens":length,"reduction_pct":val,"status":"negative example" if adverse else "ordinary"})
            est=100*(1-np.exp(np.mean(np.log(1-np.array(vals)/100))))
            assert abs(est-side["reduction_percent"])<1e-10
            lo,hi=side["ci95_reduction_percent"]; color=TEAL if row==2 else BLUE
            ax.errorbar([xpos],[est],yerr=[[est-lo],[hi-est]],fmt="s",color=color,ms=4,lw=1.15,capsize=2.0)
            rho[f"{pr}:{contrast}"]=float(np.corrcoef(ranks(xs),ranks(vals))[0,1])
    fig.text(.022,.52,"Complete-request time reduction (%)",rotation=90,ha="center",va="center")
    fig.text(.54,.080,"Prompt length (tokens) within each study",ha="center")
    fig.text(.02,.022,"All: equal-root estimate and 95% CI.  Open diamond: A5000 train/279.",color=GRAY)
    assert len(coords)==108
    alt=ROOT/"alternatives";alt.mkdir(exist_ok=True)
    description=json.loads((ROOT/"results/captions.json").read_text())["f05_prompt_length"]["description"]
    for ext in ["pdf","svg"]:
        meta={"Creator":"HeteroSpec author comparison","Subject":description,"CreationDate":None,"ModDate":None} if ext=="pdf" else {"Creator":"HeteroSpec author comparison","Description":description,"Date":None}
        fig.savefig(alt/("f05_prompt_length."+ext),metadata=meta)
    plt.close(fig)
    out={"input_binding":"#276 scientific_data.zip, statistics/prior_studies_recomputed/estimates/{workload_roots,paired_request_times}.csv",
         "intervals":"all_point_estimates_and_intervals.json: modern_effects[study_pr,contrast].ci95_reduction_percent",
         "estimator":"100*(1-exp(mean over rounds of log(candidate_s/control_s))); equal log root weights in All; stratified whole-root 95% intervals",
         "descriptive_only":"No fitted curve or causal or between-deployment comparison. No new manuscript endpoint.",
         "selection":"Editable diagnostic attachment only; the formal Figure 5 remains the six-cell root-rank plot.",
         "sample_identity":{"study_257_roots":12,"study_255_roots":24,"study_specific_root_entries":36,"direct_contrasts_per_root":3,"effect_marks":108},
         "observed_root_marks":coords,"exploratory_within_panel_Spearman":rho}
    dest=ROOT/"results/f05_prompt_length_mapping.json";dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(out,indent=2)+"\n")


if __name__=="__main__":main()
