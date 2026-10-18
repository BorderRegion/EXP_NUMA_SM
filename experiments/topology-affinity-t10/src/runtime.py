from common import *
from topology_math import DT, hungarian, residual, corr
import ctypes as C, time, gc, gzip, csv, subprocess
import numpy as np
import torch
torch.set_num_threads(2)
P=C.c_void_p;I=C.c_int
timing=C.CDLL(str(ROOT/'build/baseline/vector.so'))
timing.ll_error.restype=C.c_char_p
timing.ll_timed.argtypes=[P];timing.ll_timed.restype=P
timing.ll_repeat.argtypes=[P,I,C.POINTER(C.c_double)]
timing.ll_drop.argtypes=[P]
timing.ll_dag.argtypes=[P];timing.ll_dag.restype=C.c_char_p
fast=C.CDLL(str(ROOT/'build/baseline/softmax_const.so'))
fast.sf_error.restype=C.c_char_p
fast.sf_launch.argtypes=[C.POINTER(P),C.POINTER(I),C.c_ulonglong]
copy=C.CDLL(str(ROOT/'build/baseline/refresh.so'))
copy.copy_launch.argtypes=[P,P,I,C.c_ulonglong]
probe=C.CDLL(str(ROOT/'build/probe.so'))
probe.probe_error.restype=C.c_char_p
probe.probe_launch.argtypes=[P,P,C.POINTER(I),P,C.c_ulonglong]
SCOPES=PROTOCOL['scopes'];PAGES=PROTOCOL['micro']['pages']
TOPO=read(ROOT/'freeze/HARDWARE_TOPOLOGY.json')
for _path,_hash in PROTOCOL['baseline_hashes'].items():
    assert sha(ROOT/_path)==_hash, 'Frozen fast-kernel/timing binary changed'
