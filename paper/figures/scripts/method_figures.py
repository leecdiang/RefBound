#!/usr/bin/env python3
"""Draw the three method pages from pinned local inputs. Run with Python 3 + Matplotlib."""

if not __debug__:
    raise SystemExit("Optimized Python is unsupported: verification must remain enabled.")

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
M = ROOT / "method"
sys.dont_write_bytecode = True
sys.path.insert(0, str(M))
from evidence import evidence

# Keep transient font caches inside the owned tree (also on a clean offline host).
_cache = tempfile.TemporaryDirectory(prefix=".mpl-", dir=M)
os.environ["MPLCONFIGDIR"] = _cache.name
os.environ["SOURCE_DATE_EPOCH"] = "1794960000"
import matplotlib as mpl
mpl.use("Agg")
# Some headless macOS installations return an empty SPFontsDataType plist.
# These pages use only the two TrueType files shipped with Matplotlib; skip
# platform font-list helper processes during the initial font-cache build.
_path = os.environ.get("PATH","")
try:
    if sys.platform=="darwin":os.environ["PATH"]=_cache.name
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties
finally:
    os.environ["PATH"]=_path
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, Polygon

mpl.rcParams.update({"font.family":"DejaVu Sans", "font.size":8.2, "pdf.fonttype":42,
                     "pdf.use14corefonts":False,"svg.fonttype":"none","svg.hashsalt":"hs-independent-method-v1",
                     "axes.unicode_minus":False, "figure.facecolor":"white", "savefig.facecolor":"white",
                     "path.simplify":False})
W = 5.477*72
INK, GRAY, FAINT, GUIDE = "#1E303B","#465965","#82919A","#CFD8DC"
BLUE, TEAL, RUST = "#254B70","#087B70","#A95524"
BPALE, TPALE, RPALE = "#EDF2F6","#E8F3F0","#F8EEE4"
Z = lambda i: "z" + str(i).translate(str.maketrans("0123456789","₀₁₂₃₄₅₆₇₈₉"))
INTERVAL = lambda a,b: f"{a}–{b}"
PAGES = {}


