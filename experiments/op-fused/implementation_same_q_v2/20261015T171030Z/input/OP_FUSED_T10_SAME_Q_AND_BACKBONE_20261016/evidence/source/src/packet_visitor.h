/***************************************************************************************************
 * Copyright (c) 2017 - 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 * list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 * this list of conditions and the following disclaimer in the documentation
 * and/or other materials provided with the distribution.
 *
 * 3. Neither the name of the copyright holder nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 **************************************************************************************************/

/*! \file
    \brief Base scheduler for grouped problems
*/

#pragma once
// Adapted from CUTLASS device-only GroupedProblemVisitor. Only work-unit counting,
// within-packet progression, and output tile ordinal mapping are changed.
#include "cutlass/gemm/kernel/gemm_grouped_problem_visitor.h"
namespace cutlass { namespace gemm { namespace kernel {
template <typename ProblemSizeHelper,
          typename ThreadblockShape,
          int PrefetchTileCount,
          int ThreadCount, bool Full>
struct OpPacketVisitor: public BaseGroupedProblemVisitor<ProblemSizeHelper, ThreadblockShape> {
  using Base = BaseGroupedProblemVisitor<ProblemSizeHelper, ThreadblockShape>;
  struct Params : Base::Params {
    int q_cap=1, target_waves=1, work_budget=128;
    const int *sideband_total=nullptr;
    CUTLASS_HOST_DEVICE Params() = default;
    CUTLASS_HOST_DEVICE Params(GemmCoord const *s,int n,void const *w=nullptr,int t=0)
      : Base::Params(s,n,w,t) {}
  };
  int q_cap_, waves_, budget_, total_=0, within_=0;
  CUTLASS_DEVICE int q_for(GemmCoord const &problem, GemmCoord const &grid) const {
    int cap=min(q_cap_,max(1,grid.m()));
    if (Full) {
      cap=min(cap,max(1,total_/(int(gridDim.x)*waves_)));
      cap=min(cap,max(1,budget_/((problem.k()+ThreadblockShape::kK-1)/ThreadblockShape::kK)));
    }
    return cap>=4?4:(cap>=2?2:1);
  }
  CUTLASS_DEVICE int packet_count(GemmCoord const &problem, GemmCoord const &grid) const {
    if (!grid.m() || !grid.n()) return 0;
    int q=q_for(problem,grid);return grid.n()*((grid.m()+q-1)/q);
  }
  CUTLASS_DEVICE int32_t threadblock_idx() const {
    GemmCoord p=this->problem_size(),g=this->grid_shape(p);
    int q=q_for(p,g),pp=(g.m()+q-1)/q,idx=this->tile_idx-this->problem_tile_start;
    int n=idx/pp,m=(idx%pp)*q+within_;
    return m*g.n()+n;
  }
  CUTLASS_DEVICE void advance(int32_t grid_size) {
    GemmCoord p=this->problem_size(),g=this->grid_shape(p);
    int q=q_for(p,g),pp=(g.m()+q-1)/q,idx=this->tile_idx-this->problem_tile_start;
    int len=min(q,g.m()-(idx%pp)*q);
    if (++within_>=len) {within_=0;Base::advance(grid_size);}
  }
  static int const kThreadCount = ThreadCount;
  static bool const kRequiresPrecomputation = false;
  static int const kThreadsPerWarp = 32;

  struct SharedStorage {};

  // Final tile of the problem loaded by this thread. Each thread will hold
  // a separate value.
  int32_t problem_ending_tile;

  SharedStorage &shared_storage;

  //
  // Methods
  //
  CUTLASS_DEVICE
  OpPacketVisitor(
    Params const &params_,
    SharedStorage &shared_storage_,
    int32_t block_idx
  ): Base(params_, block_idx),
  problem_ending_tile(0),
  shared_storage(shared_storage_)
  {
    q_cap_=params_.q_cap;waves_=params_.target_waves;budget_=params_.work_budget;
    if (Full) {
      if (params_.sideband_total) total_=*params_.sideband_total;
      else {
        int lane=threadIdx.x%32,sum=0;
        for (int e=lane;e<params_.problem_count;e+=32) {
          GemmCoord p=params_.problem_sizes[e];this->possibly_transpose_problem(p);
          GemmCoord g=this->grid_shape(p);sum+=g.m()*g.n();
        }
        for (int offset=16;offset>0;offset/=2) sum+=__shfl_down_sync(0xffffffff,sum,offset);
        total_=__shfl_sync(0xffffffff,sum,0);
      }
    }
    this->problem_idx = -1 * kThreadsPerWarp;
    this->problem_tile_start = 0;
  }

