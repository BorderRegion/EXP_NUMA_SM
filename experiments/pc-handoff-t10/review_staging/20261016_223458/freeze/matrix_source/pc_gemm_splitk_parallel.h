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
    \brief Template for GEMM performing a reduction over K partitions in parallel.
*/

#pragma once

#include "cutlass/cutlass.h"

#include "cutlass/gemm/gemm.h"
#include "cutlass/matrix_coord.h"

/////////////////////////////////////////////////////////////////////////////////////////////////

namespace cutlass {
namespace gemm {
namespace kernel {

/////////////////////////////////////////////////////////////////////////////////////////////////

template <
  typename Mma_,                  ///! Threadblock-scoped matrix multiply-accumulate 
  typename Epilogue_,             ///! Epilogue
  typename ThreadblockSwizzle_    ///! Threadblock swizzling function
>
struct PcGemmSplitKParallel {

  using Mma = Mma_;
  using Epilogue = Epilogue_;
  using OutputOp = typename Epilogue::OutputOp;
  using ThreadblockSwizzle = ThreadblockSwizzle_;

  /// Warp count (concept: GemmShape)
  using WarpCount = typename Mma::WarpCount;
  static int const kThreadCount = 32 * WarpCount::kCount;

  static int const kAlignmentK = Mma::Operator::Shape::kK;

  /// Parameters structure
  struct Params {
    cutlass::gemm::GemmCoord problem_size;
    cutlass::gemm::GemmCoord grid_tiled_shape;
    int swizzle_log_tile;
    typename Mma::IteratorA::Params params_A;
    typename Mma::IteratorA::TensorRef ref_A;
    typename Mma::IteratorB::Params params_B;
    typename Mma::IteratorB::TensorRef ref_B;
    typename Epilogue::OutputTileIterator::Params params_D;
    typename Epilogue::OutputTileIterator::TensorRef ref_D;
    typename OutputOp::Params output_op;
    int64_t splitk_slice_stride;
    int gemm_k_size;

    //
    // Methods
    //

    CUTLASS_HOST_DEVICE
    Params(): swizzle_log_tile(0) { }

    CUTLASS_HOST_DEVICE
    Params(
      cutlass::gemm::GemmCoord const & problem_size,
      cutlass::gemm::GemmCoord const & grid_tiled_shape,
      typename Mma::IteratorA::TensorRef ref_A,
      typename Mma::IteratorB::TensorRef ref_B,
      typename Epilogue::OutputTileIterator::TensorRef ref_D,
      typename OutputOp::Params output_op,
      int64_t splitk_slice_stride
    ):
      problem_size(problem_size),
      grid_tiled_shape(grid_tiled_shape),
      swizzle_log_tile(ThreadblockSwizzle().get_log_tile(grid_tiled_shape)),
      params_A(ref_A.layout()),
      ref_A(ref_A),
      params_B(ref_B.layout()),
      ref_B(ref_B),
      params_D(ref_D.layout()),
      ref_D(ref_D),
      output_op(output_op),
      splitk_slice_stride(splitk_slice_stride) {

      int full_gemm_k_iterations = problem_size.k() / Mma::Shape::kK;
      int gemm_k_iterations = full_gemm_k_iterations / grid_tiled_shape.k();

      gemm_k_size = gemm_k_iterations * Mma::Shape::kK;
    }
  };

  /// Shared memory storage structure
  union SharedStorage {
    typename Mma::SharedStorage main_loop;
    typename Epilogue::SharedStorage epilogue;
  };

  //
  // Methods
  //

  CUTLASS_HOST_DEVICE
  PcGemmSplitKParallel() { } 

