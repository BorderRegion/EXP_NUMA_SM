"""Stdlib-only paired, stratified block bootstrap. No pixel/frame pseudoreplication."""
from __future__ import annotations
import math, random

def paired_summary(records:list[dict], draws:int=20000, seed:int=2026101403)->dict:
    if draws<100: raise ValueError('Use at least 100 draws')
    if not records: raise ValueError('No records')
    groups={};seen=set();platforms=set()
    for r in records:
        platforms.add(r['platform']);key=(r['platform'],r['condition'],r['block_id'])
        if key in seen: raise ValueError('Duplicate process block')
        seen.add(key)
        n=float(r['reference_ms']);t=float(r['candidate_ms'])
        if not math.isfinite(n) or not math.isfinite(t) or min(n,t)<=0: raise ValueError('Nonpositive timing')
        groups.setdefault(r['condition'],[]).append((math.log(t/n),t-n))
    if len(platforms)!=1: raise ValueError('Do not pool raw timings across platforms')
    def mean(xs):return sum(xs)/len(xs)
    def effect(gs):return math.exp(mean([mean([v[0] for v in vs]) for vs in gs]))
    point=effect(list(groups.values()))
    rng=random.Random(seed);boot=[]
    for _ in range(draws):
        boot.append(effect([[rng.choice(vs) for _ in vs] for vs in groups.values()]))
    boot.sort()
    def q(p):
        z=(len(boot)-1)*p;l=int(z);h=min(l+1,len(boot)-1)
        return boot[l]+(boot[h]-boot[l])*(z-l)
    lo,hi=q(.025),q(.975)
    return {'platform':next(iter(platforms)),'ratio':point,'time_reduction_pct':100*(1-point),
      'ratio_ci_95':[lo,hi],'time_reduction_ci_95':[100*(1-hi),100*(1-lo)],
      'mean_stratum_delta_ms':mean([mean([v[1] for v in vs]) for vs in groups.values()]),
      'strata':len(groups),'process_blocks':len(records),'seed':seed,'draws':draws,
      'scope':'exploratory paired process-block bootstrap; not cross-device inference'}
