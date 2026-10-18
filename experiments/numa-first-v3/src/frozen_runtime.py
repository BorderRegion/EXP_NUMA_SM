"""Recorded operating state; phase windows are not per-kernel clock samples."""
import csv,json
import numpy as np
from frozen_common import *
r=runroot();d=json.loads((r/'derived/ANALYSIS.json').read_text());led=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()];allrows=[];windowrows=[];batches=[]
for w in led:
 p=Path(w['out'])/'telemetry.csv'
 if not p.exists():continue
 windows=[(int(x['phase_metadata']['wall_start_ns']),int(x['phase_metadata']['wall_end_ns'])) for x in d['rows'] if x['worker']==w['key']]
 for x in csv.DictReader(p.open()):
  allrows.append(x)
  if any(a<=int(x['wall_ns'])<=b for a,b in windows):windowrows.append(x)
for x in d['rows']:
 if x['stage']=='S4':batches.append(float(x['phase_metadata']['batch_gpu_ms']))
def summary(rows):
 z={}
 for key in ['temperature_c','power_mw','sm_mhz','mem_mhz','gpu_util_pct','memory_util_pct']:
  a=[float(x[key]) for x in rows if x.get(key) and not x[key].startswith('NA')]
  z[key]=dict(n=len(a),min=min(a),median=float(np.median(a)),p95=float(np.quantile(a,.95)),max=max(a)) if a else None
 return z
write(r/'derived/RUNTIME_SUMMARY.json',dict(recorded_at=utc(),all_worker_samples=summary(allrows),measured_phase_window_samples=summary(windowrows),requested_cap_mw=sorted({x['requested_limit_mw'] for x in allrows}),enforced_cap_mw=sorted({x['enforced_limit_mw'] for x in allrows}),power_above_concurrent_cap_samples=sum(float(x['power_mw'])>float(x['enforced_limit_mw']) for x in allrows if x['power_mw'].isdigit() and x['enforced_limit_mw'].isdigit()),batch_span_ms=dict(min=min(batches),max=max(batches),outside20to100=sum(not 20<=x<=100 for x in batches),phases=len(batches)),scope='All worker samples include conditioning/setup/idle and qualifications; measured phase windows include request gaps, phase-end checks and S4batch.1Hz is not perkernel active-clock measurement, fields queried sequentially. Power spikes retained, origin not independently diagnosed.'))
print('runtime samples',len(allrows),'within measured windows',len(windowrows))
