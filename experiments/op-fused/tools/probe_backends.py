"""Finite E0 backend qualification, no downloads or fallback disguises."""
import argparse,json,pathlib,traceback,time
import torch
import torch.nn.functional as F
from torch.nn.attention import sdpa_kernel,SDPBackend
import triton
import triton.language as tl

@triton.jit
def local_mm_probe(A,B,C,M:tl.constexpr,N:tl.constexpr,K:tl.constexpr,BM:tl.constexpr,BN:tl.constexpr,BK:tl.constexpr):
    # Literal specialization of installed torch/_inductor/kernel/mm.py's mainloop.
    pid=tl.program_id(0);grid_m=tl.cdiv(M,BM);grid_n=tl.cdiv(N,BN)
    width=8*grid_n;group_id=pid//width;group_size=tl.minimum(grid_m-group_id*8,8)
    pm=group_id*8+pid%group_size;pn=(pid%width)//group_size
    rm=pm*BM+tl.arange(0,BM);rn=pn*BN+tl.arange(0,BN);rk=tl.arange(0,BK)
    am=rm%M;bn=rn%N
    acc=tl.zeros((BM,BN),tl.float32)
    for ki in range(0,tl.cdiv(K,BK)):
        ak=rk+ki*BK
        a=tl.load(A+am[:,None]*K+ak[None,:],ak[None,:]<K,0)
        b=tl.load(B+ak[:,None]*N+bn[None,:],ak[:,None]<K,0)
        acc=tl.dot(a,b,acc,allow_tf32=False,out_dtype=tl.float32)
    tl.store(C+rm[:,None]*N+rn[None,:],acc,(rm[:,None]<M)&(rn[None,:]<N))

def main(out):
    torch.set_num_threads(2);torch.manual_seed(2026101517)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction=False
    info=dict(torch=torch.__version__,triton=triton.__version__,cuda=torch.version.cuda,
              device=str(torch.cuda.get_device_properties(0)),arch_list=torch.cuda.get_arch_list(),results={})
    def attempt(name,fn):
        t=time.perf_counter()
        try: info['results'][name]=dict(status='PASS',details=fn())
        except Exception as e:info['results'][name]=dict(status='UNSUPPORTED_OR_FAILED',error=str(e),traceback=traceback.format_exc())
        info['results'][name]['setup_and_probe_s']=time.perf_counter()-t
        (out/'backend_probe.json').write_text(json.dumps(info,indent=2))
        print(name,info['results'][name]['status'],flush=True)
    a=torch.randn((64,128),device='cuda',dtype=torch.float16)/128**.5
    b=torch.randn((128,256),device='cuda',dtype=torch.float16)
    ref=a.double()@b.double()
    def gemm():
        y=a@b;torch.cuda.synchronize();return dict(max_abs=float((y.double()-ref).abs().max()))
    attempt('torch_cublas_fp16',gemm)
    def tri():
        c=torch.empty((64,256),device='cuda',dtype=torch.float16)
        k=local_mm_probe[(4,)](a,b,c,64,256,128,32,128,32,num_warps=4,num_stages=2)
        torch.cuda.synchronize();(out/'triton_probe.ptx').write_text(k.asm['ptx'])
        (out/'triton_probe.cubin').write_bytes(k.asm['cubin'])
        return dict(max_abs=float((c.double()-ref).abs().max()),mma_in_ptx='mma.sync' in k.asm['ptx'],metadata=str(k.metadata))
    attempt('triton_installed_torch_mainloop_sm75',tri)
    q=torch.randn(1,32,1,128,device='cuda',dtype=torch.float16)
    k=torch.randn(1,8,128,128,device='cuda',dtype=torch.float16);v=torch.randn_like(k)
    for backend in [SDPBackend.EFFICIENT_ATTENTION,SDPBackend.FLASH_ATTENTION,SDPBackend.MATH]:
        def sdpa(backend=backend):
            with sdpa_kernel(backend):y=F.scaled_dot_product_attention(q,k,v,enable_gqa=True)
            torch.cuda.synchronize();return dict(shape=list(y.shape),finite=bool(y.isfinite().all()))
        attempt('sdpa_gqa_'+str(backend),sdpa)
    def efficient_lowlevel():
        y=torch.ops.aten._efficient_attention_forward(q.transpose(1,2),k.transpose(1,2),v.transpose(1,2),None,None,None,None,None,0.,0)[0]
        torch.cuda.synchronize();return dict(shape=list(y.shape))
    attempt('aten_efficient_native_gqa',efficient_lowlevel)
    info['attention_schema']=str(torch.ops.aten._efficient_attention_forward.default._schema)
    info['memory']=dict(free=torch.cuda.mem_get_info()[0],total=torch.cuda.mem_get_info()[1],peak_reserved=torch.cuda.max_memory_reserved())
    (out/'backend_probe.json').write_text(json.dumps(info,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);main(p.parse_args().out)
