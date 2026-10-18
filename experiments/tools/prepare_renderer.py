"""Materialize a narrow, reviewable tile-index transformation from locked upstream."""
from pathlib import Path
import shutil,difflib,json,hashlib
ROOT=Path(__file__).resolve().parents[1];source=ROOT/'vendor/diff-gaussian-rasterization';dest=ROOT/'build/renderer_source';dest.mkdir(parents=True,exist_ok=True)
for p in (source/'cuda_rasterizer').iterdir():
 if p.is_file():shutil.copy2(p,dest/p.name)
original=(dest/'forward.cu').read_text();start=original.index('template <uint32_t CHANNELS>\n__global__ void __launch_bounds__(BLOCK_X * BLOCK_Y)\nrenderCUDA(');end=original.index('\nvoid FORWARD::render(',start)
mapped=original[start:end].replace('renderCUDA(','renderMappedCUDA(',1).replace('float* __restrict__ out_color)','float* __restrict__ out_color, const int* table, int task_count, unsigned* visits)',1)
mapped=mapped.replace('// Identify current tile and associated min/max pixel range.','for(int task_index=blockIdx.x;task_index<task_count;task_index+=gridDim.x){\n const unsigned tile=table[task_index];\n if(visits && threadIdx.x==0 && threadIdx.y==0) atomicAdd(visits+tile,1);\n // Identify current tile and associated min/max pixel range.',1)
mapped=mapped.replace('block.group_index().x * BLOCK_X, block.group_index().y * BLOCK_Y','(tile % horizontal_blocks) * BLOCK_X, (tile / horizontal_blocks) * BLOCK_Y')
mapped=mapped.replace('ranges[block.group_index().y * horizontal_blocks + block.group_index().x]','ranges[tile]')
pos=mapped.rfind('}');mapped=mapped[:pos]+' block.sync();\n }\n'+mapped[pos:]
body=original[:end]+ '\n'+mapped+original[end:]
marker='\trenderCUDA<NUM_CHANNELS> << <grid, block >> > ('
hook='''\tec_last_args={ranges,point_list,W,H,means2D,colors,conic_opacity,final_T,n_contrib,bg_color,out_color};
 ec_before_render();
 if(ec_active){ec_dispatch(ec_last_args);return;}
'''
body=body.replace(marker,hook+marker,1)
body='#include "render_dispatch.h"\n'+body
body+='''
void ec_launch_mapped(const RenderArgs&a,const int*table,int count,int grid,cudaStream_t stream,unsigned*visits){
 renderMappedCUDA<NUM_CHANNELS><<<grid,dim3(BLOCK_X,BLOCK_Y),0,stream>>>(a.ranges,a.point_list,a.width,a.height,a.means2D,a.colors,a.conic,a.final_T,a.n_contrib,a.background,a.out_color,table,count,visits);
}
int ec_render_occupancy(){int n=0;cudaOccupancyMaxActiveBlocksPerMultiprocessor(&n,renderMappedCUDA<NUM_CHANNELS>,BLOCK_X*BLOCK_Y,0);return n;}
'''
(dest/'forward.cu').write_text(body)
(ROOT/'preregistration/renderer.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),body.splitlines(True),fromfile='upstream/forward.cu',tofile='transformed/forward.cu')))
print('Prepared renderer with untouched Native kernel, transformed complete-tile loop, end barrier; upstream preprocessing/binning/sort unchanged')
