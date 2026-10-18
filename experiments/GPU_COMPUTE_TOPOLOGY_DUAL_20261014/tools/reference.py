"""CPU reference utilities, NOT a GPU scheduler and NOT research evidence."""
from __future__ import annotations
import math
from typing import Iterable, Sequence

def _positive(values: Sequence[float], *, allow_zero: bool=False) -> list[float]:
    xs=[float(x) for x in values]
    if not xs or any(not math.isfinite(x) or x < 0 or (x == 0 and not allow_zero) for x in xs):
        raise ValueError('Expected finite nonnegative/positive values.')
    return xs

def quotas(total: int, capacities: Sequence[float]) -> list[int]:
    """Largest remainder allocation; preserves every task and uses stable ties."""
    if isinstance(total,bool) or not isinstance(total,int) or total < 0:
        raise ValueError('total must be a nonnegative integer')
    cap=_positive(capacities,allow_zero=True)
    if sum(cap)<=0: raise ValueError('At least one capacity must be positive')
    ideal=[total*c/sum(cap) for c in cap]
    result=[math.floor(x) for x in ideal]
    for i in sorted(range(len(cap)),key=lambda i:(-(ideal[i]-result[i]),i))[:total-sum(result)]:
        result[i]+=1
    return result

def static_minimax(costs: Sequence[Sequence[float]], setup: Sequence[float]|None=None) -> list[int]:
    """Small initialization-only greedy assignment; cost rows are tasks, cols groups.
    Positive infinity denotes a forbidden group. This is a transparent heuristic,
    not claimed to be optimal, topology-correct, or novel.
    """
    if not costs: return []
    ng=len(costs[0])
    if ng==0 or any(len(row)!=ng for row in costs): raise ValueError('ragged costs')
    rows=[]
    for row in costs:
        row=[float(x) for x in row]
        if any(math.isnan(x) or x<0 for x in row) or not any(math.isfinite(x) for x in row):
            raise ValueError('Invalid costs or task has no allowed group')
        rows.append(row)
    loads=[0.0]*ng if setup is None else _positive(setup,allow_zero=True)
    if len(loads)!=ng: raise ValueError('setup dimension mismatch')
    def priority(i:int):
        f=[x for x in rows[i] if math.isfinite(x)]
        return (-(max(f)-min(f)),-max(f),i)
    out=[-1]*len(rows)
    for t in sorted(range(len(rows)),key=priority):
        legal=[g for g in range(ng) if math.isfinite(rows[t][g])]
        g=min(legal,key=lambda g:(max(loads[j]+(rows[t][j] if j==g else 0.0) for j in range(ng)),loads[g]+rows[t][g],g))
        out[t]=g;loads[g]+=rows[t][g]
    return out

def static_ownership(task_groups: Sequence[int], worker_groups: Sequence[int]) -> list[list[int]]:
    """Reference for finite cooperative roster: missing groups go to lowest active.
    Logical task ownership does NOT change if a worker later migrates SM.
    """
    if any(g<0 or not isinstance(g,int) for g in list(task_groups)+list(worker_groups)):
        raise ValueError('groups must be nonnegative integers')
    if not worker_groups:
        if task_groups: raise ValueError('No workers')
        return []
    members={g:[i for i,x in enumerate(worker_groups) if x==g] for g in sorted(set(worker_groups))}
    lists={g:[] for g in members}
    for t,g in enumerate(task_groups): lists[g if g in members else min(members)].append(t)
    out=[[] for _ in worker_groups]
    for g,tasks in lists.items():
        for k,t in enumerate(tasks): out[members[g][k%len(members[g])]].append(t)
    return out

def validate_ownership(owned:Sequence[Sequence[int]], ntasks:int) -> bool:
    flat=[t for row in owned for t in row]
    return sorted(flat)==list(range(ntasks))

def break_even(extra_init_ms: float, native_ms: float, candidate_ms: float) -> int|None:
    """First positive integer N for strict total-time gain; no gain returns None."""
    c=float(extra_init_ms);n=float(native_ms);t=float(candidate_ms)
    if not all(math.isfinite(x) for x in (c,n,t)) or c<0 or n<=0 or t<=0:
        raise ValueError('Invalid timing')
    delta=n-t
    return None if delta<=0 else math.floor(c/delta)+1

def same_gpc_components(records: Iterable[dict]) -> list[list[int]]:
    """Union observed SMs WITHIN EACH VALID cluster launch. Components may be
    proper subsets of a GPC; absent edges are not different-GPC evidence."""
    parent={}
    def root(x):
        parent.setdefault(x,x)
        while x!=parent[x]: parent[x]=parent[parent[x]];x=parent[x]
        return x
    buckets={}
    for r in records:
        if not r.get('cluster_semantics_qualified',False): continue
        if int(r.get('cluster_size',1))<=1: continue
        a,b=int(r['sm_begin']),int(r['sm_end'])
        if a!=b: continue
        root(a)
        key=(r['process_id'],r['launch_id'],r['cluster_id'])
        buckets.setdefault(key,set()).add(a)
    for smids in buckets.values():
        ss=sorted(smids)
        for x in ss[1:]: parent[root(x)]=root(ss[0])
    groups={}
    for x in parent: groups.setdefault(root(x),[]).append(x)
    return sorted((sorted(v) for v in groups.values()),key=lambda x:x[0])
