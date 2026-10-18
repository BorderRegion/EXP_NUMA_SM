"""CPU-only planning references. Not vendor kernel code or hardware inference."""
from __future__ import annotations
import itertools
import math
import random
from collections.abc import Iterable, Sequence


def ceildiv(n: int, d: int) -> int:
    if n < 0 or d <= 0:
        raise ValueError('n >= 0 and d > 0 required')
    return (n + d - 1) // d


def aligned_split_ranges(k: int, splits: int, block_k: int = 32) -> list[tuple[int, int]]:
    """Equal rounded-up K slices, for planning; verify vendor's actual implementation."""
    if min(k, splits, block_k) <= 0:
        raise ValueError('positive K/S/block_k required')
    width = ceildiv(k, splits * block_k) * block_k
    intervals = [(s * width, min(k, (s + 1) * width)) for s in range(splits)]
    if any(lo >= hi for lo, hi in intervals):
        raise ValueError('empty split: choose fewer splits or a different documented recipe')
    return intervals


def tile_shape(m: int, n: int, bm: int, bn: int) -> tuple[int, int]:
    if min(m, n, bm, bn) <= 0:
        raise ValueError('dimensions must be positive')
    return ceildiv(m, bm), ceildiv(n, bn)


def workspace_bytes(m: int, n: int, splits: int, bm: int = 32, bn: int = 64,
                    padded: bool = False, element_bytes: int = 4) -> int:
    if min(m, n, splits, bm, bn, element_bytes) <= 0:
        raise ValueError('positive dimensions required')
    if padded:
        tm, tn = tile_shape(m, n, bm, bn)
        return tm * tn * bm * bn * splits * element_bytes
    return m * n * splits * element_bytes


def kv_bytes(batch: int, length: int, heads_kv: int, head_dim: int,
             element_bytes: int = 2) -> int:
    if min(batch, length, heads_kv, head_dim, element_bytes) <= 0:
        raise ValueError('positive dimensions required')
    return 2 * batch * length * heads_kv * head_dim * element_bytes


def owner_rank(tile: int, tiles: int, scheme: str = 'interleave') -> tuple[int, int, int]:
    """Return group, rank-within-group, group tile count; no lookup table."""
    if not 0 <= tile < tiles:
        raise ValueError('tile out of range')
    if scheme == 'interleave':
        g, rank = tile & 1, tile // 2
        count = (tiles + 1 - g) // 2
    elif scheme == 'contiguous':
        cut = (tiles + 1) // 2
        g = int(tile >= cut)
        rank = tile if g == 0 else tile - cut
        count = cut if g == 0 else tiles - cut
    else:
        raise ValueError('unsupported owner scheme')
    return g, rank, count


