#pragma once
// Proposed scaffold ONLY. Not compiled or executed with CUDA by the author.
// Adapt host bindings to existing qualified T10 Green/Graph runner.
// Production rules: no per-task LUT, no clock/SM/diagnostic operations in Diag=false.
#include <cuda_runtime.h>
#include <stdint.h>

struct FrozenProbeRecord {
  unsigned long long ticks;
  unsigned long long sum;
  unsigned sm_begin, sm_end, physical_region, visit;
};

__device__ __forceinline__ unsigned frozen_smid() {
  unsigned v;
  asm volatile("mov.u32 %0, %%smid;" : "=r"(v));
  return v;
}
__device__ __forceinline__ unsigned class_region_0x33(unsigned j, unsigned d, unsigned bias) {
  const unsigned u = j << 1;
  return u | ((__popc(u & 0x33u) & 1u) ^ bias ^ d);
}
__device__ __forceinline__ unsigned physical_word_4k(unsigned region, unsigned k) {
  return ((((k >> 10) * 64u) + region) << 10) + (k & 1023u);
}
__device__ __forceinline__ unsigned frozen_load_cg(const unsigned* p) {
  unsigned v;
  asm volatile("ld.global.cg.u32 %0,[%1];" : "=r"(v) : "l"(p) : "memory");
  return v;
}

// Host MUST validate: block=(128,1,1), grid.y=z=1; Visits in {1,8};
// region_words = active_bytes / (64*4), multiple of 1024; allocation has all bytes;
// a is odd, b is nonnegative, inner_repeats in {1,4}, bias/data_class in {0,1};
// each output slot is owned by exactly one CTA job. out and data never alias.
// ClassOnly=true => 32 regions; false => all64, and colored_output MUST be false.
// Label-only control should change HOST labels only; do not add GPU arithmetic.
// Payload/offset interventions change initialized data/base pointer, not this mapping.
template<bool Diag, unsigned Visits, bool ClassOnly>
__global__ void frozen_region_consume(
    const unsigned* __restrict__ data,
    unsigned long long* __restrict__ out,
    FrozenProbeRecord* __restrict__ record,
    unsigned region_words,
    unsigned data_class,
    unsigned bias,
    unsigned a,
    unsigned b,
    unsigned inner_repeats,
    bool colored_output) {
  static_assert(Visits == 1 || Visits == 8, "Only preregistered visit counts");
  constexpr unsigned PerVisit = ClassOnly ? 32u : 64u;
  constexpr unsigned Jobs = PerVisit * Visits;
  __shared__ unsigned long long reduction[128];
  // Compile-time false branches must DCE these diagnostic-only allocations/ops.
  __shared__ unsigned long long begin_ticks;
  __shared__ unsigned begin_sm;
  for (unsigned pos = blockIdx.x; pos < Jobs; pos += gridDim.x) {
    const unsigned job = (a * pos + b) & (Jobs - 1u);
    const unsigned j = job & (PerVisit - 1u);
    const unsigned visit = job / PerVisit;
    unsigned region;
    if constexpr (ClassOnly) region = class_region_0x33(j, data_class, bias);
    else region = j;
    const unsigned logical = (ClassOnly && colored_output) ? data_class * 32u + j : region;
    const unsigned out_index = visit * 64u + logical;
    if constexpr (Diag) {
      if (threadIdx.x == 0) {
        begin_sm = frozen_smid();
        begin_ticks = clock64();
      }
      __syncthreads();
    }
    unsigned long long sum = 0;
    for (unsigned repeat = 0; repeat < inner_repeats; ++repeat) {
      for (unsigned k = threadIdx.x; k < region_words; k += 128u) {
        sum += (unsigned long long)frozen_load_cg(data + physical_word_4k(region, k));
      }
    }
    reduction[threadIdx.x] = sum;
    __syncthreads();
    for (unsigned distance = 64; distance; distance >>= 1) {
      if (threadIdx.x < distance) reduction[threadIdx.x] += reduction[threadIdx.x + distance];
      __syncthreads();
    }
    if (threadIdx.x == 0) {
      out[out_index] = reduction[0];
      if constexpr (Diag) {
        record[out_index] = {clock64() - begin_ticks, reduction[0],
                             begin_sm, frozen_smid(), region, visit};
      }
    }
    // Required even with no diagnostics: no next job may overwrite shared sums early.
    __syncthreads();
  }
}
