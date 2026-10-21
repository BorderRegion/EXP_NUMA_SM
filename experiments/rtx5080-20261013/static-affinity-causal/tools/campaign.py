from pathlib import Path
import contextlib,datetime,hashlib,json
from run import execute
R=Path(__file__).resolve().parents[1]
c=json.loads((R/'CAUSAL_COMPLETION_CONTRACT.json').read_text());f=json.loads((R/'BINARY_FREEZE.json').read_text())
assert hashlib.sha256((R/'src/causal.cu').read_bytes()).hexdigest()==f['source_sha256']
assert hashlib.sha256((R/'build/causal').read_bytes()).hexdigest()==f['binary_sha256']
with (R/'results/raw/campaign_dispatch.txt').open('x') as log:
    for i,p in enumerate(c['process_plan']):
        label=f"f3_{p['scope'].lower()}_r{p['recipe']}_b{p['block']}"
        args=[R/'build/causal',R/'results/raw'/label,str(c['small_tasks'] if p['scope']=='SMALL' else c['pressure_tasks']),str(p['block']),str(p['seed']),str(p['recipe']),''.join(map(str,p['order'])),'full']
        with contextlib.redirect_stdout(log):execute(label,args)
        log.flush();print(f'{i+1}/24 {label} PASS',flush=True)
print('All 144 formal sessions completed.',flush=True)
