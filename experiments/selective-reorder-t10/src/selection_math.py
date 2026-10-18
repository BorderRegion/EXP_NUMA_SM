"""CPU reference only. No GPU results, physical NUMA claim, or trained coefficients.

Small helpers for a cost-aware init selector; call choose_plan at initialization,
not from a per-tile/device task loop. Times are microseconds throughout.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
import statistics
from typing import Mapping, Sequence, Iterable

BASE_ACTIONS = ('LIB', 'SINGLE', 'SPLIT')
PARTITIONS = (((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2)))

def quantile(values: Iterable[float], q: float) -> float:
    a = sorted(float(x) for x in values)
    if not a or not 0 <= q <= 1 or not all(math.isfinite(x) for x in a):
        raise ValueError('finite nonempty values and q in [0,1] required')
    x = (len(a) - 1) * q
    lo, hi = math.floor(x), math.ceil(x)
    return a[lo] * (hi - x) + a[hi] * (x - lo) if lo != hi else a[lo]

def additive_pc(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    n = len(matrix)
    if n < 2 or any(len(r) != n for r in matrix):
        raise ValueError('square matrix, at least 2 groups')
    if any(not math.isfinite(x) or x <= 0 for row in matrix for x in row):
        raise ValueError('positive finite elapsed times required')
    rows = [sum(row)/n for row in matrix]
    cols = [sum(matrix[i][j] for i in range(n))/n for j in range(n)]
    grand = sum(rows)/n
    return [[matrix[i][j] - rows[i] - cols[j] + grand for j in range(n)] for i in range(n)]

def pc_features(matrix: Sequence[Sequence[float]], producer_us: Sequence[float],
                reducer_us: Sequence[float], partition: int, pi: int,
                card_variation: float) -> list[float]:
    """A proxy, not a proof that merging resource groups preserves service costs."""
    if len(matrix) != 4 or len(producer_us) != 4 or len(reducer_us) != 4:
        raise ValueError('exactly four measured resource groups required')
    if partition not in range(3) or pi not in (0, 1):
        raise ValueError('invalid partition/pi')
    if not math.isfinite(card_variation) or card_variation < 0:
        raise ValueError('invalid variability')
    if any(x <= 0 or not math.isfinite(x) for x in list(producer_us)+list(reducer_us)):
        raise ValueError('finite positive service times required')
    groups = PARTITIONS[partition]
    def imbalance(times):
        caps = [sum(1.0/times[g] for g in group) for group in groups]
        return abs(caps[0]-caps[1])/sum(caps)
    residual = additive_pc(matrix)
    paired = [residual[i][j] for branch in (0, 1)
              for i in groups[branch] for j in groups[branch ^ pi]]
    grand = sum(sum(row) for row in matrix)/16
    return [imbalance(producer_us), imbalance(reducer_us), statistics.mean(paired)/grand, card_variation]

def log_shape_features(m:int, n:int, k:int, tile_m:int, tile_n:int, split:int|None, sms:int=56) -> list[float]:
    if min(m,n,k,tile_m,tile_n,sms) <= 0 or (split is not None and split <= 0):
        raise ValueError('positive dimensions only')
    effective_split = split if split is not None else 1
    # For opaque LIB, S=1 geometry is only a shared modeling proxy.
    # Explicit partial bytes are unknown/0 and the missingness flag is 0.
    partial_bytes = 4*m*n*split if split is not None else 0
    tiles = math.ceil(m/tile_m)*math.ceil(n/tile_n)
    padded = tiles*tile_m*tile_n
    vals=[math.log2(m),math.log2(n),math.log2(k),math.log2(1+2*m*n*k),
          math.log2(1+2*k*(m+n)),math.log2(1+partial_bytes),math.log2(1+tiles),
          math.log2(1+tiles*effective_split/sms),1-m*n/padded,math.log2(effective_split),float(split is not None)]
    return vals

def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Partial-pivot elimination for the tiny regularized system."""
    n=len(b); mat=[list(a[i])+[b[i]] for i in range(n)]
    for j in range(n):
        p=max(range(j,n),key=lambda i:abs(mat[i][j]))
        if abs(mat[p][j])<1e-12: raise ValueError('singular system')
        mat[j],mat[p]=mat[p],mat[j]
        pivot=mat[j][j]
        mat[j]=[x/pivot for x in mat[j]]
        for i in range(n):
            if i==j:continue
            f=mat[i][j]
            mat[i]=[x-f*y for x,y in zip(mat[i],mat[j])]
    return [mat[i][-1] for i in range(n)]

@dataclass
class RidgeModel:
    means: list[float]
    scales: list[float]
    beta: list[float]
    def predict_us(self, features: Sequence[float]) -> float:
        if len(features)!=len(self.means) or not all(math.isfinite(x) for x in features):
            raise ValueError('invalid feature vector')
        y=self.beta[0]+sum(b*(x-m)/s for b,x,m,s in zip(self.beta[1:],features,self.means,self.scales))
        if not math.isfinite(y) or not -700<y<700:raise ValueError('invalid predicted log time')
        return math.exp(y)
    def to_dict(self):return asdict(self)

