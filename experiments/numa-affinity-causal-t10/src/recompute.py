"""Independent CPU-only recomputation and full integrity audit; no CUDA import."""
from common import *
from analyze import run as analyze,cells,key
from topology_math import hungarian
from make_maps import bottleneck
import numpy as np,csv,gzip,collections,sys
def run(reanalyze=True):
 ledger=[json.loads(l) for l in (RUN/'ledger.jsonl').read_text().splitlines()];by={m['key']:m for m in ledger};assert len(by)==len(ledger)
 assert {m['key'] for m in ledger if m['status']!='COMPLETED'}=={'memcheck'}
 assert 'Unable to find injection library' in ((RUN/'memcheck/stderr.log').read_text()+(RUN/'memcheck/stdout.log').read_text()) and by['memcheck']['worker_seconds']<1
 for k in ['qualification','memcheck_v2','synccheck','racecheck','diagnose']+[f'{phase}_{i}' for phase,n in [('dev',2),('confirm',6)] for i in range(n)]:assert by[k]['status']=='COMPLETED' and read(RUN/k/'complete.json')['status']=='PASS'
 freeze=read(ROOT/'freeze/IMPLEMENTATION.json');assert sha(ROOT/'freeze/MAPS.json')==freeze['maps_sha256']
 for name,h in read(ROOT/'freeze/MAPS.json')['source_hashes'].items():assert sha(ROOT/'freeze'/name)==h
 for rel,h in freeze['hashes'].items():assert sha(ROOT/rel)==h,(rel,'implementation hash')
 for rel,h in read(ROOT/'freeze/PROTOCOL.json')['baseline_hashes'].items():assert sha(ROOT/rel)==h
 assert freeze['created_utc']<by['dev_0']['started']
 amendment=read(ROOT/'freeze/SEED_AMENDMENT.json');assert sha(ROOT/'freeze/PROTOCOL_initial.json')==amendment['old_protocol_sha256'] and sha(ROOT/'freeze/PROTOCOL.json')==amendment['new_protocol_sha256'];assert amendment['created_utc']<by['confirm_0']['started']
 for m in ledger:assert m['protocol_sha256']==amendment['old_protocol_sha256' if m['started']<amendment['created_utc'] else 'new_protocol_sha256']
 seeds=[(phase,i,V,base+i*1000000+V) for phase,base,n in [('qualification',121000000,1),('dev',122000000,2),('confirm',223000000,6),('diagnose',124000000,1)] for i in range(n) for V in [131072,129024]];assert len(set(x[3] for x in seeds))==len(seeds)
 selection=read(ROOT/'freeze/SELECTION.json');assert selection['created_utc']<by['confirm_0']['started']
 for rel,h in selection['source_hashes'].items():assert sha(ROOT/rel)==h
 for m in ledger:
  assert read(RUN/m['key']/'manifest.json')==m
  if m['key'].startswith(('dev_','confirm_')):
   for rel,h in freeze['hashes'].items():
    if rel.startswith('src/'):assert m['sources'][rel]==h
    if Path(rel).parent==Path('build') and Path(rel).suffix=='.so':assert m['binaries'][Path(rel).name]==h
 # The balanced partition has exact coverage, no overlap, and at most one element imbalance.
 for V in [131072,129024]:
  counts=np.array([V//56+(sm<V%56) for sm in range(56)]);starts=np.array([sm*(V//56)+min(sm,V%56) for sm in range(56)]);assert starts[0]==0 and np.array_equal(starts[1:],starts[:-1]+counts[:-1]) and starts[-1]+counts[-1]==V and np.ptp(counts)<=1
  if V==129024:assert np.ptp(counts)==0
 # Frozen pooled-address schedule is derived only from old training matrices.
 model=read(ROOT/'freeze/MAPS.json');old=read(ROOT/'freeze/SOFTMAX_MAPS.json');a=bottleneck(np.mean(old['cost_cycles'],axis=0));mapping=np.arange(56)//2
 for i,j in enumerate(a):mapping[2*j+1]=i
 for m in model['maps']:
  assert sorted(m['map'][1::2])==list(range(28))
  if m['policy']=='POOLED':assert m['map']==mapping.tolist()
 for x in read(ROOT/'derived/INSTRUCTION_AUDIT.json'):assert x['equal_instructions']
 assert len(read(ROOT/'derived/INSTRUCTION_AUDIT.json'))==3
 # Independently recompute the best random schedule from development only.
 d=collections.defaultdict(lambda:collections.defaultdict(list))
 for x in cells('dev'):
  if x['label'].startswith('RND'):d[key(x)][x['label']].append(np.log(x['gpu']))
 for k,pol in d.items():assert min(pol,key=lambda n:np.mean(pol[n]))==selection['choices'][k]['policy']
 counts=collections.Counter();operators=collections.Counter();numeric=0;temps=[];limits=[];hashes={};graph_count=0;max_work_gap=0
 for m in ledger:
  w=RUN/m['key']
  for l in (w/'telemetry.jsonl').read_text().splitlines():
   z=json.loads(l);temps.append(z['temperature_c']['value']);limits.append(z['limit_mw']['value'])
  if m['status']!='COMPLETED':continue
  if (w/'numerical.json').exists():
   z=read(w/'numerical.json');assert all(x['status']=='PASS' and x['relative_l2']<1e-5 and x['max_scaled_error']<1 and abs(x['sum']-1)<1e-5 for x in z);numeric+=len(z)
   for x in z:
    if x.get('variant') in ['BAL','BOTH'] and 'work_min' in x:assert x['work_max']-x['work_min']<=1
    if x.get('variant') in ['FIX','BOTH'] and 'collector_sm' in x:assert x['collector_sm']==1
  if m['key'] in ['memcheck_v2','synccheck','racecheck']:
   text=(w/'stdout.log').read_text()+(w/'stderr.log').read_text();assert 'ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text
  if m['key'].startswith(('dev_','confirm_')):
   phase=m['key'].split('_')[0];config=read(ROOT/'freeze/PROTOCOL.json')['development' if phase=='dev' else 'confirmation'];paths=list(w.glob('V*/*/*/page*/requests.csv.gz'));assert len(paths)==48
   own=0;worker_hash=set();actual_conditions=set()
   for p in paths:
    cfg=read(p.parent/'config.json');actual_conditions.add((cfg['V'],cfg['variant'],cfg['page'],cfg['scope']));meta=read(p.parent/'mapping.json');worker_hash.update(meta['input_hashes']);assert meta['flags_va']%(2<<20)==0
    assert read(p.parent/'complete.json')['status']=='PASS'
    with gzip.open(p,'rt') as f:
     z=list(csv.DictReader(f))
    test=[x for x in z if x['phase']=='test'];labels=set(cfg['policies']);assert len(test)==len(labels)*config['blocks']*config['replays'];assert {x['label'] for x in test}==labels
    assert {int(x['block']) for x in test}==set(range(config['blocks']))
    buckets=collections.Counter((int(x['block']),x['label']) for x in test);assert len(buckets)==config['blocks']*len(labels) and set(buckets.values())=={config['replays']}
    for x in z:assert float(x['gpu_us'])>0 and float(x['host_us'])>0
    counts[phase]+=len(test);operators[phase]+=sum(int(x['batch']) for x in test);own+=len(test)
    dags=read(p.parent/'graphs.json');assert set(dags)==labels
    for label,dag in dags.items():
     batch=32 if 'batch' in cfg['scope'] else 1;fresh=cfg['scope'] in ['fresh','freshbatch'];nodes=dag['nodes'];assert len(nodes)==batch*((2 if label=='NATIVE' else 1)+int(fresh));assert all(n['type']==0 for n in nodes)
     ids={n['id']:n for n in nodes};adj=collections.defaultdict(list);incoming=collections.Counter()
     for u,v in dag['edges']:assert u in ids and v in ids;adj[u].append(v);incoming[v]+=1
     roots=[i for i in ids if incoming[i]==0];assert len(roots)==1 and len(dag['edges'])==len(nodes)-1 and all(incoming[i]<=1 and len(adj[i])<=1 for i in ids)
     chain=[];cur=roots[0]
     while True:
      assert cur not in chain;chain.append(cur)
      if not adj[cur]:break
      cur=adj[cur][0]
     assert len(chain)==len(nodes)
     expected_functions=((['copy_logits'] if fresh else [])+(['partial','finish'] if label=='NATIVE' else ['paired']))*batch
     assert all(f in ids[i]['function'] for i,f in zip(chain,expected_functions))
     paired=[n for n in nodes if 'paired' in n['function']]
     if label!='NATIVE':
      assert len(paired)==batch
      for n in paired:assert n['grid']==[56,1,1] and n['block']==[128,1,1] and n['shared_bytes']==49152
     graph_count+=1
   assert actual_conditions=={(V,var,p,s) for V in [131072,129024] for var in ['OLD','BAL','FIX','BOTH'] for p in ([0,17,257] if var=='BOTH' else [17]) for s in ['ready','fresh','batch','freshbatch']}
   assert own==(41472 if phase=='dev' else 110592);hashes[m['key']]=worker_hash
 for a,h in hashes.items():
  for b,j in hashes.items():
   if a!=b:assert not (h&j),(a,b,'input overlap')
 assert min(temps)>0 and max(temps)<82 and set(limits)=={100000}
 diag=read(RUN/'diagnose/trace_summary.json');assert len(diag)==1280
 for x in diag:
  if x['variant'] in ['FIX','BOTH']:assert x['collector']==1
  if x['variant'] in ['BAL','BOTH']:assert x['work_max']-x['work_min']<=1
 assert numeric==57308 and graph_count==6912
 seconds=sum(x['worker_seconds'] for x in ledger);assert seconds<=read(ROOT/'freeze/PROTOCOL.json')['worker_budget_seconds']
 assert sha(ROOT/'src/secondary.py')==read(ROOT/'freeze/SECONDARY_ANALYSIS.json')['script_sha256']
 if reanalyze:
  analyze('dev');analyze('confirm')
  from secondary import run as secondary
  secondary()
  from baseline_audit import run as baseline_audit
  baseline_audit()
  from timing_sensitivity import run as timing_sensitivity
  timing_sensitivity()
 audit=dict(status='PASS',workers=len(ledger),failed_workers=['memcheck'],worker_seconds=seconds,worker_budget_seconds=2400,numerical_checks=numeric,timing_observations=dict(counts),operator_requests=dict(operators),graph_checks=graph_count,temperature_range_c=[min(temps),max(temps)],power_limit_w=100,input_sets_disjoint=True,balanced_partition_coverage='PASS',fixed_collector='PASS',baseline_instruction_equality='PASS',frozen_hashes_checked=len(freeze['hashes']),selected_random_from_development_only='PASS')
 write(ROOT/'derived/AUDIT.json',audit);print('AUDIT_PASS',json.dumps(audit));return audit
if __name__=='__main__':run('--audit-only' not in sys.argv)
