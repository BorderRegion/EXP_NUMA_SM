"""CPU-only paired statistics. Does not run kernels or correct away drift."""
from __future__ import annotations
import math
import random
import statistics
from typing import Iterable, Sequence

def quantile(values: Iterable[float], q: float) -> float:
    x=sorted(float(v) for v in values)
    if not x or not 0 <= q <= 1 or any(not math.isfinite(v) for v in x):
        raise ValueError('nonempty finite values and q in [0,1] required')
    pos=(len(x)-1)*q;lo=int(math.floor(pos));hi=int(math.ceil(pos))
    return x[lo]+(x[hi]-x[lo])*(pos-lo)

def quartet_contrast(labels: Sequence[str], means_us: Sequence[float]) -> dict:
    """B/A, not 'gain'. ABBA balances order, not arbitrary nonlinear drift."""
    if ''.join(labels) not in ('ABBA','BAAB') or len(means_us)!=4:
        raise ValueError('exact ABBA or BAAB quartet required')
    if any(not math.isfinite(t) or t<=0 for t in means_us):
        raise ValueError('positive finite window times required')
    a=[float(t) for c,t in zip(labels,means_us) if c=='A']
    b=[float(t) for c,t in zip(labels,means_us) if c=='B']
    z=statistics.mean(map(math.log,b))-statistics.mean(map(math.log,a))
    return dict(log_ratio=z, ratio=math.exp(z), delta_us=statistics.mean(b)-statistics.mean(a),
                reference_geomean_us=math.exp(statistics.mean(map(math.log,a))),
                reference_arithmetic_us=statistics.mean(a), candidate_arithmetic_us=statistics.mean(b))

def latency_bucket(predicted_base_us: float) -> int:
    if not math.isfinite(predicted_base_us) or predicted_base_us<=0:raise ValueError('invalid scale')
    return 0 if predicted_base_us<250 else 1 if predicted_base_us<2000 else 2

def error_card(errors: Sequence[tuple[float,float]], minimum_shapes: int=6) -> dict:
    """(OOF predicted base us, observed - predicted log ratio), one row/shape.
    The 90th percentile is an empirical safety margin, NOT a coverage guarantee.
    """
    if not errors:raise ValueError('missing OOF errors')
    vals=[e for _,e in errors]
    out={'pooled':max(0.,quantile(vals,.9)),'n':len(vals),'buckets':{}}
    for b in range(3):
        v=[e for t,e in errors if latency_bucket(t)==b]
        out['buckets'][str(b)]={'n':len(v),'q_log':max(0.,quantile(v,.9)) if len(v)>=minimum_shapes else out['pooled'],
                                'source':'local_log' if len(v)>=minimum_shapes else 'pooled_log'}
    return out

def margin_value(card: dict, predicted_base_us: float, aa_floor_log: float=0.) -> float:
    if not math.isfinite(aa_floor_log) or aa_floor_log<0:raise ValueError('invalid AA margin')
    q=card['buckets'][str(latency_bucket(predicted_base_us))]['q_log']
    if not math.isfinite(q) or q<0:raise ValueError('invalid model margin')
    return max(q,aa_floor_log)

def block_bootstrap_logratios(block_values: Sequence[float], confidence=.95, draws=5000, seed=20261017) -> dict:
    """One already-aggregated value per independent process/superblock."""
    if len(block_values)<2 or any(not math.isfinite(v) for v in block_values):raise ValueError('>=2 finite blocks')
    if not 0<confidence<1 or draws<10:raise ValueError('invalid bootstrap request')
    rng=random.Random(seed);n=len(block_values)
    boot=[sum(block_values[rng.randrange(n)] for _ in range(n))/n for _ in range(draws)]
    alpha=(1-confidence)/2
    return {'ratio':math.exp(statistics.mean(block_values)),
            'ci':[math.exp(quantile(boot,alpha)),math.exp(quantile(boot,1-alpha))],
            'n_independent_blocks':n,'confidence':confidence,'interpretation':'descriptive_not_device_generalization'}
