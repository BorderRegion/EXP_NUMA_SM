"""Budget/state summaries from measured telemetry, no inferred GPU busy time."""
import csv,json,math
from collections import defaultdict
import numpy as np
from common import *
r=runroot();led=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()];rows=[];stages=defaultdict(float);keys=['temperature_c','power_mw','sm_mhz','mem_mhz','gpu_util_pct','memory_util_pct'];all_samples=[]
def stats(v):
 v=np.array(v,dtype=float);return dict(n=len(v),min=float(v.min()),p05=float(np.quantile(v,.05)),median=float(np.median(v)),p95=float(np.quantile(v,.95)),max=float(v.max())) if len(v) else None
for w in led:
 stages[w['stage']]+=w['worker_s'];p=Path(w['out'])/'telemetry.csv';data=list(csv.DictReader(p.open()));all_samples.extend(data);d={k:stats([float(x[k]) for x in data if x[k] and not x[k].startswith('NA')]) for k in keys};d.update(key=w['key'],stage=w['stage'],status=w['status'],worker_s=w['worker_s'],requested_cap_mw=sorted({x['requested_limit_mw'] for x in data}),enforced_cap_mw=sorted({x['enforced_limit_mw'] for x in data}),throttle_reason_bitmasks=sorted({x['throttle_reasons'] for x in data}));rows.append(d)
aggregate={k:stats([float(x[k]) for x in all_samples if x[k] and not x[k].startswith('NA')]) for k in keys};aggregate.update(requested_cap_mw=sorted({x['requested_limit_mw'] for x in all_samples}),enforced_cap_mw=sorted({x['enforced_limit_mw'] for x in all_samples}),above_reported_cap_samples=sum(float(x['power_mw'])>float(x['enforced_limit_mw']) for x in all_samples if not x['power_mw'].startswith('NA') and not x['enforced_limit_mw'].startswith('NA')),scope='All settled workers at roughly1Hz, including conditioning, preparation and idle gaps. Sequential NVML queries are not an atomic sample. Power spikes retained; their physical/sensor origin not independently diagnosed.')
write(r/'derived/RUNTIME_SUMMARY.json',dict(generated_at=utc(),worker_s=sum(stages.values()),worker_hours=sum(stages.values())/3600,cap_hours=24,stages_s=dict(stages),workers=rows,aggregate=aggregate,scope='GPU-worker lock occupancy including CPU preparation/reference/idle gaps within workers; not actual GPU busy time; wall-clock research/analysis not included; previous campaigns excluded',resource_price='0 per user-owned-machine resource fee; electricity not metered',control='100W fixed limit, NOT fixed draw and NOT fixed clocks. Observed state retained without performance-based deletion.'))
print('settled workers',len(led),'new hours',sum(stages.values())/3600)
