"""Continue the authorized finite campaign after its existing P1 workers finish."""
import json,subprocess,time
from common import *
from worker import run
r=runroot();deadline=time.monotonic()+21600
while True:
 rows=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()]
 keys={x['key']:x['status'] for x in rows};needed=[f'confirm_{i}' for i in [2,3,4,5]]
 if any(keys.get(k)=='FAILED' for k in needed):raise RuntimeError('A discovery worker failed; automatic continuation stopped')
 if all(keys.get(k)=='COMPLETED' for k in needed):break
 if time.monotonic()>deadline:raise RuntimeError('Discovery wait deadline; no extra GPU work started')
 time.sleep(5)
b=r/'compiled'
run('P2','native_render_qualification',[b/'render/render_native','--assets',r/'prepared/truck','--width','1280','--height','720','--sequence','0','--frames','4','--warmup','4','--profile','1','--cubin',b/'probe.cubin','--out','{OUT}'])
run('P2','native_operator_qualification',[PYTHON,ROOT/'src/native_ops.py','--family','all','--block','90','--profile','1','--requests','8','--out','{OUT}'])
subprocess.run([PYTHON,str(ROOT/'src/native_campaign.py'),'P2'],check=True)
