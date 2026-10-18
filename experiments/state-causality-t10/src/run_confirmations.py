from worker import run
from common import *
for b in range(2):
 remain=1200-sum(x['worker_s'] for x in lines(runroot()/'ledger.jsonl'))
 if remain<100:
  append(ROOT/'reports/OMISSIONS.jsonl',dict(kind='confirm',block=b,reason='Less100s conservativebudget',remaining_s=remain));continue
 run(f'S4_confirm_{b}',[PYTHON,ROOT/'src/state_experiment.py','{OUT}','confirm',b])
