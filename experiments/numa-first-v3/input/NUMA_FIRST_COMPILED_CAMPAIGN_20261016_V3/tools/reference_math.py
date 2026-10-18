"""CPU-only references for the experiment plan. No GPU or system operations.

A parity layout is a mathematical representation. This module neither discovers
GPU NUMA nor certifies that a virtual-address formula matches physical placement.
"""
from __future__ import annotations
import math
from typing import Iterable, Sequence


def _layout_check(page_bits: int, mask: int, bias: int, domain: int) -> None:
    if not isinstance(page_bits, int) or not 1 <= page_bits <= 30:
        raise ValueError('page_bits must be an integer in [1, 30]')
    if not isinstance(mask, int) or not 0 < mask < (1 << page_bits):
        raise ValueError('mask must be nonzero and fit within page_bits')
    if bias not in (0, 1) or domain not in (0, 1):
        raise ValueError('bias and domain must be binary')


def home(slot: int, mask: int, bias: int = 0) -> int:
    """Evaluate a supplied abstract bit model, NOT hardware home detection."""
    if slot < 0 or mask <= 0 or bias not in (0, 1):
        raise ValueError('invalid bit model')
    return ((slot & mask).bit_count() & 1) ^ bias


def colored_slot(j: int, page_bits: int, mask: int, bias: int, domain: int) -> int:
    """Map an index within one half-view to a unique slot of a specified color."""
    _layout_check(page_bits, mask, bias, domain)
    if not isinstance(j, int) or not 0 <= j < (1 << (page_bits - 1)):
        raise ValueError('logical page is outside the half-view')
    p = (mask & -mask).bit_length() - 1
    u = (j & ((1 << p) - 1)) | ((j >> p) << (p + 1))
    correction = home(u, mask, bias) ^ domain
    return u | (correction << p)


def logical_page(slot: int, page_bits: int, mask: int, bias: int) -> tuple[int, int]:
    """Return (domain, index) under the exact same supplied abstract layout."""
    _layout_check(page_bits, mask, bias, 0)
    if not isinstance(slot, int) or not 0 <= slot < (1 << page_bits):
        raise ValueError('slot outside allocation')
    p = (mask & -mask).bit_length() - 1
    j = (slot & ((1 << p) - 1)) | ((slot >> (p + 1)) << p)
    return home(slot, mask, bias), j


def mapped_byte_offset(logical_offset: int, granule_bits: int,
                         page_bits: int, mask: int, bias: int, domain: int) -> int:
    """Offset within an OWNED virtual allocation after the supplied permutation.

    This is not a GPU physical address. Caller passes an offset in the half-view.
    """
    if not isinstance(granule_bits, int) or not 0 <= granule_bits <= 30:
        raise ValueError('granule_bits outside supported reference range')
    if logical_offset < 0 or logical_offset >= (1 << (granule_bits + page_bits - 1)):
        raise ValueError('logical offset outside half-view')
    j, off = divmod(logical_offset, 1 << granule_bits)
    return (colored_slot(j, page_bits, mask, bias, domain) << granule_bits) | off


def affine_permutation(n: int, multiplier: int, offset: int) -> list[int]:
    """Finite index test only; exact arithmetic, no resource placement claim."""
    if n <= 0 or math.gcd(multiplier, n) != 1:
        raise ValueError('affine multiplier must be coprime with n')
    return [(multiplier * i + offset) % n for i in range(n)]


def log_interaction_2x2(times: Sequence[Sequence[float]]) -> float:
    if len(times) != 2 or any(len(row) != 2 for row in times):
        raise ValueError('exactly 2 by 2 required')
    vals = [float(v) for row in times for v in row]
    if any(not math.isfinite(v) or v <= 0 for v in vals):
        raise ValueError('all times must be positive and finite')
    a,b,c,d = map(math.log, vals)
    return 0.5 * (b+c-a-d)


def geometric_mean(values: Iterable[float]) -> float:
    vals = list(values)
    if not vals or any(not math.isfinite(v) or v <= 0 for v in vals):
        raise ValueError('positive finite nonempty observations required')
    return math.exp(math.fsum(math.log(v) for v in vals) / len(vals))


def break_even_count(extra_init: float, reference_time: float,
                     candidate_time: float) -> int | None:
    """First integer N with nonnegative savings, under this constant-time model."""
    if any(not math.isfinite(x) for x in (extra_init, reference_time, candidate_time)):
        raise ValueError('finite inputs required')
    if extra_init < 0 or min(reference_time, candidate_time) <= 0:
        raise ValueError('invalid costs')
    delta = reference_time - candidate_time
    if delta <= 0:
        return None
    return math.ceil(extra_init / delta)


def even_williams_orders(n: int) -> list[list[int]]:
    """Balanced first-order predecessor design for even n strategies."""
    if n < 2 or n % 2:
        raise ValueError('this reference implements even n >= 2 only')
    first = [0]
    for k in range(1, n):
        first.append((k+1)//2 if k % 2 else n-k//2)
    return [[(v+shift)%n for v in first] for shift in range(n)]


def consumed_worksets(l2_bytes: int, cap_bytes: int = 1 << 30) -> list[dict]:
    if l2_bytes <= 0 or cap_bytes <= 0:
        raise ValueError('positive device/cap sizes required')
    out=[]; seen=set()
    for factor in (0.5, 2, 8, 32):
        actual=min(int(l2_bytes*factor), cap_bytes)
        if actual not in seen:
            seen.add(actual)
            out.append({'requested_l2_factor':factor, 'bytes':actual,
                        'actual_l2_factor':actual/l2_bytes,
                        'capped':actual != int(l2_bytes*factor)})
    return out


def render_layout_header(page_bits: int, granule_bits: int, mask: int, bias: int) -> str:
    """Emit conditional formula code. No real-GPU hypothesis or compiled artifact.

    Any deployment MUST bind its fitted model/evidence and allocation generation
    externally. Passing arguments to this function does not validate that evidence.
    """
    _layout_check(page_bits, mask, bias, 0)
    if not 0 <= granule_bits <= 30:
        raise ValueError('invalid granule bits')
    p=(mask & -mask).bit_length()-1
    return f'''// CONDITIONAL LAYOUT FORMULA ONLY: not a T10 or 5070Ti physical hash.
// This source has not been compiled or evaluated on a GPU by the plan author.
// Bind measured model, allocation generation, valid view size, and actual resource.
#pragma once
#include <stdint.h>

template<unsigned Domain> struct CompiledColorLayout {{
  static_assert(Domain < 2, "binary layout only");
  static constexpr unsigned kPageBits = {page_bits};
  static constexpr unsigned kGranuleBits = {granule_bits};
  static constexpr unsigned kPivot = {p};
  static constexpr uint64_t kMask = {mask}ULL;
  static constexpr unsigned kBias = {bias};
  // Preconditions: logicalByte lies in a half-view, and accesses do not cross a
  // physical layout seam unless the iterator explicitly splits the transaction.
  __device__ __forceinline__ static uint64_t offset(uint64_t logicalByte) {{
    const uint64_t j = logicalByte >> kGranuleBits;
    const uint64_t low = j & ((1ULL << kPivot) - 1ULL);
    const uint64_t u = low | ((j >> kPivot) << (kPivot + 1));
    const uint64_t bit = (__popcll(u & kMask) & 1U) ^ kBias ^ Domain;
    const uint64_t slot = u | (bit << kPivot);
    return (slot << kGranuleBits) |
           (logicalByte & ((1ULL << kGranuleBits) - 1ULL));
  }}
}};
'''
