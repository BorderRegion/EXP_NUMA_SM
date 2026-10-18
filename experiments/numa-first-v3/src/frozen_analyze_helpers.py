"""CPU-only block-mean interval helper, no runtime side effects."""
import numpy as np
def interval(v,confidence=.95):
 v=np.asarray(v,float)
 if not len(v):return None
 rng=np.random.default_rng(2026101641);bs=v[rng.integers(0,len(v),(20000,len(v)))].mean(1);alpha=1-confidence
 return dict(estimate=float(v.mean()),ci=np.quantile(bs,[alpha/2,1-alpha/2]).tolist(),values=v.tolist(),blocks=len(v),confidence=confidence,exploratory=True)
