"""Inspect vector exports and compile old/new grayscale and CVD print proofs.

Only review proofs are rasterized. All author-facing scientific figures remain
vectors with searchable text. Severity-100 matrices: Machado, Oliveira &
Fernandes 2009, DOI 10.1109/TVCG.2009.113. Numerical constants cross-checked
against colorspacious/cvd.py at 58948923b706879a54071568c7501be3f108797c.
"""

if not __debug__:
    raise SystemExit("Optimized Python is unsupported: verification must remain enabled.")

import argparse
import base64
from collections import Counter
from io import BytesIO
import logging
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import font_manager
import numpy as np
from fontTools import subset
from fontTools.ttLib import TTFont
import pypdfium2 as pdf
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTChar
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdftypes import resolve1
from pdfminer.psparser import literal_name

import press


M = {
    "Gray / relative luminance": np.tile([.2126,.7152,.0722],(3,1)),
    "Protan / severity 100": [[.152286,1.052583,-.204868],[.114503,.786281,.099216],[-.003882,-.048116,1.051998]],
    "Deutan / severity 100": [[.367322,.860646,-.227968],[.280085,.672501,.047413],[-.011820,.042940,.968881]],
    "Tritan / severity 100": [[1.255528,-.076749,-.178779],[-.078411,.930809,.147602],[.004733,.691367,.303900]],
}
SVG="{http://www.w3.org/2000/svg}"
PALETTE=["#254B70","#087B70","#A95524"]
META={"Creator":"HeteroSpec independent author comparison","CreationDate":None,"ModDate":None}
logging.getLogger("fontTools.subset").setLevel(logging.ERROR)


def lin(x):
    return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)


def transform(im, matrix):
    light = lin(np.asarray(im,dtype=np.float32)/255)
    v=np.clip(light@np.asarray(matrix,dtype=np.float32).T,0,1)
    return np.rint(255*np.where(v<=.0031308,12.92*v,1.055*v**(1/2.4)-.055)).astype("uint8")


def contrast(hex_color):
    light=lin(np.array([int(hex_color[i:i+2],16) for i in (1,3,5)])/255)
    return round(1.05/(float(np.dot(light,[.2126,.7152,.0722]))+.05),3)


def inspect_pdf(file):
    with file.open("rb") as f:
        doc=PDFDocument(PDFParser(f)); fonts={}; images=0; seen=set()
        def resource(r):
            nonlocal images
            d=resolve1(r)
            for ref in resolve1(d.get("Font",{})).values():
                font=resolve1(ref)
                for ff in resolve1(font.get("DescendantFonts",[font])):
                    fd=resolve1(ff); ds=resolve1(fd.get("FontDescriptor",{}))
                    fonts[str(literal_name(fd.get("BaseFont",fd.get("Subtype"))))]=bool(set(ds)&{"FontFile","FontFile2","FontFile3"})
            for ref in resolve1(d.get("XObject",{})).values():
                key=getattr(ref,"objid",id(ref))
                if key in seen:continue
                seen.add(key);form=resolve1(ref); typ=literal_name(form.get("Subtype"))
                if typ=="Image": images+=1
                elif typ=="Form" and form.get("Resources"):resource(form.get("Resources"))
        for page in PDFPage.create_pages(doc): resource(page.resources)
    return {"fonts_embedded":fonts,"embedded_images":images}


def walk(x):
    if isinstance(x,LTChar):yield x
    elif hasattr(x,"__iter__"):
        for ch in x:yield from walk(ch)


def embed_svg_text_fonts(path):
    # Add subset fonts to SVGs that use Matplotlib's default DejaVu Sans. Keep
    # original families, styles, IDs and editable text rather than outlining.
    src=path.read_text()
    src=re.sub(r"\n?<style id=\"atelier-fonts\".*?</style>\n?","",src,flags=re.S)
    tree=ET.fromstring(src); runs=list(tree.iter(SVG+"text"))
    assert runs and not list(tree.iter(SVG+"image")),path
    sames=["".join(e.itertext()) for e in runs]
    chars="".join(sames)
    if not any("DejaVu Sans" in str(e.attrib) for e in tree.iter()):
        return {"embedded_svg_subsets":[],"note":"see native SVG family and PDF embedded fonts"}
    fontroot=Path(matplotlib.get_data_path())/"fonts/ttf";css=[]; files={}
    # Regular weight is always included; add weight/style variants only if used.
    tags=["Regular"]
    style=" ".join(str(e.attrib) for e in tree.iter(SVG+"text"))+" "+" ".join(str(e.attrib) for e in tree.iter(SVG+"tspan"))
    if re.search(r"\b(?:bold|600|700)\b",style): tags.append("Bold")
    if re.search(r"\b(?:italic|oblique)\b",style): tags.append("Oblique")
    if "Bold" in tags and "Oblique" in tags:tags.append("BoldOblique")
    for tag in tags:
        name="DejaVuSans"+("" if tag=="Regular" else "-"+tag)+".ttf"
        fontfile=fontroot/name;files[name]=press.sha(fontfile)
        ft=TTFont(fontfile,recalcTimestamp=False);opts=subset.Options()
        sub=subset.Subsetter(options=opts);sub.populate(text=chars+" −×±→");sub.subset(ft)
        buf=BytesIO();ft.save(buf);ft.close()
        data=base64.b64encode(buf.getvalue()).decode()
        weight="bold" if "Bold" in tag else "normal"; slant="oblique" if "Oblique" in tag else "normal"
        css.append("@font-face{font-family:'DejaVu Sans';font-weight:"+weight+";font-style:"+slant+";src:url(data:font/ttf;base64,"+data+") format('truetype')}")
    style='<style id="atelier-fonts" type="text/css">'+"\n".join(css)+"</style>"
    src=src.replace("<defs>", "<defs>"+style,1) if "<defs>" in src else src.replace("</svg>","<defs>"+style+"</defs></svg>")
    path.write_text(src)
    return {"embedded_svg_subsets":tags,"base_font_sha256":files}


