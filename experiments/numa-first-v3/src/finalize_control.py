"""Read-only final verification: V3 made no power/fan/service mutations."""
import json,subprocess
from common import *
r=runroot();before=json.loads((r/'control_state_before.json').read_text());checks=[]
for x in before['files']:
 p=Path(x['path']);actual=sha(p) if p.exists() else None;checks.append(dict(path=str(p),before=x['sha256'],after=actual,unchanged=actual==x['sha256']))
query=['nvidia-smi','-i',UUID,'--query-gpu=uuid,power.limit,enforced.power.limit,temperature.gpu,memory.used,memory.free,clocks.sm,clocks.mem','--format=csv']
device=subprocess.check_output(query,text=True);services=subprocess.run(['systemctl','is-active','t10-quiet-fan.service','t10-quiet-power.service'],capture_output=True,text=True);apps=subprocess.check_output(['nvidia-smi','-i',UUID,'--query-compute-apps=pid,process_name,used_memory','--format=csv'],text=True)
caps=[float(x.strip()) for x in subprocess.check_output(['nvidia-smi','-i',UUID,'--query-gpu=power.limit,enforced.power.limit','--format=csv,noheader,nounits'],text=True).strip().split(',')];caps_match=len(caps)==2 and all(abs(x-100)<.01 for x in caps)
processes=subprocess.check_output(['ps','-eo','pid,args'],text=True);active=[line for line in processes.splitlines() if str(r) in line and any(term in line for term in ['/render_native ','/probe_runner ','/fine_runner ','/fine_shift_runner ','/micro_campaign ','/micro_lifecycle ','native_ops.py','condition.py','lifecycle_native.py']) and '/bin/bash -c ' not in line]
write(r/'RESTORATION_REPORT.json',dict(checked_at=utc(),status='VERIFIED_UNCHANGED' if all(x['unchanged'] for x in checks) and not active and services.returncode==0 and caps_match else 'REQUIRES_REVIEW',file_checks=checks,service_status=services.stdout,device=device,power_limit_readback_w=dict(requested=caps[0],enforced=caps[1]),power_limits_match_100W=caps_match,compute_apps=apps,experiment_processes=active,restoration_action='None required: no hardware/system configuration changed in V3; existing100W policy and protective services retained',cache_cleanup='Only regenerable software caches deleted, see CACHE_CLEANUP.json; not a hardware setting'))
print(device,services.stdout,'active_experiment_processes',len(active))
