from common import *
import collections,subprocess
r=runroot();inv=read(r/'derived/inventory.json');scope=read(ROOT/'freeze/formal_scope.json');expected=dict(aa_episodes=24,calibration_quartets=1152,card_episodes=384,formal_quartets=scope['main_pairs_expected'],direct_quartets=144,formal_AA_quartets=scope['AA_expected'],lifecycle_phases=72,lifecycle_H_records=288,lifecycle_sample_records=288,tuner_quartets=288)
for k,v in expected.items():assert inv[k]==v,(k,inv[k],v)
ph=inv['deployment_phases_by_stage'];assert ph['S5_TRACE']==90 and ph['S5_BINDING']==12 and ph['S5_OOD']==36;assert ph['S5_FFN']+inv['ffn_aliases']==96
witness=read(ROOT/'freeze/witness.json');assert ph.get('S5_WITNESS',0)==(9 if witness['case_ids'] else 0)
assert all(x['contains_all_16_new'] and x['requests']==128 for x in read(r/'derived/actual_trace_action_counts.json'))
ledger=lines(r/'ledger.jsonl');assert all(x['status']=='COMPLETED' for x in ledger),[(x['key'],x['status']) for x in ledger if x['status']!='COMPLETED'];used=sum(x['worker_s'] for x in ledger);begin=read(ROOT/'BEGIN_EXECUTION.json');assert used<=begin['effective_new_gpu_cap_s'] and used+begin['prior_worker_s']<=330*60 and elapsed()<540*60
stagecaps={'S0':5,'S1':30,'S2':75,'S3':0,'S4':75,'S5':45,'S6':10}
for s,cap in stagecaps.items():assert sum(x['worker_s'] for x in ledger if x['key'].split('_')[0]==s)<=cap*60,(s,cap)
for file in ['LEGACY_CPU_EQUIVALENCE.json','NEW_CPU_EQUIVALENCE.json','DEPLOYED_HOST_CPU_EQUIVALENCE.json','NEW_ALLOCATOR_CHECK.json','RAW_EVIDENCE_AUDIT.json','CONSISTENT_RENAMING_V2.json']:assert read(ROOT/'reports'/file)['status']=='PASS'
profiles=read(worker_dir('S6_profiles')/'profiles.json');assert len(profiles)==4
for x in profiles:
 assert len(x['kernel_events'])==8*x['plan']['kernel_nodes'];assert len(x['memcpy_events'])==0;assert x['correctness']['status']=='PASS'
freeze=read(ROOT/'freeze/EXECUTION_FREEZE.json');assert freeze['model_sha']==sha(ROOT/'freeze/POLICY_FREEZE.json') and freeze['choice_sha']==sha(ROOT/'freeze/choices_before_timing.json')
for n,h in freeze['sources'].items():assert sha(ROOT/'src'/n)==h,n
for x in ledger:
 if x['key'].startswith(('S4','S5','S6')):
  assert x['binaries']==freeze['binaries'],x['key'];assert x['process_started_at']>freeze['created_at']
files=['/usr/local/sbin/t10_quiet_fan.py','/etc/systemd/system/t10-quiet-fan.service','/etc/systemd/system/t10-quiet-power.service','/etc/systemd/system/t10-quiet-power.service.d/90-op-fused-fixed100.conf']
final=dict(at=utc(),changed_settings=[],restoration_needed=False,configuration_sha256={p:sha(p) for p in files},current_state=subprocess.check_output(['nvidia-smi','-q','-d','POWER,CLOCK'],text=True),services=subprocess.check_output(['systemctl','is-active','t10-quiet-fan.service','t10-quiet-power.service'],text=True))
assert final['services'].splitlines()==['active','active'];write(ROOT/'reports/FINAL_STATE_AND_RESTORE.json',final)
p=subprocess.run(['journalctl','-k','--since',begin['start_utc'],'--grep','NVRM.*Xid|GPU has fallen off'],capture_output=True,text=True);write(ROOT/'reports/KERNEL_JOURNAL_CHECK.json',dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr,scope='Accessible kernel journal only, not proof of inaccessible history'))
write(ROOT/'reports/FINAL_COMPLETENESS_AUDIT.json',dict(status='PASS',expected=expected,actual=inv,stage_gpu_minutes={s:sum(x['worker_s'] for x in ledger if x['key'].split('_')[0]==s)/60 for s in stagecaps},new_gpu_minutes=used/60,cumulative_selective_gpu_minutes=(used+begin['prior_worker_s'])/60,wall_minutes=elapsed()/60,formal_scope=scope,full_cold_start_cost='NA_UNSEPARATED_COMPONENTS_DOCUMENTED',clock_locked_condition='NA_NO_NONINTERACTIVE_MANAGEMENT'))
print('FINAL_COMPLETENESS_PASS',round(used/60,3),'GPU minutes')
