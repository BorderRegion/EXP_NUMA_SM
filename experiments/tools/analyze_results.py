#!/usr/bin/env python3
"""CPU-only, deterministic, paired process-block analysis from the raw index."""
import pathlib,json,csv,statistics,collections,math,random,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'derived/t10';OUT.mkdir(exist_ok=True)
def bootstrap(records,draws=20000,seed=2026101403):
 groups=collections.defaultdict(list);seen=set()
 for r in records:
  key=(r['condition'],r['block_id'])
  if key in seen:raise ValueError('duplicate independent block')
  seen.add(key);groups[r['condition']].append(math.log(r['candidate_ms']/r['reference_ms']))
 if not groups:return None
 def mean(x):return sum(x)/len(x)
 point=math.exp(mean([mean(v)for v in groups.values()]));rng=random.Random(seed);boot=[]
 for _ in range(draws):boot.append(math.exp(mean([mean([rng.choice(v)for __ in v])for v in groups.values()])))
 boot.sort()
 def q(p):z=(draws-1)*p;i=int(z);return boot[i]+(boot[min(i+1,draws-1)]-boot[i])*(z-i)
 return dict(ratio=point,time_reduction_pct=100*(1-point),ratio_ci95=[q(.025),q(.975)],ratio_ci97_5=[q(.0125),q(.9875)],draws=draws,seed=seed,strata=len(groups),independent_blocks=len(records),blocks_per_stratum={k:len(v)for k,v in groups.items()},scope='Within-device exploratory paired process blocks; 97.5% marginal intervals provide Bonferroni joint 95% coverage for two primary contrasts within a declared aggregate. Cell intervals descriptive.')
