from runtime import *
DT_TAIL=np.dtype([(x,'<u8',(56,)) for x in ['start','arrived','paired','done']]+[(x,'<u4',(56,)) for x in ['collector','observed','errors']]+[(x,'<f4',(56,)) for x in ['maximum','sum']])
assert DT_TAIL.itemsize==2912
NAMES=PROTOCOL['policies'];PERMS=static_perms();MAPS=np.array([map_from_perm(PERMS[n]) for n in NAMES],dtype=np.int32)
PLACEMENTS=[(o,p) for o in PROTOCOL['offset_pages'] for p in PAGES]
CHOICES=[dict(offset=o,page=p,family=n) for o,p in PLACEMENTS for n in NAMES]
IDENTITY=next(i for i,c in enumerate(CHOICES) if c==dict(offset=0,page=17,family='IDENTITY'))
tp=C.CDLL(str(ROOT/'build/tail_probe.so'));tp.tail_error.restype=C.c_char_p
tp.tail_batch.argtypes=[P,P,C.POINTER(I),C.POINTER(I),C.POINTER(C.c_ulonglong),I,C.c_ulonglong]
diag=C.CDLL(str(ROOT/'build/diagnostic.so'));diag.sf_error.restype=C.c_char_p;diag.sf_launch.argtypes=[C.POINTER(P),C.POINTER(I),C.c_ulonglong]
sg=C.CDLL(str(ROOT/'build/shared_graph.so'));sg.sg_error.restype=C.c_char_p
sg.sg_create.argtypes=[P];sg.sg_create.restype=P;sg.sg_identity.argtypes=[P];sg.sg_identity.restype=C.c_char_p
sg.sg_set.argtypes=[P,C.POINTER(I),C.c_ulonglong,I];sg.sg_run.argtypes=[P,I,C.POINTER(C.c_double)];sg.sg_drop.argtypes=[P]

class SharedJob:
    def __init__(self,d,slot,scope):
        self.d=d;self.slot=slot;self.scope=scope;self.batch=SCOPES[scope]['batch']
        old=Job(d,slot,'IDENTITY',17,scope)
        self.ptr=sg.sg_create(old.graph.raw_cuda_graph());assert self.ptr,sg.sg_error()
        self.dag=old.dag;self.identity=json.loads(sg.sg_identity(self.ptr));old.close();self.choice=IDENTITY
    def set(self,index):
        begin=time.perf_counter_ns();c=CHOICES[index];a=(I*56)(*MAPS[NAMES.index(c['family'])])
        rc=sg.sg_set(self.ptr,a,self.d.w.flags.data_ptr()+c['offset']*4096,c['page']);assert rc==self.batch,sg.sg_error()
        assert json.loads(sg.sg_identity(self.ptr))==self.identity
        self.choice=index;return (time.perf_counter_ns()-begin)/1000
    def run(self,n=1):
        a=(C.c_double*(n*2))();assert sg.sg_run(self.ptr,n,a)==0,sg.sg_error()
        return np.ctypeslib.as_array(a).copy().reshape(n,2)
    def check(self):return self.d.check(self.slot,CHOICES[self.choice]['offset'])
    def close(self):
        if self.ptr:sg.sg_drop(self.ptr);self.ptr=None

def profile(d,scope,sanitizer=False):
    alltrace=[];trace=torch.zeros(56*8,device='cuda',dtype=torch.int64)
    mapping=d.w.maps[17,'IDENTITY'];a=(P*6)(d.x[0].data_ptr(),d.y.data_ptr(),d.w.flags.data_ptr(),C.addressof(mapping),trace.data_ptr(),d.partial.data_ptr());c=(I*4)(d.V,1,17,1)
    for i in range(PROTOCOL['trace_launches']):
        st=torch.cuda.current_stream().cuda_stream
        if SCOPES[scope]['fresh']:assert copy.copy_launch(d.source[0].data_ptr(),d.x[0].data_ptr(),d.V,st)==0
        assert diag.sf_launch(a,c,st)==0,diag.sf_error()
        alltrace.append(trace.clone())
    torch.cuda.synchronize();r=torch.stack(alltrace).cpu().numpy().reshape(-1,56,8);check=d.check(0)
    assert (r[:,:,7]==np.arange(56)).all() and (r[:,:,6].sum(axis=1)==1).all()
    assert (np.diff(r[:,:,:6],axis=2)>=0).all()
    duration=np.median(r[:,:,1]-r[:,:,0],axis=0)
    delay=np.ascontiguousarray(duration-duration.min(),dtype=np.uint64)
    if sanitizer:delay=np.minimum(delay,np.uint64(5000))
    else:assert delay.max()<10000
    return r,delay,check

