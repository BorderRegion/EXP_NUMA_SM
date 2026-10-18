"""Finite CPU analysis and read-only restoration after the six planned workers."""
import json,time,subprocess,sys,platform
from frozen_common import *
r=runroot()
while not (r/'GPU_WORK_COMPLETE.json').exists():
 led=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()] if (r/'ledger.jsonl').exists() else []
 if any(x['status']!='COMPLETED' and x['key']!='memcheck' for x in led):raise RuntimeError('Failed GPU prerequisite; retain data and investigate')
 time.sleep(15)
for name in ['frozen_analyze.py','frozen_runtime.py','frozen_plot.py','frozen_report.py']:
 print('FINAL_CPU',name,utc(),flush=True);subprocess.run([PYTHON,str(ROOT/'src'/name)],check=True)
before=json.loads((r/'control_state_before.json').read_text());files=[]
for f in before['files']:
 p=Path(f['path']);now=sha(p) if p.exists() else None;files.append(dict(path=str(p),before=f['sha256'],after=now,unchanged=now==f['sha256']))
services=subprocess.run(['systemctl','is-active','t10-quiet-fan.service','t10-quiet-power.service'],capture_output=True,text=True)
query=['nvidia-smi','-i',UUID,'--query-gpu=power.limit,enforced.power.limit,temperature.gpu,memory.used,memory.free,clocks.sm,clocks.mem','--format=csv'];device=subprocess.check_output(query,text=True);caps=[float(x.strip()) for x in subprocess.check_output(['nvidia-smi','-i',UUID,'--query-gpu=power.limit,enforced.power.limit','--format=csv,noheader,nounits'],text=True).strip().split(',')]
active=[x for x in subprocess.check_output(['ps','-eo','pid,args'],text=True).splitlines() if str(r)+'/compiled/frozen_campaign' in x and '/bin/bash -c ' not in x]
restore=dict(checked_at=utc(),status='VERIFIED_UNCHANGED' if all(x['unchanged'] for x in files) and services.returncode==0 and not active and caps==[100.,100.] else 'REQUIRES_REVIEW',file_checks=files,services=services.stdout,device=device,requested_enforced_limits_w=caps,experiment_processes=active,action='No system/hardware configuration writes in this followup; initial100W and protection retained.')
write(r/'RESTORATION_REPORT.json',restore);assert restore['status']=='VERIFIED_UNCHANGED'
d=json.loads((r/'derived/ANALYSIS.json').read_text());led=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()];by={x['key']:x for x in led};assert len(by)==len(led);assert all(by[f'block_{b}']['status']=='COMPLETED' for b in range(6));assert d['status']=='COMPLETE';assert d['counts']=={'S2':432,'S3':252,'S4':240};assert d['epochs']==118272 and d['saved_full_output_checks']==3012 and d['s1_raw_records_checked']==688128
worker_s=sum(x['worker_s'] for x in led);m=json.loads((r/'manifest.json').read_text());old=Path(m['old_run']);parent_actual=sum(json.loads(x)['worker_s'] for x in (old/'ledger.jsonl').read_text().splitlines());assert worker_s<=m['new_cap_s'] and worker_s+parent_actual<=86400
ordered=sorted(led,key=lambda x:x['lock_acquired_at']);assert all(x['released_at']<=y['lock_acquired_at'] for x,y in zip(ordered,ordered[1:]));assert worker_s<1800,'Recheck stage-wise ceilings if total exceeds smallest executed-stage budget'
for b in range(6):
 p=r/'raw'/f'block_{b}';assert len(list((p/'done').glob('*.json')))==154;assert set(x['status'] for x in __import__('csv').DictReader((p/'scope_status.csv').open()))=={'AVAILABLE_EXACT_FROZEN_SM_SET'}
memcheck=(r/'raw/memcheck_existing_complete_tool/stdout.log').read_text()+(r/'raw/memcheck_existing_complete_tool/stderr.log').read_text();assert 'ERROR SUMMARY: 0 errors' in memcheck
write(r/'derived/COMPLETION_AUDIT.json',dict(completed_at=utc(),status='COMPLETE_WITH_EXPLICIT_PROFILE_NA',phase_count=d['phase_count'],epochs=d['epochs'],s1_records=d['s1_raw_records_checked'],formal_full_output_checks=d['saved_full_output_checks'],worker_hours=worker_s/3600,parent_used_hours=parent_actual/3600,combined_hours=(worker_s+parent_actual)/3600,single_gpu_worker_serial_verified=True,stage_budget_bound='Entire occupied GPU campaign below1800s, the smallest nonzero executed-stage allowance; thus each S0..S4 is below its allowance. S5GPUprofile0, CPU analysis excluded. No fabricated per-stage exact utilization.',known_failed_attempts=['memcheck: injection library missing before target launch; complete existing tool retry passed'],profiles=dict(captures=0,max=4,status='NA_EXISTING_PROFILER_NOT_LOCATED',actual_branch_overlap='NOT_MEASURED',cache_traffic='NOT_MEASURED'),restoration=restore['status'],numa_physical='NOT_ESTABLISHED'))
import numpy,matplotlib
write(r/'ENVIRONMENT_FINAL.json',dict(recorded_at=utc(),python=sys.version,platform=platform.platform(),numpy=numpy.__version__,matplotlib=matplotlib.__version__,cuda_build='See compiled/build.json exact commands and source/binary hashes',network='No network or installation in this followup',admin='One sudo-n check; no password entry or configuration write'))
m.update(status='COMPLETE_WITH_EXPLICIT_PROFILE_NA',completed_at=utc(),worker_hours=worker_s/3600,completion_audit='derived/COMPLETION_AUDIT.json');write(r/'manifest.json',m)
write(r/'FINAL_SOURCES.json',dict(recorded_at=utc(),sources={p.name:sha(p) for p in (ROOT/'src').glob('frozen_*') if p.is_file()},scope='Final analysis/tooling hashes; GPU code bound by immutable compiled snapshots and perworker manifests.'))
(ROOT/'FROZEN_STATUS.md').write_text(f'''# T10 冻结规则补充实验：测量与分析完成\n\n- GPU-worker {worker_s/3600:.4f}/6小时，合并父账{(worker_s+parent_actual)/3600:.4f}/24小时。\n- 6正式进程块，924phase、118272epochs、688128条S1记录，3012份正式完整输出检查。\n- 无新mask/方向/SM组选择；clean SASS、数值和前后位置资格通过。\n- 100W与保护服务只读核查通过。profile/counter/实际重叠时间线缺项明确列出。\n- 报告：T10_NUMA_FROZEN_RULE_MECHANISM_REPORT.md；另附物理/经验主张边界与简短导师稿。\n- 审阅包路径、SHA及鲜解压复算结果在当前运行目录 DELIVERY.json。完整新raw仍保留本地。\n''')
write(r/'CPU_FINALIZATION_READY.json',dict(completed_at=utc(),status='READY_FOR_VISUAL_REVIEW_AND_PACKAGE',worker_hours=worker_s/3600));print('CPU_FINALIZATION_READY',utc(),flush=True)
