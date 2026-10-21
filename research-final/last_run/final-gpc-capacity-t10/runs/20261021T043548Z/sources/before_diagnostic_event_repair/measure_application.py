from range_runtime import *
import random
folder=Path(os.environ['T10_WORKER_DIR']);mode=sys.argv[1];block=int(sys.argv[2]);limited='--limited' in sys.argv
c=Control();gs,resource_ms=groups_create(c);rows=[];phases=[];checks=[];plans_meta=[];capacity=[];seeds=[]
weights=read(RUN/'freeze/CAP_WEIGHTS.json') if mode!='DEV' else None
cases=CASES[:4] if mode=='DEV' or limited or mode=='DYNAMIC' else CASES
rng=random.Random(211500+block+(10000 if mode=='CONFIRM' else 0));order=list(cases);rng.shuffle(order)
def save():
 write(folder/'PHASES.json',phases);write(folder/'CHECKS.json',checks);write(folder/'PLANS.json',plans_meta);write(folder/'CAPACITY.json',capacity);write(folder/'INPUTS.json',seeds)
 with gzip.open(folder/'REQUESTS.json.gz','wt') as f:json.dump(rows,f)
for case in order:
 cid=case['id'];seed=211600+block*10000+int(cid[1:])*100+(500000 if mode=='CONFIRM' else 0)+(700000 if mode=='DYNAMIC' else 0);offset=case['D']*2*(block%4)*128
 d=GQAData(shape(cid),seed,offset);seeds.append(dict(case=cid,metadata=d.meta))
 for append in ([True] if limited else [False,True]):
  scope='append' if append else 'attention';skey=cid+':'+scope;prefix=dict(mode=mode,block=block,case=cid,scope=scope)
  ref=NativePlan(c,d,append,'E56',True);raw=[]
  for slot in range(4):d.reset();ref.run(1,slot);checks.append(dict(**prefix,action='ORIGINAL_DIRECT',slot=slot,check=d.check_mode(append,slot)));raw.append(d.out.cpu().clone())
  ref.close();rr=ranges_for(d,[10,12,12,10,12]);tasktotal=sum(r['task_count'] for r in rr)
  actions={'N19':NativePlan(c,d,append),'E56_DIRECT':RangePlan(c,d,append,[0],[dict(task_begin=0,task_count=tasktotal)]),'SM_PROP':RangePlan(c,d,append,gs,rr),'EQUAL_GPC':RangePlan(c,d,append,gs,ranges_for(d,[1]*5))}
  if mode=='DEV':
   for i,g in enumerate(GROUP_ORDER):
    rp=RangePlan(c,d,append,[gs[i]],[dict(task_begin=0,task_count=tasktotal,physical_gpc=g)],diagnostic=True)
    checks.append(dict(**prefix,action='ISOLATED_'+str(g),checks=qualify(rp,raw)));warm(rp);sample=[]
    for slot in range(4):
     for rep in range(8):rp.run(1,slot);sample.append(float(rp.spans(slot)[0]))
    work=sum(task_costs(d.meta['lengths'],d.HK,rp.W));capacity.append(dict(**prefix,kind='ISOLATED',gpc=g,proxy_work=work,span_us=float(np.mean(sample)),samples_us=sample,capacity=work/np.mean(sample)))
    rp.close()
   diag=RangePlan(c,d,append,gs,rr,diagnostic=True);checks.append(dict(**prefix,action='CONCURRENT_DIAG',checks=qualify(diag,raw)));warm(diag);sample=[]
   for slot in range(4):
    for rep in range(8):diag.run(1,slot);sample.append(diag.spans(slot).tolist())
   arr=np.asarray(sample)
   for i,g in enumerate(GROUP_ORDER):capacity.append(dict(**prefix,kind='CONCURRENT',gpc=g,proxy_work=rr[i]['proxy_work'],span_us=float(arr[:,i].mean()),samples_us=arr[:,i].tolist(),capacity=rr[i]['proxy_work']/arr[:,i].mean(),range=rr[i]))
   diag.close()
  else:
   w=weights['weights'][case['weights_from']+':'+scope]['concurrent'];actions['CAP']=RangePlan(c,d,append,gs,ranges_for(d,w));actions['WRONG_CAP']=RangePlan(c,d,append,gs,ranges_for(d,w[1:]+w[:1]))
  signatures={};aliases={};canonical={}
  for a,p in actions.items():
   signature=json.dumps([p.info['kind'],p.groups,[(r['task_begin'],r['task_count']) for r in p.ranges],p.info.get('mode'),p.info.get('fused')],sort_keys=True)
   if signature in signatures:aliases[a]=signatures[signature];p.close()
   else:signatures[signature]=a;canonical[a]=p
  for a,p in canonical.items():
   checks.append(dict(**prefix,action=a,checks=qualify(p,raw if a!='N19' else None)));plans_meta.append(dict(**prefix,action=a,**p.info,resource_setup_ms=resource_ms))
  for a,p in canonical.items():warm(p)
  if mode=='DEV':
   pilot=canonical['N19'].run(8);n=4*math.ceil(max(8,min(128,math.ceil(5000/np.median(pilot[:,1]))))/4)
   plans_meta.append(dict(**prefix,kind='PILOT',replays=n,pilot=pilot.tolist()))
  else:n=weights['replays'][skey]
  action_samples={a:[] for a in canonical};seq=[a for a in canonical if a!='N19'];rng.shuffle(seq)
  # Every candidate gets an ABBA or BAAB paired native window. All raw order kept.
  for ix,a in enumerate(seq):
   warm(canonical['N19']);warm(canonical[a]);pair=['N19',a,a,'N19'] if (ix+block)%2==0 else [a,'N19','N19',a]
   for segment,label in enumerate(pair):
    vals=canonical[label].run(n,segment%4);action_samples[label].append(vals)
    for k,v in enumerate(vals):rows.append(dict(**prefix,comparison=a,action=label,segment=segment,slot=(segment+k)%4,gpu_us=float(v[0]),ready_us=float(v[1])))
  for a,p in canonical.items():
   vals=np.concatenate(action_samples[a]);warm_batch(p);batch=[p.batch(32,i%4).tolist() for i in range(4)]
   phases.append(dict(**prefix,action=a,status='MEASURED',gpu_us=float(vals[:,0].mean()),ready_us=float(vals[:,1].mean()),requests=len(vals),batch32_gpu_us=float(np.mean([v[0] for v in batch])),batch32_ready_us=float(np.mean([v[1] for v in batch])),batch_raw=batch,utc=utc()))
  for a,target in aliases.items():phases.append(dict(**prefix,action=a,status='STRUCTURAL_ALIAS',alias_of=target))
  for p in canonical.values():p.close()
  save();print('APPLICATION',mode,block,cid,scope,'PASS',flush=True)
 d.close()
for g in gs:c.drop(g)
write(folder/'DONE.json',dict(status='PASS',mode=mode,block=block,labels=len(phases)))
