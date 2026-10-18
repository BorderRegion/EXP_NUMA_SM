"""Copy local CUTLASS bodies with narrowly scoped address/CTA ownership edits."""
from pathlib import Path
import difflib,hashlib,json
root=Path(__file__).resolve().parents[1];vendor=root.parent/'op-fused/vendor/cutlass/include'
p=vendor/'cutlass/gemm/kernel/gemm_splitk_parallel.h';original=p.read_text();s=original
s=s.replace('struct GemmSplitKParallel {','struct PcGemmSplitKParallel {').replace('GemmSplitKParallel() { }','PcGemmSplitKParallel() { }')
s=s.replace('void operator()(Params const &params, SharedStorage &shared_storage) {','void operator()(Params const &params, SharedStorage &shared_storage, int owner, int owners, int slab, int reverse_tasks, unsigned *trace, unsigned generation) {')
a='''    cutlass::gemm::GemmCoord threadblock_tile_offset =
        threadblock_swizzle.get_tile_offset(params.swizzle_log_tile);'''
b='''    int total_tiles = params.grid_tiled_shape.m() * params.grid_tiled_shape.n();
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
#endif'''
assert a in s;s=s.replace(a,b)
s=s.replace('''    threadblock_tile_offset =
        threadblock_swizzle.get_tile_offset(params.swizzle_log_tile);''','    // Preserve the logical tile selected before the unchanged MMA body.')
a='''    // Tile iterator writing to output tile
    typename Epilogue::OutputTileIterator iterator_D(
      params.params_D,
      params.ref_D.data(),
      params.problem_size.mn(),
      thread_idx,
      threadblock_offset
    );

    iterator_D.add_pointer_offset(params.splitk_slice_stride * threadblock_tile_offset.k());'''
b='''    // Producer writes the final workspace address directly; no packing pass.
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
    typename Epilogue::OutputTileIterator iterator_D(out_params, out_pointer, out_extent, thread_idx, threadblock_offset);'''
assert a in s;s=s.replace(a,b);(root/'adapters/pc_gemm_splitk_parallel.h').write_text(s)
(root/'patches/producer.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile=str(p),tofile='adapters/pc_gemm_splitk_parallel.h')))
p=vendor/'cutlass/reduction/kernel/reduce_split_k.h';original=p.read_text();s=original.replace('class ReduceSplitK {','class PcReduceSplitK {')
s=s.replace('void operator()(Params const &params, SharedStorage &storage) {','void operator()(Params const &params, SharedStorage &storage, int BM, int BN, int owner, int owners, int slab, int reverse_tasks, unsigned *trace, unsigned generation) {')
a='''    MatrixCoord thread_offset(
      MatrixCoord::Index(int(blockIdx.x) * Shape::kRow + threadIdx.y),
      MatrixCoord::Index(int(blockIdx.y) * Shape::kColumn + threadIdx.x * kElementsPerAccess)
    );'''
b='''    int tn = (params.problem_size.column()+BN-1)/BN;
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
#endif'''
assert a in s;s=s.replace(a,b)
a='''    char const *workspace_ptr = 
      reinterpret_cast<char const *>(
        params.workspace.data() + params.workspace.offset(thread_offset));'''
b='''    char const *workspace_ptr = reinterpret_cast<char const *>(params.workspace.data() +
      (slab ? (int64_t(tile)*params.partitions*BM*BN + lr*BN+lc) : params.workspace.offset(thread_offset)));
    size_t step = slab ? sizeof(ElementWorkspace)*BM*BN : params.partition_stride;'''
assert a in s;s=s.replace(a,b).replace('workspace_ptr += params.partition_stride;','workspace_ptr += step;')
(root/'adapters/pc_reduce_split_k.h').write_text(s)
(root/'patches/reducer.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile=str(p),tofile='adapters/pc_reduce_split_k.h')))
print('two adapters generated; MMA and reduction arithmetic unchanged')
