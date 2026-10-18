"""All P1 exceptions and contrasts retained; descriptive post-hoc diagnosis."""
import json,csv
from collections import defaultdict
import numpy as np
from common import *
r=runroot();s=json.loads((r/'derived/P1_SUMMARY.json').read_text());cond=s['confirmation_conditions'];allsm=sorted(cond,key=lambda c:(c['early_late_sm_residual_correlation'] or {}).get('mean',-2),reverse=True)
rank=[]
for c in allsm:
 q={k:c[k] for k in ['bytes','cg','concurrent','mode','cache','early_late_sm_residual_correlation','early_late_group_residual_correlation','sm_common_coverage','late_signed_log_effect']};rank.append(q)
parities=[]
for allocation in ['dev_0','dev_1','confirm_2','confirm_3','confirm_4','confirm_5']:
 z=np.load(r/'raw'/allocation/'sm_address_evidence.npz');ks=z['keys'];i=np.flatnonzero((ks==[2097152,4096,1,0,2,2]).all(1))[0]
 for sm in np.flatnonzero((z['counts'][i]>0).any((0,2))):
  vals=[]
  for half in [0,1]:
   row=z['residual'][i,half,sm];sign=np.array([1 if (j&3).bit_count()%2==0 else -1 for j in range(64)]);valid=np.isfinite(row);vals.append(float(np.mean(row[valid]*sign[valid])))
  parities.append(dict(allocation=allocation,sm=int(sm),post_hoc_mask3_signed_log_residual=vals))
write(r/'derived/P1_EXCEPTION_AUDIT.json',dict(generated_at=utc(),all_conditions_ranked_by_sm_correlation=rank,post_hoc_parity3_diagnostic=parities,interpretation='Small working-set sparse SM-address stability is a real observation in these records, not dismissed by the failed coarse group fit. Coverage only~28% for strongest recipe, uneven weights and shared fixed order-seed schedule; subgroup structure not yet a physical-node claim. P3 finer public-control allocation experiment pre-frozen after observing this exception. Its later outcomes remain separate.'))