class Page:
    def __init__(self, h, name):
        self.fig = Figure(figsize=(W/72,h/72),dpi=144,facecolor="white")
        self.fig.set_layout_engine(None) if hasattr(self.fig,"set_layout_engine") else None
        self.ax = self.fig.add_axes([0,0,1,1],xlim=(0,W),ylim=(h,0),frameon=False)
        self.ax.axis("off")
        self.name,self.h = name,h
        self.texts = []
        self.artists = []
        self._n=0

    def gid(self, tag):
        self._n+=1
        return f"{self.name}-{tag}-{self._n}"

    def text(self,x,y,s,c=INK,fs=8.2,ha="left",bold=False,tag="label",z=5):
        font=Path(mpl.get_data_path())/"fonts"/"ttf"/("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
        props=FontProperties(family="DejaVu Sans",fname=str(font),size=fs,weight="bold" if bold else "normal")
        o=self.ax.text(x,y,str(s),fontproperties=props,
                       ha=ha,va="center",color=c,clip_on=False,zorder=z,gid=self.gid(tag))
        self.texts.append(o)
        self.artists.append({"svg_id":o.get_gid(),"kind":"text","text":str(s),
                             "x_pt":x,"y_pt":y,"font_pt":fs,"weight":"bold" if bold else "normal"})
        return o

    def line(self,pts,c=GUIDE,lw=.65,tag="line",z=2):
        gid=self.gid(tag)
        self.ax.add_line(Line2D(*zip(*pts),linewidth=lw,color=c,solid_capstyle="butt",
                                solid_joinstyle="round",zorder=z,gid=gid))
        self.artists.append({"svg_id":gid,"kind":"line","points_pt":pts,"role":tag})

    def rect(self,x,y,w,h,face="white",edge="none",lw=.65,tag="box",z=3):
        gid=self.gid(tag)
        self.ax.add_patch(Rectangle((x,y),w,h,linewidth=lw,facecolor=face,edgecolor=edge,
                                    zorder=z,gid=gid))
        self.artists.append({"svg_id":gid,"kind":"rectangle","bounds_pt":[x,y,w,h],"role":tag})

    def poly(self,pts,face,edge="none",lw=.65,tag="shape",z=3):
        gid=self.gid(tag)
        self.ax.add_patch(Polygon(pts,closed=True,linewidth=lw,facecolor=face,edgecolor=edge,
                                  joinstyle="miter",zorder=z,gid=gid))
        self.artists.append({"svg_id":gid,"kind":"polygon","points_pt":pts,"role":tag})

    def arrow(self,x1,y1,x2,y2,c=GRAY,lw=.78,sz=3.2,tag="flow"):
        from math import hypot
        dx,dy=x2-x1,y2-y1
        le=hypot(dx,dy)
        if le==0:return
        u,v=dx/le,dy/le
        self.line([(x1,y1),(x2-sz*.72*u,y2-sz*.72*v)],c,lw,tag)
        self.poly([(x2,y2),(x2-sz*u+sz*.48*v,y2-sz*v-sz*.48*u),
                   (x2-sz*u-sz*.48*v,y2-sz*v+sz*.48*u)],c,tag=tag,z=4)

    def head(self,y,letter,title,aside=None):
        self.text(3,y,f"({letter})",BLUE,8.7,bold=True,tag="panel")
        self.text(22,y,title,INK,8.7,bold=False,tag="panel-title")
        if aside:self.text(W-3,y,aside,GRAY,8.0,"right",tag="study")

    def rule(self,y):
        self.line([(3,y),(W-3,y)],GUIDE,.7,tag="panel-rule")

    def save(self,sub,proof):
        out=ROOT/sub
        out.mkdir(parents=True,exist_ok=True)
        # Agg is also used for geometric checks; an external PDF interpreter
        # supplies the independent proof images when requested.
        canvas=FigureCanvasAgg(self.fig)
        canvas.draw()
        width,height=canvas.get_width_height()
        rend=canvas.get_renderer()
        # Check each editable label for clipping and inadvertent label-to-label
        # collisions. Positive tolerances allow antialiasing and neighboring
        # words printed as separate style spans.
        boxes=[]
        for s in self.texts:
            b=s.get_window_extent(rend)
            assert b.x0>=-0.05 and b.x1<=width+1 and b.y0>=0 and b.y1<=height+1,(self.name,s.get_text(),list(b.extents))
            boxes.append((s.get_text(),b))
        for i,(a,ba) in enumerate(boxes):
            for b,bb in boxes[i+1:]:
                x=min(ba.x1,bb.x1)-max(ba.x0,bb.x0)
                y=min(ba.y1,bb.y1)-max(ba.y0,bb.y0)
                if x>1.8 and y>2.2:
                    raise ValueError(f"{self.name}: text collision: {a!r} / {b!r} ({x/2:.1f} × {y/2:.1f} pt)")
        stem=out/self.name
        desc=CAPS[self.name]["description"]
        self.fig.savefig(str(stem)+".svg",format="svg",metadata={"Title":self.name,"Description":desc,"Date":"2026-11-18"})
        self.fig.savefig(str(stem)+".pdf",format="pdf",metadata={"Title":self.name,"Subject":desc,
                       "CreationDate":datetime(2026,11,18,tzinfo=timezone.utc)})
        PAGES[self.name]={"width_in":5.477,"height_pt":self.h,"ordinary_type_pt":8.2,
                          "minimum_type_pt":min(t.get_fontsize() for t in self.texts),
                          "editable_labels":len(self.texts),"checked_text_bounds_and_overlaps":True}
        (M/(self.name+"_artist_ledger.json")).write_text(json.dumps({
            "scientific_data":"figure_marks.json", "mapping_notes":"INTEGRATION_NOTES.md",
            "coordinates":"PostScript points from top left; schematic spans are query membership",
            "artists":self.artists},indent=2,ensure_ascii=False)+"\n")
        if proof:
            import subprocess
            d=M/"proofs"
            d.mkdir(exist_ok=True)
            subprocess.run(["gs","-q","-dBATCH","-dNOPAUSE","-dSAFER","-dUseCropBox","-sDEVICE=png16m",
                            "-dTextAlphaBits=4","-dGraphicsAlphaBits=4","-r180",
                            "-sOutputFile="+str(d/(self.name+".png")),str(stem)+".pdf"],check=True)


def group_badge(p,x,y,w,h,n,*,packed=False):
    """q8 miniature: inner boxes are matmul column groups; pack adds a common envelope."""
    if packed:
        p.rect(x-2.8,y-2.3,w+5.6,h+4.6,"white",BLUE,.7,tag="shared-matmul")
    gap=3.4 if n>1 else 0
    size=(w-gap*(n-1))/n
    for j in range(n):
        a=x+j*(size+gap)
        p.rect(a,y,size,h,BPALE,BLUE,.78,tag="arithmetic-group")
        for t in range(1,8//n):
            z=a+t*size/(8//n)
            p.line([(z,y+2),(z,y+h-2)],FAINT,.47,tag="query-column",z=4)


def obligations(data):
    p=Page(265,"f01_obligations")
    A,B=data["rtx"],data["vulkan"]
    p.head(9,"a","Projection arithmetic","RTX · complete operator outputs")
    p.text(4,29,"Arithmetic recipe",GRAY,8.0)
    p.text(129,29,"Grouping at q8",GRAY,8.0,"center")
    p.text(286,23,"Unequal model/operator pairs",GRAY,8.2,"center")
    centers=[199,243,287,331,375]
    for x,q in zip(centers,A["widths"]):
        p.text(x,39,f"q{q}",GRAY,8.2,"center",tag="q")
    yrows=[54,71,88]
    labels={"wide":"Native width","tile":"Tiles of ≤4","packed":"Packed fours"}
    for y,k in zip(yrows,labels):
        p.text(4,y,labels[k],tag="recipe")
        n=A["q8_matmuls"][k][0] if k!="packed" else 8//4
        group_badge(p,99,y-3.4,61,6.8,n,packed=k=="packed")
        for x,q in zip(centers,A["widths"]):
            v,=[i for i in A["counts"] if i["q"]==q and i["route"]==k]
            s=f'{v["different"]}/{v["n"]}' if v["n"] else "not run"
            if v["different"]:
                p.rect(x-16,y-6.1,32,12.2,RPALE,tag="nonzero-count")
            p.text(x,y,s,RUST if v["different"] else GRAY if not v["n"] else INK,
                   8.2,"center",bold=bool(v["different"]),tag=f"count-{k}-q{q}")
    p.rule(101)
    p.head(113,"b","Physical attention views","B570 / Vulkan · committed vocabulary vectors")
    p.text(176,130,"Before repair: heavy segment = unequal",GRAY,8.2,"center")
    p.text(337.8,130,"Unequal vectors",GRAY,8.2,"center")
    p.text(4,145,"Arm",GRAY,8.0)
    rootnames={"CodeContests/valid/108":"Code/108","CodeContests/valid/43":"Code/43","GSM8K/test/496":"GSM8K/496"}
    tracks=[(83,138),(148,203),(213,268)]
    for (l,r),root in zip(tracks,B["roots"]):
        p.text((l+r)/2,145,rootnames[root],GRAY,8.0,"center",tag="input")
    bx,ax=313,366
    p.text(bx,145,"Before",GRAY,8.0,"center")
    p.text(ax,145,"After",GRAY,8.0,"center")
    names={"R":"Reference R","M_PQ":"Greedy PQ","M_QB":"Greedy QB","C_PQ":"Speculative PQ","C_QB":"Speculative QB"}
    for k,row in enumerate(B["arms"]):
        y=161+k*14
        p.text(4,y,names[row["arm"]],tag="arm")
        for (l,r),tr in zip(tracks,row["before"]["traces"]):
            p.line([(l,y),(r,y)],FAINT,.7,tag="match-span")
            for end in (l,r):
                p.line([(end,y-1.6),(end,y+1.6)],FAINT,.55,tag="track-end")
            for lo,hi in tr["unequal"]:
                a=l+(r-l)*lo/tr["n"];b=l+(r-l)*hi/tr["n"]
                p.rect(a,y-2.1,b-a,4.2,RUST,tag="unequal-index-run")
        for x,k2 in ((bx,"before"),(ax,"after")):
            v=row[k2]
            p.text(x,y,f'{v["different"]}/{v["n"]}',RUST if v["different"] else INK,8.2,"center",
                   bold=bool(v["different"]),tag=f'count-{row["arm"]}-{k2}')
    p.text(4,234,"Output index",GRAY,8.0)
    for j,(l,r) in enumerate(tracks):
        tr=B["arms"][-1]["before"]["traces"][j]
        p.text((l+r)/2,234,"0–127",GRAY,7.8,"center",tag="index-range")
        for lo,hi in tr["unequal"]:
            x=l+(r-l)*lo/tr["n"]
            p.line([(x,218),(x,222)],RUST,.7,tag="first-mismatch")
            p.text(x,224,lo,RUST,7.8,"center",True,tag="first-mismatch")
    p.line([(4,242),(W-3,242)],GUIDE,.6)
    p.text(4,254,"All five arms",bold=True,tag="total")
    n,=set(t["n"] for t in B["arms"][0]["before"]["traces"])
    p.text(83,254,f'{len(tracks)} inputs × {n} output positions per arm',GRAY,8.2)
    for x,k in ((bx,"before"),(ax,"after")):
        a=sum(r[k]["different"] for r in B["arms"]);b=sum(r[k]["n"] for r in B["arms"])
        p.text(x,254,f"{a:,}/{b:,}",RUST if a else INK,8.2,"center",True,tag="total-vector-count")
    return p


def step_groups(d):
    return [g["stop"]-g["start"] for g in d["runs"]]


def intervals(widths):
    a=0
    for b in widths:
        yield a,a+b
        a+=b


def extent_key(p,x,y,cell,d,previous=None):
    """One printed number per query, one open-topped bracket per compatible run."""
    for i,e in enumerate(d["extent"]):
        changed=previous is not None and e!=previous["extent"][i]
        p.text(x+(i+.5)*cell,y-1,f"{e}",TEAL,8.2,"center",bold=changed,tag="changed-extent" if changed else "extent-value")
    for g in d["runs"]:
        a=x+g["start"]*cell+1.4;b=x+g["stop"]*cell-1.4
        p.line([(a,y+3.7),(a,y+6),(b,y+6),(b,y+3.7)],TEAL,.85,tag="extent-run")


def vertical_span(p,x,y0,w,h,q,stage):
    view=stage=="attn"
    p.rect(x,y0,w,h,TPALE if view else BPALE,TEAL if view else BLUE,.8,tag="attention-run" if view else "projection-group")
    p.text(x+w/2,y0+h/2,f"q{q}",TEAL if view else BLUE,8.2,"center",bold=not view,tag="query-width")


def grouped_flow(p,xs,ws,y0,dy,d,arm):
    outer=d["outer"][arm]
    run=step_groups(d)
    gol=list(intervals(outer));gr=list(intervals(run))
    mid=lambda pair:y0+dy*(pair[0]+pair[1])/2
    for group,stage,x,w in ((gol,"qkv",xs[0],ws[0]),(gr,"attn",xs[1],ws[1]),(gol,"out",xs[2],ws[2])):
        for a,b in group:
            vertical_span(p,x,y0+dy*a+1.4,w,dy*(b-a)-2.8,b-a,stage)
            # Ticks on both outside edges identify the four logical query rows.
            for i in range(a,b):
                y=y0+dy*(i+.5)
                c=TEAL if stage=="attn" else BLUE
                p.line([(x,y),(x+2,y)],c,.55,tag="row-port",z=4)
                p.line([(x+w-2,y),(x+w,y)],c,.55,tag="row-port",z=4)
    for j in (0,1):
        x1=xs[j]+ws[j]+.3;x2=xs[j+1]-.6; join=(x1+x2)/2
        if arm=="SIMPLE":
            for pair in gr:p.arrow(x1,mid(pair),x2,mid(pair),GRAY,.65,2.7)
        elif j==0:
            y=mid(gol[0])
            p.line([(x1,y),(join,y)],GRAY,.75,tag="fan-to-views")
            p.line([(join,mid(gr[0])),(join,mid(gr[-1]))],GRAY,.75,tag="fan-to-views")
            for pair in gr:p.arrow(join,mid(pair),x2,mid(pair),GRAY,.75,2.7,"fan-to-views")
        else:
            for pair in gr:p.line([(x1,mid(pair)),(join,mid(pair))],GRAY,.8,tag="ordered-join")
            p.line([(join,mid(gr[0])),(join,mid(gr[-1]))],GRAY,.8,tag="ordered-join")
            p.arrow(join,mid(gol[0]),x2,mid(gol[0]),GRAY,.8,3,"ordered-join")


def lanes(data):
    f,s=data["case"]
    p=Page(322,"f02_local_lowering")
    p.head(9,"a","Local attention refinement","A5000 · 32B · C4 on · P4 off")
    sx=[105,150,196]; sw=[32,32,35]
    lx=[251,301,351]; lw=[32,32,37]
    p.text((sx[0]+sx[-1]+sw[-1])/2,28,"SIMPLE · two native calls",INK,8.4,"center",True,tag="policy")
    p.text((lx[0]+lx[-1]+lw[-1])/2,28,"LOCAL · one native call",INK,8.4,"center",True,tag="policy")
    p.text(4,45,"Position",GRAY,8)
    p.text(56,45,"Extent",GRAY,8)
    for xs,ws in ((sx,sw),(lx,lw)):
        for x,w,txt in zip(xs,ws,["QKV","Attn.","O/FFN"]):
            p.text(x+w/2,45,txt,GRAY,8,"center")
    y0,dy=53,14.2
    for i,(position,extent) in enumerate(zip(f["positions"],f["extent"])):
        y=y0+dy*(i+.5)
        p.text(4,y,position,tag="query-position")
        p.text(25,y,("seed" if i==0 else f"p{i}"),GRAY,8.0,tag="known-input")
        p.text(68,y,extent,TEAL,8.2,"center",tag="required-extent")
    for xs,ws,arm in [(sx,sw,"SIMPLE"),(lx,lw,"LOCAL")]:
        grouped_flow(p,xs,ws,y0,dy,f,arm)
    p.text(4,120,"KV is written before attention. LOCAL rejoins the output rows in order before O/FFN.",GRAY)
    p.rule(132)
    p.head(144,"b","Owned row at rejection")
    left,cw=88.5,26.8
    p.text(4,160,"SIMPLE source",GRAY,8)
    for j,(a,b) in enumerate(intervals(f["outer"]["SIMPLE"]),1):
        lo,hi=left+a*cw+1,left+b*cw-1
        p.text((lo+hi)/2,160,f"call {j}",GRAY,8.0,"center",tag="copy-origin")
        p.line([(lo,171),(lo,168),(hi,168),(hi,171)],FAINT,.75,tag="copy-origin")
    p.text(4,182,"Owned logits",bold=True)
    for i in range(f["q"]):
        selected=i==f["frontier"]
        p.rect(left+i*cw+.7,175,cw-1.4,14,RPALE if selected else "white",RUST if selected else FAINT,.8 if selected else .55,tag="owned-slot")
        p.text(left+(i+.5)*cw,182,Z(i),RUST if selected else INK,8.4,"center",selected,tag="owned-row")
    p.text(4,200,"Sync and copy after each native call.",GRAY)
    p.text(217,165,f"{Z(0)} accepts p1; {Z(f['frontier'])} rejects p{f['frontier']+1}.",tag="greedy-action")
    p.text(217,181,f"Correction = argmax({Z(f['frontier'])}).",RUST,8.2,bold=True,tag="chosen-frontier")
    p.text(217,200,f"Trim tentative KV at {INTERVAL(f['keep'],f['tentative']['max'])}.",tag="trim")
    p.line([(4,215),(11,215)],BLUE,2.25,tag="materialized")
    p.text(16,215,f"Commit: keep KV {INTERVAL(f['active']['min'],f['active']['max'])}",BLUE,bold=True,tag="kept-prefix")
    p.poly([(166,211.6),(169.4,215),(166,218.4),(162.6,215)],"white",RUST,1.05,tag="pending")
    p.text(175,215,f"Correction pending at {f['pending_position']}",RUST,bold=True,tag="pending-position")
    p.rule(227)
    p.head(239,"c","Successor view guard","LOCAL · own commit")
    p.text(4,258,f"{INTERVAL(f['positions'][0],f['positions'][-1])}",tag="old-positions")
    p.text(4,279,f"{INTERVAL(s['positions'][0],s['positions'][-1])}",tag="new-positions")
    extent_key(p,53,258,34,f)
    extent_key(p,53,279,34,s,f)
    p.text(205,258,f"Same q{s['q']}, max {max(s['extent'])} and reference policy.",tag="guard-invariants")
    p.text(205,273,"Full vector differs: rebuild "+ " + ".join(map(str,step_groups(s)))+" views.",TEAL,8.2,bold=True,tag="guard-fails")
    p.text(205,288,"Reuse also checks shape and mask.",GRAY,tag="guard-scope")
    p.text(4,304,f"The correction is the new seed at {s['positions'][0]}. All {s['accepted']} new proposals are accepted.",tag="successor-frontier")
    p.text(4,316,f"Owned {Z(s['frontier'])} supplies the bonus: keep KV {INTERVAL(s['active']['min'],s['active']['max'])}, bonus pending at {s['pending_position']}.",tag="successor-state")
    return p


def plate(p,x,y,w,h,n,stage,label):
    """Shallow oblique face cues layer membership; no quantitative depth axis."""
    col=TEAL if stage=="attn" else BLUE
    face=TPALE if stage=="attn" else BPALE
    dx,up=3.5,3.5
    p.poly([(x,y),(x+dx,y-up),(x+w+dx,y-up),(x+w,y)],face,col,.7,tag="schematic-top-face")
    p.poly([(x+w,y),(x+w+dx,y-up),(x+w+dx,y+h-up),(x+w,y+h)],face,col,.7,tag="schematic-side-face")
    p.rect(x,y,w,h,"white" if stage=="attn" else face,col,.72,tag="view-plate" if stage=="attn" else "projection-plate")
    for i in range(1,n):
        u=x+i*w/n
        p.line([(u,y),(u+dx,y-up)],col,.55,tag="logical-row-seam",z=4)
    p.text(x+w/2,y+h/2,label,col,8.2,"center",stage!="attn",tag="plate-group")


def layer_stacks(p,d):
    top=[53,81,109]
    xmap={"SIMPLE":107,"LOCAL":255};cell=31.8;h=12.2
    for arm,base in xmap.items():
        widths=d["outer"][arm]
        views=step_groups(d)
        colcenter=lambda a,b:base+cell*(a+b)/2
        header="SIMPLE · two whole calls" if arm=="SIMPLE" else "LOCAL · one whole call"
        p.text(base+2*cell+1,24,header,bold=True,fs=8.3,ha="center",tag="policy")
        for j,pos in enumerate(d["positions"]):p.text(base+(j+.5)*cell+1,39,pos,GRAY,8.0,"center",tag="query-position")
        for i,y in enumerate(top):
            gs=views if i==1 else widths
            for j,(a,b) in enumerate(intervals(gs)):
                gap=4
                lx=base+a*cell;rx=base+b*cell
                if a:lx+=gap*.65
                if b!=d["q"]:rx-=gap*.65
                stage="attn" if i==1 else "qkv" if i==0 else "out"
                label=str(d["runs"][j]["value"]) if i==1 else f"q{b-a}"
                plate(p,lx,y,rx-lx,h,b-a,stage,label)
        whole=list(intervals(widths));pieces=list(intervals(views))
        def centers(g):return [colcenter(a,b) for a,b in g]
        if arm=="SIMPLE":
            for c in centers(whole):
                for ya,yb in zip(top,top[1:]):p.arrow(c,ya+h+.8,c,yb-4.2,GRAY,.7,3.2)
        else:
            c,=centers(whole); v=centers(pieces); yhub=(top[0]+h+top[1]-3.5)/2
            p.line([(c,top[0]+h+.8),(c,yhub)],GRAY,.75,tag="make-views")
            p.line([(v[0],yhub),(v[-1],yhub)],GRAY,.75,tag="make-views")
            for cx in v:p.arrow(cx,yhub,cx,top[1]-4.2,GRAY,.75,3.2,"make-views")
            yhub=(top[1]+h+top[2]-3.5)/2
            for cx in v:p.line([(cx,top[1]+h+.8),(cx,yhub)],GRAY,.75,tag="logical-join")
            p.line([(v[0],yhub),(v[-1],yhub)],GRAY,.75,tag="logical-join")
            p.arrow(c,yhub,c,top[2]-4.2,GRAY,.75,3.2,"logical-join")


def layered(data):
    f,s=data["case"]
    p=Page(333,"f02_layered")
    p.head(8,"a","Where the cut falls inside a decoder layer","A5000 · 32B · C4 on · P4 off")
    p.text(4,39,"Query position",GRAY,8)
    p.text(4,59,"QKV + KV write",BLUE,8.2,bold=True)
    p.text(4,87,"Attention extent",TEAL,8.2,bold=True)
    p.text(4,115,"Output + FFN",BLUE,8.2,bold=True)
    layer_stacks(p,f)
    p.text(4,135,"LOCAL joins the attention rows in logical order before the output projection and FFN.",GRAY)
    p.text(4,149,f"Sync and own each call’s requested logits. SIMPLE retains {Z(f['frontier'])} from its first call.",tag="copy-barrier")
    p.rule(161)
    p.head(173,"b","A pending token connects two transactions")
    lx,rx=172,319
    p.text(lx,192,"At the crossing",INK,8.4,"center",True)
    p.text(rx,192,"From that arm’s commit",INK,8.4,"center",True)
    p.text(4,211,"Known positions",GRAY)
    for cx,d in ((lx,f),(rx,s)):
        p.text(cx,211,INTERVAL(d["positions"][0],d["positions"][-1]),ha="center",tag="positions")
    p.text(4,228,"Full extent vector",GRAY)
    for cx,d,prev in ((lx,f,None),(rx,s,f)):extent_key(p,cx-59,228,29.5,d,prev)
    p.text(4,249,"LOCAL reuse",GRAY)
    p.text(lx,249,f"q{f['q']}, max {max(f['extent'])}",ha="center",tag="reuse-invariants")
    p.text(rx,249,"Rebuild "+ " + ".join(map(str,step_groups(s)))+" views",TEAL,8.2,"center",True,tag="rebuild")
    p.text(4,265,"Width, maximum and policy agree. Reuse checks the full vector, policy, shape and mask.",GRAY)
    p.line([(4,275),(W-3,275)],GUIDE,.6)
    for y,label,values in [
        (285,"Greedy decision",(f"Accept p1; reject p{f['frontier']+1}",f"Accept all {s['accepted']}")),
        (299,"Owned frontier",(Z(f["frontier"])+" → "+f["kind"],Z(s["frontier"])+" → "+s["kind"])),
        (313,"Retained active KV",tuple(INTERVAL(d["active"]["min"],d["active"]["max"]) for d in (f,s))),
        (327,"Outside KV · pending",tuple(f'{d["kind"].capitalize()} at {d["pending_position"]}' for d in (f,s))),
    ]:
        p.text(4,y,label,GRAY)
        for cx,st in zip((lx,rx),values):
            c=RUST if y in (299,327) else INK
            p.text(cx,y,st,c,8.2,"center",y==327,tag="ledger")
    return p


def captions(d):
    f,s=d["fig2"]["case"]
    return {
        "f01_obligations":{
            "caption":r"Independent tests of arithmetic and physical-view bitwise agreement. (a) Unequal complete operator outputs among 16 RTX model/operator pairs, relative to concatenated scalar columns; packed q2/q4 were not run. (b) B570 committed-vector mismatches fall from 198/1,920 to 0/1,920 after coordinated extent/crop, layout and dispatch repair (three inputs, 128 rows each, five arms). Tracks show committed output indices; PQ/QB denote recorded attention layouts.",
            "description":"The upper matrix compares native, tiled and packed projection arithmetic on RTX. Native q8, q16 and q32 each have 16 unequal complete outputs among 16 pairs; tiled and packed fours match, and packed q2/q4 are marked not run. The lower B570 tracks locate 99 mismatches at indices 29 through 127 on one of three inputs in each of two speculative arms. Counts total 198 of 1,920 vectors before physical-view repair and zero afterward."},
        "f02_local_lowering":{
            "caption":r"Local lowering at the selected A5000 32B crossing with frozen proposals (C4 on, P4 off). (a) SIMPLE splits the whole decoder into q3+q1 calls; LOCAL retains q4 projections and FFN around $3+1$ attention views. Spans encode query membership. (b) SIMPLE's owned row supplies the rejection correction after native storage is reused. (c) LOCAL's successor starts from its own commit and rebuilds views when the full extent vector changes.",
            "description":"Three panels show the crossing construction, a rejected proposal and the successor guard. At positions 253 to 256, SIMPLE makes q3 and q1 decoder calls while LOCAL makes a q4 call with 3+1 attention views and rejoins before output projection and FFN. SIMPLE preserves its first call's owned logit row z1 by synchronization and copying. Rejection leaves KV positions 0 to 254 and a correction pending at 255. LOCAL continues from its own commit at positions 255 to 258, rebuilds 1+3 views after the full extent vector changes, and leaves the bonus selected from z3 pending at 259. Box spans encode query membership, not time or memory size; the two policy arms are alternatives."},
        "f02_layered":{
            "caption":r"The same local lowering, shown as a schematic layer section and two transaction records. (a) Horizontal extent is query membership. The shallow faces identify operator groups; depth has no numerical or storage meaning. SIMPLE cuts the whole call after query 3. LOCAL writes KV from the four-query group, splits only the attention views, and rejoins their outputs in query order. Before the next native call, each requested full logit row is synchronized and copied. (b) The two columns follow the first call's own committed state. Rejection selects owned $z_1$ from SIMPLE's first subcall; the pending correction becomes the next seed. Although LOCAL retains q4, maximum extent 512 and the same reference policy, the full extent vector changes, so the successor rebuilds $1+3$ views. Its all-accepted outcome uses $z_3$ for the pending bonus.",
            "description":"Two shallow layer stacks compare a cut through every SIMPLE operator with a LOCAL cut confined to attention. A ledger contrasts the crossing and its successor: row one gives a correction pending at 255, the full extent vector changes, and row three then gives a bonus pending at 259."},
    }


def dump(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof",action="store_true",help="also rasterize the finished PDFs with Ghostscript")
    options=parser.parse_args()
    data=evidence()
    CAPS=captions(data)
    dump(M/"figure_marks.json",data)
    dump(M/"captions.json",CAPS)
    obligations(data["fig1"]).save("figures",options.proof)
    lanes(data["fig2"]).save("figures",options.proof)
    layered(data["fig2"]).save("alternatives",options.proof)
    dump(M/"render_check.json",PAGES)
    _cache.cleanup()
    print("Wrote Figure 1, Figure 2 and its layered alternative (5.477 in; PDF + SVG).")
