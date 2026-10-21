from campaign_runtime import *
import sys
stage=sys.argv[1];block=int(sys.argv[2]);folder=Path(os.environ['T10_WORKER_DIR'])
allph=[];allrows=[];allalias=[];allchecks=[];allorders=[];provenance=[]
def qualify(plans,s):
 seen=set()
 for label,p in plans.items():
  if p.signature in seen:continue
  seen.add(p.signature)
  for slot in range(4):
   s.d.reset();p.run(1,slot);allchecks.append(dict(case=s.cid,label=label,start_slot=slot,check=p.check(slot,True)))
 s.d.reset()
def run_suite(plans,s,task='JOINT'):
 canonical_by_sig={};unique={};alias={}
 for label,p in plans.items():
  if p.signature not in canonical_by_sig:canonical_by_sig[p.signature]=label;unique[label]=p
  alias[label]=canonical_by_sig[p.signature]
 allalias.append(dict(stage=stage,block=block,case=s.cid,task=task,aliases=alias,requested_actions={label:getattr(p,'a',None) for label,p in plans.items()}))
 qualify(plans,s)
 s.d.headroom()
 labels=list(unique);rng=np.random.default_rng(193000000+block*1000+(1 if s.cid=='LONG' else 2)*100+{'S1':1,'S2':2,'S3':3,'HOLDOUT':4}[stage]+(10 if task=='FG' else 20 if task=='BG' else 0));rng.shuffle(labels)
 anchor=plans['GREEN56'] if stage=='S1' else plans['SHARED56']
 order=[('ANCHOR_HEAD',None,anchor,4),('AA_HEAD',None,anchor,4)]+[('PRIMARY',label,unique[label],8) for label in labels]+[('PRIMARY',label,unique[label],8) for label in labels[::-1]]+[('ANCHOR_TAIL',None,anchor,4),('AA_TAIL',None,anchor,4)]
 order_doc=dict(stage=stage,block=block,case=s.cid,task=task,first_sweep=labels,second_sweep=labels[::-1],frozen_before_timing=True)
 allorders.append(order_doc);write(folder/'ORDER.json',allorders)
 samples=collections.defaultdict(list);durations=collections.defaultdict(list);warms=collections.defaultdict(list)
 for pos,(role,label,p,n) in enumerate(order):
  ident=label if role=='PRIMARY' else role;key=(s.cid,task,role,ident);t=time.perf_counter();s.d.reset()
  nw=0;tw=0.
  while nw<2 or tw<50000:
   a=p.run(4);nw+=4;tw+=a[:,3].sum()
  a=p.run(n);durations[key].append((time.perf_counter()-t)*1000);warms[key].append(dict(jobs=nw,host_us=float(tw)));offset=len(samples[key]);samples[key].extend(a.tolist())
  for i,x in enumerate(a):
   allrows.append(dict(run=RUN.name,stage=stage,block=block,case=s.cid,task=task,role=role,label=ident,order_position=pos,sample=offset+i,first_slot=i%4,input_seed=s.d.seed,allocation_generation=f'{stage}_{block}_{s.cid}',sm_set_hash=p.meta['sm_set_hash'],state_epoch=utc(),**{m:(float(x[j]) if x[j]>=0 else None) for j,m in enumerate(METRICS)}))
  # Cached output references only; no new FP64 reference construction between timing actions.
  allchecks.append(dict(case=s.cid,task=task,label=ident,role=role,order_position=pos,check=p.check((n-1)%4,False),scope='output versus precomputed references; full KV checked in pre-suite qualification'))
  print('PHASE',stage,block,s.cid,task,pos,ident,flush=True)
 for key,values in samples.items():
  cid,task,role,label=key;p=unique[label] if role=='PRIMARY' else anchor;a=np.array(values)
  assert len(a)==(16 if role=='PRIMARY' else 4)
  allph.append(dict(run=RUN.name,stage=stage,block=block,case=cid,task=task,role=role,label=label,formal_jobs=len(a),phase_wall_ms=sum(durations[key]),warmups=warms[key],input_seed=s.d.seed,allocation_generation=f'{stage}_{block}_{cid}',math='UNCHANGED_STAGE26_E56_AND_CUBLAS',launcher='static_tail_events_v1',**p.meta,**{m:(float(a[:,j].mean()) if (a[:,j]>=0).all() else None) for j,m in enumerate(METRICS)}))
 save_csv(folder/'requests.csv.gz',allrows);write(folder/'PHASES.json',allph);write(folder/'ALIASES.json',allalias);write(folder/'NUMERICAL.json',allchecks)
for cid in (['LONG','RAGGED'] if block%2==0 else ['RAGGED','LONG']):
 s=Suite(cid,block,(14 if cid=='LONG' else 18) if stage=='HOLDOUT' else None)
 if stage=='S1':
  conditions=['PRIMARY56','GREEN56']+[f'{fam}_Q{q}' for q in [10,20,28,36,46] for fam in ['NEUTRAL','PACK','SPREAD']]
  plans={task:{label:s.solo(task,label) for label in conditions} for task in ['FG','BG']}
  for task in (['FG','BG'] if block%2==0 else ['BG','FG']):run_suite(plans[task],s,task)
 elif stage=='S2':
  ks=read(RUN/'freeze/PREFIX.json')[cid];actions=[native(n) for n in BASELINES]+[action(fam,q,mode,ks[f'{fam}_Q{q}']['k']) for q in [10,20,28,36,46] for fam in ['NEUTRAL','PACK','SPREAD'] for mode in ['FIXED','RELEASE']]
  run_suite({name(a):s.plan(a) for a in actions},s)
 else:
  chosen=read(RUN/'freeze/SELECTION.json')[cid];actions={n:native(n) for n in BASELINES}
  for label in ['Q_ONLY','SIMPLE_SPREAD','JOINT_POOL']:actions[label]=chosen[label]['action']
  if stage=='S3':
   pc=chosen['PC_STAR']['action']
   for fam in ['NEUTRAL','PACK','SPREAD']:actions['ABLATE_'+fam]=dict(pc,family=fam)
   actions['ABLATE_OTHER_MODE']=dict(pc,mode='RELEASE' if pc['mode']=='FIXED' else 'FIXED')
  run_suite({label:s.plan(a) for label,a in actions.items()},s)
 provenance.append(s.provenance());write(folder/'PROVENANCE.json',provenance)
 with gzip.open(folder/f'{cid}_RESOURCE_TRACE.json.gz','wt') as f:json.dump(s.c.observations,f)
 s.close()
write(folder/'COMPLETE.json',dict(status='PASS',stage=stage,block=block,measured_primary_phases=sum(x['role']=='PRIMARY' for x in allph),all_phases=len(allph),timing_rows=len(allrows),aliases_are_same_physical_plan=True));print('WORKER_COMPLETE',stage,block,flush=True)
