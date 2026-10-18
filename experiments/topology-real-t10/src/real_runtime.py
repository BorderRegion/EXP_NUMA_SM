from runtime import *
from selector import CHOICES,CANDIDATES,BASE,shortlist,decide
NAMES=PROTOCOL['policies'];PERMS=static_perms()
MAPS=np.ascontiguousarray([map_from_perm(PERMS[c['family']]) for c in CHOICES],dtype=np.int32)
PAGES_ARRAY=np.ascontiguousarray([c['page'] for c in CHOICES],dtype=np.int32)
sg=C.CDLL(str(ROOT/'build/shared_graph.so'));sg.sg_error.restype=C.c_char_p
sg.sg_create.argtypes=[P];sg.sg_create.restype=P;sg.sg_identity.argtypes=[P];sg.sg_identity.restype=C.c_char_p
sg.sg_set.argtypes=[P,C.POINTER(I),C.c_ulonglong,I];sg.sg_run.argtypes=[P,I,C.POINTER(C.c_double)];sg.sg_drop.argtypes=[P]
sg.sg_scan.argtypes=[P,C.POINTER(I),C.POINTER(C.c_ulonglong),C.POINTER(I),C.POINTER(I),I,I,C.POINTER(C.c_double)]

class SharedJob:
    def __init__(self,d,slot,scope):
        self.d=d;self.slot=slot;self.scope=scope;self.w=d.w;self.choice=BASE
        old=Job(d,slot,'IDENTITY',17,scope)
        self.ptr=sg.sg_create(old.graph.raw_cuda_graph());assert self.ptr,sg.sg_error()
        self.dag=old.dag;self.identity=json.loads(sg.sg_identity(self.ptr));old.close()
    def verify(self):assert json.loads(sg.sg_identity(self.ptr))==self.identity
    def set(self,index):
        begin=time.perf_counter_ns();c=CHOICES[index]
        rc=sg.sg_set(self.ptr,MAPS[index].ctypes.data_as(C.POINTER(I)),self.w.flags.data_ptr()+c['offset']*4096,c['page']);assert rc==32,sg.sg_error()
        self.verify();self.choice=index;return (time.perf_counter_ns()-begin)/1000
    def run(self,n=1):
        a=(C.c_double*(n*2))();assert sg.sg_run(self.ptr,n,a)==0,sg.sg_error()
        return np.ctypeslib.as_array(a).copy().reshape(n,2)
    def scan(self,ids,replays,flags):
        ids=np.ascontiguousarray(ids,dtype=np.int32);a=np.zeros((len(ids),1+2*replays),dtype=np.float64)
        assert sg.sg_scan(self.ptr,MAPS.ctypes.data_as(C.POINTER(I)),flags.ctypes.data_as(C.POINTER(C.c_ulonglong)),PAGES_ARRAY.ctypes.data_as(C.POINTER(I)),ids.ctypes.data_as(C.POINTER(I)),len(ids),replays,a.ctypes.data_as(C.POINTER(C.c_double)))==0,sg.sg_error()
        self.verify();self.choice=int(ids[-1]);return a
    def check(self):
        old=self.d.w;self.d.w=self.w
        try:return self.d.check(self.slot,CHOICES[self.choice]['offset'])
        finally:self.d.w=old
    def close(self):
        if self.ptr:sg.sg_drop(self.ptr);self.ptr=None

def calibrate(job,out,seed):
    out.mkdir(parents=True);begin=time.perf_counter_ns();started=utc()
    rng=np.random.default_rng(seed)
    flags=np.ascontiguousarray([job.w.flags.data_ptr()+c['offset']*4096 for c in CHOICES],dtype=np.uint64)
    screen_ids=rng.permutation(CANDIDATES).astype(np.int32);screen=job.scan(screen_ids,2,flags)
    screen_gpu=screen[:,1:].reshape(-1,2,2)[:,1,0]
    finalists=shortlist(screen_ids,screen_gpu)
    refine_ids=np.concatenate([rng.permutation(finalists) for _ in range(2)]).astype(np.int32)
    refine=job.scan(refine_ids,3,flags);refine_gpu=refine[:,1:].reshape(-1,3,2)[:,1:,0]
    mapping,fit=decide(screen_ids,screen_gpu,refine_ids,refine_gpu)
    job.set(mapping['TUNED']);job.run(2)
    # The returned choice is now installed and conditioned on this same Graph.
    setup_ms=(time.perf_counter_ns()-begin)/1e6;ended=utc()
    for n,a in [('screen_ids',screen_ids),('screen',screen),('refine_ids',refine_ids),('refine',refine)]:np.save(out/(n+'.npy'),a)
    result=dict(started=started,ended=ended,setup_ms=setup_ms,flags_va=job.w.flags.data_ptr(),mapping=mapping,fit=fit,seed=seed,choices=CHOICES,handles=job.identity,calibration_operator_calls=(16*2+8*3+2)*32)
    write(out/'selected.json',result);return result
