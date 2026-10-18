"""One legal pointwise consumer, with explicit half rounding boundaries."""
import ctypes as C
from pathlib import Path
import torch
PATH=Path(__file__).resolve().parents[1]/'src/same_q_v2/libopf_activation.so'
LIB=C.CDLL(str(PATH))
LIB.opf_activation.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_void_p]
LIB.opf_activation.restype=C.c_int
def activation(gu,out):
    assert gu.is_contiguous() and out.is_contiguous()
    code=LIB.opf_activation(gu.data_ptr(),out.data_ptr(),out.shape[0],out.shape[1],torch.cuda.current_stream().cuda_stream)
    if code:raise RuntimeError('activation '+str(code))
def qualify_activation():
    # All finite FP16 gate values, several finite multipliers; same half output
    # bits as the original torch SiLU then multiply sequence, including zeros.
    values=torch.arange(65536,device='cuda',dtype=torch.int32).to(torch.int16).view(torch.float16)
    values=values[torch.isfinite(values)]
    tests=[]
    for mult in [1.0,-0.75,0.03125,3.125]:
        gu=torch.stack((values,torch.full_like(values,mult)),dim=1).contiguous()
        out=torch.empty((len(values),1),device='cuda',dtype=torch.float16)
        ref=torch.nn.functional.silu(gu[:,:1])*gu[:,1:]
        activation(gu,out);torch.cuda.synchronize()
        mismatches=int((out.view(torch.int16)!=ref.view(torch.int16)).sum())
        tests.append(dict(finite_gate_patterns=len(values),multiplier=mult,bitwise_mismatches=mismatches))
    return dict(status='PASS' if all(x['bitwise_mismatches']==0 for x in tests) else 'FAILED',tests=tests,
      math='round_half(SiLU(float(gate))) * half(up), then round_half',fast_math=False)
