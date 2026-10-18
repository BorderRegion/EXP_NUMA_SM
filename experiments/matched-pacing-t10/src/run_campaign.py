"""Exactly four formalworkers, each preceded by fixed unreserved host idle."""
from common import *
from worker import run
from nvml_state import NVML
import subprocess
protocol=read(ROOT/'freeze/PROTOCOL.json');r=runroot()
for block,hz in enumerate(protocol['monitor_hz_order']):
 budget_check();remaining=read(ROOT/'BEGIN_EXECUTION.json')['new_gpu_cap_minutes']*60-sum(x['worker_s'] for x in lines(r/'ledger.jsonl'))
 if remaining<protocol['budgets']['minimum_remaining_s_per_formal_worker']:
  append(ROOT/'reports/OMISSIONS.jsonl',dict(block=block,reason='Insufficient conservative worker allowance',remaining_s=remaining));break
 assert subprocess.check_output(['systemctl','is-active','t10-quiet-fan.service'],text=True).strip()=='active'
 idle=r/'preparation'/f'block_{block}';idle.mkdir(parents=True,exist_ok=False);start=time.monotonic_ns();nv=NVML()
 cmd=['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv'];(idle/'apps_before.csv').write_text(subprocess.check_output(cmd,text=True))
 print('FIXED_IDLE_BEGIN',block,hz,utc(),flush=True)
 try:
  while (time.monotonic_ns()-start)/1e9<protocol['idle_preparation_s']:
   budget_check();tick=time.monotonic();row=nv.snapshot();append(idle/'telemetry.jsonl',row)
   assert row['limit_mw']['value']==100000 and row['temperature_c']['value']<82
   time.sleep(max(0,1-(time.monotonic()-tick)))
 finally:nv.close()
 end=time.monotonic_ns();(idle/'apps_after.csv').write_text(subprocess.check_output(cmd,text=True))
 write(idle/'idle.json',dict(block=block,monitor_hz_for_next_worker=hz,requested_s=protocol['idle_preparation_s'],start_ns=start,end_ns=end,actual_s=(end-start)/1e9,gpu_context_created=False,gpu_lock_held=False,scope='Fixed CPU/NVML-only idle preparation, no GPUworker reservation; not charged toGPUworkerbudget; walltime retained'))
 print('FIXED_IDLE_END',block,utc(),flush=True)
 run(f'M1_block_{block}',[PYTHON,ROOT/'src/matched_experiment.py','{OUT}','matched',block,hz])
write(ROOT/'reports/SAMPLING_COMPLETE.json',dict(at=utc(),gpu_worker_s=sum(x['worker_s'] for x in lines(r/'ledger.jsonl')),completed_formal=sum(x['key'].startswith('M1_') and x['status']=='COMPLETED' for x in lines(r/'ledger.jsonl'))))
