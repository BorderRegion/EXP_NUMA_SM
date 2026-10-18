#!/usr/bin/env python3
"""Read-only post-run checks, cost decomposition and scope gaps; no GPU calls."""
import pathlib,json,csv,hashlib,statistics,collections,re
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'derived/t10'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 runs=[json.loads(x) for x in (ROOT/'run_index.jsonl').read_text().splitlines()];ids=[x['run_id'] for x in runs];assert len(ids)==len(set(ids))
 formal=[r for r in runs if r['stage']in['E4_W1','E4_W2']];assert len(formal)==48 and all(r['status']=='SUCCESS' for r in formal)
 checks=[];cost=[];health=[];plans=[];full_samples=0
 for r in runs:
  p=ROOT/r['path'];m=json.loads((p/'manifest.json').read_text());assert r['run_id']==m['run_id'] and r['status']==m['status']
  if r['status']=='SUCCESS' and (p/'correctness.json').exists():assert json.loads((p/'correctness.json').read_text())['status']=='PASS'
  if r['stage']=='E3':
   rows=list(csv.DictReader(open(p/'task_map.csv')));assert sorted(int(x['task'])for x in rows)==list(range(r['config']['tasks']))
   if r['config']['policy']!='N':
    expected=list(map(int,(ROOT/r['config']['plan_dir']/(r['config']['policy']+'.txt')).read_text().split()));assert [int(x['group'])for x in rows]==expected
  for name in ['health_before.csv','health_after.csv']:
   try:
    vals=[float(x)for x in (p/name).read_text().strip().split(',')];health.append(dict(run_id=r['run_id'],stage=r['stage'],when=name,temperature_c=vals[0],sm_mhz=vals[1],memory_mhz=vals[2],power_w=vals[3],memory_mib=vals[4],util_pct=vals[5]))
   except ValueError:raise ValueError('Invalid health record '+str(p))
 for r in formal:
  p=ROOT/r['path'];c=r['config'];key=(r['stage'],c.get('scene',c.get('input')),c['sequence'],c['block']);assert key not in checks;checks.append(key)
  stdout=(p/'stdout.log').read_text();completed=re.findall(r'SESSION_COMPLETE ([NRM]) warmup=(\d+) measured=(\d+)',stdout);assert len(completed)==3 and all(int(w)>=128 and int(n)==512 for _,w,n in completed)
  by=collections.defaultdict(list)
  for x in csv.DictReader(open(p/'frames.csv')):by[x['policy']].append(x)
  assert set(by)==set('NRM')
  for pol,rows in by.items():
   assert len(rows)==512 and [int(x['frame'])for x in rows]==list(range(512))
   for x in rows:
    assert all(int(x[k])==0 for k in ['planner_calls','plan_D2H_bytes','plan_H2D_bytes','recompile_count'])
    i=int(x['frame']);assert x['digest']==by['N'][i]['digest']
    if r['stage']=='E4_W1':assert x['camera_id']==by['N'][i]['camera_id']
   item=dict(run_id=r['run_id'],stage=r['stage'],input=key[1],sequence=key[2],block=key[3],policy=pol,mean_cpu_ready_ms=statistics.mean(float(x['cpu_ready_ms'])for x in rows))
   for field in ['upstream_ms','render_ms','dispatch_cpu_ms','memory_used_bytes']:
    item[field]=statistics.mean(float(x[field])for x in rows) if field in rows[0] else None
   item['plan_load_upload_ms']=None;item['plan_bytes']=0
   for x in csv.DictReader(open(p/'init_costs.csv')):
    if x['policy']==pol:item['plan_load_upload_ms']=float(x['plan_load_upload_ms']);item['plan_bytes']=int(x['plan_bytes'])
   cost.append(item)
  for frame in [0,256,511]:
   # The saved bytes are compared in addition to the online digest, where retained.
   files=[p/f'{pol}_frame_{frame}.bin' for pol in 'NRM']
   if all(f.exists()for f in files):
    assert len({sha(f)for f in files})==1
    full_samples+=1
 for build in sorted({r['build_id']for r in formal}|{r['build_id']for r in runs if r['stage']in['E2','E3']}):
  p=ROOT/'build'/build;m=json.loads((p/'build.json').read_text());sn=p/'source_snapshot'
  for original,expected in m['source_hashes'].items():
   q=sn/pathlib.Path(original).name;assert q.exists(),q;assert sha(q)==expected,q
  bins=m.get('binary_hashes',{'renderer_runner':m.get('binary_sha256')})
  for name,expected in bins.items():
   if expected:assert sha(p/name)==expected,p/name
 for card in (ROOT/'preregistration').glob('W*/*/plan_card.json'):
  d=json.loads(card.read_text());weight=json.loads((card.parent/'weights.json').read_text());n=len(weight['weights']);ws=weight['weights'];cl=weight['classes']
  for pol,expected in d['plan_hashes'].items():
   p=card.parent/(pol+'.txt');assert sha(p)==expected;mapping=list(map(int,p.read_text().split()));assert len(mapping)==n and set(mapping)=={0,1}
   for g in [0,1]:
    for k in range(3):tasks=[i for i,v in enumerate(mapping)if v==g and cl[i]==k];plans.append(dict(workload=card.parts[-3],input=card.parent.name,policy=pol,group=g,task_class=k,tasks=len(tasks),estimated_work=sum(ws[i]for i in tasks)))
 def write(name,rows):
  with open(OUT/name,'w')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 write('execution_costs.csv',cost);write('health_observations.csv',health);write('plan_work_distribution.csv',plans)
 report=dict(status='PASS',formal_blocks=len(checks),formal_build_cohorts={s:sorted({r['build_id']for r in formal if r['stage']==s})for s in ['E4_W1','E4_W2']},unique_run_ids=True,successful_correctness_records_pass=True,retained_full_samples_identical=True,full_sample_triplets_verified=full_samples,all_E3_loaded_maps_match_frozen_plans=True,actual_timed_source_and_binary_hashes_match=True,steady_contract_zero=True,health_ranges={k:[min(x[k]for x in health),max(x[k]for x in health)]for k in ['temperature_c','sm_mhz','power_w','memory_mib']},design_limits=['E3 policies are fresh processes paired by randomized batch, not shared allocation blocks.','E4 limited confirmation has only an initial N anchor, no timed trailing N drift anchor; R/M order randomized.','Six process blocks per condition on one device remain exploratory.','Common diagnostic digest and selected full readback are outside primary timer; no E5 instrumentation ablation.','No clock locking or power/thermal intervention. Capacity is effective service rate, not isolated physical-unit speed.','Initial CPU planner construction and isolated context setup wall times were not instrumented.','No physical GPC labels; no claim of fine physical placement in application runs.'])
 (OUT/'audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