def vector_check(file):
    pg=next(extract_pages(str(file))); w,h=pg.width,pg.height; chars=list(walk(pg))
    sizes=Counter(round(c.size,1) for c in chars if c.get_text().strip())
    ink=[(c.get_text(),*[round(a,2) for a in c.bbox]) for c in chars if c.get_text().strip()
         and (c.x0<-.8 or c.y0<-1.5 or c.x1>w+.8 or c.y1>h+1.5)]
    rep=inspect_pdf(file);tree=ET.parse(file.with_suffix(".svg")).getroot(); texts=list(tree.iter(SVG+"text"))
    rep.update(media_box_bp=[w,h],size_histogram=dict(sizes),possible_edge_glyphs=ink,
               svg_text_elements=len(texts),svg_images=len(list(tree.iter(SVG+"image"))))
    assert abs(w-394.344)<.12 and rep["fonts_embedded"] and all(rep["fonts_embedded"].values()),(file,rep)
    assert not rep["embedded_images"] and not rep["svg_images"] and texts,(file,rep)
    return rep


def img(p):
    with pdf.PdfDocument(p) as doc: return np.asarray(doc[0].render(scale=2).to_pil().convert("RGB")).copy()


def comparison():
    old=press.BUILD/"baseline"/"figures"; press.unpack(press.BUILD/"baseline")
    dest=press.OUT/"COLOR_AND_GRAY_PROOFS.pdf";press.OUT.mkdir(exist_ok=True)
    modes=list(M)
    plt.rcParams.update({"pdf.fonttype":42,"font.size":8,"figure.facecolor":"white"})
    with PdfPages(dest,metadata=META) as book:
        for stem,ident in zip(press.FIGS,press.FIG_IDS):
            for j in (0,2):
                fig=plt.figure(figsize=(13.5,10))
                for side,(directory,title) in enumerate([(old,"Frozen PR 276"),(press.ROOT/"figures","Independent candidate")]):
                    orig=img(directory/(stem+".pdf"))
                    hh=5.477*orig.shape[0]/orig.shape[1]
                    for row in (0,1):
                        mode=modes[j+row];x=(side*6.75+.6365)/13.5;top=(9.33 if row==0 else 4.62)
                        fig.text(x,(top+.17)/10,f"Figure {ident}   /   {title}   /   {mode}",color="#303940",fontsize=8)
                        ax=fig.add_axes([x,(top-hh)/10,5.477/13.5,hh/10])
                        ax.imshow(transform(orig,M[mode]),interpolation="none",aspect="auto");ax.set_axis_off()
                book.savefig(fig,dpi=144);plt.close(fig)
    return dest


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--no-sim",action="store_true");a=ap.parse_args()
    candidates=sorted((press.ROOT/"figures").glob("*.pdf"))+sorted((press.ROOT/"alternatives").glob("*.pdf"))
    assert len(list((press.ROOT/"figures").glob("*.pdf")))==8
    assert len(list((press.ROOT/"alternatives").glob("*.pdf")))==3
    reports={}
    for p in candidates:
        emb=embed_svg_text_fonts(p.with_suffix(".svg"));reports[str(p.relative_to(press.ROOT))]={**vector_check(p),**emb}
    if not a.no_sim: comparison()
    press.emit(press.ROOT/"proof/VECTOR_AND_COLOR_AUDIT.json",{
        "native_width_in":5.477,"guidance_not_certification":True,"color_reference":"Machado et al. 2009, DOI 10.1109/TVCG.2009.113",
        "simulation_pipeline":"sRGB -> linear light -> severity-100 matrix -> gamut clip -> sRGB; grayscale uses linear Rec.709 luminance",
        "simulations_executed":not a.no_sim,
        "review_comparisons":None if a.no_sim else "8 figures × 4 modes × frozen/candidate; 144 dpi on native-size comparison leaves",
        "human_accessibility_test":False,
        "planned_primary_inks_white_contrast":{c:contrast(c) for c in PALETTE},"exports":reports})
    print("Checked",len(reports),"pairs of vector exports.")
