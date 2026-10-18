#pragma once
#include "cutlass/gemm/device/gemm_splitk_parallel.h"
#include "cutlass/gemm/device/gemm.h"
#include "pc_gemm_splitk_parallel.h"
#include "pc_reduce_split_k.h"
using Half=cutlass::half_t;
using Row=cutlass::layout::RowMajor; using Col=cutlass::layout::ColumnMajor;
using Out=cutlass::epilogue::thread::LinearCombination<float,4,float,float>;
using Convert=cutlass::epilogue::thread::Convert<float,4,float>;
using Add=cutlass::reduction::thread::ReduceAdd<float,float,4>;
using Red=cutlass::reduction::kernel::PcReduceSplitK<cutlass::MatrixShape<4,128>,Out,Add>;
using NativeRed=cutlass::reduction::kernel::ReduceSplitK<cutlass::MatrixShape<4,128>,Out,Add>;
template<int BM,int BN,int WM,int WN> struct Recipe {
 using TB=cutlass::gemm::GemmShape<BM,BN,32>; using Warp=cutlass::gemm::GemmShape<WM,WN,32>; using Ins=cutlass::gemm::GemmShape<16,8,8>;
 using Split=cutlass::gemm::device::GemmSplitKParallel<Half,Row,Half,Col,float,Row,float,cutlass::arch::OpClassTensorOp,cutlass::arch::Sm75,TB,Warp,Ins,Out,Convert,Add>;
 using Native=typename Split::GemmKernel;
 using P=cutlass::gemm::kernel::PcGemmSplitKParallel<typename Native::Mma,typename Native::Epilogue,typename Native::ThreadblockSwizzle>;
 using Normal=cutlass::gemm::device::Gemm<Half,Row,Half,Col,float,Row,float,cutlass::arch::OpClassTensorOp,cutlass::arch::Sm75,TB,Warp,Ins,Out>;
 using S1=typename Normal::GemmKernel;
};
using R0=Recipe<32,64,32,32>;using R1=Recipe<64,64,32,32>;using R2=Recipe<64,128,32,64>;using R3=Recipe<128,128,64,64>;
