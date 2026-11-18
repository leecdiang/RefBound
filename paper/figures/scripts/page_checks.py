"""Check author-proof page boxes, object labels, page content and visible whitespace."""

if not __debug__:
    raise SystemExit("Optimized Python is unsupported: verification must remain enabled.")

from pathlib import Path
import argparse
import math
import numpy as np
import pypdfium2 as pdf
from PIL import Image, ImageDraw
import press


def run(contact=None):
    p=press.OUT/"MANUSCRIPT_PREVIEW.pdf"
    metadata=press.inspect if hasattr(press,"inspect") else None
    doc=pdf.PdfDocument(p); rep=[]; sheets={}
    for i, pg in enumerate(doc,1):
        text=pg.get_textpage().get_text_range()
        im=pg.render(scale=1.25).to_pil().convert("RGB")
        arr=np.array(im); ink=(arr.min(axis=-1)<150); ys,xs=np.nonzero(ink)
        assert xs.size and "Temporary page!" not in text, f"empty/temporary page {i}"
        assert tuple(pg.get_size())==(486.0,720.0)
        w,h=im.size
        rep.append(dict(page=i,text_characters=len(text),dark_ink_envelope_in=[
            round(float(xs.min()/w*6.75),3),round(float(ys.min()/h*10),3),
            round(float(xs.max()/w*6.75),3),round(float(ys.max()/h*10),3)]))
        if contact:
            ix=(i-1)%6;g=(i-1)//6
            sheet=sheets.setdefault(g,Image.new("RGB",(1290,1280),"#e9e9eb"))
            im.thumbnail((414,604))
            x=ix%3*430+8+(414-im.width)//2;y=ix//3*640+24
            sheet.paste(im,(x,y));ImageDraw.Draw(sheet).text((ix%3*430+8,y-17),str(i),fill="#18202b")
    if contact:
        contact=Path(contact);contact.mkdir(parents=True,exist_ok=True)
        for k,s in sheets.items():s.save(contact/f"pages-{k*6+1:02}.jpg",quality=88)
    data=press.info_from_aux(press.BUILD/"candidate")
    assert len(data)==38,data
    assert max(data.values())==len(rep)
    press.emit(press.ROOT/"proof/PAGE_METRICS.json",dict(pages=rep,label_count=len(data),no_empty_page=True,
        method="PDFium text and 90-dpi ink bounds; automated checks complement rendered page review"))
    print(len(rep),"nonempty author pages;",len(data),"exhibit/end labels")


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--contact")
    a=ap.parse_args();run(a.contact)
