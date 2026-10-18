"""CPU-only planning/statistics helpers. NOT a CUDA scheduler or legality verifier.

These functions test finite logical mappings and summarize supplied measurements.
They neither query hardware nor establish that an integration is correct on GPU.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json
import math
import random
from typing import Iterable, Sequence


def ceil_div(a: int, b: int) -> int:
    if isinstance(a, bool) or isinstance(b, bool) or a < 0 or b <= 0:
        raise ValueError('ceil_div needs non-negative a and positive b')
    return (a + b - 1) // b


def floor_pow2(x: int) -> int:
    if x < 1:
        raise ValueError('x must be positive')
    return 1 << (x.bit_length() - 1)


@dataclass(frozen=True)
class Problem:
    m: int
    n: int
    k: int

    def __post_init__(self) -> None:
        if any(isinstance(v, bool) or not isinstance(v, int) for v in (self.m, self.n, self.k)):
            raise TypeError('integer dimensions required')
        if self.m < 0 or self.n < 0 or self.k <= 0:
            raise ValueError('m,n>=0; k>0 required')


@dataclass(frozen=True)
class Packet:
    problem: int
    n_tile: int
    m_first: int
    length: int

    def tiles(self) -> tuple[tuple[int, int, int], ...]:
        return tuple((self.problem, m, self.n_tile)
                     for m in range(self.m_first, self.m_first + self.length))


def make_packets(problems: Sequence[Problem], tile_m: int, tile_n: int, tile_k: int,
                 workers: int, q_cap: int = 4, target_waves: int = 2,
                 work_budget_k_tiles: int = 64) -> tuple[Packet, ...]:
    """Enumerate finite reference packets, not intended for a production host path.

    A production implementation must decode packet ordinals in the native visitor
    or use an existing producer's metadata. Do not upload this Python list each step.
    """
    if min(tile_m, tile_n, tile_k, workers, target_waves, work_budget_k_tiles) <= 0:
        raise ValueError('tile/resource parameters must be positive')
    if q_cap not in (1, 2, 4, 8):
        raise ValueError('unsupported q_cap')
    shapes = [(ceil_div(p.m, tile_m), ceil_div(p.n, tile_n),
               ceil_div(p.k, tile_k)) for p in problems]
    total_tiles = sum(m * n for m, n, _ in shapes)
    parallel_cap = max(1, total_tiles // (workers * target_waves))
    result: list[Packet] = []
    for e, (mt, nt, kt) in enumerate(shapes):
        if mt == 0 or nt == 0:
            continue
        q = floor_pow2(min(q_cap, parallel_cap,
                          max(1, work_budget_k_tiles // kt), mt))
        for n in range(nt):
            for m in range(0, mt, q):
                result.append(Packet(e, n, m, min(q, mt - m)))
    return tuple(result)


def expected_tiles(problems: Sequence[Problem], tile_m: int, tile_n: int) -> set[tuple[int,int,int]]:
    if tile_m <= 0 or tile_n <= 0:
        raise ValueError('positive tiles required')
    return {(e, m, n) for e, p in enumerate(problems)
            for m in range(ceil_div(p.m, tile_m))
            for n in range(ceil_div(p.n, tile_n))}


def assign_static(packets: Sequence[Packet], workers: int) -> tuple[tuple[Packet,...],...]:
    if workers <= 0:
        raise ValueError('workers must be positive')
    return tuple(tuple(packets[i::workers]) for i in range(workers))


def check_coverage(problems: Sequence[Problem], packets: Sequence[Packet],
                   tile_m: int, tile_n: int) -> dict:
    expected = expected_tiles(problems, tile_m, tile_n)
    seen: set[tuple[int,int,int]] = set()
    duplicate = 0
    for packet in packets:
        if packet.length <= 0:
            raise ValueError('non-positive packet')
        for tile in packet.tiles():
            if tile in seen:
                duplicate += 1
            seen.add(tile)
    return {'expected_count': len(expected), 'seen_unique': len(seen),
            'duplicates': duplicate, 'missing': len(expected-seen),
            'unexpected': len(seen-expected)}


def apportioned_counts(total: int, experts: int, distribution: str) -> tuple[int,...]:
    """Exact integer allocation of synthetic routed rows. No model provenance implied."""
    if total < 0 or experts <= 0:
        raise ValueError('invalid sizes')
    if distribution == 'uniform':
        weights = [Fraction(1) for _ in range(experts)]
    elif distribution == 'zipf':
        weights = [Fraction(1, i+1) for i in range(experts)]
    elif distribution == 'one_heavy':
        weights = [Fraction(max(1, experts-1))] + [Fraction(1) for _ in range(experts-1)]
    elif distribution == 'sparse_active':
        active = max(1, experts//4)
        weights = [Fraction(int(i<active)) for i in range(experts)]
    else:
        raise ValueError('unknown distribution')
    norm = sum(weights)
    exact = [total*w/norm for w in weights]
    counts = [int(x) for x in exact]
    remainder = total-sum(counts)
    ranking = sorted(range(experts), key=lambda i: (-(exact[i]-counts[i]), i))
    for i in ranking[:remainder]:
        counts[i] += 1
    return tuple(counts)


def attention_lengths(batch: int, mean_length: int, distribution: str, seed: int) -> tuple[int,...]:
    if batch <= 0 or mean_length <= 0:
        raise ValueError('positive batch/length required')
    total = batch * mean_length
    if distribution == 'uniform':
        return (mean_length,) * batch
    if distribution in ('long_tail', 'order_permuted'):
        extras = apportioned_counts(total-batch, batch, 'zipf')
    elif distribution == 'staggered':
        weights = [Fraction(i+1) for i in range(batch)]
        vals = [Fraction(total-batch)*w/sum(weights) for w in weights]
        extras = [int(x) for x in vals]
        order = sorted(range(batch), key=lambda i: (-(vals[i]-extras[i]), i))
        for i in order[:total-batch-sum(extras)]:
            extras[i] += 1
    else:
        raise ValueError('unknown attention distribution')
    result = [x+1 for x in extras]
    if distribution == 'order_permuted':
        random.Random(seed).shuffle(result)
    return tuple(result)


def balanced_orders(items: Sequence[str], blocks: int, seed: int) -> list[list[str]]:
    """Williams design for even n; odd n uses its reversed companion.

    Taking fewer than a full design cycle is NOT complete carryover balancing.
    """
    if not items or len(set(items)) != len(items) or blocks <= 0:
        raise ValueError('unique items and positive blocks required')
    labels = list(items)
    random.Random(seed).shuffle(labels)
    n = len(labels)
    base = [0] + [((i+1)//2 if i%2 else n-i//2) for i in range(1,n)]
    design = [[labels[(x+r)%n] for x in base] for r in range(n)]
    if n%2 and n>1:
        design += [list(reversed(row)) for row in design]
    return [list(design[b % len(design)]) for b in range(blocks)]


def grouped_tensor_bytes(rows: Sequence[int], k: int, n: int, element_bytes: int = 2) -> int:
    if not rows or min(k,n,element_bytes)<=0 or any(x<0 for x in rows):
        raise ValueError('invalid dimensions')
    # Inputs, all resident expert weights, final outputs only; workspace is separate.
    return element_bytes*(sum(rows)*k + len(rows)*k*n + sum(rows)*n)


def moe_layer_tensor_bytes(tokens: int, experts: int, hidden: int, intermediate: int,
                           top_k: int, element_bytes: int = 2) -> int:
    if min(tokens,experts,hidden,intermediate,top_k,element_bytes)<=0 or top_k>experts:
        raise ValueError('invalid dimensions')
    pairs=tokens*top_k
    weights=3*experts*hidden*intermediate*element_bytes
    # Conservative explicit activation buffers, not a claim about backend peak.
    activations=(tokens*hidden + pairs*hidden + 2*pairs*intermediate +
                 pairs*intermediate + pairs*hidden + tokens*hidden)*element_bytes
    router=tokens*experts*4 + pairs*(4+4) + (experts+1)*8
    return weights+activations+router


def memory_feasible(total_device_bytes: int, current_free_bytes: int,
                    requested_new_bytes: int, workspace_bytes: int = 0,
                    min_free_bytes: int = 2<<30, free_fraction: float = .15) -> bool:
    if min(total_device_bytes,current_free_bytes,requested_new_bytes,workspace_bytes,min_free_bytes)<0:
        raise ValueError('negative bytes')
    if current_free_bytes>total_device_bytes or not 0<=free_fraction<1:
        raise ValueError('invalid capacity')
    headroom=max(min_free_bytes, math.ceil(total_device_bytes*free_fraction))
    return current_free_bytes-requested_new_bytes-workspace_bytes>=headroom


def paired_effect(candidate: Sequence[float], reference: Sequence[float],
                  draws: int = 20000, seed: int = 2026101509) -> dict:
    """Paired bootstrap over provided independent block means, not raw iterations."""
    if len(candidate)!=len(reference) or len(candidate)<2 or draws<=0:
        raise ValueError('matching independent blocks (>=2) and positive draws required')
    if any(not math.isfinite(x) or x<=0 for x in (*candidate,*reference)):
        raise ValueError('finite positive times required')
    logs=[math.log(a/b) for a,b in zip(candidate,reference)]
    ratio=math.exp(sum(logs)/len(logs))
    rng=random.Random(seed)
    samples=sorted(math.exp(sum(rng.choice(logs) for _ in logs)/len(logs)) for _ in range(draws))
    lo=samples[math.floor(.025*(draws-1))]
    hi=samples[math.ceil(.975*(draws-1))]
    return {'independent_blocks':len(logs),'time_ratio':ratio,
            'time_reduction_percent':100*(1-ratio),'ratio_ci95':[lo,hi],
            'reduction_ci95':[100*(1-hi),100*(1-lo)],
            'mean_absolute_delta':sum(a-b for a,b in zip(candidate,reference))/len(logs),
            'bootstrap_draws':draws,'seed':seed,
            'interpretation':'exploratory paired-block interval; not multiplicity adjusted'}


def factorial_interaction(f0s0: float, f0s1: float, f1s0: float, f1s1: float) -> dict:
    vals=(f0s0,f0s1,f1s0,f1s1)
    if any(not math.isfinite(x) or x<=0 for x in vals):
        raise ValueError('finite positive values required')
    return {'schedule_at_existing_fusion':f0s1/f0s0,
            'schedule_at_added_fusion':f1s1/f1s0,
            'added_fusion_at_simple_schedule':f1s0/f0s0,
            'log_interaction':math.log(f1s1/f1s0)-math.log(f0s1/f0s0)}


def launch_delta(baseline: dict, candidate: dict) -> dict:
    """Arithmetic on supplied ledgers ONLY; not observed hardware verification."""
    fields=('scheduler_kernel_nodes','total_kernel_nodes','host_waits','metadata_d2h_bytes')
    result={}
    for key in fields:
        b=baseline.get(key); c=candidate.get(key)
        if b is None or c is None:
            result[key]=None
            continue
        if not isinstance(b,int) or not isinstance(c,int) or min(b,c)<0:
            raise ValueError('nonnegative integer counts or None required')
        result[key]=c-b
    result['evidence_status']='SUPPLIED_LEDGER_ARITHMETIC_NOT_RUNTIME_PROOF'
    return result


def canonical_hash(obj: object) -> str:
    return sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
