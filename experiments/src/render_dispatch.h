#pragma once
#include <cuda_runtime_api.h>
struct RenderArgs{
 const uint2* ranges;const unsigned* point_list;int width,height;
 const float2* means2D;const float* colors;const float4* conic;
 float* final_T;unsigned* n_contrib;const float* background;float* out_color;
};
extern bool ec_active;
extern RenderArgs ec_last_args;
void ec_before_render();
void ec_dispatch(const RenderArgs&);
void ec_launch_mapped(const RenderArgs&,const int* table,int count,int grid,cudaStream_t stream,unsigned* visits);
int ec_render_occupancy();
void ec_digest(const RenderArgs&,unsigned long long* partial);
