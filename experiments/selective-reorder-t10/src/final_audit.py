from common import *
import subprocess,collections,re,time
r=runroot();assert (r/'DEPLOYMENT_GPU_COMPLETE.json').exists();ledger=lines(r/'ledger.jsonl');settled={x['key']:x for x in ledger};checks=[]
counts={**{f'S2_base_{b}':360 for b in range(2)},**{f'S2_action_{b}':192 for b in range(3)},**{f'S2_card_{b}':128 for b in range(2)},**{f'S4_block_{b}':11*len(read(ROOT/'freeze/FORMAL_COVERAGE.json')['case_ids']) for b in range(6)},**{f'S5_trace_{b}':17 for b in range(6)},**{f'S5_ood_{b}':12 for b in range(3)}}
for key,count in counts.items():
 folder=worker_dir(key);m=read(folder/'manifest.json');assert m['status']=='COMPLETED';rows=lines(folder/'phases.jsonl');assert len(rows)==count,(key,len(rows),count);assert all(x['status']=='PASS' for x in rows);checks.append(dict(worker=key,phases=len(rows),status='PASS'))
for b in range(6):
 folder=worker_dir(f'S5_ffn_{b}');assert read(folder/'manifest.json')['status']=='COMPLETED';actual=lines(folder/'phases.jsonl');aliases=lines(folder/'aliases.jsonl');assert len(actual)+len(aliases)==16
for b in range(3):assert len(lines(worker_dir(f'S5_lifecycle_{b}')/'lifecycle.jsonl'))==24 and settled[f'S5_lifecycle_{b}']['status']=='COMPLETED'
lifecycle_sample_rows={b:len(lines(worker_dir(f'S5_lifecycle_{b}')/'lifecycle_samples.jsonl')) for b in range(3)}
assert lifecycle_sample_rows=={0:0,1:0,2:96},lifecycle_sample_rows
orders=read(INPUT/'plans/formal_orders.json')['orders'];raw_bit_checks=0;card_roster=read(ROOT/'freeze/RESOURCE_CARD.json')['roster']['groups'];partitions=[[[0,1],[2,3]],[[0,2],[1,3]],[[0,3],[1,2]]]
for b in range(6):
 roster=read(worker_dir(f'S4_block_{b}')/'roster.json')
 for i,g in enumerate(roster['quad']):assert roster['groups'][str(g)]==card_roster[str(i)]
 for part,pair in enumerate(roster['halves']):
  for branch,g in enumerate(pair):assert roster['groups'][str(g)]==sorted(sum([card_roster[str(q)] for q in partitions[part][branch]],[]))
 rows=lines(worker_dir(f'S4_block_{b}')/'phases.jsonl');predictions=lines(worker_dir(f'S4_block_{b}')/'choices_before_measurement.jsonl')
 assert len(predictions)==24
 for cid in read(ROOT/'freeze/FORMAL_COVERAGE.json')['case_ids']:
  rr=[x for x in rows if x['case']==cid];want=next(x['main_order'] for x in orders if x['case_id']==cid and x['block']==b)
  assert [x['action'] for x in rr if x['role']=='main']==want
  assert all(x['config'][14]==0 and x['config'][19]==0 for x in rr)
  for x in rr:
   if x['action'].startswith('PC'):assert x['raw_bit_equal'] is True;raw_bit_checks+=1
 for row in lines(worker_dir(f'S5_trace_{b}')/'phases.jsonl'):
  assert row['requests']==128 and all(p['action']=='LIB' for p in row['plans'])
  assert all('input_seed' in p and 'gpu_tensor_bytes' in p for p in row['plans'])
 assert len(lines(worker_dir(f'S5_trace_{b}')/'conditioning.jsonl'))==1
