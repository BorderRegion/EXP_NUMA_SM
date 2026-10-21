from common import *
import sys,csv,gzip,collections,itertools
import numpy as np
sys.path.insert(0,str(REPO/'sm-topology-t10/src'))
from analysis_lib import load_worker,residual
out=RUN/'derived/E1';out.mkdir(parents=True,exist_ok=True)
old=REPO/'sm-topology-t10';oldrun=old/'runs/20261017T121101Z'
top=list(csv.DictReader((REPO/'gpc-mask-t10/reports/SM_TO_GPC_TPC.csv').open()))
sm={int(r['global_logical_sm']):{k:int(v) for k,v in r.items()} for r in top}
rule=read(old/'freeze/MAPPING.json')['address_exploratory_2groups']
pref={s:i for i,ss in enumerate(rule) for s in ss}
assert len(pref)==56
assert all(len({pref[s] for s in sm if sm[s]['physical_gpc']==g})==1 for g in [0,1,2,3,5])
src_manifest=[];address=[];pairs=[];signed=[];gpc_cells=[];pair_categories=[];main_effects=[]
for block in range(6):
 folder=oldrun/'raw'/f'matrix_{block}';env=read(folder/'environment.json');e,r,ids=load_worker(folder)
 for f in ['epochs.csv','records.bin','environment.json','chain_starts.csv','manifest.json']:
  src_manifest.append(dict(path=str((folder/f).relative_to(REPO)),sha256=sha(folder/f)))
 for mode in [0,1]:
  for round_ in [0,1]:
   a=np.empty((56,64,2));p=np.empty((3,56,56,2))
   for q in e[(e['mode']==mode)&(e['round']==round_)]:
    x=r[q['record_offset']];values=[float(x[k])/int(q['steps']) for k in ['ns','cycles']]
    if q['kind']==2:a[int(q['src']),int(q['region'])]=values
    elif q['kind']==1:p[int(q['slot']),int(q['src']),int(q['dst'])]=values
   for unit_i,unit in enumerate(['ns','cycles']):
    av=a[:,:,unit_i];res=residual(np.log(av));classes=np.array([(reg&0x33).bit_count()%2 for reg in range(64)])
    for s in range(56):
     v0=float(av[s,classes==0].mean());v1=float(av[s,classes==1].mean())
     signed.append(dict(block=block,round=round_,cache=['cg','ca'][mode],unit=unit,sm=s,gpc=sm[s]['physical_gpc'],historical_group=pref[s],class0_mean=v0,class1_mean=v1,class1_minus_class0=v1-v0,log_class1_over_class0=float(np.log(av[s,classes==1]).mean()-np.log(av[s,classes==0]).mean())))
     for reg in range(64):
      address.append(dict(block=block,round=round_,cache=['cg','ca'][mode],unit=unit,sm=s,gpc=sm[s]['physical_gpc'],region=reg,class_0x33=int(classes[reg]),chain_va=env['chain_va'],per_step=float(av[s,reg]),log_row_column_residual=float(res[s,reg])))
    for g in [0,1,2,3,5]:
     selected=[s for s in range(56) if sm[s]['physical_gpc']==g]
     for reg in range(64):gpc_cells.append(dict(block=block,round=round_,cache=['cg','ca'][mode],unit=unit,gpc=g,region=reg,sm_count=len(selected),raw_sm_equal_mean=float(av[selected,reg].mean()),log_residual_sm_equal_mean=float(res[selected,reg].mean())))
    for slot in range(3):
     pv=p[slot,:,:,unit_i];pr=residual(np.log(pv),True)
     offset=[0,17*4096,257*4096][slot]
     for s in range(56):
      main_effects.append(dict(block=block,round=round_,mode=mode,slot=slot,unit=unit,sm=s,sender_log_mean=float(np.log(np.delete(pv[s,:],s)).mean()),receiver_log_mean=float(np.log(np.delete(pv[:,s],s)).mean())))
      by=collections.defaultdict(list)
      for d in range(56):
       cat='same_CTA_diagonal' if s==d else 'same_TPC' if sm[s]['global_logical_tpc']==sm[d]['global_logical_tpc'] else 'same_GPC_other_TPC' if sm[s]['physical_gpc']==sm[d]['physical_gpc'] else 'cross_GPC_same_historical_group' if pref[s]==pref[d] else 'cross_historical_group'
       row=dict(block=block,round=round_,mode=mode,slot=slot,unit=unit,source_sm=s,destination_sm=d,source_gpc=sm[s]['physical_gpc'],destination_gpc=sm[d]['physical_gpc'],category=cat,request_va=env['flag_va']+offset,ack_va=env['flag_va']+offset+128,payload_va=env['flag_va']+offset+256,rtt=float(pv[s,d]),log_row_column_residual=None if s==d else float(pr[s,d]))
       pairs.append(row)
       if s!=d:by[cat].append(row)
      for cat,rr in by.items():pair_categories.append(dict(block=block,round=round_,mode=mode,slot=slot,unit=unit,source_sm=s,category=cat,n_receivers=len(rr),rtt_geomean=float(np.exp(np.mean([np.log(v['rtt']) for v in rr]))),residual_mean=float(np.mean([v['log_row_column_residual'] for v in rr]))))
 print('HISTORY_BLOCK',block,flush=True)
