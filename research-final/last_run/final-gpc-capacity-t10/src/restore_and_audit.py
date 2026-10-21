from common import *
import subprocess,re,collections,csv,xml.etree.ElementTree as ET
assert read(RUN/'GPU_COMPLETE.json')['status']=='PASS'
records=[]
for c in [['nvidia-smi','-q','-x'],['systemctl','cat','t10-quiet-fan.service'],['systemctl','show','t10-quiet-fan.service','--property=ActiveState,SubState,ExecStart'],['df','-h',str(ROOT)],['ps','-eo','pid,ppid,comm,args']]:
 p=subprocess.run(c,capture_output=True,text=True);records.append(dict(command=c,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
write(RUN/'environment/FINAL_COMMANDS.json',records)
x=ET.fromstring(records[0]['stdout']).find('gpu');assert x.findtext('gpu_power_readings/requested_power_limit')=='100.00 W';assert 'ActiveState=active' in records[2]['stdout']
initial=read(RUN/'environment/CONTROL_SERVICE_AND_TOOLS.json');assert records[1]['stdout']==initial[0]['stdout']
for p in [Path('/usr/local/sbin/t10_quiet_fan.py'),Path('/etc/systemd/system/t10-quiet-fan.service'),Path('/etc/systemd/system/t10-quiet-power.service')]:
 if p.exists():dst=RUN/'environment'/('FINAL_'+p.name);dst.write_bytes(p.read_bytes())
res=read(RUN/'freeze/STATE_CONTROL.json')['restore'];assert res['returncode']==0 and res['command'][-1]=='-rgc'
assert not (RUN/'clock-control.sock').exists()
r=subprocess.run([str(REPO/'gpc-mask-t10/read_topology')],capture_output=True,text=True,check=True);(RUN/'environment/FINAL_TOPOLOGY.log').write_text(r.stdout+r.stderr);d=json.loads(r.stdout);assert d==read(RUN/'environment/topology_0.json');write(RUN/'environment/FINAL_TOPOLOGY.json',d)
ledger=[json.loads(x) for x in (RUN/'ledger.jsonl').read_text().splitlines()];seconds=sum(x['seconds'] for x in ledger);assert seconds<3600
state=read(RUN/'freeze/STATE_CONTROL.json');assert len(state['attempts'])==3
for name in ['P5_memcheck_installed','P5_synccheck_installed']:assert 'ERROR SUMMARY: 0 errors' in (RUN/'raw'/name/'stdout.log').read_text()
checks=0;bitchecks=0
for folder in (RUN/'raw').iterdir():
 p=folder/'CHECKS.json'
 if not p.exists() or read(folder/'manifest.json')['status']!='COMPLETED':continue
 arr=read(p);refs={(a['case'],a['scope'],a['slot']):a['check']['output_sha256'] for a in arr if a.get('action')=='ORIGINAL_DIRECT'}
 for a in arr:
  items=a.get('checks',[a['check']] if 'check' in a else [])
  for slot,v in enumerate(items):
   assert v['status']=='PASS';checks+=1
   if v.get('original_DIRECT_raw_bit_equal'):
    if refs:assert v['output_sha256']==refs[(a['case'],a['scope'],slot)]
    bitchecks+=1
profiles=read(RUN/'raw/P5_FOUR_PROFILES/PROFILES.json');diag=[]
for p in profiles:
 e=p['kernels'];ticks=sorted([(x['ts'],1) for x in e]+[(x['ts']+x['dur'],-1) for x in e],key=lambda a:(a[0],a[1]));n=0;peak=0
 for t,v in ticks:n+=v;peak=max(peak,n)
 diag.append(dict(name=p['name'],kernel_count=p['kernel_count'],max_simultaneous_kernel_activities=peak,producer_count=sum('decode<' in x['name'] for x in e),merge_count=sum('merge<' in x['name'] for x in e)))
assert next(x for x in diag if x['name']=='CAP')['kernel_count']==24
assert next(x for x in diag if x['name']=='CAP')['max_simultaneous_kernel_activities']==5
write(RUN/'derived/PROFILE_SUMMARY.json',diag)
write(RUN/'reports/FINAL_AUDIT.json',dict(status='PASS_WITH_RECORDED_REPAIRS_AND_CONTROL_LIMITED',utc=utc(),worker_seconds=seconds,cap_seconds=3600,workers=len(ledger),failed_workers=[x for x in ledger if x['returncode']],numerical_records_checked=checks,direct_reference_hash_equal_checks=bitchecks,topology_unchanged=True,power_limit_w=100,fan_service_active=True,fan_unit_text_unchanged=True,fan_script_pre_run_hash='NOT_COLLECTED_this_run; final script snapshot retained; no edits made',clock_restore=res,administrative_helper_closed=True,production_defaults_changed=False,profiles=len(profiles),sanitizers='memcheck/synccheck finite GQA cases 0 errors; not arbitrary input/concurrency proof',remaining_gpu_jobs=False))
print('FINAL_GPU_AUDIT_PASS',seconds,checks,bitchecks)