def slab_tile(tile: int, tiles: int, scheme: str = 'interleave') -> int:
    g, rank, _ = owner_rank(tile, tiles, scheme)
    return rank + (0 if g == 0 else (tiles + 1) // 2)


def partial_offset(tile: int, split: int, element: int, tiles: int, splits: int,
                   tile_elements: int, layout: str = 'tile_slab',
                   scheme: str = 'interleave') -> int:
    if min(tiles, splits, tile_elements) <= 0:
        raise ValueError('positive dimensions required')
    if not (0 <= tile < tiles and 0 <= split < splits and 0 <= element < tile_elements):
        raise ValueError('index out of range')
    # Both references below are padded tile-coordinate layouts, NOT vendor row-major.
    if layout == 'split_major_tile_reference':
        return (split * tiles + tile) * tile_elements + element
    if layout == 'tile_slab':
        t = slab_tile(tile, tiles, scheme)
        return (t * splits + split) * tile_elements + element
    raise ValueError('unknown layout')


def inverse_partial_offset(offset: int, tiles: int, splits: int, tile_elements: int,
                           layout: str = 'tile_slab', scheme: str = 'interleave') -> tuple[int, int, int]:
    if min(tiles, splits, tile_elements) <= 0 or not 0 <= offset < tiles * splits * tile_elements:
        raise ValueError('invalid offset or dimensions')
    q, e = divmod(offset, tile_elements)
    if layout == 'split_major_tile_reference':
        s, t = divmod(q, tiles)
    elif layout == 'tile_slab':
        compact, s = divmod(q, splits)
        if scheme == 'contiguous':
            t = compact
        elif scheme == 'interleave':
            cut = (tiles + 1) // 2
            t = 2 * compact if compact < cut else 2 * (compact - cut) + 1
        else:
            raise ValueError('unknown owner scheme')
    else:
        raise ValueError('unknown layout')
    return t, s, e


def ownership(tiles: int, splits: int, swap_consumer: bool = False,
              scheme: str = 'interleave') -> dict[str, list[list[tuple[int, int]]]]:
    if min(tiles, splits) <= 0:
        raise ValueError('positive dimensions required')
    p: list[list[tuple[int, int]]] = [[], []]
    c: list[list[tuple[int, int]]] = [[], []]
    for t in range(tiles):
        g, _, _ = owner_rank(t, tiles, scheme)
        p[g].extend((t, s) for s in range(splits))
        c[g ^ int(swap_consumer)].append((t, -1))
    return {'producer': p, 'consumer': c}


def balanced_even_orders(n: int) -> list[list[int]]:
    """Williams design for even n, each ordered pair occurs once as adjacency."""
    if n < 2 or n % 2:
        raise ValueError('even number >= 2 required')
    base = [0]
    for i in range(1, n):
        base.append((i + 1) // 2 if i % 2 else n - i // 2)
    return [[(x + shift) % n for x in base] for shift in range(n)]


def log_interaction(t00: float, t01: float, t10: float, t11: float) -> float:
    values = [t00, t01, t10, t11]
    if any(not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('positive finite timings required')
    return 0.5 * (math.log(t01) + math.log(t10) - math.log(t00) - math.log(t11))


def geometric_mean(values: Iterable[float]) -> float:
    v = list(values)
    if not v or any(x <= 0 or not math.isfinite(x) for x in v):
        raise ValueError('nonempty positive finite values required')
    return math.exp(sum(map(math.log, v)) / len(v))


def break_even(extra_init_ms: float, reference_us: float, candidate_us: float) -> int | None:
    if not all(math.isfinite(x) for x in [extra_init_ms, reference_us, candidate_us]):
        raise ValueError('nonfinite input')
    if extra_init_ms < 0 or min(reference_us, candidate_us) <= 0:
        raise ValueError('invalid cost')
    saved = reference_us - candidate_us
    if saved <= 0:
        return None
    return math.floor(extra_init_ms * 1000 / saved) + 1  # strict net benefit


def merge_attention(partial_outputs: Sequence[Sequence[float]], lse: Sequence[float]) -> list[float]:
    if len(partial_outputs) != len(lse) or not lse:
        raise ValueError('nonempty matching parts required')
    dim = len(partial_outputs[0])
    if dim == 0 or any(len(p) != dim for p in partial_outputs):
        raise ValueError('shape mismatch')
    if any(math.isnan(x) or x == math.inf for x in lse):
        raise ValueError('invalid LSE')
    finite = [x for x in lse if x != -math.inf]
    if not finite:
        return [0.0] * dim  # explicit all-masked contract, not default for all vendors
    m = max(finite)
    weights = [0.0 if x == -math.inf else math.exp(x - m) for x in lse]
    total = sum(weights)
    active = [(w, p) for w, p in zip(weights, partial_outputs) if w > 0.0]
    if any(not math.isfinite(x) for _, p in active for x in p):
        raise ValueError('nonfinite nonempty partial output')
    return [sum(w * p[j] for w, p in active) / total for j in range(dim)]


def bootstrap_blocks(block_case_ratios: dict[str, dict[str, float]],
                     samples: int = 20000, seed: int = 20261016,
                     alpha: float = 0.05) -> dict[str, float | int]:
    """Resample whole blocks across a fixed shared case set; never resample epochs."""
    if samples <= 0 or not 0 < alpha < 1 or len(block_case_ratios) < 2:
        raise ValueError('need >=2 blocks, positive samples, 0<alpha<1')
    blocks = sorted(block_case_ratios)
    cases = set(block_case_ratios[blocks[0]])
    if not cases or any(set(block_case_ratios[b]) != cases for b in blocks):
        raise ValueError('incomplete or different case coverage; do not silently fill missing cells')
    per_block = [math.log(geometric_mean(block_case_ratios[b][c] for c in sorted(cases))) for b in blocks]
    point = math.exp(sum(per_block) / len(per_block))
    rng = random.Random(seed)
    reps = sorted(math.exp(sum(per_block[rng.randrange(len(blocks))] for _ in blocks) / len(blocks))
                  for _ in range(samples))
    def quantile(p: float) -> float:
        x = p * (samples - 1)
        i = int(x); j = min(i + 1, samples - 1)
        return reps[i] + (reps[j] - reps[i]) * (x - i)
    return {'ratio': point, 'ci_low': quantile(alpha / 2), 'ci_high': quantile(1 - alpha / 2),
            'blocks': len(blocks), 'cases': len(cases), 'bootstrap_samples': samples}
