"""Historical #276 comparison builder; not the integrated manuscript entry point.

Kept for inherited helper functions imported by access.py. The default integrated
rebuild never invokes this module as a script. Its optional old preview route
uses the frozen #276 narrative, not the parent's final author manuscript.
No network; operates only on scratch copies.

`inventory` needs only the frozen ZIP. `preview` builds the complete paper + the
caption-only reader packet. `atlas` makes native-size old/new vector spreads.
"""

if not __debug__:
    raise SystemExit("Optimized Python is unsupported: verification must remain enabled.")

from pathlib import Path
from zipfile import ZipFile
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess

import pypdfium2 as pdf


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build"
OUT = ROOT / "preview"
MANUSCRIPT = "8224998c5aa3032476d669990e6ae20e10cd1fb0"
SOURCE = "26a99d9a3638ead1a27cdd38d9363813e94bdbb178bf7696582b9bd3844c969f"
ENV = dict(os.environ, SOURCE_DATE_EPOCH="1794960000", FORCE_SOURCE_DATE="1", TZ="UTC")
SECTIONS = ["introduction", "reference", "method", "implementation", "design", "results",
            "related", "discussion", "conclusion", "supplement"]
FIGS = ["f01_obligations","f02_local_lowering","f07_confirmation","f04_few_column",
        "f05_prefill","f06_b570","f03_transaction","f08_c4_initial"]
FIG_IDS = ["1","2","3","4","5","6","S1","S2"]
TABS = ["t01_dispatch","t02_qualification","t03_deployments","t04_studies","t05_m1",
        "t07_confirmation_natural","t06_neighbors","s01_local_pairs","s02_diagnostics",
        "s14_confirmation_effects","s15_confirmation_A","s16_confirmation_B","s17_confirmation_costs",
        "s18_rtx269_effects","s19_rtx269_blocks","s20_rtx269_roots","s21_rtx269_phases",
        "s11_direct_effects","s03_phase_costs","s06_m1_family","s07_m1_roots","s05_natural",
        "s04_ledger","s08_access","s09_pilot","s12_historical_geometry","s13_historical_applications"]
