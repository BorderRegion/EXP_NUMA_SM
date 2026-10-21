"""CPU-only descriptive audit; no corrected performance or candidate selection."""
from common import *
import sys, numpy as np, collections
if len(sys.argv)>1: RUN=Path(sys.argv[1]).resolve()
ph=read(RUN/'derived/ALL_PHASES.json');aa=read(RUN/'derived/ANCHORS_AA.json')
noise=[];sensitivity=[];costs=[];absolute=[]
for stage in ['E2','E3','E4']:
 metric='job_output_ready_us' if stage=='E4' else 'gpu_per_request_us'
 selected=[x for x in aa if x['stage']==stage and x['metric']==metric and (stage=='E4' or x['view']=='batch')]
 for x in selected:
  noise.append({**x,'max_abs_individual_block_change_percent':max(abs(100*(v-1)) for v in x['block_time_ratios'])})
 rr=[x for x in ph if x['stage']==stage and (stage=='E4' or x['view']=='batch')]
 for case in sorted({x['case'] for x in rr}):
  for family in ['PACK','SPREAD']:
   for ref in ['ANCHOR_HEAD','AA_HEAD','ANCHOR_TAIL','AA_TAIL']:
    ratios=[]
    for b in range(6):
     cell=[x for x in rr if x['case']==case and x['block']==b]
     v=np.exp(np.mean([np.log(x[metric]) for x in cell if x['role']=='PRIMARY' and x['policy'].startswith(family)]))
     denom=next(x[metric] for x in cell if x['role']==ref)
     ratios.append(float(v/denom))
    sensitivity.append(dict(stage=stage,case=case,metric=metric,family=family,reference_role=ref,block_ratios=ratios,time_change_percent=float(100*np.expm1(np.log(ratios).mean())),purpose='Unadjusted alternate reference sensitivity; never changes primary contrast'))
 for policy in sorted({x['policy'] for x in rr if x['role'] in ['PRIMARY','BODY_CONTROL']}):
  sub=[x for x in rr if x['policy']==policy and x['role'] in ['PRIMARY','BODY_CONTROL']]
  for key in ['setup_ms','resource_setup_ms','graph_setup_ms','gemm_handle_workspace_setup_ms','phase_setup_including_diagnostics_ms']:
   vals=[x[key] for x in sub if key in x]
   if vals:costs.append(dict(stage=stage,policy=policy,cost=key,count=len(vals),minimum=float(min(vals)),median=float(np.median(vals)),maximum=float(max(vals)),scope='Recorded research setup; not production minimum, not included in warm timing'))
for case in ['GQA4_LONG','BATCH4_RAGGED']:
 for policy in sorted({x['policy'] for x in ph if x['stage']=='E4' and x['role'] in ['PRIMARY','BODY_CONTROL']}):
  rr=[x for x in ph if x['stage']=='E4' and x['case']==case and x['policy']==policy and x['role'] in ['PRIMARY','BODY_CONTROL']]
  absolute.append(dict(case=case,policy=policy,geometric_mean_ms={k:float(np.exp(np.mean([np.log(x[k]) for x in rr]))/1000) for k in ['job_gpu_us','job_output_ready_us','foreground_completion_us','background_completion_us']}))
write(RUN/'derived/DESCRIPTIVE_AUDIT.json',dict(noise=noise,alternate_anchor_sensitivity=sensitivity,setup_costs=costs,e4_absolute=absolute,limitations=['No frequency regression, data deletion, posthoc choice, or effect correction','Auxiliary anchors have fewer samples than primary phases','Head/tail references cannot identify a unique state-change cause']))
print('DESCRIPTIVE_AUDIT_WRITTEN')
