"""P4 batch count comes exclusively from three completed P2 native pilots."""
import json,math,statistics
from collections import defaultdict
from common import *
r=runroot();measure=defaultdict(list);sources=[]
for block in range(3):
 p=r/'raw'/f'p2_native_b{block}';assert (p/'block_complete.json').exists()
 for f in sorted(p.glob('operators/*/result.json')):
  d=json.loads(f.read_text());sources.append(dict(path=str(f.relative_to(r)),sha256=sha(f)))
  for phase in d['phases']:
   if phase['role']=='primary' and phase['method'].startswith('N'):
    z=phase['common_native_pilot'];measure[d['case']['id'],phase['state']].append(z['event_span_ms']/z['repeats'])
repeat={};evidence=[]
for (case,state),v in measure.items():
 assert len(v)==3;ms=statistics.median(v);count=min(32768,max(1,math.ceil(100/ms)));repeat.setdefault(case,{})[state]=count;evidence.append(dict(case=case,state=state,pilot_ms_per_request=v,median=ms,frozen_repeats=count,predicted_native_span_ms=count*ms))
if (r/'NATIVE_REPEAT_FREEZE.json').exists():
 assert json.loads((r/'NATIVE_REPEAT_FREEZE.json').read_text())['repeats']==repeat
 print('Existing repeat freeze verified');raise SystemExit(0)
write(r/'NATIVE_REPEAT_FREEZE.json',dict(frozen_at=utc(),repeats=repeat,evidence=evidence,sources=sources,method='ceil(100 ms / median P2 Native pilot ms-per-replay), bounds1..32768; same count for every method and all P4 blocks of a case/state',change='P2 development rounded to128-replay chunks, making large sparse batches exceed target. P4 freezes direct integer counts before any P4 results; warmup still at least64 plus150ms. No candidate-specific counts.'))
print('Frozen',len(measure),'case/state counts')
