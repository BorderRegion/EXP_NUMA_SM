import json,subprocess,shutil,sys
from frozen_common import *
r=runroot();old=json.loads((r/'manifest.json').read_text());prior=Path(old['old_run']);before=json.loads((prior/'control_state_before.json').read_text());files=[]
for x in before['files']:
 p=Path(x['path']);files.append(dict(path=str(p),sha256=sha(p) if p.exists() else None))
query=['nvidia-smi','-i',UUID,'--query-gpu=uuid,name,driver_version,power.min_limit,power.max_limit,power.limit,enforced.power.limit,temperature.gpu,clocks.sm,clocks.mem,clocks_event_reasons.active','--format=csv'];device=subprocess.run(query,capture_output=True,text=True);(r/'device_initial.csv').write_text(device.stdout+device.stderr)
services=subprocess.run(['systemctl','is-active','t10-quiet-fan.service','t10-quiet-power.service'],capture_output=True,text=True)
priv=subprocess.run(['sudo','-n','true'],capture_output=True,text=True)
write(r/'control_state_before.json',dict(recorded_at=utc(),files=files,device=device.stdout,service_status=services.stdout,privileged_entry_available=priv.returncode==0,privilege_check_stderr=priv.stderr))
if priv.returncode:(ROOT/'POWER_CONTROL_LIMIT.md').write_text('本轮已有100 W请求/执行上限。免密管理入口检查失败；保持现有动态频率及风扇/过温/低转速保护，不新增功耗档或频率扫描。此为权限记录，继续已有条件，不需要再次批准。\n')
write(r/'PROFILE_AVAILABILITY.json',dict(checked_at=utc(),commands={x:shutil.which(x) for x in ['nsys','ncu','compute-sanitizer']},known_sanitizer='/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/compute-sanitizer',scope='No executable Nsight timeline/counter profiler located in existing PATH or recorded toolkit bin. Existing CUPTI API-call diagnostic is not an activity timeline; no fresh profiler installation. Up to four captures allowed, zero planned if tools unavailable.'))
sys.path.insert(0,str(INPUT/'tools'));from make_plan import build
c=json.loads((r/'campaign.json').read_text());assert build(c)==[json.loads(x) for x in (r/'PHASE_PLAN.jsonl').read_text().splitlines()]
# CPU plan converted to an explicit tab-separated host input; no performance-dependent choices.
fields=['plan_id','stage','block','case_id','policy','size_mib','scope','profile','cache','diagnostic','inner_repeats','role','payload_xor','base_offset_bytes']
with (r/'plan.tsv').open('w') as f:
 f.write('\t'.join(fields)+'\n')
 for x in build(c):f.write('\t'.join(str(int(x.get(k,0))) if k=='diagnostic' else str(x.get(k,{'inner_repeats':1,'role':'main','payload_xor':0,'base_offset_bytes':0}.get(k,''))) for k in fields)+'\n')
with (r/'frozen_sets.txt').open('w') as f:
 for scope,v in json.loads((r/'FROZEN_RULE.json').read_text())['scopes'].items():
  for dc in range(2):f.write(scope+' '+str(dc)+' '+str(v['bias'])+' '+','.join(map(str,v[f'C{dc}_actual_sm_ids']))+'\n')
print('setup and original plan verified',r)
