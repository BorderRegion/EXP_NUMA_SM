from common import *
from worker import run
assert (ROOT/'freeze/MAPPING.json').exists()
write(ROOT/'freeze/BEFORE_CONFIRMATION.json',dict(at=utc(),mapping_sha256=sha(ROOT/'freeze/MAPPING.json'),new_sources={p.name:sha(p) for p in (ROOT/'src').glob('*') if p.is_file()}))
base=[ROOT/'build/runner','--cubin',ROOT/'build/probe.cubin']
for b in [2,3]:run(f'matrix_{b}',base+['--plan',ROOT/'plans'/f'matrix_{b}.txt','--out','{OUT}'])
for b in range(4):run(f'deploy_{b}',base+['--plan',ROOT/'plans'/f'deploy_{b}.txt','--maps',ROOT/'plans/frozen_maps.txt','--out','{OUT}'])
write(ROOT/'GPU_EXECUTION_COMPLETE.json',dict(at=utc(),status='COMPLETE',source_frozen=True,new_worker_seconds=sum(json.loads(s)['worker_seconds'] for s in (RUN/'ledger.jsonl').read_text().splitlines())))
