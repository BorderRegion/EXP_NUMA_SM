"""Thin static-descriptor adapter. CUDA math/visitor lives in grouped_backend.cu."""
import ctypes as C
import hashlib
from pathlib import Path
import torch

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'src/libopf_grouped.so'
LIB=C.CDLL(str(PATH))
LIB.opf_resources.argtypes=[C.c_int,C.c_int,C.POINTER(C.c_int)];LIB.opf_resources.restype=C.c_int
LIB.opf_create.argtypes=[C.c_int]*7+[C.c_void_p]*8+[C.POINTER(C.c_int)]
LIB.opf_create.restype=C.c_void_p
LIB.opf_run.argtypes=[C.c_void_p,C.c_void_p];LIB.opf_run.restype=C.c_int
LIB.opf_destroy.argtypes=[C.c_void_p];LIB.opf_destroy.restype=None
LIB.opf_count_visits.argtypes=[C.c_int]*6+[C.c_void_p]*4;LIB.opf_count_visits.restype=C.c_int
LIB.opf_pack.argtypes=[C.c_int]+[C.c_void_p]*3+[C.c_int]*2+[C.c_void_p]*2+[C.c_int]*2+[C.c_void_p]*2
LIB.opf_pack.restype=C.c_int

def count_visits(op):
    bm=op.resource_table[0]['tile_m'];prefix=[0]
    for m,n,k in op.shapes:prefix.append(prefix[-1]+((m+bm-1)//bm)*((n+127)//128))
    device_prefix=torch.tensor(prefix[:-1],device='cuda',dtype=torch.int32)
    counts=torch.zeros(prefix[-1],device='cuda',dtype=torch.int32)
    code=LIB.opf_count_visits(op.recipe,op.mode,len(op.shapes),op.workers,op.q_cap,op.waves,
        op.descriptors[0].data_ptr(),device_prefix.data_ptr(),counts.data_ptr(),torch.cuda.current_stream().cuda_stream)
    if code:raise RuntimeError(f'coverage kernel error {code}')
    torch.cuda.synchronize()
    values=counts.cpu().tolist()
    assert all(x==1 for x in values),(op.metadata(),values[:20])
    return dict(tiles=len(values),all_exactly_once=True,diagnostic_only=True)

def pack_rows(x,token,out,up,down,totals,sideband):
    code=LIB.opf_pack(int(sideband),x.data_ptr(),token.data_ptr(),out.data_ptr(),out.shape[0],out.shape[1],
       up.descriptors[0].data_ptr(),down.descriptors[0].data_ptr(),len(up.shapes),
       up.resource_table[0]['tile_m'],totals.data_ptr(),torch.cuda.current_stream().cuda_stream)
    if code:raise RuntimeError(f'pack error {code}')

def resources(recipe,mode):
    out=(C.c_int*8)();code=LIB.opf_resources(recipe,mode,out)
    if code:raise RuntimeError(f'CUTLASS resources error {code}')
    return dict(zip(['active_blocks_per_sm','threads','shared_bytes','registers_per_thread',
                     'sms','tile_m','tile_n','tile_k'],out))

class CutlassGrouped:
    def __init__(self,aa,bb,cc,recipe=0,mode=0,q_cap=1,waves=1,workers=None,sideband=None,sort_k=False):
        assert len(aa)==len(bb)==len(cc)>0
        self.handle=None
        self.recipe,self.mode,self.q_cap,self.waves=recipe,mode,q_cap,waves
        order=sorted(range(len(aa)),key=lambda i:-aa[i].shape[1]) if sort_k else list(range(len(aa)))
        aa,bb,cc=([xs[i] for i in order] for xs in [aa,bb,cc])
        self.storage=[aa,bb,cc,sideband]
        shapes=[]
        for a,b,c in zip(aa,bb,cc):
            m,k=a.shape;k2,n=b.shape
            assert k==k2 and tuple(c.shape)==(m,n)
            assert k>0 and n>0 and k%8==0 and n%8==0
            for t in (a,b,c):
                assert t.dtype==torch.float16 and t.is_cuda and t.stride(-1)==1
                assert t.stride(0)%8==0 and t.data_ptr()%16==0
            shapes.append((m,n,k))
        self.shapes=shapes
        self.resource_table=[resources(recipe,x) for x in range(3)]
        bm,bn=self.resource_table[0]['tile_m'],128
        self.total_tiles=sum(((m+bm-1)//bm)*((n+bn-1)//bn) for m,n,k in shapes)
        capacity=min(x['active_blocks_per_sm'] for x in self.resource_table)*self.resource_table[0]['sms']
        self.workers=workers if workers is not None else max(1,min(self.total_tiles,capacity))
        self.descriptors=[torch.tensor(shapes,device='cuda',dtype=torch.int32)]
        for xs in [aa,bb,cc]:self.descriptors.append(torch.tensor([x.data_ptr() for x in xs],device='cuda',dtype=torch.int64))
        for xs in [aa,bb,cc]:self.descriptors.append(torch.tensor([x.stride(0) for x in xs],device='cuda',dtype=torch.int64))
        status=C.c_int()
        self.handle=LIB.opf_create(recipe,mode,len(aa),self.workers,q_cap,waves,128,
            *[x.data_ptr() for x in self.descriptors],sideband.data_ptr() if sideband is not None else 0,C.byref(status))
        if status.value or not self.handle:raise RuntimeError(f'CUTLASS initialize error {status.value}')
    def __call__(self):
        code=LIB.opf_run(self.handle,torch.cuda.current_stream().cuda_stream)
        if code:raise RuntimeError(f'CUTLASS run error {code}')
    def close(self):
        if self.handle:LIB.opf_destroy(self.handle);self.handle=None
    def __del__(self):self.close()
    def metadata(self):
        return dict(recipe=self.recipe,mode=self.mode,q_cap=self.q_cap,target_waves=self.waves,
                    work_budget_k_tiles=128,total_tiles=self.total_tiles,workers=self.workers,
                    resources=self.resource_table,shapes=self.shapes,
                    binary_sha256=hashlib.sha256(PATH.read_bytes()).hexdigest(),
                    descriptor_scope='STATIC_OPERATOR; no per-step host rebuild claim',
                    scheduler_kernel_nodes=0,metadata_d2h_bytes=0,host_waits_inside=0)
