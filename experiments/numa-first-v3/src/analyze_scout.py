"""Two extra allocation scouts: descriptive granularity check, no held-out late rounds."""
import numpy as np
from common import *
r=runroot();a=np.load(r/'raw/scout_0/region_evidence.npz');b=np.load(r/'raw/scout_1/region_evidence.npz');rows=[]
for window in [128,4096,65536,2097152]:
 for cg in [0,1]:
  for concurrent in [0,1]:
   for mode in [0,4]:
    for cache in range(4):
     ix=(a['config'][:,1]==window)&(a['config'][:,2]==cg)&(a['config'][:,3]==concurrent)&(a['config'][:,4]==mode)&(a['config'][:,5]==cache)
     ys=[z['residual'][ix].mean(0) for z in [a,b]];corr=float(np.corrcoef(ys[0],ys[1])[0,1])
     rows.append(dict(window_bytes=window,cg=cg,concurrent=concurrent,mode=mode,cache=cache,between_two_allocation_group_residual_correlation=corr,residual_rms=[float(np.sqrt((y*y).mean())) for y in ys]))
write(r/'derived/SCOUT_SUMMARY.json',dict(status='EXPLORATORY_ONLY',allocation_count=2,main_allocation_count_addition=0,physical_allocations='two extra fresh processes, not the same live pools as dev_0/dev_1',working_set_bytes=134217728,rounds=4,late_validation_rounds=0,rows=rows,limitations='virtual windows, not physical pages; two observations have no confirmatory interval; not used to select main window or train confirmation masks'))
print('scout',len(rows))