def save(name,rows):
 with gzip.open(out/(name+'.csv.gz'),'wt',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
for name,rows in [('address_raw_by_round',address),('address_signed_by_sm',signed),('address_gpc_cells',gpc_cells),('pair_raw_by_round',pairs),('pair_sender_categories',pair_categories),('pair_main_effects',main_effects)]:save(name,rows)
rng=np.random.default_rng(2026101901);boot=rng.integers(0,6,(20000,6))
summary=[]
for cache in ['cg','ca']:
 for unit in ['ns','cycles']:
  for g in [0,1,2,3,5]:
   rr=[x for x in signed if x['cache']==cache and x['unit']==unit and x['gpc']==g]
   vals=np.array([np.mean([x['class1_minus_class0'] for x in rr if x['block']==b]) for b in range(6)])
   logs=np.array([np.mean([x['log_class1_over_class0'] for x in rr if x['block']==b]) for b in range(6)])
   summary.append(dict(cache=cache,unit=unit,gpc=g,class1_minus_class0=float(vals.mean()),difference_ci95=np.quantile(vals[boot].mean(axis=1),[.025,.975]).tolist(),block_differences=vals.tolist(),block_log_class1_over_class0=logs.tolist(),log_ratio_percent=float(logs.mean()*100),negative_blocks=int((vals<0).sum()),historical_group=pref[next(s for s in sm if sm[s]['physical_gpc']==g)]))
weights=[]
for cache in ['cg','ca']:
 for unit in ['ns','cycles']:
  rr=[x for x in summary if x['cache']==cache and x['unit']==unit]
  for weighting in ['SM_equal','GPC_equal']:
   for group in [0,1]:
    chosen=[x for x in rr if x['historical_group']==group]
    ww=[sum(1 for s in sm if sm[s]['physical_gpc']==x['gpc']) if weighting=='SM_equal' else 1 for x in chosen]
    vals=np.average(np.array([x['block_differences'] for x in chosen]),axis=0,weights=ww)
    weights.append(dict(cache=cache,unit=unit,weighting=weighting,historical_group=group,block_signed_difference=vals.tolist(),mean=float(vals.mean()),ci95=np.quantile(vals[boot].mean(axis=1),[.025,.975]).tolist()))
write(out/'SUMMARY.json',dict(gpc_signed=summary,group_weighting=weights,history_group_gpcs={str(i):sorted({sm[s]['physical_gpc'] for s in group}) for i,group in enumerate(rule)},development_blocks=[0,1],confirmation_blocks=[2,3,4,5],units='time per dependent-load step, not bare L2 latency',pair_address_class='not assigned; actual flag VA and offsets only',row_counts={k:len(v) for k,v in [('address',address),('signed',signed),('pairs',pairs)]}))
write(out/'SOURCE_PROVENANCE.json',dict(sources=src_manifest,old_mapping_sha256=sha(old/'freeze/MAPPING.json'),historical_topology_sha256=sha(REPO/'gpc-mask-t10/reports/SM_TO_GPC_TPC.csv'),current_matches_historical=True,current_boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),topology_join_limit='Stage15 did not issue contemporaneous RM GET. Same UUID, current boot predates both campaigns, and current RM map matches stage22; intervening driver reset/reload not independently proven absent. No geometric-distance claim.'))
print('E1_PASS',len(address),len(pairs),flush=True)
