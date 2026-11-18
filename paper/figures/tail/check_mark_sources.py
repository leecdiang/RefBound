"""CPU-only check of tail figure marks against retained measurement records.

Checks saved scalar/paired values and rendered SVG identities. It does not
execute a model, reconstruct unavailable archives, or generate new intervals.
"""

if not __debug__:
    raise SystemExit("Optimized Python is unsupported: verification must remain enabled.")

from pathlib import Path
import csv, json, math, xml.etree.ElementTree as ET
from collections import defaultdict, Counter
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'inputs/scientific_data'
source=json.loads((DATA/'data/plot_data.json').read_text())
pairs=list(csv.DictReader((DATA/'statistics/prior_studies_recomputed/estimates/paired_request_times.csv').open()))
by={(r['pr'],r['contrast']):r for r in source['modern']}
groups=defaultdict(list)
for r in pairs:groups[int(r['study_pr']),r['contrast'],r['root']].append(r)
SVG='{http://www.w3.org/2000/svg}'
checks={}
for stem,pr in [('f06_b570',247),('f08_c4_initial',256),('f03_transaction',None)]:
 m=json.loads((ROOT/'tail'/f'{stem}_data_map.json').read_text())['marks']
 tree=ET.parse(ROOT/'figures'/f'{stem}.svg').getroot()
 ids={e.get('id'):e for e in tree.iter() if e.get('id')}
 roots=[]; diffs=[]
 for mark in m:
  assert mark['gid'] in ids,mark['gid']
  if mark['kind']=='interval':
   _,contrast,_=mark['key'].split('/') if mark['key'].count('/')==2 else ('','','')
   # Contrast strings contain '/', so strip the study and terminal field.
   contrast=mark['key'].split('/',1)[1].rsplit('/',1)[0]
   limits=by[pr,contrast]['ci95_ratio']
   assert mark['value']==limits
  if mark['kind']=='root_ratio':
   raw=mark['key'].split('/',1)[1].rsplit('/',1)[0]
   contrast=next(k for pp,k in by if pp==pr and raw.startswith(k+'/'))
   root=raw[len(contrast)+1:]
   sv=next(e['ratio'] for e in by[pr,contrast]['root_effects'] if e['root']==root)
   assert mark['value']==sv
   rr=groups[pr,contrast,root]
   assert len(rr)==2,(pr,contrast,root)
   gm=math.exp(sum(math.log(float(r['candidate_s'])/float(r['control_s'])) for r in rr)/2)
   diffs.append(abs(gm-sv)); assert abs(gm-sv)<1e-12
   roots.append((contrast,root))
  # The SVG marker coordinate must match the numeric/physical artist ledger.
  if mark['kind'] not in ('interval',):
   use=next(ids[mark['gid']].iter(SVG+'use'),None)
   assert use is not None,mark['gid']
   assert abs(float(use.get('x'))-mark['x'])<1e-5
   assert abs(float(use.get('y'))-mark['y'])<1e-5
 if stem=='f06_b570':
  assert len(roots)==72 and len(set(r for c,r in roots))==24
  assert Counter(c for c,r in roots)=={'TO_C/TO_A':24,'SD_C/SD_A':24,'SD_C/TO_C':24}
  assert sum(z['kind']=='summary' for z in m)==3
  assert sum(z['kind']=='interval' for z in m)==3
 if stem=='f08_c4_initial':
  assert len(roots)==72 and len(set(r for c,r in roots))==24
  assert sum(z['kind']=='paired_root_seconds' for z in m)==24
 if stem=='f03_transaction':
  assert sum(z['kind']=='first_pair_arm' for z in m)==8
  assert sum(z['kind']=='event_arm' for z in m)==8
 checks[stem]={'kind_counts':dict(Counter(z['kind'] for z in m)),
               'root_ratio_marks':len(roots),'distinct_roots':len(set(r for c,r in roots)),
               'max_difference_from_two_round_geometric_ratio':max(diffs) if diffs else None,
               'svg_marker_positions_equal_ledger':True}
# Validate all scientific Fig.1/Fig.2 values, apart from the corrected pointer to notes.
method=json.loads((ROOT/'method/figure_marks.json').read_text())
a=method['fig1']['rtx']['counts'];v=method['fig1']['vulkan']['arms']
assert all(r['n']==(0 if r['route']=='packed' and r['q'] in [2,4] else 16) for r in a)
assert all(r['before']['n']==r['after']['n']==384 for r in v)
assert sum(r['before']['different'] for r in v)==198
assert sum(r['after']['different'] for r in v)==0
assert sum(r['before']['n'] for r in v)==1920
f,s=method['fig2']['case']
assert f['outer']=={'SIMPLE':[3,1],'LOCAL':[4]}
assert f['extent']==[256,256,256,512] and s['extent']==[256,512,512,512]
assert f['frontier']==1 and f['pending_position']==255 and f['active']['max']==254
assert s['positions']==[255,256,257,258] and s['frontier']==3 and s['pending_position']==259
assert s['seed']==f['pending_id']
checks['method_invariants']={'RTX_object_denominator':16,'B570_vectors_per_arm':384,'B570_total_vectors':1920,
  'before_unequal':198,'after_unequal':0,'owned_and_successor_relationships':True}
report={'scope':'Saved scalar/paired values and SVG mark binding; no GPU/model replay and no new CI.',
        'status':'PASS','checks':checks}
(ROOT/'tail/MARK_SOURCE_CHECK.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
