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
  \brief Kernel performing a reduction over densely packed tensors in global memory
*/

#pragma once

#include "cutlass/cutlass.h"
#include "cutlass/tensor_ref.h"
#include "cutlass/numeric_types.h"
#include "cutlass/array.h"
#include "cutlass/functional.h"
#include "cutlass/matrix_shape.h"
#include "cutlass/numeric_conversion.h"

#include "cutlass/layout/matrix.h"

/////////////////////////////////////////////////////////////////////////////////////////////////

namespace cutlass {
namespace reduction {
namespace kernel {

/////////////////////////////////////////////////////////////////////////////////////////////////

template <
  typename Shape_,              ///< shape of CTA        (concept: MatrixShape)
  typename OutputOp_ ,          ///< output operator     (concept: epilogue::thread operator)
  typename ReductionOp_,        ///< reduction operator  (concept: ReductionOperator)
  int PartitionsPerStage = 4    ///< number of partitions to issue 
>
class PcReduceSplitK {
public:

  using Shape = Shape_;
  using ReductionOp = ReductionOp_;
  using OutputOp = OutputOp_;
  static int const kElementsPerAccess = OutputOp::kCount;
  static int const kPartitionsPerStage = PartitionsPerStage;

  using ElementWorkspace = typename ReductionOp::Element;
  using ElementAccumulator = typename ReductionOp::ElementAccumulator;
  using ElementOutput = typename OutputOp::ElementOutput;

  using WorkspaceTensorRef = TensorRef<ElementWorkspace, layout::RowMajor>;
  using OutputTensorRef = TensorRef<ElementOutput, layout::RowMajor>;
  using StrideIndex = typename WorkspaceTensorRef::Layout::Stride::Index;

  using FragmentWorkspace = AlignedArray<ElementWorkspace, kElementsPerAccess>;
  using FragmentAccumulator = Array<ElementAccumulator, kElementsPerAccess>;
  using FragmentOutput = AlignedArray<ElementOutput, kElementsPerAccess>;

  //
  // Types
  //

  /// Params structure
  struct Params {

    MatrixCoord problem_size;
    int partitions;
    size_t partition_stride;
    WorkspaceTensorRef workspace;
    OutputTensorRef destination;
    OutputTensorRef source;
    typename OutputOp::Params output;
    typename ReductionOp::Params reduction;

    //
    // Methods
    //

    CUTLASS_HOST_DEVICE
    Params() { }

    CUTLASS_HOST_DEVICE
    Params(
      MatrixCoord problem_size_,
      int partitions_,
      size_t partition_stride_,
      WorkspaceTensorRef workspace_,
      OutputTensorRef destination_,
      OutputTensorRef source_,
      typename OutputOp::Params output_ = typename OutputOp::Params(),
      typename ReductionOp::Params reduction_ = typename ReductionOp::Params()
    ):
      problem_size(problem_size_),
      partitions(partitions_),
      partition_stride(sizeof(FragmentWorkspace) * partition_stride_ / kElementsPerAccess),
      workspace(workspace_),
      destination(destination_),
      source(source_),
      output(output_),
      reduction(reduction_) {

    }
  };

  struct SharedStorage { };


public:

  /// Computes the grid size given a chosen threadblock shape
  CUTLASS_HOST_DEVICE
  static dim3 grid_shape(
    cutlass::MatrixCoord problem_size) {

    return dim3(
      (problem_size.row() + Shape::kRow - 1) / Shape::kRow,
      (problem_size.column() + Shape::kColumn - 1) / Shape::kColumn);
  }

  /// Determines the threadblock shape
  CUTLASS_HOST_DEVICE
  static dim3 block_shape() {
    return dim3(Shape::kColumn / kElementsPerAccess, Shape::kRow);
  }