TAB_IDS = [str(i) for i in range(1,8)] + ["S"+str(i) for i in range(1,21)]
FIG_PAGES = [3,5,11,12,13,15,20,27]
TAB_PAGES = [6,7,8,9,14,14,16,21,21,22,22,23,23,24,25,25,26,27,28,28,29,29,30,31,31,32,32]
TOK = re.compile(r"\\paper(figure|table)(?:\[[^\]]*\])?(?=\{)")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def emit(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def groups(txt, pos, n):
    out = []
    for _ in range(n):
        assert txt[pos] == "{", (pos,txt[pos:pos+20])
        start = pos + 1
        depth = 1
        pos += 1
        while depth:
            c = txt[pos]
            if c == "\\":
                pos += 2
                continue
            depth += (c == "{") - (c == "}")
            pos += 1
        out.append((start,pos-1))
    return out


def tokens(txt):
    for m in TOK.finditer(txt):
        kind = m.group(1)
        bounds = groups(txt,m.end(),4 if kind=="figure" else 3)
        yield kind, bounds, [txt[a:b] for a,b in bounds]


def unpack(d):
    arch = ROOT/"inputs/arxiv_source.zip"
    assert sha(arch) == SOURCE
    d.mkdir(parents=True,exist_ok=True)
    with ZipFile(arch) as z:
        files = json.loads(z.read("MANIFEST.json"))["files"]
        for f in files:
            name = f["path"]
            dest = (d/name).resolve()
            assert d.resolve() in dest.parents
            payload = z.read(name)
            assert hashlib.sha256(payload).hexdigest() == f["sha256"]
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(payload)


def inventory():
    d = BUILD/"baseline"
    unpack(d)
    exhibits = {}
    for sec in SECTIONS+["rtx_confirmation"]:
        file = d/"sections"/(sec+".tex")
        for kind,bounds,(stem,caption,*rest) in tokens(file.read_text()):
            ids,stems,pages = (FIG_IDS,FIGS,FIG_PAGES) if kind=="figure" else (TAB_IDS,TABS,TAB_PAGES)
            i = stems.index(stem)
            assert stem not in exhibits
            exhibits[stem] = dict(id=ids[i],kind=kind,source_file="sections/"+file.name,
                                  asset=("figures/"+stem+".pdf" if kind=="figure" else "tables/"+stem+".tex"),
                                  label=rest[-1],baseline_page=pages[i],old_caption=caption,
                                  old_alt=rest[0] if kind=="figure" else None)
    assert set(exhibits)==set(FIGS+TABS)
    ordered = {name:exhibits[name] for name in FIGS+TABS}
    emit(ROOT/"provenance/EXHIBIT_INVENTORY.json",ordered)
    return ordered


def captions():
    fg = {}
    for directory in ("method","results","tail"):
        fg.update(json.loads((ROOT/directory/"captions.json").read_text()))
    tb = json.loads((ROOT/"table_design/captions.json").read_text())
    assert set(FIGS)<=set(fg) and set(TABS)<=set(tb)
    return fg,tb


def check_log(d, job, *, strict=True):
    text=(d/(job+".log")).read_text(errors="replace")
    patterns={"overfull":r"Overfull \\[hv]box[^\n]*","undefined":r"(?:Reference|Citation) [^\n]* undefined|There were undefined references",
              "missing_glyph":r"Missing character:[^\n]*","duplicate_destination":r"destination with the same identifier[^\n]*",
              "missing_destination":r"has been referenced but does not exist[^\n]*"}
    result={k:re.findall(v,text) for k,v in patterns.items()}
    if strict and any(result[k] for k in ("overfull","undefined","missing_glyph","duplicate_destination","missing_destination")):
        raise RuntimeError(f"{job}: {result}; see {d}/{job}.log")
    return result


def tex(d, job, main=False):
    if main:
        cmd=["latexmk","-norc","-pdf","-interaction=nonstopmode","-halt-on-error","-file-line-error",
             "-pdflatex=pdflatex -no-shell-escape %O %S",job+".tex"]
    else:
        cmd=["pdflatex","-no-shell-escape","-interaction=nonstopmode","-halt-on-error","-file-line-error",job+".tex"]
    run=subprocess.run(cmd,cwd=d,env=ENV,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (d/(job+".driver.txt")).write_bytes(run.stdout)
    if run.returncode:
        raise RuntimeError(f"{d}/{job}: {run.stdout[-5000:].decode(errors='replace')}")


def prepare(exhibits):
    old=BUILD/"baseline"; new=BUILD/"candidate"
    unpack(new)
    figcap,tabcap=captions()
    for s in FIGS:
        shutil.copyfile(ROOT/f"figures/{s}.pdf",new/f"figures/{s}.pdf")
    for s in TABS:
        shutil.copyfile(ROOT/f"tables/{s}.tex",new/f"tables/{s}.tex")
    edits={}
    for file in sorted((new/"sections").glob("*.tex")):
        text=file.read_text()
        changes=[]
        for kind,b,v in tokens(text):
            s=v[0]
            c=figcap[s] if kind=="figure" else {"caption":tabcap[s]}
            if isinstance(c["caption"],dict):
                c["caption"]=c["caption"]["caption"]
            changes.append((*b[1],c["caption"]))
            if kind=="figure":
                changes.append((*b[2],c["description"]))
        for a,b,replacement in sorted(changes,reverse=True):
            text=text[:a]+replacement+text[b:]
        if file.name=="design.tex":
            # The local TeX Live 2025 build of the unchanged source spills 10.95pt
            # on this paragraph. Offer a break at an existing slash, changing no text.
            text=text.replace("16 APPS/MATH roots and four sessions",
                              r"16 APPS/\allowbreak{}MATH roots and four sessions")
        file.write_text(text)
        if changes: edits[file.name]=len(changes)
    # Removing exactly the caption/alt groups must recover the original narrative byte-for-byte.
    def mask(text):
        spans=[span for k,b,v in tokens(text) for span in b[1:(3 if k=="figure" else 2)]]
        for a,b in sorted(spans,reverse=True): text=text[:a]+"<caption>"+text[b:]
        return text.replace(r"APPS/\allowbreak{}MATH","APPS/MATH")
    for p in old.glob("sections/*.tex"):
        assert mask(p.read_text())==mask((new/"sections"/p.name).read_text())
    for name in ["main.tex","preamble.tex","references.bib","acmart.cls"]:
        assert sha(old/name)==sha(new/name)
    return new,edits


def pages_of(path):
    with pdf.PdfDocument(path) as doc:
        return len(doc),[list(doc[i].get_size()) for i in range(len(doc))]


def labels(aux):
    # acmart's numeric citations use natbib. Preserve the original resolved values for
    # detachable exhibits, but disable links to targets outside this standalone packet.
    return "\n".join(s for s in aux.splitlines() if s.startswith((r"\newlabel{",r"\bibcite{")))


def packet(d, exhibits, *, versions, name, stems, old_dir=None):
    old_dir = old_dir or BUILD/"baseline"
    fg,tb=captions()
    pre = r"""\documentclass[acmsmall,screen,nonacm]{acmart}
\input{preamble}
\hypersetup{draft}
\makeatletter\input{proof-labels.tex}\makeatother
\begin{document}
\pagestyle{empty}
\newcommand{\eyebrow}[2]{\noindent{\sffamily\small #1\hfill #2}\par\vspace{3pt}\hrule height .35pt\vspace{10pt}}
"""
    (d/"proof-labels.tex").write_text(labels((d/"main.aux").read_text()))
    pieces=[pre]
    for stem in stems:
        e=exhibits[stem]; title=("Figure " if e["kind"]=="figure" else "Table ")+e["id"]
        for ver in versions:
            before=ver=="276"
            tag="Frozen author edition / PR 276" if before else "Independent candidate / author comparison"
            cap=e["old_caption"] if before else (fg[stem]["caption"] if e["kind"]=="figure" else tb[stem])
            asset=(old_dir/e["asset"]).relative_to(BUILD) if before else (d/e["asset"]).relative_to(BUILD)
            rel="../"+str(asset)
            body=(r"\noindent\includegraphics[width=\linewidth]{"+rel+"}\\par" if e["kind"]=="figure"
                  else r"\begingroup\centering\input{"+rel+r"}\par\endgroup")
            captex=r"{\small\noindent "+r"\textsc{"+title+r".} "+cap+r"\par}"
            pieces.append(r"\thispagestyle{empty}\eyebrow{"+title+"}{"+tag+"}\n"
                          +(body+"\n\\vspace{8pt}\n"+captex if e["kind"]=="figure" else captex+"\n\\vspace{6pt}\n"+body)
                          +"\n\\clearpage\n")
    (d/(name+".tex")).write_text("\n".join(pieces)+"\\end{document}\n")
    tex(d,name,main=True)
    actual=pages_of(d/(name+".pdf"))[0]
    assert actual==len(stems)*len(versions),(name,actual,len(stems),len(versions))
    return check_log(d,name)


def spreads(d,items,name):
    # Two complete 6.75 x 10 inch leaves; no downsampling, scaling, cropping or margins.
    text=r"""\documentclass{article}
\usepackage{graphicx}
\usepackage[paperwidth=13.5in,paperheight=10in,margin=0in]{geometry}
\begin{document}
\pdfpagewidth=13.5in\pdfpageheight=10in
\pdfhorigin=0pt\pdfvorigin=0pt
"""
    for l,r in items:
        def panel(side):
            f,n=side
            return r"\includegraphics[page="+str(n)+r",width=6.75in,height=10in]{"+f+r"}"
        text+=r"\shipout\hbox{"+panel(l)+panel(r)+"}\n"
    (d/(name+".tex")).write_text(text+"\\end{document}\n")
    tex(d,name)
    pg,sz=pages_of(d/(name+".pdf"));assert pg==len(items) and all(abs(x-972)<.1 and abs(y-720)<.1 for x,y in sz),(pg,sz[:1])


def info_from_aux(d):
    text=(d/"main.aux").read_text()
    out={}
    for name in [x["label"] for x in inventory().values()]+["page:body-end","page:references-end","page:supplement-end"]:
        hit=re.search(r"\\newlabel\{"+re.escape(name)+r"\}\{\{[^}]*\}\{(\d+)\}",text)
        if hit: out[name]=int(hit[1])
    return out


def preview(exhibits):
    OUT.mkdir(exist_ok=True)
    d,edits=prepare(exhibits);tex(d,"main",main=True)
    log=check_log(d,"main")
    pg,sz=pages_of(d/"main.pdf")
    assert all(abs(w-486)<.1 and abs(h-720)<.1 for w,h in sz)
    proof=packet(d,exhibits,versions=["candidate"],name="figures-only",stems=FIGS)
    shutil.copyfile(d/"main.pdf",OUT/"MANUSCRIPT_PREVIEW.pdf")
    shutil.copyfile(d/"figures-only.pdf",OUT/"FIGURES_ONLY.pdf")
    emit(ROOT/"proof/PREVIEW_BUILD.json",dict(baseline=MANUSCRIPT,body_unchanged_after_masking_caption_groups_and_one_discretionary_break=True,
         discretionary_break=r"design.tex: APPS/\allowbreak{}MATH, typesetting only; unchanged text, no negative spacing or size change.",
         object_keys=len(exhibits),caption_group_edits=edits,pages=pg,media_box=sz[0],label_pages=info_from_aux(d),
         tex_log_findings=log,reader_packet_findings=proof))


def atlas(exhibits):
    d=BUILD/"candidate"
    assert (d/"main.aux").exists(),"build preview first"
    OLD=ROOT/"inputs/heterospec_author_review.pdf"
    assert sha(OLD)=="5922130db5a52cfbc640dda7796b255fd825a0d05fefcb66ea77d01e583c8904"
    shutil.copyfile(OLD,d/"baseline-whole.pdf")
    log=packet(d,exhibits,versions=["276","candidate"],name="all-pairs",stems=FIGS+TABS)
    pairpages=[(("all-pairs.pdf",2*i+1),("all-pairs.pdf",2*i+2)) for i in range(len(FIGS+TABS))]
    # Include actual manuscript pages, with their original heading, paragraph, caption,
    # and text scaling. Locate candidate figures by TeX label, never assuming identical pagination.
    pages=info_from_aux(d)
    embed=[(("baseline-whole.pdf",exhibits[s]["baseline_page"]),("main.pdf",pages[exhibits[s]["label"]])) for s in FIGS]
    spreads(d,pairpages[:8]+embed,"figure-atlas")
    spreads(d,pairpages[8:],"table-atlas")
    shutil.copyfile(d/"figure-atlas.pdf",OUT/"FIGURE_COMPARISON.pdf")
    shutil.copyfile(d/"table-atlas.pdf",OUT/"TABLE_COMPARISON.pdf")
    alternatives=sorted((ROOT/"alternatives").glob("*.pdf"))
    alt_pages=[]
    if alternatives:
        pre=r"""\documentclass[acmsmall,screen,nonacm]{acmart}
\input{preamble}
\begin{document}\pagestyle{empty}
"""
        for p in alternatives:
            shutil.copyfile(p,d/p.name)
            title=p.stem.replace("_",r"\_")
            pre+=r"\noindent{\small\sffamily Alternative proof: \texttt{"+title+r"}}\par\vspace{10pt}"+"\n"
            pre+=r"\noindent\includegraphics[width=\linewidth]{"+p.name+"}\\par\\clearpage\n"
        (d/"alternatives-proof.tex").write_text(pre+r"\end{document}"+"\n")
        tex(d,"alternatives-proof",main=True)
        assert pages_of(d/"alternatives-proof.pdf")[0]==len(alternatives)
        alt_pages=[p.name for p in alternatives]
        shutil.copyfile(d/"alternatives-proof.pdf",OUT/"ALTERNATE_LAYOUTS.pdf")
    emit(ROOT/"proof/ATLAS_MAP.json",dict(figure_spreads=FIG_IDS,figure_actual_page_spreads=[
        dict(id=i,baseline=l[1],candidate=r[1]) for i,(l,r) in zip(FIG_IDS,embed)],
        table_spreads=TAB_IDS,alternative_proof_pages=alt_pages,spread_in=[13.5,10],leaf_in=[6.75,10],source_width_in=5.477,tex_findings=log))


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target",choices=["inventory","preview","atlas","all"]);args=ap.parse_args()
    x=inventory()
    if args.target in ("preview","all"): preview(x)
    if args.target in ("atlas","all"): atlas(x)
    print(args.target,":",len(FIGS),"figures /",len(TABS),"tables")
