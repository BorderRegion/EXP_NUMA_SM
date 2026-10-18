from worker import *
run('D5_PROFILES',[PYTHON,ROOT/'src/capture_diag.py','{OUT}'])
rows=lines(runroot()/'ledger.jsonl');used=sum(x['worker_s'] for x in rows if x['key'].startswith('D5_'));total=sum(x['worker_s'] for x in rows);remaining=min(300-used,85*60-total,(330-read(ROOT/'BEGIN_EXECUTION.json')['prior_gpu_minutes'])*60-total)
if remaining>=80:
 run('D5_OBSERVER',[PYTHON,ROOT/'src/observer_diag.py','{OUT}'])
 write(ROOT/'reports/OPTIONAL_OBSERVER.json',dict(status='COMPLETED',predeclared_order=['OFF','ON'],extra_sampling_period_s=.2,baseline_sampling_period_s=1,scope='Single paired observer diagnostic, not independent precision validation'))
else:write(ROOT/'reports/OPTIONAL_OBSERVER.json',dict(status='NOT_RUN_BUDGET_GATE',remaining_stage_s=remaining,minimum_reserved_s=80))
print('PROFILES_AND_OPTIONAL_OBSERVER_DONE',flush=True)
