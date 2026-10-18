"""CPU-only integrity, statistics and protocol audit. Does not launch CUDA."""
from common import *
import numpy as np,collections,csv,gzip,sys
from analyze import run as claim_analyze
from analyze_softmax import run as soft_analyze
from analyze_controls import run as controls_analyze
from analyze_const import run as const_analyze
from topology_math import load_worker,residual,corr,hungarian
def run(reanalyze=True):
 ledger=[json.loads(x) for x in (RUN/'ledger.jsonl').read_text().splitlines()];by={x['key']:x for x in ledger};assert len(by)==len(ledger)
 expected_failed={'qualification','soft_qualification_initial'}
 assert {x['key'] for x in ledger if x['status']!='COMPLETED'}==expected_failed
 expected={'claim_dev':2,'claim_confirm':6,'soft_dev':2,'soft_confirm':6,'soft_panel':6,'soft_fresh':6,'soft_common':6,'soft_batch':6,'const_confirm':6}
 for group,n in expected.items():
  for i in range(n):assert by[f'{group}_{i}']['status']=='COMPLETED' and read(RUN/f'{group}_{i}/complete.json')['status']=='PASS'
 assert sum(x['worker_seconds'] for x in ledger)<=read(ROOT/'freeze/PROTOCOL.json')['worker_budget_seconds']
 freeze_files=['CLAIM_IMPLEMENTATION','SOFTMAX_IMPLEMENTATION','SOFTMAX_CALIBRATION_EXECUTION','CONTROL_EXECUTION','CONST_IMPLEMENTATION']
 checked={}
 for name in freeze_files:
  v=read(ROOT/f'freeze/{name}.json')
  for rel,h in v['hashes'].items():assert sha(ROOT/rel)==h,(name,rel);checked[rel]=h
 for name,h in read(ROOT/'freeze/PROTOCOL.json')['baseline_hashes'].items():assert sha(ROOT/'build/baseline'/name)==h
 assert read(ROOT/'freeze/CLAIM_SELECTION.json')['development_sha256']==sha(ROOT/'derived/claim_dev.json')
 assert read(ROOT/'freeze/SOFTMAX_BASELINE.json')['development_sha256']==sha(ROOT/'derived/soft_dev.json')
 chronology=[('CLAIM_SELECTION','claim_confirm_0'),('SOFTMAX_MAPS','soft_dev_0'),('SOFTMAX_BASELINE','soft_confirm_0'),('PANEL_PROTOCOL','soft_panel_0'),('FRESH_PROTOCOL','soft_fresh_0'),('CONST_PROTOCOL','const_confirm_0'),('MAILBOX_CHOICE','const_confirm_0'),('COMMON_MAP_PROTOCOL','soft_common_0'),('BATCH_PROTOCOL','soft_batch_0')]
 for freeze,worker in chronology:assert read(ROOT/f'freeze/{freeze}.json')['created_utc']<by[worker]['started'],(freeze,worker)
 # Both implementations retain the exact same baseline binaries and same source
 # throughout each measured phase. New-stage source files are allowed to be added.
 for prefix,freeze in [('claim_', 'CLAIM_IMPLEMENTATION'),('soft_', 'SOFTMAX_IMPLEMENTATION'),('const_', 'CONST_IMPLEMENTATION')]:
  frozen=read(ROOT/f'freeze/{freeze}.json')['hashes']
  for name,m in by.items():
   if not any(name.startswith(g+'_') for g in expected if g.startswith(prefix)):continue
   for rel,h in frozen.items():
    if rel.startswith('src/') and rel in m['sources']:assert m['sources'][rel]==h,(name,rel)
    if rel.startswith('build/') and Path(rel).parent==Path('build') and Path(rel).suffix in ['.so','.cubin']:assert m['binaries'][Path(rel).name]==h,(name,rel)
 rows=0;batches=0;operators=0;all_hashes={};numeric=0;temps=[];limits=[];worker_info=[]
 for m in ledger:
  w=RUN/m['key'];assert read(w/'manifest.json')==m
  for line in (w/'telemetry.jsonl').read_text().splitlines():
   x=json.loads(line);temps.append(x['temperature_c']['value']);limits.append(x['limit_mw']['value'])
  if m['status']!='COMPLETED':continue
  if (w/'numerical.json').exists():
   a=read(w/'numerical.json');assert all(x['status']=='PASS' for x in a);numeric+=len(a)
  if (w/'api.json').exists():
   a=read(w/'api.json');assert all(y['status']=='PASS' for x in a for y in x['checks']);numeric+=sum(len(x['checks']) for x in a)
  if any(z in m['key'] for z in ['memcheck','synccheck','racecheck']):
   text=(w/'stdout.log').read_text()+(w/'stderr.log').read_text();assert ('ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text),m['key']
  own=0;hashset=set()
  for path in w.rglob('mapping.json'):
   x=read(path);h=x.get('logits_sha256',x.get('q_sha256',[]));hashset.update(h)
  if hashset:all_hashes[m['key']]=hashset
  for path in w.rglob('requests.csv.gz'):
   with gzip.open(path,'rt') as f:
    for x in csv.DictReader(f):
     assert float(x['gpu_us'])>0 and float(x['host_us'])>0
     if x['phase']=='test':
      b=int(x.get('batch_size',1));rows+=1;own+=1;operators+=b;batches+=int(b>1)
  expected_counts={'claim_dev':6240,'claim_confirm':18432,'soft_dev':15840,'soft_confirm':42240,'soft_panel':58752,'soft_fresh':14400,'soft_common':20736,'soft_batch':9792,'const_confirm':109440}
  for group,count in expected_counts.items():
   if m['key'].startswith(group+'_'):
    assert own==count,(m['key'],own,count)
    paths=list(w.rglob('requests.csv.gz'));assert len(paths)==(8 if group.startswith('claim_') else 24 if group=='const_confirm' else 12),(m['key'],'condition coverage')
  worker_info.append(dict(key=m['key'],test_observations=own,seconds=m['worker_seconds']))
 # Four slots repeat within a worker/offset intentionally; input sets must not
 # overlap between different development/confirmation/control processes.
 keys=sorted(all_hashes)
 for i,k in enumerate(keys):
  for other in keys[i+1:]:assert not (all_hashes[k]&all_hashes[other]),('input overlap',k,other)
 assert max(temps)<82 and set(limits)=={100000}
 common_checks=0
 for p in RUN.glob('soft_common_*/*/offset_*/configs.json'):
  x=read(p);assert set(x['all_job_map_pointers'])=={x['common_map_va']};common_checks+=1
 assert common_checks==6*4*3
 graph_checks=0
 for p in RUN.glob('const_confirm_*/*/*/offset_*/graphs.json'):
  fresh=p.parent.parent.parent.name=='fresh'
  for name,dag in read(p).items():
   expected_nodes=(2 if name=='NATIVE' else 1)+int(fresh);nodes=dag['nodes'];assert len(nodes)==expected_nodes and all(x['type']==0 for x in nodes),(p,name,'node count/type')
   paired=[x for x in nodes if 'paired' in x['function']]
   if name!='NATIVE':
    assert len(paired)==1;node=paired[0];assert node['grid']==[56,1,1] and node['block']==[128,1,1] and node['shared_bytes']==49152
    assert ('Schedule' in node['function'])==(not name.startswith('OLD_')),(p,name,node['function'])
   graph_checks+=1
 for p in RUN.glob('soft_batch_*/*/offset_*/graphs.json'):
  for name,dag in read(p).items():
   assert len(dag['nodes'])==(64 if name=='NATIVE' else 32) and all(x['type']==0 for x in dag['nodes']);graph_checks+=1
 tensors=[]
 for i in range(4):
  w=RUN/f'soft_tensor_{i}';e,r,ids=load_worker(w);assert ids==list(range(56)) and len(e)==4704;assert read(w/'environment.json')['flag_va']%(2<<20)==0;a=np.full((2,3,28,28),np.nan)
  for x in e:
   src=x['src']//2;dst=x['dst']//2;g=[0,17,257].index(x['slot']-src);a[x['round'],g,src,dst]=r[x['record_offset']]['cycles']/x['steps']
  assert np.isfinite(a).all();tensors.append(a)
 cost=np.mean(tensors[:2],axis=(0,1));assert np.array_equal(cost,np.array(read(ROOT/'freeze/SOFTMAX_MAPS.json')['cost_cycles']))
 val=np.mean(tensors[2:],axis=(0,1))
 for g,entry in enumerate(read(ROOT/'derived/softmax_topology.json')):
  assert np.array_equal(val[g],np.array(entry['confirmation'])) and np.array_equal(cost[g],np.array(entry['training']))
  assert abs(corr(residual(cost[g]),residual(val[g]))-entry['residual_correlation'])<1e-12
 for m in read(ROOT/'freeze/SOFTMAX_MAPS.json')['maps']:
  assert sorted(m['consumer_per_producer'])==list(range(1,56,2))
  for i,sm in enumerate(m['consumer_per_producer']):assert m['map'][sm]==i
 for proto in ['FRESH_PROTOCOL','COMMON_MAP_PROTOCOL','BATCH_PROTOCOL']:
  obj=read(ROOT/f'freeze/{proto}.json')
  for rel,h in obj.get('hashes',{}).items():assert sha(ROOT/rel)==h
  script={'COMMON_MAP_PROTOCOL':'common_map_experiment.py','BATCH_PROTOCOL':'batch_experiment.py'}.get(proto)
  if script:assert sha(ROOT/'src'/script)==obj['script_sha256']
 assert sha(ROOT/'build/softmax.so')==read(ROOT/'freeze/COMMON_MAP_PROTOCOL.json')['binary_sha256']
 assert sha(ROOT/'build/softmax_const.so')==read(ROOT/'freeze/BATCH_PROTOCOL.json')['binary_sha256']
 # Reanalysis is deterministic; development files are compared to their frozen
 # hashes again afterwards to make any accidental selection drift fatal.
 if reanalyze:
  claim_analyze('dev');claim_analyze('confirm');soft_analyze('dev');soft_analyze('confirm')
  for phase in ['panel','fresh','common','batch']:controls_analyze(phase)
  const_analyze()
  from costs import main as cost_analyze
  cost_analyze()
 assert read(ROOT/'freeze/CLAIM_SELECTION.json')['development_sha256']==sha(ROOT/'derived/claim_dev.json')
 assert read(ROOT/'freeze/SOFTMAX_BASELINE.json')['development_sha256']==sha(ROOT/'derived/soft_dev.json')
 development_rows=sum(x['test_observations'] for x in worker_info if '_dev_' in x['key'])
 audit=dict(development_timing_observations=development_rows,independent_validation_timing_observations=rows-development_rows,status='PASS',workers=len(ledger),expected_failed_workers=sorted(expected_failed),worker_seconds=sum(x['worker_seconds'] for x in ledger),worker_budget_seconds=3600,test_timing_observations=rows,test_batched_observations=batches,operator_requests_in_test=operators,numerical_checks=numeric,temperature_range_c=[min(temps),max(temps)],power_limit_w=100,input_sets_disjoint=True,source_and_binary_hashes_checked=len(checked),common_map_same_address_checks=common_checks,actual_graph_checks=graph_checks,worker_info=worker_info)
 write(ROOT/'derived/AUDIT.json',audit);print('RECOMPUTE_PASS',json.dumps({k:v for k,v in audit.items() if k!='worker_info'},ensure_ascii=False));return audit
if __name__=='__main__':run('--audit-only' not in sys.argv)
