"""Small end-of-campaign completeness/readback audit; no performance threshold."""
from common import *
import subprocess,collections
r=runroot();assert (r/'GPU_EXECUTION_COMPLETE.json').exists()
ledger=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()];settled={x['key']:x for x in ledger};checks=[]
expected={'E1_block_0':352,'E1_block_1':352,**{f'E2_matrix_{b}':768 for b in range(4)},**{f'E2_bridge_{b}':54 for b in range(4)},**{f'E3_block_{b}':60 for b in range(6)},'E4_native_development':24,**{f'E4_native_{b}':24 for b in range(6)},**{f'E5_gemm_{b}':30 for b in range(6)},**{f'E5_attention_{b}':24 for b in range(6)},**{f'E5_ablation_{b}':24 for b in range(6)},**{f'E5_workspace_{b}':12 for b in range(4)}}
for key,n in expected.items():
 actual=worker_key(key);assert settled[actual]['status']=='COMPLETED',key
 rows=[json.loads(x) for x in (worker_dir(key)/'phases.jsonl').read_text().splitlines()];assert len(rows)==n,(key,len(rows),n);assert all(x['status'] in ['PASS','NA_MEMORY_HEADROOM'] for x in rows);checks.append(dict(key=key,actual_worker=actual,phases=len(rows),NA=sum(x['status']!='PASS' for x in rows)))
for b in range(3):
 assert settled[worker_key(f'E5_lifetime_{b}')]['status']=='COMPLETED'
 assert len((worker_dir(f'E5_lifetime_{b}')/'lifetime.jsonl').read_text().splitlines())==8
profiles=json.loads((worker_dir('E6_profiles')/'profiles.json').read_text());assert len(profiles)==8
assert settled[worker_key('E6_profiles')]['status']=='COMPLETED'
assert all(x['status']=='CAPTURED' and len(x['kernel_events'])>0 for x in profiles)
assert all(len(x['producer_overlap_samples'])==8 for x in profiles if x['label'].endswith(('_M','_P')))
assert len((r/'profile_attempts.jsonl').read_text().splitlines())==8
assert settled[worker_key('qualify_attention_metadata_all')]['status']=='COMPLETED'
metadata=[json.loads(x) for x in (worker_dir('qualify_attention_metadata_all')/'metadata_audits.jsonl').read_text().splitlines()];assert len(metadata)==48
assert (worker_dir('qualify_attention_dag')/'complete.json').exists()
for b in range(4):
 rows=[json.loads(x) for x in (worker_dir(f'E2_matrix_{b}')/'phases.jsonl').read_text().splitlines()];keys={(x['case'],x['workspace_slot'],x['round'],x['P_group'],x['C_group']) for x in rows};assert len(keys)==768
# Verify the actually executed reduced main order, after exact aliases were removed.
rank_counts=collections.Counter()
for b in range(6):
 rows=[json.loads(x) for x in (worker_dir(f'E3_block_{b}')/'phases.jsonl').read_text().splitlines()]
 for case in sorted({x['case'] for x in rows}):
  main=[x['policy'] for x in rows if x['case']==case and x.get('role')=='main'];assert sorted(main)==['CORE','M','P']
  for rank,policy in enumerate(main):rank_counts[case,policy,rank]+=1
assert all(n==2 for n in rank_counts.values())
# Main complete paired coverage, exact mapping identities and deployed code diagnostics.
derived=json.loads((ROOT/'derived/comparisons.json').read_text())
for effect in ['M/LIB','M/G','M/CORE','M/P']:
 a=next(x for x in derived if x['stage']=='E3' and x['effect']==effect and x['metric']=='gpu_us');assert a['n_blocks']==6 and a['n_cases']==12 and a['paired_observations']==72
rule=json.loads((ROOT/'freeze/pc_rule.json').read_text());assert rule['pi']==0
assert next(x for x in derived if x['stage']=='E3' and x['effect']=='M/G' and x['metric']=='gpu_us')['structural_identity']
for x in json.loads((ROOT/'derived/dag_examples.json').read_text()):
 if x['stage']=='E3' and x['policy'] in ['G','M','P']:assert x['math_kernel_count']==4 and x['body_node_count']==4
budget=collections.defaultdict(float)
for x in ledger:budget[x.get('stage',x['key'].split('_')[0] if x['key'].startswith(('E1_','E2_','E3_','E4_','E5_','E6_')) else 'E0')]+=x['worker_s']
assert sum(budget.values())<24*3600
for s,cap in {'E0':1,'E1':4,'E2':4,'E3':6,'E4':4,'E5':3,'E6':1}.items():assert budget[s]<=cap*3600
initial=json.loads((ROOT/'freeze/power.json').read_text());files=[dict(path=x['path'],before_sha=x['sha256'],after_sha=sha(x['path']),unchanged=sha(x['path'])==x['sha256']) for x in initial['files']];assert all(x['unchanged'] for x in files)
services=subprocess.check_output(['systemctl','is-active','t10-quiet-fan.service','t10-quiet-power.service'],text=True);assert services==initial['services']
query=subprocess.check_output(['nvidia-smi','-i',UUID,'--query-gpu=uuid,power.limit,enforced.power.limit,temperature.gpu,clocks.sm,clocks.mem','--format=csv,noheader,nounits'],text=True);parts=[x.strip() for x in query.split(',')];assert float(parts[1])==100 and float(parts[2])==100
apps=subprocess.check_output(['nvidia-smi','-i',UUID,'--query-compute-apps=pid,process_name,used_memory','--format=csv'],text=True)
write(ROOT/'reports/FINAL_POWER_READBACK.json',dict(at=utc(),status='PASS_UNCHANGED_100W_PROTECTION_ACTIVE',files=files,services=services,power_readback=query,compute_apps=apps,controls_modified_this_campaign=False,secondary_125W='NA_PRIVILEGED_ENTRY_UNAVAILABLE',note='No restoration mutation necessary; original protected configuration was never changed. Desktop display process may remain; queue complete and experimental worker child exited.'))
write(ROOT/'reports/FINAL_COMPLETENESS_AUDIT.json',dict(at=utc(),status='PASS',workers=checks,profile_attempts=len(profiles),settled_worker_hours=sum(budget.values())/3600,paired_main_coverage='12 fixed test cases x 6 process blocks',candidate_attention='ADAPTER_MISSING',actual_activation_epilogue_fusion='NOT_IMPLEMENTED; F1 is dependency contraction',no_automatic_speedup_threshold=True))
print('FINAL_AUDIT_PASS',len(checks),sum(budget.values())/3600)