SM=TOPO['global_sm_order']['entries']
GPC=np.array([x['gpc'] for x in SM])
TPC=np.array([x['global_tpc'] for x in SM])
SAME_GPC=(GPC[::2,None]==GPC[None,1::2])
SAME_TPC=(TPC[::2,None]==TPC[None,1::2])
CLASSES={'same_tpc':SAME_TPC,'same_gpc_other_tpc':SAME_GPC&~SAME_TPC,'cross_gpc':~SAME_GPC}
assert np.array_equal(SAME_TPC,np.eye(28,dtype=bool))
def tensor_sha(x):return hashlib.sha256(x.detach().cpu().contiguous().numpy().tobytes()).hexdigest()
def save_rows(p,rows):
    with gzip.open(p,'wt',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def verify_topology(out):
    p=subprocess.run([str(ROOT/'build/read_topology')],capture_output=True,text=True)
    (out/'topology_query.log').write_text(p.stderr)
    (out/'topology_query.json').write_text(p.stdout)
    assert p.returncode==0 and json.loads(p.stdout)==TOPO,'Physical topology changed'
    assert torch.cuda.get_device_properties(0).multi_processor_count==56
def bottleneck(cost,allowed=None):
    if allowed is None:allowed=np.ones((28,28),dtype=bool)
    assert cost.shape==allowed.shape
    n=len(cost);ii=np.arange(n);vals=np.unique(cost[allowed]);lo=0;hi=len(vals)-1
    while lo<hi:
        mid=(lo+hi)//2;bad=(~allowed)|(cost>vals[mid]);a=hungarian(bad.astype(float))
        if bad[ii,a].any():lo=mid+1
        else:hi=mid
    bad=(~allowed)|(cost>vals[lo]);a=hungarian(cost+bad*(np.ptp(cost)+1)*(n+1))
    assert not bad[ii,a].any()
    return a
def map_from_perm(perm):
    assert sorted(perm)==list(range(28))
    result=np.arange(56,dtype=np.int32)//2
    for p,c in enumerate(perm):result[2*c+1]=p
    return result.tolist()
def static_perms():
    inside=np.empty(28,dtype=int)
    for g in sorted(set(GPC)):
        ix=np.flatnonzero(GPC[::2]==g);inside[ix]=np.roll(ix,-1)
    cost=np.random.default_rng(610001).random((28,28))
    cross=hungarian(cost+SAME_GPC*100)
    assert not SAME_GPC[np.arange(28),cross].any()
    maps=dict(IDENTITY=np.arange(28),ALIAS_IDENTITY=np.arange(28),SAME_GPC=inside,CROSS_GPC=cross)
    maps.update({f'RND{i:02d}':np.random.default_rng(610100+i).permutation(28) for i in range(8)})
    return maps

class Workspace:
    def __init__(self):
        self.storage=torch.zeros(4<<20,device='cuda',dtype=torch.uint8)
        start=(-self.storage.data_ptr())%(2<<20)
        self.flags=self.storage[start:start+(2<<20)]
        self.maps={};self.perms={};self.device_maps={};self.trace=torch.zeros(112,device='cuda',dtype=torch.int32)
        assert self.flags.data_ptr()%(2<<20)==0
        self.install({(p,n):a for p in PAGES for n,a in static_perms().items()})
    def install(self,items):
        for key,perm in items.items():
            perm=np.asarray(perm,dtype=int)
            self.perms[key]=perm
            self.maps[key]=(I*56)(*map_from_perm(perm))
            arr=np.full(512,-1,dtype=np.int32)
            for i,j in enumerate(perm):
                arr[2*(2*i)]=i;arr[2*(2*i)+1]=0
                arr[2*(2*j+1)]=i;arr[2*(2*j+1)+1]=1
            self.device_maps[key]=torch.tensor(arr,device='cuda')
        torch.cuda.synchronize()
    def micro(self,plans,out,name,concurrent=False):
        # A plan row is kind,round,mode,slot,src,dst,steps,region,policy-index.
        n=len(plans);stride=28 if concurrent else 1
        records=torch.zeros(n*stride*DT.itemsize,device='cuda',dtype=torch.uint8)
        begin=time.perf_counter();e0=torch.cuda.Event(enable_timing=True);e1=torch.cuda.Event(enable_timing=True)
        e0.record();st=torch.cuda.current_stream().cuda_stream
        for i,row in enumerate(plans):
            key=(row[3],PROTOCOL['policies'][row[8]]) if concurrent else (0,'IDENTITY')
            a=(I*9)(*row)
            rc=probe.probe_launch(self.flags.data_ptr(),records.data_ptr()+i*stride*DT.itemsize,a,self.device_maps[key].data_ptr(),st)
            assert rc==0,probe.probe_error()
        e1.record();torch.cuda.synchronize()
        gpu_ms=e0.elapsed_time(e1);wall_ms=(time.perf_counter()-begin)*1000
        raw=records.cpu().numpy().tobytes();r=np.frombuffer(raw,dtype=DT).copy()
        (out/f'{name}.bin').write_bytes(raw);np.save(out/f'{name}_plans.npy',np.asarray(plans,dtype=np.int32))
        # Preserve raw results before checking, including any failures.
        first=r[::stride]
        assert np.all(np.sort(first['roster_begin'],axis=1)==np.arange(56))
        assert np.array_equal(first['roster_begin'],first['roster_end'])
        assert np.all(r['errors']==0) and np.array_equal(r['src_begin'],r['src_end']) and np.array_equal(r['dst_begin'],r['dst_end'])
        assert np.all(r['cycles']>0) and np.all(r['ns']>0)
        for k,row in enumerate(plans):
            rr=r[k*stride:(k+1)*stride]
            assert np.all(rr['src_value']==row[6]+16) and np.all(rr['dst_value']==row[6]+16)
            if concurrent:
                perm=self.perms[row[3],PROTOCOL['policies'][row[8]]]
                assert np.array_equal(rr['src_begin'],np.arange(0,56,2))
                assert np.array_equal(rr['dst_begin'],2*perm+1)
            else:assert rr[0]['src_begin']==row[4] and rr[0]['dst_begin']==row[5]
        del records
        info=dict(status='PASS',launches=n,records=len(r),wall_ms=wall_ms,gpu_queue_ms=gpu_ms,
                  note='Queue interval includes host submission gaps; individual RTT uses source clock.',flags_va=self.flags.data_ptr())
        write(out/f'{name}_audit.json',info)
        return r,info

class Data:
    def __init__(self,V,seed,w,ring=4):
        self.V=V;self.w=w;g=torch.Generator().manual_seed(seed)
        self.source=[(torch.randn(V,generator=g)*3).cuda() for _ in range(ring)]
        self.x=[x.clone() for x in self.source];self.y=torch.empty_like(self.x[0]);self.partial=torch.empty(112,device='cuda')
        self.refs=[torch.softmax(x.cpu().double(),dim=0) for x in self.source]
        torch.cuda.synchronize()
        self.meta=dict(V=V,seed=seed,input_hashes=[tensor_sha(x) for x in self.source],flags_va=w.flags.data_ptr(),x_va=[x.data_ptr() for x in self.x])
    def check(self,slot):
        y=self.y.cpu().double();ref=self.refs[slot];delta=(y-ref).abs()
        scaled=float((delta/(2e-8+3e-5*ref.abs())).max());rel=float(delta.norm()/ref.norm());mass=float(y.sum())
        assert bool(torch.isfinite(y).all()) and scaled<1 and rel<1e-5 and abs(mass-1)<1e-5,(scaled,rel,mass)
        ctrl=self.w.flags.view(torch.int32)[400*1024:400*1024+6].cpu().numpy();assert ctrl[2]==0
        return dict(status='PASS',relative_l2=rel,max_scaled_error=scaled,sum=mass,output_sha256=tensor_sha(self.y))

class Job:
    def __init__(self,d,slot,policy,page=17,scope='ready',trace=False):
        self.d=d;self.slot=slot;self.policy=policy;self.page=page;self.scope=scope
        self.batch=SCOPES[scope]['batch'];self.fresh=SCOPES[scope]['fresh'];self.ptr=None;self.graph=None
        self.mapping=d.w.maps[page,policy]
        self.a=(P*6)(d.x[slot].data_ptr(),d.y.data_ptr(),d.w.flags.data_ptr(),C.addressof(self.mapping),d.w.trace.data_ptr(),d.partial.data_ptr())
        self.c=(I*4)(d.V,1,page,int(trace))
        start=time.perf_counter()
        for _ in range(2):self.op()
        torch.cuda.synchronize();self.graph=torch.cuda.CUDAGraph(keep_graph=True)
        with torch.cuda.graph(self.graph):
            for _ in range(self.batch):self.op()
        raw=self.graph.raw_cuda_graph();self.ptr=timing.ll_timed(raw);assert self.ptr,timing.ll_error()
        self.dag=json.loads(timing.ll_dag(raw));self.setup_ms=(time.perf_counter()-start)*1000
        nodes=self.dag['nodes'];assert len(nodes)==self.batch*(2 if self.fresh else 1)
        assert all(n['type']==0 for n in nodes)
        soft_nodes=[n for n in nodes if 'paired' in n.get('function','')]
        assert len(soft_nodes)==self.batch and all(n['grid']==[56,1,1] for n in soft_nodes)
    def op(self):
        st=torch.cuda.current_stream().cuda_stream
        if self.fresh:assert copy.copy_launch(self.d.source[self.slot].data_ptr(),self.d.x[self.slot].data_ptr(),self.d.V,st)==0
        if fast.sf_launch(self.a,self.c,st):raise RuntimeError(fast.sf_error().decode())
    def run(self,n=1):
        a=(C.c_double*(n*2))();assert timing.ll_repeat(self.ptr,n,a)==0,timing.ll_error()
        return np.ctypeslib.as_array(a).copy().reshape(n,2)
    def check(self):
        torch.cuda.synchronize();self.run();return self.d.check(self.slot)
    def close(self):
        if self.ptr:timing.ll_drop(self.ptr);self.ptr=None
        self.graph=None
