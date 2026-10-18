"""CPU-only finite references. No GPU, network, management or package installs."""
from __future__ import annotations
import math
from typing import Iterable, Sequence

MASK = 0x33

def parity(x: int) -> int:
    if x < 0: raise ValueError('nonnegative bit word required')
    return x.bit_count() & 1

def class_of(region: int, bias: int = 0) -> int:
    if not 0 <= region < 64 or bias not in (0, 1): raise ValueError('region/bias')
    return parity(region & MASK) ^ bias

def slot(j: int, d: int, bias: int = 0) -> int:
    if not 0 <= j < 32 or d not in (0, 1) or bias not in (0, 1): raise ValueError('slot input')
    u = j << 1
    return u | (parity(u & MASK) ^ bias ^ d)

def word_index(region: int, k: int) -> int:
    if not 0 <= region < 64 or k < 0: raise ValueError('index input')
    return (((k >> 10) * 64 + region) << 10) + (k & 1023)

def inverse_word(index: int) -> tuple[int, int]:
    if index < 0: raise ValueError('index')
    return (index >> 10) & 63, ((index >> 16) << 10) | (index & 1023)

def enumerate_jobs(grid: int, visits: int, a: int, b: int,
                   data_class: int | None = None, bias: int = 0) -> list[tuple[int, int, int]]:
    """Return (worker, physical region, visit). Grid is logical, not SM binding."""
    if grid <= 0 or visits not in (1,8) or a <= 0 or a % 2 != 1 or b < 0:
        raise ValueError('job parameters')
    if data_class not in (None,0,1) or bias not in (0,1): raise ValueError('class')
    per_visit = 64 if data_class is None else 32
    jobs = per_visit * visits
    result = []
    for worker in range(grid):
        for pos in range(worker, jobs, grid):
            job = (a*pos+b) & (jobs-1)
            j, visit = job % per_visit, job // per_visit
            region = j if data_class is None else slot(j,data_class,bias)
            result.append((worker,region,visit))
    return result

def cell_interaction(t00: float,t01:float,t10:float,t11:float) -> float:
    vals=(t00,t01,t10,t11)
    if any(not math.isfinite(v) or v<=0 for v in vals): raise ValueError('strictly positive times')
    return 0.5*(math.log(t01)+math.log(t10)-math.log(t00)-math.log(t11))

def joint_interaction(match:float,reverse:float) -> float:
    if any(not math.isfinite(v) or v<=0 for v in (match,reverse)): raise ValueError('positive times')
    return math.log(reverse/match)

def geometric_ratio(numerator:Sequence[float],denominator:Sequence[float]) -> float:
    if not numerator or len(numerator)!=len(denominator): raise ValueError('paired nonempty arrays')
    if any(v<=0 or not math.isfinite(v) for v in (*numerator,*denominator)): raise ValueError('times')
    return math.exp(sum(math.log(a/b) for a,b in zip(numerator,denominator))/len(numerator))

def williams(n:int,row:int) -> list[int]:
    """Even-n balanced first-order design; full balance requires all n rows."""
    if n < 2 or n%2: raise ValueError('even n required')
    base=[0]
    lo,hi=1,n-1
    while lo<=hi:
        base.append(lo);lo+=1
        if lo<=hi: base.append(hi);hi-=1
    return [(x+row)%n for x in base]

def completed_bytes(size_bytes:int,visits:int,inner_repeats:int,joint:bool) -> dict:
    if size_bytes not in (2<<20,32<<20) or visits not in (1,8) or inner_repeats not in (1,4):
        raise ValueError('outside frozen matrix')
    unique=size_bytes if joint else size_bytes//2
    return {'unique_input_bytes':unique,'logical_load_bytes':unique*visits*inner_repeats,
            'actual_dram_bytes':None}
