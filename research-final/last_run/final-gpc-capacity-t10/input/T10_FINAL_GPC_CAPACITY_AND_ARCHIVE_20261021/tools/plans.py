#!/usr/bin/env python3
"""CPU-only planning helpers. No CUDA, system-control, network, or GPU execution."""
from __future__ import annotations
import argparse
import bisect
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Sequence

EXPECTED = {0: 10, 1: 12, 2: 12, 3: 10, 5: 12}
GROUP_ORDER = (0, 1, 2, 3, 5)


def read_topology(path: Path) -> dict[int, dict[int, list[int]]]:
    """Read the existing RM-export CSV; never interpret logical TPC as physical ID."""
    required = {'global_logical_sm', 'physical_gpc', 'logical_local_tpc', 'logical_local_sm'}
    groups: dict[int, dict[int, list[int]]] = {}
    seen: set[int] = set()
    local_sms: dict[tuple[int, int], set[int]] = {}
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError(f'Missing topology columns: {sorted(required - set(reader.fieldnames or []))}')
        for row in reader:
            sm, g, t, local = (int(row[k]) for k in
                ('global_logical_sm', 'physical_gpc', 'logical_local_tpc', 'logical_local_sm'))
            if sm < 0 or sm in seen or local not in (0, 1):
                raise ValueError('Invalid/duplicate SM or local SM ordinal')
            seen.add(sm)
            groups.setdefault(g, {}).setdefault(t, []).append(sm)
            local_sms.setdefault((g, t), set()).add(local)
    counts = {g: sum(map(len, ts.values())) for g, ts in groups.items()}
    if counts != EXPECTED:
        raise ValueError(f'Topology changed: got {counts}, expected {EXPECTED}; re-specify, do not guess')
    for g, ts in groups.items():
        for t, sms in ts.items():
            if len(sms) != 2 or local_sms[(g, t)] != {0, 1}:
                raise ValueError('Each selected TPC must contain its two observed logical SMs')
            sms.sort()
    return groups


def subset_plan(groups: dict[int, dict[int, list[int]]], blocks: int = 6) -> list[dict]:
    if blocks != 6:
        raise ValueError('This design freezes six rotations; do not silently change replication')
    out: list[dict] = []
    all_sms = sorted(sm for ts in groups.values() for sms in ts.values() for sm in sms)
    for b in range(blocks):
        for g in GROUP_ORDER:
            tpcs = sorted(groups[g])
            r = b % len(tpcs)
            rotated = tpcs[r:] + tpcs[:r]
            for k in range(1, len(tpcs) + 1):
                chosen = rotated[:k]
                sms = sorted(sm for t in chosen for sm in groups[g][t])
                out.append({
                    'block': b, 'gpc': g, 'sm_count': len(sms),
                    'logical_tpcs': chosen, 'sm_ids': sms,
                    'unused_sm_ids': sorted(set(all_sms) - set(sms)),
                    'state': 'CPU_PLAN_ONLY_NOT_BOUND',
                    'subset_is_not_physical_floorsweeping': True})
    return out


def task_costs(lengths: Sequence[int], hkv: int, workers: int) -> list[int]:
    """Original DIRECT worker visits p=worker+i*W; empty worker costs one proxy unit."""
    if not lengths or hkv <= 0 or workers <= 0:
        raise ValueError('positive batch, hkv and workers required')
    costs: list[int] = []
    for length in lengths:
        if not isinstance(length, int) or length <= 0:
            raise ValueError('length must be a positive integer')
        pages = (length + 15) // 16
        for _head in range(hkv):
            for worker in range(workers):
                valid_pages = 0 if worker >= pages else 1 + (pages - 1 - worker) // workers
                costs.append(max(1, valid_pages))
    return costs


def contiguous_partition(costs: Sequence[float], weights: Sequence[float]) -> list[dict]:
    """CPU build-time prefix partition; GPU receives only begin/count per launch.

    Uses nearest legal prefix to each cumulative target, with deterministic lower-index tie.
    This is a finite heuristic, not an optimizer or measured-GPU implementation.
    """
    if len(weights) != 5 or len(costs) < 5:
        raise ValueError('This design requires five groups and at least five logical tasks')
    if any(not math.isfinite(x) or x <= 0 for x in [*costs, *weights]):
        raise ValueError('All costs/weights must be finite and strictly positive')
    prefix = [0.0]
    for x in costs:
        prefix.append(prefix[-1] + float(x))
    total = prefix[-1]
    wsum = math.fsum(weights)
    cuts = [0]
    cumulative = 0.0
    for i in range(4):
        cumulative += float(weights[i])
        target = total * cumulative / wsum
        lo, hi = cuts[-1] + 1, len(costs) - (4 - i)
        j = bisect.bisect_left(prefix, target, lo, hi + 1)
        candidates = {max(lo, min(hi, j)), max(lo, min(hi, j - 1))}
        cut = min(candidates, key=lambda p: (abs(prefix[p] - target), p))
        cuts.append(cut)
    cuts.append(len(costs))
    result = []
    for i, g in enumerate(GROUP_ORDER):
        a, b = cuts[i:i+2]
        result.append({'physical_gpc': g, 'task_begin': a, 'task_count': b-a,
                       'proxy_work': prefix[b]-prefix[a], 'capacity_weight': float(weights[i])})
    return result


def decode_task(local: int, begin: int, count: int, workers: int, hkv: int) -> tuple[int, int, int, int]:
    if min(begin, local) < 0 or count <= 0 or local >= count or min(workers, hkv) <= 0:
        raise ValueError('Invalid task coordinates')
    task = begin + local
    head, worker = divmod(task, workers)
    batch, kv_head = divmod(head, hkv)
    return task, batch, kv_head, worker


def opportunity(share: Sequence[float], rates: Sequence[float]) -> dict:
    """Idealized load/rate makespan only. Never replace actual native timing."""
    if len(share) != len(rates) or not share:
        raise ValueError('Length mismatch')
    if any(not math.isfinite(x) or x <= 0 for x in [*share, *rates]):
        raise ValueError('Positive finite inputs required')
    s = math.fsum(share)
    baseline = max(w/s/r for w, r in zip(share, rates))
    ideal = 1.0/math.fsum(rates)
    return {'assumption_only': True, 'baseline_proxy': baseline,
            'ideal_proxy': ideal, 'ideal_time_reduction': 1.0 - ideal/baseline,
            'not_a_native_GPU_bound': True}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('subsets')
    a.add_argument('csv', type=Path); a.add_argument('output', type=Path)
    b = sub.add_parser('partition')
    b.add_argument('--lengths', nargs='+', type=int, required=True)
    b.add_argument('--hkv', type=int, required=True)
    b.add_argument('--workers', type=int, required=True)
    b.add_argument('--weights', nargs=5, type=float, required=True)
    b.add_argument('--output', type=Path, required=True)
    ns = p.parse_args()
    if ns.command == 'subsets':
        rows = subset_plan(read_topology(ns.csv))
        obj = {'source_sha256': hashlib.sha256(ns.csv.read_bytes()).hexdigest(),
               'cpu_only': True, 'resource_sets': rows}
        output = ns.output
    else:
        obj = {'cpu_only': True, 'logical_task_order': '(b*Hkv+hk)*W+worker',
               'ranges': contiguous_partition(task_costs(ns.lengths, ns.hkv, ns.workers), ns.weights)}
        output = ns.output
    if output.exists():
        p.error('Refusing to overwrite an existing plan; use a new path')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

if __name__ == '__main__':
    main()
