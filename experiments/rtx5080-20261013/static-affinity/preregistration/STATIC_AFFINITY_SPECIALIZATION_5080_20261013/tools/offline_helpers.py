"""CPU-only reference helpers. No GPU, network, subprocess, or experiment execution.

These functions check finite toy models and reporting arithmetic. They do not
infer physical GPU topology or validate CUDA synchronization.
"""
from __future__ import annotations
from collections import Counter
from decimal import Decimal, ROUND_FLOOR
import math
import random
from typing import Mapping, Sequence


def require_finite(value: float, *, positive: bool = False) -> float:
    x = float(value)
    if not math.isfinite(x) or (positive and x <= 0):
        raise ValueError('Expected a finite' + (' positive' if positive else '') + ' number')
    return x


def interaction_residual(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    """Two-way residual for a COMPLETE BALANCED cell-mean matrix.

    Does not accept missing cells. Production analysis must account for epoch,
    cache and order effects; this elementary function alone is not a NUMA test.
    """
    if len(matrix) < 2 or not matrix or len(matrix[0]) < 2:
        raise ValueError('At least two measured positions and two regions required')
    width = len(matrix[0])
    if any(len(row) != width for row in matrix):
        raise ValueError('Ragged matrix')
    a = [[require_finite(x, positive=True) for x in row] for row in matrix]
    row_means = [sum(row) / width for row in a]
    col_means = [sum(row[j] for row in a) / len(a) for j in range(width)]
    grand = sum(row_means) / len(a)
    return [[x - row_means[i] - col_means[j] + grand
             for j, x in enumerate(row)] for i, row in enumerate(a)]


def permutation_is_exact(values: Sequence[int], task_count: int) -> bool:
    if type(task_count) is not int or task_count < 0:
        raise ValueError('task_count must be a nonnegative integer')
    return (len(values) == task_count and all(type(v) is int for v in values)
            and sorted(values) == list(range(task_count)))


def assign_roster_reference(home_groups: Sequence[int], roster_groups: Sequence[int]) -> dict[int, list[int]]:
    """Logical ownership reference, not a CUDA launch or SM-placement guarantee.

    A missing home group redirects to an active group deterministically. Every
    actual worker is represented by its index, even if several run on one SM.
    """
    if any(type(x) is not int or x < 0 for x in list(home_groups) + list(roster_groups)):
        raise ValueError('Groups must be nonnegative integer labels')
    if not roster_groups:
        if home_groups:
            raise ValueError('Cannot assign nonempty tasks to no workers')
        return {}
    active = sorted(set(roster_groups))
    workers = {g: [i for i, x in enumerate(roster_groups) if x == g] for g in active}
    tasks_by_group: dict[int, list[int]] = {g: [] for g in active}
    for task, home in enumerate(home_groups):
        target = home if home in workers else active[home % len(active)]
        tasks_by_group[target].append(task)
    result = {i: [] for i in range(len(roster_groups))}
    for g in active:
        for k, task in enumerate(tasks_by_group[g]):
            result[workers[g][k % len(workers[g])]].append(task)
    assert permutation_is_exact([t for ts in result.values() for t in ts], len(home_groups))
    return result


def paired_geomean_ratio(candidate_ms: Sequence[float], reference_ms: Sequence[float]) -> float:
    if not candidate_ms or len(candidate_ms) != len(reference_ms):
        raise ValueError('Paired nonempty equal-length observations required')
    ratios = [math.log(require_finite(a, positive=True) / require_finite(b, positive=True))
              for a, b in zip(candidate_ms, reference_ms)]
    return math.exp(sum(ratios) / len(ratios))


def first_strict_break_even_frame(extra_init_ms: float, baseline_ms: float, specialized_ms: float) -> int | None:
    """Minimum integer N>=1 for N*(B-S)>C. Constant-times diagnostic only."""
    c = require_finite(extra_init_ms)
    b = require_finite(baseline_ms, positive=True)
    s = require_finite(specialized_ms, positive=True)
    if c < 0:
        raise ValueError('Additional setup cost cannot be negative in this helper')
    delta = Decimal(str(b)) - Decimal(str(s))
    if delta <= 0:
        return None
    return max(1, int((Decimal(str(c)) / delta).to_integral_value(rounding=ROUND_FLOOR)) + 1)


def phase_order(policies: Sequence[str], block: int, seed: int, native: str = 'N_NATIVE') -> list[str]:
    """Native anchors plus reproducibly shuffled non-native policies."""
    if len(set(policies)) != len(policies) or native not in policies:
        raise ValueError('Policies must be unique and include native')
    if type(block) is not int or block < 0:
        raise ValueError('Nonnegative block index required')
    middle = [p for p in policies if p != native]
    random.Random(f'{seed}:{block}').shuffle(middle)
    return [native, *middle, native]


def plan_fingerprint_matches(saved: Mapping[str, object], current: Mapping[str, object]) -> bool:
    """Conservative metadata comparison. Not proof of resource validity."""
    keys = ('gpu_uuid', 'driver', 'cubin_hash', 'control_recipe_hash',
            'scene_logical_hash', 'allocation_generation', 'capacity', 'mapping_version')
    return all(k in saved and k in current and saved[k] is not None
               and current[k] is not None and saved[k] == current[k] for k in keys)
