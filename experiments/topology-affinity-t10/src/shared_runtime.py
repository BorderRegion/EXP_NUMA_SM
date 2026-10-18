from runtime import *
sg=C.CDLL(str(ROOT/'build/shared_graph.so'))
sg.sg_error.restype=C.c_char_p;sg.sg_create.argtypes=[P];sg.sg_create.restype=P
sg.sg_identity.argtypes=[P];sg.sg_identity.restype=C.c_char_p
sg.sg_set.argtypes=[P,C.POINTER(I)];sg.sg_run.argtypes=[P,I,C.POINTER(C.c_double)];sg.sg_drop.argtypes=[P]
class SharedJob:
    def __init__(self,d,slot,page,scope,trace=False):
        self.d=d;self.slot=slot;self.page=page;self.batch=SCOPES[scope]['batch']
        old=Job(d,slot,'IDENTITY',page,scope,trace)
        self.ptr=sg.sg_create(old.graph.raw_cuda_graph());assert self.ptr,sg.sg_error()
        self.dag=old.dag;self.identity=json.loads(sg.sg_identity(self.ptr))
        old.close()
    def set(self,name):
        t=time.perf_counter_ns();rc=sg.sg_set(self.ptr,self.d.w.maps[self.page,name]);delta=(time.perf_counter_ns()-t)/1000
        assert rc==self.batch,(rc,sg.sg_error())
        assert json.loads(sg.sg_identity(self.ptr))==self.identity
        return delta
    def run(self,n=1):
        a=(C.c_double*(2*n))();assert sg.sg_run(self.ptr,n,a)==0,sg.sg_error()
        return np.ctypeslib.as_array(a).copy().reshape(n,2)
    def close(self):
        if self.ptr:sg.sg_drop(self.ptr);self.ptr=None
