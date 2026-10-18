#pragma once
#include "cutlass/gemm/kernel/gemm_grouped_problem_visitor.h"

namespace cutlass { namespace gemm { namespace kernel {
// Inherit CUTLASS problem discovery, prefix state and worker advance unchanged.
// Only translate the native ordinal to N-panel-major output coordinates.
// No extra fields, total reduction, packet state, policy parameters or sideband.
template<typename Shape, int Threads>
struct Q1MinimalVisitor : GemmGroupedProblemVisitor<
    Shape, GroupScheduleMode::kDeviceOnly, Threads, Threads, false> {
  using Base = GemmGroupedProblemVisitor<
      Shape, GroupScheduleMode::kDeviceOnly, Threads, Threads, false>;
  using Params = typename Base::Params;
  using SharedStorage = typename Base::SharedStorage;
  CUTLASS_DEVICE Q1MinimalVisitor(Params const &p, SharedStorage &s, int32_t block)
      : Base(p, s, block) {}
  CUTLASS_DEVICE int32_t threadblock_idx() const {
    auto grid = this->grid_shape(this->problem_size());
    int r = Base::threadblock_idx();
    return (r % grid.m()) * grid.n() + r / grid.m();
  }
};
}}}