def fit_ridge(features: Sequence[Sequence[float]], time_us: Sequence[float], lam:float=1.0) -> RidgeModel:
    if not features or len(features)!=len(time_us) or lam<=0:raise ValueError('invalid training data')
    d=len(features[0]);n=len(features)
    if not d or any(len(x)!=d for x in features):raise ValueError('inconsistent vectors')
    if any(not math.isfinite(v) for row in features for v in row):raise ValueError('nonfinite features')
    if any(t<=0 or not math.isfinite(t) for t in time_us):raise ValueError('invalid times')
    means=[sum(x[j] for x in features)/n for j in range(d)]
    scales=[max(1e-8,math.sqrt(sum((x[j]-means[j])**2 for x in features)/n)) for j in range(d)]
    x=[[1.]+[(v-m)/s for v,m,s in zip(row,means,scales)] for row in features]
    a=[[sum(row[i]*row[j] for row in x) for j in range(d+1)] for i in range(d+1)]
    for j in range(1,d+1):a[j][j]+=lam
    y=[math.log(t) for t in time_us]
    b=[sum(row[j]*v for row,v in zip(x,y)) for j in range(d+1)]
    return RidgeModel(means,scales,_solve(a,b))

@dataclass(frozen=True)
class Decision:
    base_action: str
    chosen_action: str
    reason: str
    predicted_base_us: float
    predicted_chosen_us: float
    required_saving_us: float
    expected_reuse: int | None


def choose_base(predicted_us: Mapping[str,float], incremental_setup_us: Mapping[str,float],
                paired_error_to_lib_us: Mapping[str,float], expected_reuse:int|None,
                selection_us:float=0.) -> str:
    """Choose among native full-device implementations, pricing preparation too."""
    if 'LIB' not in predicted_us or any(t<=0 or not math.isfinite(t) for t in predicted_us.values()):
        raise ValueError('valid LIB and finite positive predictions required')
    if expected_reuse is not None and expected_reuse<1:raise ValueError('invalid horizon')
    if selection_us<0 or not math.isfinite(selection_us):raise ValueError('invalid selection cost')
    horizon=expected_reuse or 1; chosen='LIB'; best=predicted_us['LIB']
    for action in ('SINGLE','SPLIT'):
        if action not in predicted_us:continue
        setup=incremental_setup_us.get(action,math.inf);err=paired_error_to_lib_us.get(action,math.inf)
        if setup<0 or err<0:raise ValueError('negative cost/error')
        if not math.isfinite(setup) or not math.isfinite(err):continue
        score=predicted_us[action]+max(.5,.01*predicted_us['LIB'],err)+selection_us+setup/horizon
        if score<best:best=score;chosen=action
    return chosen

def choose_plan(predicted_us: Mapping[str,float], extra_setup_us: Mapping[str,float],
                paired_error_us: Mapping[str,float], expected_reuse:int|None,
                selection_us:float=0., in_envelope:bool=True,
                allowed_actions:Sequence[str]|None=None,
                frozen_base_action:str|None=None) -> Decision:
    """Conservative one-time choice; does not claim no future regressions.

    extra_setup_us contains nonnegative incremental setup relative to the chosen
    BASE path. If reuse is unknown, evaluate a single-call horizon and retain None
    in the record: never silently amortize over an imagined long session.
    """
    if selection_us<0 or not math.isfinite(selection_us):raise ValueError('invalid selection time')
    if expected_reuse is not None and expected_reuse<1:raise ValueError('reuse must be positive or None')
    if 'LIB' not in predicted_us:raise ValueError('LIB fallback required')
    if any(not math.isfinite(t) or t<=0 for t in predicted_us.values()):raise ValueError('finite positive predictions required')
    valid=set(predicted_us) if allowed_actions is None else set(allowed_actions)&set(predicted_us)
    valid.add('LIB')
    if frozen_base_action is not None and (frozen_base_action not in BASE_ACTIONS or frozen_base_action not in valid):
        raise ValueError('invalid preselected base action')
    base=frozen_base_action or min((a for a in BASE_ACTIONS if a in valid),key=lambda a:(predicted_us[a],BASE_ACTIONS.index(a)))
    tb=predicted_us[base]
    if not in_envelope:
        return Decision('LIB','LIB','OUT_OF_ENVELOPE',predicted_us['LIB'],predicted_us['LIB'],0.,expected_reuse)
    horizon=expected_reuse or 1
    selected=base;selected_score=tb;required=0.
    for a in sorted(valid):
        if a in BASE_ACTIONS:continue
        setup=extra_setup_us.get(a,math.inf);err=paired_error_us.get(a,math.inf)
        if setup<0 or err<0:raise ValueError('cost/error must be nonnegative')
        if not math.isfinite(setup) or not math.isfinite(err):continue
        margin=max(.5,.01*tb,err)+selection_us+setup/horizon
        score=predicted_us[a]+margin
        if score<selected_score:
            selected=a;selected_score=score;required=margin
    reason='PREDICTED_NET_GAIN' if selected!=base else 'KEEP_BASE'
    return Decision(base,selected,reason,tb,predicted_us[selected],required,expected_reuse)

def amortized_total_us(steady_us:float,init_us:float,count:int)->float:
    if steady_us<=0 or init_us<0 or count<1:raise ValueError('invalid lifecycle parameters')
    return init_us+count*steady_us

def compile_ridge_header(models: Mapping[str,RidgeModel]) -> str:
    """Generate host straight-line prediction functions, not a GPU task LUT."""
    lines=['#pragma once','#include <cmath>','namespace selective_generated {']
    for action,m in models.items():
        if not action.replace('_','').isalnum():raise ValueError('unsafe C++ identifier')
        lines.append(f'inline double predict_{action}(const double* x) {{')
        expr=f'{m.beta[0]:.17g}'
        for i,(b,mu,sd) in enumerate(zip(m.beta[1:],m.means,m.scales)):
            expr+=f' + ({b:.17g}) * ((x[{i}] - ({mu:.17g})) / ({sd:.17g}))'
        lines.append(f'  return std::exp({expr});')
        lines.append('}')
    lines.append('} // namespace selective_generated')
    return '\n'.join(lines)+'\n'