  /// Perform a reduction
  CUTLASS_DEVICE
  void operator()(Params const &params, SharedStorage &storage, int BM, int BN, int owner, int owners, int slab, int reverse_tasks, unsigned *trace, unsigned generation) {

    // Determine CTA position
    int tn = (params.problem_size.column()+BN-1)/BN;
    int total = ((params.problem_size.row()+BM-1)/BM)*tn;
    int cut=(total+1)/2;
    int count=owners==2 ? (owner==0 ? cut : total-cut) : total;
    int rows=(BM+Shape::kRow-1)/Shape::kRow, cols=(BN+Shape::kColumn-1)/Shape::kColumn;
    int local=int(blockIdx.x)/(rows*cols), sub=int(blockIdx.x)%(rows*cols);
    if(reverse_tasks) local=count-1-local;
    int tile=(owners==2 && owner==1 ? cut : 0)+local;
    int lr=(sub/cols)*Shape::kRow+threadIdx.y;
    int lc=(sub%cols)*Shape::kColumn+threadIdx.x*kElementsPerAccess;
    if(lr>=BM || lc>=BN) return;
    MatrixCoord thread_offset((tile/tn)*BM+lr,(tile%tn)*BN+lc);
#if PC_DIAG
    if(threadIdx.x==0 && threadIdx.y==0) {
      unsigned sm; asm volatile("mov.u32 %0, %smid;" : "=r"(sm));
      unsigned *r=trace+(total*params.partitions + tile*rows*cols+sub)*5;
      r[0]=sm; r[1]=tile; r[2]=0xffffffffu; r[3]=owner; r[4]=generation;
    }
#endif

    // One guard conditional
    if (!(thread_offset.row() < params.problem_size.row() && 
          thread_offset.column() < params.problem_size.column())) {

      return;
    }


    ReductionOp reduction_op(params.reduction);

    FragmentAccumulator accumulator;

    accumulator.clear();  
    
    //
    // Load the first slice
    //

    char const *workspace_ptr = reinterpret_cast<char const *>(params.workspace.data() +
      (slab ? (int64_t(tile)*params.partitions*BM*BN + lr*BN+lc) : params.workspace.offset(thread_offset)));
    size_t step = slab ? sizeof(ElementWorkspace)*BM*BN : params.partition_stride;

    FragmentWorkspace workspace_frag[kPartitionsPerStage];
    
    //
    // Construct the output operator
    //
    
    OutputOp output_op(params.output);

    //
    // Load and accumulate with a simple batched loading sequence.
    //

    CUTLASS_PRAGMA_NO_UNROLL
    for (int k = 0; k < params.partitions; k += kPartitionsPerStage) {

      CUTLASS_PRAGMA_UNROLL
      for (int i = 0; i < kPartitionsPerStage; ++i) {
        if (k + i < params.partitions) {
          workspace_frag[i] = *reinterpret_cast<FragmentWorkspace const *>(workspace_ptr);
          workspace_ptr += step;
        }
      }   

      CUTLASS_PRAGMA_UNROLL
      for (int i = 0; i < kPartitionsPerStage; ++i) {
        if (k + i < params.partitions) {
          accumulator = reduction_op(accumulator, workspace_frag[i]);
        }
      }
    }

    //
    // Conditionally load the source
    //

    FragmentOutput source_frag;

    source_frag.clear();

    FragmentOutput const *source_ptr = reinterpret_cast<FragmentOutput const *>(
      params.source.data() + params.source.offset(thread_offset));

    if (output_op.is_source_needed()) {
      reinterpret_cast<FragmentOutput &>(source_frag) = *source_ptr;
    }
    
    //
    // Compute the output
    //

    typename OutputOp::FragmentOutput output_frag = output_op(accumulator, source_frag);

    //
    // Store
    //

    FragmentOutput *dest_ptr = reinterpret_cast<FragmentOutput *>(
      params.destination.data() + params.destination.offset(thread_offset));

    *dest_ptr = reinterpret_cast<FragmentOutput const &>(output_frag);
  }
};

/////////////////////////////////////////////////////////////////////////////////////////////////

} // namespace kernel
} // namespace reduction
} // namespace cutlass