def write_csv(p,rows):
 if not rows:return
 with open(p,'w')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 runs=list(map(json.loads,(ROOT/'run_index.jsonl').read_text().splitlines()));formal=[r for r in runs if r['stage']in['E4_W1','E4_W2']and r['status']=='SUCCESS']
 if len(formal)!=48:raise SystemExit(f'Formal work not complete: {len(formal)}/48 process blocks. Do not publish partial statistics as final.')
 sessions=[];frames_total=0
 for r in formal:
  p=ROOT/r['path'];c=r['config'];workload='W1'if r['stage']=='E4_W1'else'W2';inp=c.get('scene',c.get('input'));by=collections.defaultdict(list)
  for x in csv.DictReader(open(p/'frames.csv')):
   by[x['policy']].append(x)
   for field in ['planner_calls','plan_D2H_bytes','plan_H2D_bytes','recompile_count']:
    if int(x[field]):raise ValueError('online planning contract violated')
  if set(by)!=set('NRM'):raise ValueError('formal policies')
  for policy,rows in by.items():
   if len(rows)!=512:raise ValueError('formal frame count')
   vals=[float(x['cpu_ready_ms'])for x in rows];frames_total+=len(vals)
   sessions.append(dict(run_id=r['run_id'],path=r['path'],workload=workload,input=inp,sequence=c['sequence'],block_id=c['block'],policy=policy,mean_ms=statistics.mean(vals),median_ms=statistics.median(vals),p95_ms=sorted(vals)[int(.95*(len(vals)-1))],min_ms=min(vals),max_ms=max(vals),frames=len(vals),build_id=r['build_id']))
 write_csv(OUT/'session_summaries.csv',sessions)
 blocks={}
 for s in sessions:blocks.setdefault((s['workload'],s['input'],s['sequence'],s['block_id']),{})[s['policy']]=s['mean_ms']
 paired={};summaries={}
 for reference in ['N','R']:
  records=[dict(platform='t10',condition='/'.join(map(str,key[:3])),block_id=key[3],reference_ms=v[reference],candidate_ms=v['M'])for key,v in sorted(blocks.items())]
  paired['M/'+reference]=records;(OUT/('paired_M_'+reference+'.json')).write_text(json.dumps(records,indent=2))
  summaries['ALL_M/'+reference]=bootstrap(records)
  for workload in ['W1','W2']:summaries[workload+'_M/'+reference]=bootstrap([r for r in records if r['condition'].startswith(workload+'/')])
  for workload,inp in sorted(set(k[:2]for k in blocks)):summaries[workload+'/'+inp+'_M/'+reference]=bootstrap([r for r in records if r['condition'].startswith(workload+'/'+inp+'/')])
  for condition in sorted(set(r['condition']for r in records)):summaries[condition+'_M/'+reference]=bootstrap([r for r in records if r['condition']==condition])
 (OUT/'application_statistics.json').write_text(json.dumps(summaries,indent=2))
 mechanism=[];models=[];mblocks={}
 for r in runs:
  if r['stage']!='E3'or r['status']!='SUCCESS':continue
  c=r['config'];p=ROOT/r['path'];s=json.loads((p/'summary.json').read_text());key=(c['distribution'],c['load'],c['block']);mblocks.setdefault(key,{})[c['policy']]=s['mean_cpu_ready_ms'];mechanism.append(dict(distribution=c['distribution'],load=c['load'],block_id=c['block'],policy=c['policy'],mean_ms=s['mean_cpu_ready_ms'],run_id=r['run_id'],path=r['path']))
  if c['policy']in['M','R']:
   card=json.loads((ROOT/c['plan_dir']/'plan_card.json').read_text());rates=card['rates'];pred=[0.,0.];seen={0:[],1:[]};scalar=[3/sum(1/v for v in row)for row in rates];normalizer=statistics.mean(scalar)
   # R's assignment is invariant to a common scale. For prediction in ms,
   # normalize its scalar speeds to mean 1, retaining task_cost's ms unit.
   for x in csv.DictReader(open(p/'task_map.csv')):
    g=int(x['group']);cl={0:0,2:1,3:2}[int(x['family'])]
    pred[g]+=1/rates[g][cl] if c['policy']=='M' else card['task_cost'][int(x['task'])]*normalizer/scalar[g]
   for x in csv.DictReader(open(p/'groups.csv')):seen[int(x['group'])].append(float(x['gpu_event_ms']))
   for g in [0,1]:actual=statistics.mean(seen[g]);models.append(dict(run_id=r['run_id'],distribution=c['distribution'],load=c['load'],block=c['block'],policy=c['policy'],group=g,predicted_ms=pred[g],actual_ms=actual,relative_error=(pred[g]-actual)/actual))
 if len(mechanism)!=252:raise ValueError('E3 incomplete')
 write_csv(OUT/'mechanism_sessions.csv',mechanism);write_csv(OUT/'prediction_error.csv',models)
 mstats={}
 for ref in ['N','R']:
  rec=[dict(platform='t10',condition=f'd{key[0]}/l{key[1]}',block_id=key[2],reference_ms=v[ref],candidate_ms=v['M'])for key,v in sorted(mblocks.items())]
  mstats['ALL_M/'+ref]=bootstrap(rec)
  for cond in sorted(set(x['condition']for x in rec)):mstats[cond+'_M/'+ref]=bootstrap([x for x in rec if x['condition']==cond])
 (OUT/'mechanism_statistics.json').write_text(json.dumps(mstats,indent=2))
 counts=collections.Counter((r['stage'],r['status'])for r in runs);costs=dict(worker_seconds=sum(r['worker_seconds']for r in runs),worker_definition='Wall-clock reservation of serialized GPU worker process, includes that process CPU initialization/reference work; not pure GPU busy time',actual_cost=0,cost_unit='CNY',basis='User explicitly reports owned local hardware with no resource charge; electricity not metered',stages={s:sum(r['worker_seconds']for r in runs if r['stage']==s)for s in sorted(set(r['stage']for r in runs))})
 (OUT/'costs.json').write_text(json.dumps(costs,indent=2));(OUT/'completion.json').write_text(json.dumps(dict(formal_process_blocks=len(formal),formal_sessions=len(sessions),measured_frames=frames_total,counts=[dict(stage=k[0],status=k[1],processes=v)for k,v in sorted(counts.items())],all_primary_zero_online_planning=True),indent=2))
 print(json.dumps({k:v for k,v in summaries.items()if k.startswith(('ALL_','W1_','W2_'))},indent=2));print('COMPLETE',len(formal),len(sessions),frames_total)
if __name__=='__main__':main()
