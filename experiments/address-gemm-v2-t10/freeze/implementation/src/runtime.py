from backend import *
import gzip,csv
lib.ag_repeat.argtypes=[P,I,DP]
POLICIES=['NATIVE','DIRECT','QUEUE_BLIND','QUEUE_MATCH','QUEUE_INVERT','QUEUE_SHUFFLED','FUSED','LIB']
def repeat(j,n):
 a=(C.c_double*(5*n))();check(lib.ag_repeat(j.ptr,n,a));return np.ctypeslib.as_array(a).copy().reshape(n,5)
def make_lists(d,chunk,seed):
 tasks=(d.m*d.n+chunk-1)//chunk;pages=(d.w.data_ptr()+np.arange(tasks,dtype=np.uint64)*chunk*4)>>12
 cls=np.array([int(int(p)&0x33).bit_count()%2 for p in pages],np.int32)
 def encode(labels):
  a=np.flatnonzero(labels==0);b=np.flatnonzero(labels==1);return np.concatenate(([len(a),len(b)],a,b)).astype(np.int32)
 rng=np.random.default_rng(seed);shuffled=cls[rng.permutation(tasks)];plain=encode(cls);other=encode(shuffled)
 consistent=[]
 for task in range(tasks):
  labels=[((d.w.data_ptr()+(s*d.m*d.n+task*chunk)*4)>>12&0x33).bit_count()%2 for s in range(d.splits)]
  consistent.append(len(set(labels))==1)
 return plain,other,dict(first_slice_class=cls.tolist(),shuffled_class=shuffled.tolist(),all_splits_same_class_fraction=float(np.mean(consistent)),workspace_va=d.w.data_ptr(),chunk=chunk)
def build_jobs(e,d,c,chunk,grid,seed,diag=False):
 plain,other,meta=make_lists(d,chunk,seed);lists={'plain':torch.tensor(plain,device='cuda'),'shuffled':torch.tensor(other,device='cuda')}
 bm,bn=[(32,64),(64,64),(64,128),(128,128)][c['recipe']];tiles=((d.m+bm-1)//bm)*((d.n+bn-1)//bn);tasks=(d.m*d.n+chunk-1)//chunk
 counters={'queue':torch.zeros(2,dtype=torch.int32,device='cuda'),'fused':torch.zeros(tiles,dtype=torch.int32,device='cuda')};traces={}
 if diag:
  for p in ['QUEUE_BLIND','QUEUE_MATCH','QUEUE_INVERT','QUEUE_SHUFFLED']:
   tr=torch.zeros(tasks*5,dtype=torch.int32,device='cuda');tr[:tasks*4]=-1;traces[p]=tr
  traces['FUSED']=torch.full((tiles*c['s']*2+tiles,),-1,dtype=torch.int32,device='cuda')
 jobs={}
 for pol in POLICIES:
  kind=0 if pol=='NATIVE' else 3 if pol=='LIB' else 10 if pol=='DIRECT' else 12 if pol=='FUSED' else 11
  ls=lists['shuffled' if pol=='QUEUE_SHUFFLED' else 'plain'];counter=counters['fused' if pol=='FUSED' else 'queue'];mode=0 if pol=='QUEUE_BLIND' else 2 if pol=='QUEUE_INVERT' else 1
  jobs[pol]=[Job(e,d,recipe=c['recipe'],s=c['s'],kind=kind,slab=chunk,submit_reverse=grid,task_reverse=mode,slot=i,mapping=ls,counters=counter,placement=traces.get(pol),diag=int(diag)) for i in range(d.ring)]
  for j in jobs[pol]:j.policy=pol
 meta.update(tiles=tiles,tasks=tasks,grid=grid,queue_storage_ints=plain.size,counter_bytes=4*(2+tiles));return jobs,dict(lists=lists,counters=counters,traces=traces,meta=meta)
def close_jobs(jobs):
 for js in jobs.values():
  for j in js:j.close()
def numeric(j,d):
 d.d.fill_(float('nan'));torch.cuda.synchronize();j.run();return d.numerical(j.slot,j.alpha,j.beta)
def validate_traces(jobs,buffers,d,c,out):
 meta=buffers['meta'];n=meta['tasks'];nt=meta['tiles'];records=[]
 for pol,tr in buffers['traces'].items():
  if pol=='FUSED':tr.fill_(-1)
  else:tr.zero_();tr[:4*n]=-1
  torch.cuda.synchronize();jobs[pol][0].run();r=d.numerical(0);a=tr.cpu().numpy();np.save(out/(pol+'_placement.npy'),a)
  if pol=='FUSED':
   part=a[:nt*c['s']*2].reshape(nt,c['s'],2);last=a[nt*c['s']*2:];assert np.array_equal(np.sort(part[:,:,1],axis=1),np.tile(np.arange(c['s']),(nt,1)));assert ((part[:,:,0]>=0)&(part[:,:,0]<56)).all();assert np.array_equal(last,part[np.arange(nt),np.argmax(part[:,:,1],axis=1),0]);assert not buffers['counters']['fused'].count_nonzero().item();r['last_arrival_and_counter_reset']='PASS'
  else:
   tasks=a[:4*n].reshape(n,4);assert (a[4*n:]==1).all();assert ((tasks[:,0]>=0)&(tasks[:,0]<56)).all();assert ((tasks[:,3]>=0)&(tasks[:,3]<meta['grid'])).all()
   sm_pref=((tasks[:,0]%10>=4)&(tasks[:,0]%10<=7)).astype(int);expected=(tasks[:,3]&1) if pol=='QUEUE_BLIND' else 1-sm_pref if pol=='QUEUE_INVERT' else sm_pref;assert np.array_equal(tasks[:,1],expected)
   cls=np.array(meta['shuffled_class'] if pol=='QUEUE_SHUFFLED' else meta['first_slice_class']);assert np.array_equal(tasks[:,2],cls);r['coverage']='EACH_TASK_EXACTLY_ONCE';r['preferred_queue_fraction']=float(np.mean(tasks[:,1]==tasks[:,2]));r['actual_sms']=len(np.unique(tasks[:,0]))
  r['policy']=pol;records.append(r)
 return records

def save_rows(path,rows):
 with gzip.open(path,'wt',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
