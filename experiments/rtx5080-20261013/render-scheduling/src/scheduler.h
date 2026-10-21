#pragma once
#include <cuda_runtime.h>
#include <cstdint>
struct ScheduleStats {double cpu_plan_ms=0;int tiles=0,bundles=0,cap_hits=0;uint64_t list_entries=0;float preprocess_ms=0,scan_ms=0,sort_ms=0,build_ms=0,render_ms=0;};
struct ScheduleConfig {int policy=0,executor=0,q=8,k=4,workers=0;double alpha=.5;size_t l2=0;};
extern ScheduleConfig schedule_config;
extern ScheduleStats schedule_stats;
extern cudaEvent_t stage_events[6];
void schedule_init();
void schedule_times();
void schedule_prepare(int n,int gx,const uint2* ranges,const uint32_t* point_list);
void schedule_render(dim3 grid,dim3 block,const uint2*,const uint32_t*,int,int,const float2*,const float*,const float4*,float*,uint32_t*,const float*,float*);
int schedule_occupancy();
extern uint32_t *schedule_ids,*schedule_offsets,*schedule_counter;
extern int schedule_bundle_count;
