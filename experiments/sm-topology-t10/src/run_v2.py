from common import *
from worker import run
import json
base=[ROOT/'build_v2/runner','--cubin',ROOT/'build_v2/probe.cubin']
write(ROOT/'freeze/V2_EXECUTION.json',dict(at=utc(),protocol_sha256=sha(ROOT/'freeze/PROTOCOL_V2.json'),files={str(p.relative_to(ROOT)):sha(p) for d in ['src','build_v2'] for p in (ROOT/d).iterdir() if p.is_file()}))
san=REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer'
for tool in ['memcheck','synccheck']:
 run(f'{tool}_v2',[san,'--tool',tool,'--error-exitcode','97']+base+['--plan',ROOT/'plans/qualification_v2.txt','--maps',ROOT/'plans/frozen_maps_v2.txt','--out','{OUT}'])
# Matrix confirmations use the unchanged original binary, not the concurrent-only revision.
for b in [4,5]:run(f'matrix_{b}',[ROOT/'build/runner','--cubin',ROOT/'build/probe.cubin','--plan',ROOT/'plans'/f'matrix_{b}.txt','--out','{OUT}'])
for b in range(6):run(f'deploy_v2_{b}',base+['--plan',ROOT/'plans'/f'deploy_v2_{b}.txt','--maps',ROOT/'plans/frozen_maps_v2.txt','--out','{OUT}'])
write(ROOT/'GPU_EXECUTION_COMPLETE_V2.json',dict(at=utc(),status='COMPLETE',worker_seconds=sum(json.loads(x)['worker_seconds'] for x in (RUN/'ledger.jsonl').read_text().splitlines())))
