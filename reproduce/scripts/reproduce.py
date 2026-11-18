#!/usr/bin/env python3
"""Offline reconstruction of saved measurements; does not execute a language model."""
from pathlib import Path
import collections,csv,hashlib,json,math,random,statistics,sys
# Integrity and reference checks below require assertions to remain enabled.
if not __debug__:
 raise SystemExit("ERROR: optimized Python (-O/-OO or PYTHONOPTIMIZE) disables required validation; run without optimization.")
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def read(n):return list(csv.DictReader((ROOT/'data'/n).open()))
def summary(logs,draws):
 ratio=math.exp(float(np.mean(logs))); vals=np.exp(np.mean(np.asarray(logs)[draws],axis=1));lo,hi=np.quantile(vals,[.025,.975])
 return dict(ratio=ratio,ratio_lo=float(lo),ratio_hi=float(hi),pct=100*(1-ratio),lo=100*(1-hi),hi=100*(1-lo))
def main():
 for f in json.loads((ROOT/'SOURCE_MAP.json').read_text())['files']:
  assert hashlib.sha256((ROOT/f['file']).read_bytes()).hexdigest()==f['sha256'],f['file']
 expected=json.loads((ROOT/'data/expected.json').read_text());out={'scope':'CPU saved-measurement reconstruction; no GPU/model replay','counts':{}}
 rows=read('a5000_confirmation.csv');assert len(rows)==96
 by={(r['case'],int(r['block']),r['arm']):float(r['value_s']) for r in rows};assert len(by)==96
 lr={c:np.array([math.log(by[c,b,'LOCAL']/by[c,b,'SIMPLE']) for b in range(1,13)]) for c in ['negative','positive','C0','C1']}
 lr['interaction']=lr['positive']-lr['negative'];lr['equal_conversation_overall']=(lr['C0']+lr['C1'])/2
 rng=random.Random(20261117);draws=np.array([[rng.randrange(12) for _ in range(12)] for _ in range(10000)])
 out['a5000']={k:summary(v,draws) for k,v in lr.items()};out['counts']['a5000']=len(rows)
 rows=read('rtx_confirmation.csv');assert len(rows)==864
 t={(int(r['root_slot']),int(r['round']),r['arm']):float(r['service_s']) for r in rows};assert len(t)==864
 draws=[json.loads(s) for s in (ROOT/'data/rtx_bootstrap_indices.jsonl').read_text().splitlines()];assert len(draws)==10000
 out['rtx']={}
 for ca,co in [('C1','B'),('C4','C1'),('C4','B')]:
  a=np.array([[statistics.fmean(math.log(t[rt,2*b+j,ca]/t[rt,2*b+j,co]) for j in range(2)) for b in range(6)] for rt in range(24)])
  ratio=math.exp(float(a.mean()));vals=np.array([math.exp(float(a[np.ix_(d['roots'],d['blocks'])].mean())) for d in draws]);lo,hi=np.quantile(vals,[.025,.975])
  out['rtx'][ca+'/'+co]=dict(ratio=ratio,ratio_lo=float(lo),ratio_hi=float(hi),pct=100*(1-ratio),lo=100*(1-hi),hi=100*(1-lo))
 out['counts']['rtx']=len(rows)
 roles=read('rtx_request_roles.csv');assert len(roles)==1764
 out['rtx_roles']={str(k):v for k,v in collections.Counter((r['included'],r['stage'],r['role'],r['exclusion_reason']) for r in roles).items()}
 rows=read('prior_pairs.csv');assert len(rows)==1134
 groups=collections.defaultdict(list)
 for r in rows:groups[r['study_pr'],r['contrast'],r['root']].append(math.log(float(r['candidate_s'])/float(r['control_s'])))
 root_ratios={k:math.exp(statistics.fmean(v)) for k,v in groups.items()};out['prior_root_estimates']=[dict(study=k[0],contrast=k[1],root=k[2],ratio=v,reduction_pct=100*(1-v),paired_rounds=len(groups[k])) for k,v in sorted(root_ratios.items())]
 out['prior_contrasts']={}
 for s,c in sorted({(k[0],k[1]) for k in groups}):
  v=[v for k,v in root_ratios.items() if k[:2]==(s,c)];ratio=math.exp(statistics.fmean(map(math.log,v)));out['prior_contrasts'][s+':'+c]=dict(ratio=ratio,reduction_pct=100*(1-ratio),roots=len(v))
 assert any(r['study']=='257' and r['root']=='CodeContests/train/279' and r['contrast']=='SD_P4/TO_P4' and r['ratio']>1 for r in out['prior_root_estimates'])
 rows=read('m1_requests.csv');ms=[r for r in rows if r['kind']=='measurement'];assert len(ms)==256 and len(rows)-len(ms)==32
 groups=collections.defaultdict(list)
 for r in ms:groups[r['root'],r['arm']].append(float(r['service_s']))
 assert len(groups)==64 and all(len(v)==4 for v in groups.values())
 roots=sorted({k[0] for k in groups});arms=sorted({k[1] for k in groups});tot={k:math.fsum(v) for k,v in groups.items()};totals={a:math.fsum(tot[r,a] for r in roots) for a in arms}
 contrasts=[dict(candidate=c['candidate'],control=c['control'],ratio=totals[c['candidate']]/totals[c['control']]) for c in expected['m1']['contrasts']]
 interaction=math.exp(statistics.fmean(math.log((tot[r,'L_P_D4']/tot[r,'W_P_D4'])/(tot[r,'L_L4_D4']/tot[r,'W_L4_D4'])) for r in roots))
 out['m1']=dict(arm_total_s=totals,contrasts=contrasts,interaction_ratio=interaction,intervals_recomputed=False,negative_root_counts={p:sum(tot[r,'L_'+p+'_D4']/tot[r,'W_'+p+'_D4']>1 for r in roots) for p in ['L4','P']})
 errors=[]
 assert set(out['prior_contrasts'])==set(expected['prior']) and len(expected['prior'])==27
 for key,d in out['prior_contrasts'].items():
  for field in ['ratio','reduction_pct']:errors.append(abs(d[field]-expected['prior'][key][field]))
  actual={x['root']:x['ratio'] for x in out['prior_root_estimates'] if x['study']+':'+x['contrast']==key}
  assert set(actual)==set(expected['prior'][key]['root_ratios']),key
  errors.extend(abs(value-expected['prior'][key]['root_ratios'][root]) for root,value in actual.items())
 out['prior_reference_checks']={'contrasts':len(expected['prior']),'root_estimates':sum(len(d['root_ratios']) for d in expected['prior'].values()),'maximum_error':max(errors)}
 for family in ['a5000','rtx']:
  for key,d in out[family].items():
   for field,value in d.items():errors.append(abs(value-expected[family][key][field]))
 errors.extend(abs(v-expected['m1']['arm_total_s'][k]) for k,v in totals.items());errors.extend(abs(c['ratio']-e['ratio']) for c,e in zip(contrasts,expected['m1']['contrasts']));errors.append(abs(interaction-expected['m1']['interaction']['ratio']))
 assert max(errors)<2e-10,max(errors)
 out.update(status='PASS',maximum_reference_error=max(errors),numpy=np.__version__,python=sys.version.split()[0])
 dest=ROOT/'results';dest.mkdir(exist_ok=True);(dest/'recomputed.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
 print('PASS: A5000 96 values/48 pairs; RTX 864 formal and 1764 role records; 1134 prior contrast rows; M1 256 measured + 32 primers.');print('Maximum frozen-reference error:',max(errors))
if __name__=='__main__':main()
