from runlib import ROOT,sha
from analyze_results import bootstrap,write_csv
import csv,json,collections,statistics,math,random,sys
OUT=ROOT/'derived/t10_supplement';OUT.mkdir(exist_ok=True)
def index(stage):return [r for r in map(json.loads,(ROOT/'run_index.jsonl').read_text().splitlines()) if r['stage']==stage and r['status']=='SUCCESS']
def analyze_stage(stage):
 runs=index(stage);expected=24
 if len(runs)!=expected:raise RuntimeError(f'{stage}: {len(runs)}/{expected}, incomplete')
 sessions=[];blocks=[]
 for r in runs:
  rows=list(csv.DictReader(open(ROOT/r['path']/'frames.csv')));by=collections.defaultdict(list)
  for x in rows:by[x['phase']].append(x)
  c=r['config'];inp=c['input'] if stage=='S1' else f"{c['bytes']//1048576}MiB/{'irregular' if c['irregular'] else 'coalesced'}";means={k:statistics.mean(float(x['cpu_ready_ms']) for x in v) for k,v in by.items()}
  if len(means)!=(5 if stage=='S1' else 6):raise RuntimeError('phase missing')
  for name,rs in by.items():
   if len(rs)!=(512 if stage=='S1' else 128):raise RuntimeError('epoch missing')
   sessions.append(dict(stage=stage,input=inp,block=c['block'],run_id=r['run_id'],path=r['path'],phase=name,mean_ms=means[name],epochs=len(rs)))
  means['N']=math.sqrt(means['N_head']*means['N_tail']);blocks.append(dict(input=inp,block=c['block'],run_id=r['run_id'],path=r['path'],means=means,anchor_ratio=means['N_tail']/means['N_head'],drift_flag=abs(means['N_tail']/means['N_head']-1)>.05))
 write_csv(OUT/(stage+'_sessions.csv'),sessions);(OUT/(stage+'_blocks.json')).write_text(json.dumps(blocks,indent=2))
 contrasts=[('M','N'),('M','R'),('E','N'),('R','E'),('M','E'),('M','N_head'),('M','N_tail'),('N_tail','N_head')] if stage=='S1' else [('A','N'),('A','I'),('A','P0'),('A','P1'),('A','N_head'),('A','N_tail'),('N_tail','N_head')]
 stats={}
 aggregates={inp:[b for b in blocks if b['input']==inp] for inp in sorted({b['input'] for b in blocks})}
 if stage=='S1':aggregates.update(W1=[b for b in blocks if b['input'] in ['bonsai','train']],W2=[b for b in blocks if b['input'] not in ['bonsai','train']])
 for label,bs in aggregates.items():
  for cand,ref in contrasts:
   records=[dict(condition=b['input'],block_id=b['block'],candidate_ms=b['means'][cand],reference_ms=b['means'][ref]) for b in sorted(bs,key=lambda b:(b['input'],b['block']))];result=bootstrap(records,seed=2026101503)
   result['all_block_ratios']=[r['candidate_ms']/r['reference_ms'] for r in records]
   if stage=='S3':
    vals=[math.log(x) for x in result['all_block_ratios']];rng=random.Random(2026101503);samples=sorted(math.exp(statistics.mean(rng.choices(vals,k=len(vals)))) for _ in range(20000));q=lambda p:samples[int((len(samples)-1)*p)];result['ratio_ci98_75']=[q(.00625),q(.99375)];result['leave_one_out_ratios']=[math.exp(statistics.mean(vals[:i]+vals[i+1:])) for i in range(len(vals))]
   stats[label+'_'+cand+'/'+ref]=result
 (OUT/(stage+'_statistics.json')).write_text(json.dumps(stats,indent=2))
 if stage=='S3':
  gate={}
  for inp in aggregates:
   rs=[stats[inp+'_A/'+ref] for ref in ['N','I','P0','P1']]
   gate[inp]=dict(pass_gate=all(r['ratio_ci98_75'][1]<1 and max(r['leave_one_out_ratios'])<1 for r in rs) and rs[0]['ratio']<=.97,comparisons={ref:stats[inp+'_A/'+ref] for ref in ['N','I','P0','P1']})
  (OUT/'S4_gate.json').write_text(json.dumps(dict(any_pass=any(x['pass_gate'] for x in gate.values()),conditions=gate),indent=2))
 print(stage,'complete',len(blocks),'blocks',len(sessions),'sessions','drift flags',sum(b['drift_flag'] for b in blocks))
 for k,v in stats.items():
  if '/N' in k or '/R' in k or '/I' in k:print(k,v['ratio'],v['ratio_ci95'])
if __name__=='__main__':analyze_stage(sys.argv[1])
