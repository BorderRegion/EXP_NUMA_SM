from worker import run
from common import *
for kind,n,prefix in [('main',6,'S1'),('control',2,'S1C'),('observer',2,'S2'),('profile',2,'S3')]:
 for block in range(n):
  budget_check();r=runroot();remain=1200-sum(x['worker_s'] for x in lines(r/'ledger.jsonl'))
  if kind=='profile' and remain<80:
   append(ROOT/'reports/OMISSIONS.jsonl',dict(kind=kind,block=block,reason='Less80s conservativeworker budget',remaining_s=remain));continue
  run(f'{prefix}_{kind}_{block}',[PYTHON,ROOT/'src/state_experiment.py','{OUT}',kind,block])
write(ROOT/'reports/SAMPLING_COMPLETE.json',dict(at=utc(),status='COMPLETE',gpu_worker_s=sum(x['worker_s'] for x in lines(runroot()/'ledger.jsonl'))))