assert raw_bit_checks==864
assert read(ROOT/'reports/CPP_EQUIVALENCE.json')['status']=='PASS';frozen=read(ROOT/'freeze/POLICY_FREEZE_HASHES.json')
for path,digest in frozen['files'].items():assert sha(ROOT/path)==digest,path
origin=read(ROOT/'freeze/production_origin.json');build=Path((ROOT/'BUILD.txt').read_text().strip());old=Path(origin['production_build']);assert sha(build/'diag0.cubin')==sha(old/'diag0.cubin');assert sha(build/'diag1.cubin')==sha(old/'diag1.cubin')
sass=(build/'diag0.sass').read_text();assert 'HMMA' in sass and 'SR_SMID' not in sass and 'SR_CLOCK' not in sass
original=ROOT.parent/'pc-handoff-t10'
for relative in ['src/kernels.cu','src/kernels.cuh','adapters/pc_gemm_splitk_parallel.h','adapters/pc_reduce_split_k.h']:assert sha(ROOT/relative)==sha(original/relative),relative
async_source=(ROOT/'src/backend.cu').read_text().split('extern "C" int sr_run_async')[1].split('extern "C" int sr_wait')[0];assert 'cuGraphLaunch' in async_source and 'cuStreamSynchronize' not in async_source and 'sr_policy' not in async_source
native_states=[]
for b in range(3):
 for row in lines(worker_dir(f'S5_ood_{b}')/'phases.jsonl'):
  for p in row['plans']:
   st=p['runtime_state'];assert st['enumerated_2sm_resources']==0 and st['green_contexts']==0 and st['diag_module_loaded']==0 and p['workspace_bytes']==0;native_states.append(st)
profile=read(worker_dir('S6_profiles')/'profiles.json');assert len(profile)==3 and all(x['status']=='CAPTURED' and x['kernel_events'] for x in profile)
for x in profile:assert len(x['kernel_events'])==8*x['plan']['kernel_nodes'] and not x['memcpy_events'] and x['correctness']['status']=='PASS'
initial=read(ROOT/'freeze/power.json');files=[dict(path=x['path'],before=x['sha256'],after=sha(x['path']),unchanged=x['sha256']==sha(x['path'])) for x in initial['files']];assert all(x['unchanged'] for x in files)
services=subprocess.check_output(['systemctl','is-active','t10-quiet-fan.service','t10-quiet-power.service'],text=True);assert services==initial['services']
query=subprocess.check_output(['nvidia-smi','-i',UUID,'--query-gpu=uuid,power.limit,enforced.power.limit,temperature.gpu,clocks.sm,clocks.mem','--format=csv,noheader,nounits'],text=True);parts=[x.strip() for x in query.split(',')];assert float(parts[1])==float(parts[2])==100
apps=subprocess.check_output(['nvidia-smi','-i',UUID,'--query-compute-apps=pid,process_name,used_memory','--format=csv'],text=True)
xid=subprocess.run(['journalctl','-k','--since','2026-10-17 01:00:18','--grep','NVRM.*Xid|GPU has fallen off','--no-pager'],text=True,capture_output=True)
xid_status='NO_MATCHES_IN_ACCESSIBLE_KERNEL_JOURNAL' if '-- No entries --' in xid.stdout and not xid.stderr.strip() else 'REVIEW_OUTPUT'
write(ROOT/'reports/KERNEL_ERROR_CHECK.json',dict(at=utc(),status=xid_status,returncode=xid.returncode,stdout=xid.stdout,stderr=xid.stderr,scope='Read-only accessible kernel journal over campaign interval; not a guarantee of unavailable logs'))
assert xid_status=='NO_MATCHES_IN_ACCESSIBLE_KERNEL_JOURNAL',xid.stdout+xid.stderr
assert sum(x['worker_s'] for x in ledger)<=330*60;assert elapsed()<=540*60
write(ROOT/'reports/FINAL_POWER_READBACK.json',dict(at=utc(),status='PASS_UNCHANGED_100W_PROTECTION_ACTIVE',files=files,services=services,device=query,compute_apps=apps,controls_changed=False))
write(ROOT/'reports/FINAL_COMPLETENESS_AUDIT.json',dict(at=utc(),status='PASS',scope='Prescribed phase coverage, frozen rules, numerical and budget checks; known raw-retention limitation below is not waived or hidden.',known_evidence_limitations=['Lifecycle blocks0/1 retained complete per-plan aggregates, costs, tuning action means and numerical checks, but not individual lifecycle request arrays or per-H epoch intervals. Block2 records them. All three original blocks remain in analysis; no outcome-based replacement.'],lifecycle_sample_rows_by_block=lifecycle_sample_rows,workers=checks,ood_native_checks=len(native_states),formal_order_matches_input=True,formal_PC_raw_bit_checks=raw_bit_checks,ffn_logical_phases=96,trace_actual_phases=102,trace_all_actual_actions_LIB=True,lifecycle_phases=72,profile_captures=3,elapsed_wall_minutes=elapsed()/60,gpu_worker_minutes=sum(x['worker_s'] for x in ledger)/60,policy_hashes_unchanged=True,production_math_cubins_unchanged=True,formal_smid_clock_absent=True))
print('FINAL_AUDIT_PASS')
