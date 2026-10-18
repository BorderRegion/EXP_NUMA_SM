import json,time
from common import *
from worker import run
r=runroot()
def wait(keys):
 while True:
  ledger={x['key']:x for x in [json.loads(z) for z in (r/'ledger.jsonl').read_text().splitlines()]}
  for k in keys:
   if k in ledger and ledger[k]['status']!='COMPLETED':raise RuntimeError('Failed prerequisite: '+k)
  if all(k in ledger for k in keys):return
  time.sleep(15)
wait(['micro_qualification'])
build=json.loads((r/'compiled/lifecycle/build.json').read_text())
body=r/'compiled/micro/cyclic_development_snapshot/micro_campaign.cpp'
if not body.exists():body=ROOT/'src/micro_campaign.cpp'
assert build['body_source_sha256']==sha(body)
assert build['source_sha256']==sha(r/'compiled/lifecycle/micro_lifecycle.cpp')
assert build['binary_sha256']==sha(r/'compiled/lifecycle/micro_lifecycle')
run('P5','compiled_lifecycle_qualification',[r/'compiled/lifecycle/micro_lifecycle','--allocation','90','--out','{OUT}','--qualification','1','--probe-cubin',r/'compiled/fine_shift/probe_shift.cubin','--micro-cubin',r/'compiled/micro/micro.cubin'])
wait(['micro_b7','p4_native_b7','fine_shift_3'])
for block in range(4):run('P5',f'compiled_lifecycle_b{block}',[PYTHON,ROOT/'src/compiled_lifecycle_job.py','--block',block,'--out','{OUT}'])
