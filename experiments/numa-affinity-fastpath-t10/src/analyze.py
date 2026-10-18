from common import *
import numpy as np,csv,gzip,collections,sys
def cells(phase):
 allrows=[]
 for worker in sorted(RUN.glob('claim_'+phase+'_*')):
  process=int(worker.name.rsplit('_',1)[1])
  for path in sorted(worker.glob('*/offset_*/requests.csv.gz')):
   grouped=collections.defaultdict(list)
   with gzip.open(path,'rt') as f:
    for x in csv.DictReader(f):
     if x['phase']=='test':grouped[(int(x['block']),x['label'])].append([float(x['gpu_us']),float(x['host_us'])])
   for (block,label),values in grouped.items():
    allrows.append(dict(case=path.parent.parent.name,offset=int(path.parent.name.split('_')[1]),process=process,block=block,label=label,gpu=float(np.median(np.array(values)[:,0])),host=float(np.median(np.array(values)[:,1])),requests=len(values)))
 return allrows
def logs(rows,a,b,metric='gpu'):
 z=collections.defaultdict(dict)
 for x in rows:z[(x['case'],x['offset'],x['process'],x['block'])][x['label']]=x[metric]
 return [dict(case=k[0],offset=k[1],process=k[2],block=k[3],log_ratio=float(np.log(v[a]/v[b]))) for k,v in z.items() if a in v and b in v]
def summary(values):
 byp=collections.defaultdict(list)
 for x in values:byp[x['process']].append(x['log_ratio'])
 p=np.array([np.mean(byp[i]) for i in sorted(byp)]);assert len(p)>0
 rng=np.random.default_rng(20261018);bs=p[rng.integers(0,len(p),(30000,len(p)))].mean(axis=1)
 gain=lambda v:100*(-np.expm1(v))
 return dict(gain_pct=float(gain(p.mean())),ci95_pct=np.sort(gain(np.quantile(bs,[.025,.975]))).tolist(),ci9875_pct=np.sort(gain(np.quantile(bs,[.00625,.99375]))).tolist(),process_gain_pct=gain(p).tolist(),processes=len(p),paired_blocks=len(values))
def run(phase):
 rows=cells(phase);labels=sorted({x['label'] for x in rows});caseids=read(ROOT/'freeze/PROTOCOL.json')['cases'];results=[]
 comparisons=[(x,'FAST') for x in labels if x not in ['FAST','ANCHOR_A','ANCHOR_B']]+[('ANCHOR_B','ANCHOR_A'),('FAST','ANCHOR_A')]
 if phase=='confirm':comparisons += [('MATCH',x) for x in ['BLIND','INVERT','SHUFFLE','STATIC']]
 else:comparisons += [(k+'_MATCH',k+'_'+c) for k in ['CA','CG'] for c in ['BLIND','INVERT','SHUFFLE','STATIC']]
 for a,b in comparisons:
  v=logs(rows,a,b)
  for case in ['ALL']+[x['id'] for x in caseids]:
   vv=v if case=='ALL' else [x for x in v if x['case']==case]
   results.append(dict(comparison=a+'/'+b,case=case,metric='gpu',**summary(vv)))
 write(ROOT/f'derived/claim_{phase}.json',dict(phase=phase,results=results,cells=rows))
 if phase=='dev' and '--freeze' in sys.argv:
  assert len({x['process'] for x in rows})==2
  selected={}
  for c in caseids:
   z=[x for x in results if x['case']==c['id'] and x['comparison'] in ['CA_MATCH/FAST','CG_MATCH/FAST']]
   best=max(z,key=lambda x:x['gain_pct']);selected[c['id']]=dict(kind=best['comparison'].split('_')[0],development_gain_pct=best['gain_pct'])
  p=ROOT/'freeze/CLAIM_SELECTION.json';assert not p.exists();write(p,dict(created_utc=utc(),cases=selected,rule='Select CA/CG by equal process/offset geometric full append time; retain all modes and negatives. No geometry tuning.',development_sha256=sha(ROOT/'derived/claim_dev.json'),implementation_sha256=sha(ROOT/'freeze/CLAIM_IMPLEMENTATION.json')))
 for x in results:
  if x['comparison'] in ['CA_MATCH/FAST','CG_MATCH/FAST','CA_MATCH/CA_BLIND','CG_MATCH/CG_BLIND','MATCH/FAST','MATCH/BLIND','MATCH/INVERT','MATCH/SHUFFLE']:print(x['case'],x['comparison'],round(x['gain_pct'],4),x['ci95_pct'])
if __name__=='__main__':run(sys.argv[1])