  CUTLASS_DEVICE
  bool next_tile() {
    if (within_) return true;
    // Check whether the tile to compute is within the range of the current problem.
    int32_t problem_tile_end = __shfl_sync(0xffffffff, problem_ending_tile, this->problem_idx % kThreadsPerWarp);
    if (this->tile_idx < problem_tile_end) {
      return true;
    }

    // Check whether the tile to compute is within the current group of problems fetched by the warp.
    // The last tile for this group is the final tile of the problem held by the final thread in the warp.
    int32_t group_tile_end = __shfl_sync(0xffffffff, problem_ending_tile, kThreadsPerWarp-1);

    // Keep the starting problem for this group in `problem_idx`. This is done to reduce
    // register pressure. The starting problem for this group is simply the first problem
    // in the group most recently fetched by the warp.
    int32_t &group_problem_start = this->problem_idx;
    group_problem_start = (this->problem_idx / kThreadsPerWarp) * kThreadsPerWarp;

    // Keep the starting tile for this group in `problem_tile_start`. This is done to reduce
    // register pressure.
    int32_t &group_tile_start = this->problem_tile_start;

    // Each thread in the warp processes a separate problem to advance until
    // reaching a problem whose starting tile is less less than tile_idx.
    while (group_tile_end <= this->tile_idx) {
      group_problem_start += kThreadsPerWarp;
      if (group_problem_start > this->params.problem_count) {
        return false;
      }

      // Since `group_tile_start` is a reference to `this->problem_tile_start`, this
      // also sets `this->problem_tile_start`. The fact that `this->problem_tile_start`
      // is also set here is used later in `next_tile`.
      group_tile_start = group_tile_end;

      int lane_idx = threadIdx.x % kThreadsPerWarp;
      int32_t lane_problem = group_problem_start + lane_idx;

      // Compute the number of tiles in the problem assigned to each thread.
      problem_ending_tile = 0;
      if (lane_problem < this->params.problem_count) {
        cutlass::gemm::GemmCoord problem = this->params.problem_sizes[lane_problem];
        this->possibly_transpose_problem(problem);
        cutlass::gemm::GemmCoord grid = this->grid_shape(problem);
        problem_ending_tile = packet_count(problem,grid);
      }

      // Compute a warp-wide inclusive prefix sum to compute the ending tile index of
      // each thread's problem.
      CUTLASS_PRAGMA_UNROLL
      for (int i = 1; i < kThreadsPerWarp; i <<= 1) {
        int32_t val = __shfl_up_sync(0xffffffff, problem_ending_tile, i);
        if (lane_idx >= i) {
          problem_ending_tile += val;
        }
      }

      // The total tile count for this group is now in the final position of the prefix sum
      int32_t tiles_in_group = __shfl_sync(0xffffffff, problem_ending_tile, kThreadsPerWarp-1);

      problem_ending_tile += group_tile_start;
      group_tile_end += tiles_in_group;
    }

    // The next problem to process is the first one that does not have ending tile position
    // that is greater than or equal to tile index.
    int32_t problem_idx_in_group =
        __popc(__ballot_sync(0xffffffff, problem_ending_tile <= this->tile_idx));

    this->problem_idx = group_problem_start + problem_idx_in_group;

    // The starting tile for this problem is the ending tile of the previous problem. In cases
    // where `problem_idx_in_group` is the first problem in the group, we do not need to reset
    // `problem_tile_start`, because it is set to the previous group's ending tile in the while
    // loop above.
    if (problem_idx_in_group > 0) {
      this->problem_tile_start = __shfl_sync(0xffffffff, problem_ending_tile, problem_idx_in_group - 1);
    }

    return true;
  }

  static size_t get_workspace_size(const cutlass::gemm::GemmCoord* host_problem_sizes_ptr,
                                   int32_t problem_count,
                                   int32_t block_count) {
    return 0;
  }

  static void host_precompute(const cutlass::gemm::GemmCoord* host_problem_sizes_ptr,
                              int32_t problem_count,
                              int32_t block_count,
                              void* host_workspace_ptr) {}
};

}}}
