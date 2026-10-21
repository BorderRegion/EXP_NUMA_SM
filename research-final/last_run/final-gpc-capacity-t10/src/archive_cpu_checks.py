"""CPU read-only audits of historical primary evidence. Never overwrites old derived files."""
from common import *
import gzip,csv,collections,math,re
import numpy as np
A=REPO/'T10_RESEARCH_FINAL';checks=[]
# Stage22: independently reconstruct three read-only RM mappings and verify exported CSV.
root=REPO/'gpc-mask-t10';data=[read(root/'evidence'/f'topology_{i}.json') for i in [1,2,3]];assert data[0]==data[1]==data[2];d=data[0];phys={x['logical_gpc']:x['physical_gpc'] for x in d['floor_sweep_info']['entries']};counts=collections.Counter(phys[x['gpc']] for x in d['global_sm_order']['entries']);assert counts=={0:10,1:12,2:12,3:10,5:12}
rows=list(csv.DictReader((root/'reports/SM_TO_GPC_TPC.csv').open()))
for r,x in zip(rows,d['global_sm_order']['entries']):assert int(r['global_logical_sm'])==x['sm'] and int(r['physical_gpc'])==phys[x['gpc']]
checks.append(dict(stage='22',verification_level='RAW_RECOMPUTED',scope='all three original RM JSON snapshots agree, masks/order join and 56 exported SM rows; not historical performance rerun',records=len(rows),files=[str(root/'evidence'/f'topology_{i}.json') for i in [1,2,3]]))
# Stage26: signed per-SM summary -> every stored per-GPC per-block signed mean.
r26=REPO/'gpc-contention-gqa-t10';rr=Path((r26/'CURRENT_RUN.txt').read_text().strip());rr=rr if rr.is_absolute() else r26/'runs'/rr
with gzip.open(rr/'derived/E1/address_signed_by_sm.csv.gz','rt') as f:rs=list(csv.DictReader(f))
for item in read(rr/'derived/E1/SUMMARY.json')['gpc_signed']:
 sub=[r for r in rs if r['cache']==item['cache'] and r['unit']==item['unit'] and int(r['gpc'])==item['gpc']]
 vals=[np.mean([float(r['class1_minus_class0']) for r in sub if int(r['block'])==b]) for b in range(6)];assert np.allclose(vals,item['block_differences'],rtol=0,atol=1e-12)
checks.append(dict(stage='26',verification_level='AGGREGATES_RECOMPUTED',scope='all signed SM->GPC block means; no original load instructions/tensors/communication periods rerun',rows=len(rs),files=[str(rr/'derived/E1/address_signed_by_sm.csv.gz'),str(rr/'derived/E1/SUMMARY.json')]))
# Prior phase-level raw format is inspected by a separate checker before enabling more scopes.
write(A/'index/HISTORICAL_CPU_CHECKS.json',dict(utc=utc(),checks=checks,not_claimed='No blanket validation of 27 historical stages; report-only stages retain that status'))
for name in ['stage_catalog','claims_and_evidence']:
 p=A/'index'/(name+'.jsonl');entries=[json.loads(x) for x in p.read_text().splitlines()]
 ids={e['display_ordinal']:e['stage_uid'] for e in [json.loads(x) for x in (A/'index/stage_catalog.jsonl').read_text().splitlines()]}
 for e in entries:
  for check in checks:
   if e['stage_uid']==ids[check['stage']]:e['verification_level']=check['verification_level'];e['recomputed_scope']=check['scope']
 p.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in entries))
print('HISTORICAL_CPU_AUDITS_PASS',len(checks))
