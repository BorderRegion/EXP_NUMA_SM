from common import *
import numpy as np
cases=json.loads((INPUT/'plans/gemm_cases.json').read_text());cd={x['case_id']:x for x in cases};rows=[];stages={}
for p in sorted((runroot()/'raw').glob('E1_block_*/phases.jsonl')):rows += [json.loads(x) for x in p.read_text().splitlines()]
for p in sorted((runroot()/'raw').glob('E1_block_*/stages.jsonl')):
 for x in p.read_text().splitlines():
  a=json.loads(x);stages[a['phase_id']]=a
def binid(x):return f"M{0 if x['M']<=8 else 1 if x['M']<=128 else 2}_N{int(x['N']>4096)}"
bins={};cards=[]
for b in sorted({binid(x) for x in cases}):
 ids={x['case_id'] for x in cases if x['split']=='development' and binid(x)==b};opts=[]
 if not ids:
  bins[b]=dict(bins[b.replace('_N1','_N0')],inheritance='No N>4096 development shape exists in supplied fixed split. Predeclared inheritance from same M bin; no test tuning.');continue
 for r in range(4):
  for s in [1,2,4,8,16]:
   a=[x for x in rows if x['case'] in ids and x['policy']!='LIB' and x['recipe']==r and x['S']==s]
   assert len(a)==len(ids)*2,(b,r,s,len(a))
   score=float(np.mean([np.log(x['batch_per_replay_us']) for x in a]));opts.append(dict(recipe=r,S=s,score_log_us=score))
 best=min(opts,key=lambda x:x['score_log_us']);mechanism=min([x for x in opts if x['S']>1],key=lambda x:x['score_log_us']);bins[b]=dict(production=best,mechanism=mechanism,forced_split=best['S']==1,development_cases=sorted(ids),all_options=opts)
for cid in sorted({x['case'] for x in rows}):
 c=cd[cid];b=bins[binid(c)];v=b['mechanism'];a=[x for x in rows if x['case']==cid and x['policy']=='CORE' and x['recipe']==v['recipe'] and x['S']==v['S']];assert len(a)==2
 st=[stages[x['phase_id']] for x in a];lib=[x['batch_per_replay_us'] for x in rows if x['case']==cid and x['policy']=='LIB'];s1=[x['batch_per_replay_us'] for x in rows if x['case']==cid and x['policy']=='S1' and x['recipe']==v['recipe']]
 bm,bn=[(32,64),(64,64),(64,128),(128,128)][v['recipe']];nt=((c['M']+bm-1)//bm)*((c['N']+bn-1)//bn)
 cards.append(dict(**c,bin=binid(c),recipe=v['recipe'],S=v['S'],production_S=b['production']['S'],production_recipe=b['production']['recipe'],forced_split=b['forced_split'],lib_us=float(np.mean(lib)),samecore_S1_us=float(np.mean(s1)),split_us=float(np.mean([x['batch_per_replay_us'] for x in a])),R_fraction_proxy=float(np.mean([x['R_us']/x['chain_us'] for x in st])),P_instrumented_us=float(np.mean([x['P_us'] for x in st])),R_instrumented_us=float(np.mean([x['R_us'] for x in st])),workspace_planar_bytes=c['M']*c['N']*v['S']*4,workspace_slab_bytes=nt*bm*bn*v['S']*4,output_tiles=nt,P_ctas=nt*v['S'],R_native_ctas=((c['M']+3)//4)*((c['N']+127)//128),FLOPs=2*c['M']*c['N']*c['K'],A_B_bytes=2*c['K']*(c['M']+c['N']),logical_partial_rw_bytes=8*c['M']*c['N']*v['S']))
ordered=sorted(cards,key=lambda x:x['R_fraction_proxy']);reps=[]
for tier,ix in enumerate(np.array_split(np.arange(len(ordered)),3)):
 selected=sorted(ix,key=lambda j:abs(float(j)-float(np.mean(ix))))[:2]
 for j in sorted(selected):reps.append(dict(**ordered[j],tier=['LOW','MEDIUM','HIGH'][tier]))
result=dict(frozen_at=utc(),basis='Baseline natural instrumented reducer fraction, middle two in each tertile; no candidate results used',bins=bins,representatives=reps,owner='CONTIGUOUS_HALF_TILES',cards=cards)
write(ROOT/'freeze/selection.json',result);print(json.dumps({'bins':{k:dict(production=v['production'],mechanism=v['mechanism']) for k,v in bins.items()},'representatives':[(x['case_id'],x['tier'],x['R_fraction_proxy']) for x in reps]},indent=2))
