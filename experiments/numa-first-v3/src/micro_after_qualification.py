import json,csv,time,subprocess
from common import *
from worker import run
r=runroot()
while True:
 ledger={x['key']:x for x in [json.loads(z) for z in (r/'ledger.jsonl').read_text().splitlines()]}
 if 'micro_qualification' in ledger:
  assert ledger['micro_qualification']['status']=='COMPLETED';break
 time.sleep(15)
p=run('P3','micro_development',[PYTHON,ROOT/'src/micro_job.py','--block','0','--out','{OUT}'])
rows=list(csv.DictReader((p/'native_pilots.csv').open()));assert len(rows)==9
with (r/'MICRO_REPEAT_FREEZE.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['bytes','mode','repeats'])
 for x in rows:w.writerow([x['bytes'],x['mode'],x['batch_repeats']])
write(r/'MICRO_REPEAT_FREEZE.json',dict(frozen_at=utc(),source=str((p/'native_pilots.csv').relative_to(r)),source_sha256=sha(p/'native_pilots.csv'),counts=rows,method='ceil(100ms/N per replay), same fixed count for all8policies and all8formal blocks; sparse scratch preparation is inside evicted batch spans'))
for block in range(8):run('P4',f'micro_b{block}',[PYTHON,ROOT/'src/micro_job.py','--block',block+1,'--formal','--out','{OUT}'])