  /// Executes one GEMM
  CUTLASS_DEVICE
  void operator()(Params const &params, SharedStorage &shared_storage, int owner, int owners, int slab, int reverse_tasks, unsigned *trace, unsigned generation) {

    // Compute threadblock location
    ThreadblockSwizzle threadblock_swizzle;

    int total_tiles = params.grid_tiled_shape.m() * params.grid_tiled_shape.n();
    int cut = (total_tiles + 1) / 2;
    int base = owners == 2 && owner == 1 ? cut : 0;
    int count = owners == 2 ? (owner == 0 ? cut : total_tiles - cut) : total_tiles;
    int local = reverse_tasks ? count - 1 - int(blockIdx.x) : int(blockIdx.x);
    int tile = base + local;
    cutlass::gemm::GemmCoord threadblock_tile_offset(tile / params.grid_tiled_shape.n(), tile % params.grid_tiled_shape.n(), blockIdx.z);
#if PC_DIAG
    if (threadIdx.x == 0) {
      unsigned sm; asm volatile("mov.u32 %0, %smid;" : "=r"(sm));
      unsigned *r = trace + (tile * params.grid_tiled_shape.k() + blockIdx.z) * 5;
      r[0]=sm; r[1]=tile; r[2]=blockIdx.z; r[3]=owner; r[4]=generation;
    }
#endif

    // Early exit if CTA is out of range
    if (params.grid_tiled_shape.m() <= threadblock_tile_offset.m() ||
      params.grid_tiled_shape.n() <= threadblock_tile_offset.n()) {

      return;
    }

    // Compute initial location in logical coordinates
    cutlass::MatrixCoord tb_offset_A{
      threadblock_tile_offset.m() * Mma::Shape::kM,
      threadblock_tile_offset.k() * params.gemm_k_size,
    };

    cutlass::MatrixCoord tb_offset_B{
      threadblock_tile_offset.k() * params.gemm_k_size,
      threadblock_tile_offset.n() * Mma::Shape::kN
    };

    // Problem size is a function of threadblock index in the K dimension
    int problem_size_k;
    if (threadblock_tile_offset.k() + 1 == params.grid_tiled_shape.k()) {
      problem_size_k = params.problem_size.k();
    }
    else {
      problem_size_k = (threadblock_tile_offset.k() + 1) * params.gemm_k_size;
    }

    // Compute threadblock-scoped matrix multiply-add
    int gemm_k_iterations = (problem_size_k - tb_offset_A.column() + Mma::Shape::kK - 1) / Mma::Shape::kK;

    // Compute position within threadblock
    int thread_idx = threadIdx.x;

    // Construct iterators to A and B operands
    typename Mma::IteratorA iterator_A(
      params.params_A,
      params.ref_A.data(),
      {params.problem_size.m(), problem_size_k},
      thread_idx,
      tb_offset_A);

    typename Mma::IteratorB iterator_B(
      params.params_B,
      params.ref_B.data(),
      {problem_size_k, params.problem_size.n()},
      thread_idx,
      tb_offset_B);

    int warp_idx = threadIdx.x / 32;
    int lane_idx = threadIdx.x % 32;


    //
    // Main loop
    //

    // Construct thread-scoped matrix multiply
    Mma mma(shared_storage.main_loop, thread_idx, warp_idx, lane_idx);

    typename Mma::FragmentC accumulators;

    accumulators.clear();

    mma(gemm_k_iterations, accumulators, iterator_A, iterator_B, accumulators);

    //
    // Epilogue
    //

    OutputOp output_op(params.output_op);

    //
    // Masked tile iterators constructed from members
    //

    // Preserve the logical tile selected before the unchanged MMA body.

    //assume identity swizzle
    MatrixCoord threadblock_offset(
      threadblock_tile_offset.m() * Mma::Shape::kM,
      threadblock_tile_offset.n() * Mma::Shape::kN
    );

    // Producer writes the final workspace address directly; no packing pass.
    auto out_params = params.params_D;
    auto out_pointer = params.ref_D.data();
    auto out_extent = params.problem_size.mn();
    if (slab) {
      out_params = typename Epilogue::OutputTileIterator::Params(cutlass::layout::RowMajor(Mma::Shape::kN));
      out_pointer += (int64_t(tile) * params.grid_tiled_shape.k() + threadblock_tile_offset.k()) * Mma::Shape::kM * Mma::Shape::kN;
      out_extent = MatrixCoord(min(Mma::Shape::kM, params.problem_size.m()-threadblock_offset.row()), min(Mma::Shape::kN, params.problem_size.n()-threadblock_offset.column()));
      threadblock_offset = MatrixCoord(0,0);
    } else {
      out_pointer += params.splitk_slice_stride * threadblock_tile_offset.k();
    }
    typename Epilogue::OutputTileIterator iterator_D(out_params, out_pointer, out_extent, thread_idx, threadblock_offset);

    // Execute the epilogue
    Epilogue epilogue(
      shared_storage.epilogue, 
      thread_idx, 
      warp_idx, 
      lane_idx);

    // Run efficient epilogue
    epilogue(output_op, iterator_D, accumulators, iterator_D);
  }
};

/////////////////////////////////////////////////////////////////////////////////////////////////

} // namespace kernel
} // namespace gemm
} // namespace cutlass
