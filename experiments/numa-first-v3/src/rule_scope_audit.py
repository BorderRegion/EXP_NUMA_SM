"""Empirical prediction accuracy is not a physical-home label."""
import csv,json
import numpy as np
from common import *
r=runroot();led=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()];rows=[]
def read(p):return list(csv.DictReader(p.open()))
for w in led:
 if w['status']!='COMPLETED' or not (w['key'].startswith('micro_b') or w['key']=='micro_development'):continue
 p=Path(w['out']);member=read(p/'membership.csv');cal=read(p/'calibration.csv');train={int(x['region']) for x in read(p/'fit_regions.csv') if x['train']=='1'}
 for f in read(p/'fits.csv'):
  size=int(f['bytes']);m=[x for x in member if int(x['bytes'])==size and x['kind']=='LEARNED'];ids=sorted({int(x['group']) for x in m});groups=[{int(x['fine_group']) for x in m if int(x['group'])==g} for g in ids];a=np.zeros((4,28,64))
  for x in cal:
   if int(x['bytes'])==size:a[int(x['round']),int(x['group']),int(x['region'])]=float(x['mean_log_ticks'])
  difference=a[:,sorted(groups[1])].mean((0,1))-a[:,sorted(groups[0])].mean((0,1));mask,bias=int(f['mask']),int(f['bias']);sign=np.array([1-2*(((i&mask).bit_count()%2)^bias) for i in range(64)])
  for name,idx in [('fit',sorted(train)),('spatial_holdout',sorted(set(range(64))-train))]:
   delta=difference[idx]-difference[idx].mean();margins=delta*sign[idx];rows.append(dict(worker=w['key'],bytes=size,split=name,mask=mask,bias=bias,terms=mask.bit_count(),anchors=len(idx),fraction_same_sign=float((margins>0).mean()),mean_signed_log_contrast=float(margins.mean()),nonzero_margin_anchors=int((margins!=0).sum()),scope='Centered coarse anchor latency preference within four calibration rounds; spatial holdout only. Not physical-home correctness, not every granule within an anchor, not independent late-round confirmation.'))
write(r/'derived/RULE_SCOPE_AUDIT.json',dict(generated_at=utc(),rows=rows,representation='Single nonzero6-bit parity mask and bias, bijective slot formula. CTA-invariant prologue outside payload loops, executed by threads/warps, not literally one hardware instruction perCTA. Fixed4KiB power-of-two inner addressing. No runtime task/page scheduling LUT.',exact_algebra='All64 logical regions covered exactly once; two classes equal32regions; actual saved outputs andSM membership separately verified. This mathematical coverage does not identify physical memory homes.',physical_home_known_fraction=0,unmeasured='Actual sub-anchor physical home, PA, DRAM partition, remote traffic and domain ownership unknown. New allocation generation always refit; identical VA is not proof of identical physical placement.',deployment_key='Run UUID/driver/API and binary hashes + live allocation generation/capacity + scalar mask/bias and actual compute sets. No automatic reuse across releases or capacity changes.'))
print('empirical rule rows',len(rows))
