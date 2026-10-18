"""Reuse plans selected only on development data.
No per-request calibration. Unsupported shapes fall back to cuBLAS.
The caller owns Engine/Data lifetime and must provide ready GPU inputs, as in
this repository's existing GEMM interface. One workspace per concurrent plan.
"""
from backend import Job
from common import *

def choice(m,n,k):
 cases=read(ROOT/'freeze/PROTOCOL.json')['cases'];matches=[c for c in cases if (c['M'],c['N'],c['K'])==(m,n,k)]
 if not matches:return dict(kind=3,recipe=0,s=1,route='LIB',known_shape=False)
 row=read(ROOT/'freeze/TUNED_RECIPES.json')['cases'][matches[0]['id']];route=row['route']
 if route=='LIB':return dict(kind=3,recipe=0,s=1,route=route,known_shape=True)
 recipe,s=row['native' if route=='TUNED_NATIVE' else 'fused'];return dict(kind=0 if route=='TUNED_NATIVE' else 12,recipe=recipe,s=s,route=route,known_shape=True)

def required_workspace_words(m,n,k):
 c=choice(m,n,k);return 0 if c['kind']==3 else m*n*c['s']

def build_deployed(engine,data,slot=0):
 c=choice(data.m,data.n,data.k);need=required_workspace_words(data.m,data.n,data.k)
 if need and (data.w is None or data.w.numel()<need):raise ValueError('Insufficient private split-K workspace')
 if c['kind']==12:raise RuntimeError('Fused route requires a lifetime-managed private counter buffer; not enabled by this campaign')
 j=Job(engine,data,slot=slot,kind=c['kind'],recipe=c['recipe'],s=c['s']);j.route=c['route'];return j