def probe_batch(w,delay,rounds,seed):
    rng=np.random.default_rng(seed);plans=[]
    for rd in range(rounds):
        for idx in rng.permutation(len(CHOICES)):
            c=CHOICES[idx];plans.append([c['offset'],c['page'],NAMES.index(c['family']),rd])
    plans=np.ascontiguousarray(plans,dtype=np.int32);records=torch.zeros(len(plans)*DT_TAIL.itemsize,device='cuda',dtype=torch.uint8)
    begin=time.perf_counter_ns();st=torch.cuda.current_stream().cuda_stream
    rc=tp.tail_batch(w.flags.data_ptr(),records.data_ptr(),plans.ctypes.data_as(C.POINTER(I)),MAPS.ctypes.data_as(C.POINTER(I)),delay.ctypes.data_as(C.POINTER(C.c_ulonglong)),len(plans),st)
    assert rc==0,tp.tail_error();torch.cuda.synchronize();queue_ms=(time.perf_counter_ns()-begin)/1e6
    raw=records.cpu().numpy().tobytes();r=np.frombuffer(raw,dtype=DT_TAIL)
    assert (r['observed']==np.arange(56)).all() and (r['errors']==0).all() and (r['collector'].sum(axis=1)==1).all()
    assert (r['done']>=r['paired']).all() and (r['paired']>=r['arrived']).all() and (r['arrived']>=r['start']).all()
    expected_m=55/56;expected_s=np.sum((100+np.arange(56))*np.exp(np.arange(56)/56-expected_m))
    assert np.max(abs(r['maximum']-expected_m))<1e-5 and np.max(abs(r['sum']-expected_s))/expected_s<2e-6
    costs=np.zeros((rounds,len(CHOICES)))
    for p,v in zip(plans,r):
        k=PLACEMENTS.index((p[0],p[1]))*len(NAMES)+p[2];costs[p[3],k]=np.max(v['done']-v['start'])
    assert (costs>0).all()
    return dict(raw=raw,plans=plans,costs=costs,queue_ms=queue_ms)

def select(costs):
    h=len(costs)//2;scores=np.maximum(np.median(costs[:h],axis=0),np.median(costs[h:],axis=0));matrix=scores.reshape(len(PLACEMENTS),len(NAMES))
    joint=int(scores.argmin());place,family=divmod(joint,len(NAMES));fixed=PLACEMENTS.index((0,17))
    return dict(IDENTITY=IDENTITY,PAIR_ONLY=int(fixed*len(NAMES)+matrix[fixed].argmin()),
        PLACE_ONLY=int(matrix[:,0].argmin()*len(NAMES)),JOINT=joint,JOINT_AA=joint,
        WRONG=int(place*len(NAMES)+matrix[(place+1)%len(PLACEMENTS)].argmin()),
        POOL=int(place*len(NAMES)+matrix.mean(axis=0).argmin())),scores

def save_probe(out,name,x):
    (out/(name+'.bin')).write_bytes(x['raw']);np.save(out/(name+'_plans.npy'),x['plans']);np.save(out/(name+'_costs.npy'),x['costs'])
    write(out/(name+'_audit.json'),dict(status='PASS',launches=len(x['plans']),records=len(x['plans']),sm_observations=len(x['plans'])*56,queue_ms=x['queue_ms'],source='max per-SM duration, one full communication tail per launch'))

def calibrate(d,scope,out,seed):
    out.mkdir(parents=True);start=time.perf_counter_ns();started=utc()
    trace,delay,check=profile(d,scope)
    train=probe_batch(d.w,delay,PROTOCOL['train_rounds'],seed);mapping,scores=select(train['costs'])
    # Usable host arguments exist at this endpoint. Research logging/validation
    # and shadow-allocation control calibration are measured separately.
    params={k:(CHOICES[v],MAPS[NAMES.index(CHOICES[v]['family'])].copy()) for k,v in mapping.items()}
    setup_ms=(time.perf_counter_ns()-start)/1e6;ended=utc()
    write(out/'selected_before_validation.json',dict(started=started,ended=ended,setup_ms=setup_ms,flags_va=d.w.flags.data_ptr(),mapping=mapping,choices=CHOICES,delay_ns=delay.tolist(),train_scores=scores.tolist()))
    np.save(out/'arrival_trace.npy',trace);np.save(out/'delay.npy',delay);save_probe(out,'train',train)
    validation=probe_batch(d.w,delay,PROTOCOL['validation_rounds'],seed+1);save_probe(out,'validation',validation)
    shadow=Workspace();shadow_start=time.perf_counter_ns();other=probe_batch(shadow,delay,PROTOCOL['train_rounds'],seed+2);other_maps,_=select(other['costs']);shadow_ms=(time.perf_counter_ns()-shadow_start)/1e6
    save_probe(out,'shadow',other);mapping['SHADOW']=other_maps['JOINT']
    write(out/'complete.json',dict(status='PASS',setup_ms=setup_ms,shadow_probe_fit_ms=shadow_ms,shadow_flags_va=shadow.flags.data_ptr(),flags_va=d.w.flags.data_ptr(),mapping=mapping,numerical_check=check,selected_sha256=sha(out/'selected_before_validation.json')))
    del shadow
    return mapping,setup_ms
