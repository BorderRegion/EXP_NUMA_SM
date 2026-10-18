#pragma once
// CPU integration contract, not a qualified GPU visitor or a GEMM implementation.
// No allocation, task table, launch, synchronization, atomics, or device-to-host copy.
#include <cstdint>

#ifdef __CUDACC__
#define OPF_HD __host__ __device__
#else
#define OPF_HD
#endif

namespace opf {
using u64 = std::uint64_t;
enum class Policy : unsigned { Full, FixedCache, AblationQ1 };
enum class MetadataScope : unsigned { StaticOperator, CurrentDeviceGeneration };

struct NativeMathConfig {
  // Must come from the actual qualified backend, never from SM count alone.
  unsigned tile_m, tile_n, tile_k, stages, threads, active_workers;
  unsigned input_bits, accumulator_bits, output_bits;
  bool split_k;
  const char *backend_commit, *mainloop, *layout, *epilogue;
};
struct ProblemShape { u64 m, n, k; };
struct DeviceProblemView {
  // Pointers to device-resident arrays in a future GPU adapter. CPU tests use host arrays.
  const ProblemShape *shapes;
  const void *const *a, *const *b;
  void *const *c;
  const u64 *lda, *ldb, *ldc, *row_offsets;
  unsigned count;
  u64 generation;
};
struct WorkPolicy {
  Policy kind;
  unsigned q_cap, target_waves;
  u64 work_budget_k_tiles;
};
struct ReadyMetadata {
  u64 total_tiles, generation;
  MetadataScope scope;
  // Readiness is a caller obligation: same-stream producer order or an existing
  // event dependency. A generation tag alone does NOT establish GPU visibility.
};
struct Packet { unsigned expert; u64 n, m_first, length; };

OPF_HD inline u64 ceil_div(u64 a, u64 b) { return a / b + (a % b != 0); }
OPF_HD inline u64 min_value(u64 a, u64 b) { return a < b ? a : b; }
OPF_HD inline u64 at_least_one(u64 a) { return a ? a : 1; }
OPF_HD inline u64 floor_power_two(u64 a) {
  u64 q = 1;
  while (q <= a / 2) q *= 2;
  return q;
}
OPF_HD inline u64 packet_q(const ProblemShape &p, const NativeMathConfig &c,
                          const WorkPolicy &w, const ReadyMetadata &r) {
  const u64 mt = ceil_div(p.m, c.tile_m);
  if (!mt || !p.n) return 0;
  if (w.kind == Policy::AblationQ1) return 1;
  u64 cap = min_value(w.q_cap, mt);
  if (w.kind == Policy::Full) {
    cap = min_value(cap, at_least_one(r.total_tiles /
                     (u64(c.active_workers) * w.target_waves)));
    cap = min_value(cap, at_least_one(w.work_budget_k_tiles /
                     ceil_div(p.k, c.tile_k)));
  }
  return floor_power_two(cap);
}

// O(experts) ordinal decode; no O(tiles) materialized task list. This is a CPU-
// tested specification to connect inside a native visitor, NOT a measured fast
// device implementation. The real warp/device-only search remains to be adapted.
OPF_HD inline bool decode_packet(u64 ordinal, const DeviceProblemView &v,
                                const NativeMathConfig &c, const WorkPolicy &w,
                                const ReadyMetadata &r, Packet &out) {
  if (v.generation != r.generation) return false;
  for (unsigned e = 0; e < v.count; ++e) {
    const auto p = v.shapes[e];
    const u64 q = packet_q(p, c, w, r);
    if (!q) continue;
    const u64 mt = ceil_div(p.m, c.tile_m), nt = ceil_div(p.n, c.tile_n);
    const u64 per_panel = ceil_div(mt, q), count = nt * per_panel;
    if (ordinal < count) {
      const u64 first = (ordinal % per_panel) * q;
      out = Packet{e, ordinal / per_panel, first, min_value(q, mt - first)};
      return true;
    }
    ordinal -= count;
  }
  return false;
}

// Static native-style ordinal progression. Integrator must keep native barriers,
// pipeline resets, pointer updates and MMA/epilogue unchanged for every whole tile.
struct VisitorState { u64 next_ordinal; unsigned stride; };
OPF_HD inline bool next_complete_packet(VisitorState &state, const DeviceProblemView &v,
                                       const NativeMathConfig &c, const WorkPolicy &w,
                                       const ReadyMetadata &r, Packet &out) {
  if (!decode_packet(state.next_ordinal, v, c, w, r, out)) return false;
  state.next_ordinal += state.stride;
  return true;
}
// CORE and BAL intentionally absent: their mappings must come from the real
// backend. producer_sideband is also absent until an existing legal producer is
// identified. No CPU-made dynamic task list may be uploaded as a substitute.
}  // namespace opf
#undef OPF_HD
