#!/usr/bin/env python3
"""Verify and rebuild figures and manuscript in a separate output directory."""
if not __debug__:
    raise SystemExit('Optimized Python is unsupported: verification must remain enabled.')
import argparse, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);args=p.parse_args();out=args.output.resolve()
if out==ROOT or ROOT in out.parents or out.exists():raise SystemExit('Use a new output directory outside the candidate tree.')
for x in json.loads((ROOT/'DELIVERY_MANIFEST.json').read_text()):
 f=ROOT/x['path']
 if not f.is_file() or f.stat().st_size!=x['bytes'] or sha(f)!=x['sha256']:raise SystemExit('Package integrity check failed: '+x['path'])
out.mkdir(parents=True);shutil.copytree(ROOT/'figures',out/'figures');shutil.copytree(ROOT/'paper',out/'paper')
cache=out/'cache';cache.mkdir();env=dict(os.environ,MPLBACKEND='Agg',MPLCONFIGDIR=str(cache/'mpl'),XDG_CACHE_HOME=str(cache),PYTHONDONTWRITEBYTECODE='1',SOURCE_DATE_EPOCH='1794960000',FORCE_SOURCE_DATE='1',TZ='UTC')
with (out/'figures.log').open('w') as log:subprocess.run([sys.executable,str(out/'figures/scripts/rebuild.py')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
for typ,pat in [('figures','*.pdf'),('tables','*.tex')]:
 for expected in (ROOT/'paper'/typ).glob(pat):
  generated=out/'figures'/typ/expected.name
  if sha(generated)!=sha(expected):raise SystemExit('Generated scientific exhibit differs: '+expected.name)
  shutil.copy2(generated,out/'paper'/typ/expected.name)
for i in range(1,4):
 with (out/f'tex-pass-{i}.log').open('w') as log:subprocess.run(['pdflatex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','-file-line-error','main.tex'],cwd=out/'paper',env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
pdf=out/'paper/main.pdf';pages=len(PdfReader(pdf).pages)
if pages!=33:raise SystemExit(f'Unexpected page count: {pages}')
log=(out/'paper/main.log').read_text(errors='replace')
if 'There were undefined references' in log or 'There were undefined citations' in log:raise SystemExit('Unresolved references/citations')
(out/'BUILD_REPORT.json').write_text(json.dumps({'pages':pages,'sha256':sha(pdf),'formal_figures':8,'tables':27,'gpu_requests':0,'scope':'Frozen-data graphical and manuscript reconstruction; not model replay'},indent=2)+'\n')
print('PASS: 8 figures, 27 tables, 33-page manuscript; '+str(pdf))
