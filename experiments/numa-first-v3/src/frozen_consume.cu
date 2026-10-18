#include "frozen_consumer.cuh"
#ifndef FROZEN_DIAG
#error define FROZEN_DIAG
#endif
extern "C" __global__ void class1(const unsigned* data,unsigned long long* out,FrozenProbeRecord* record,unsigned rw,unsigned dc,unsigned bias,unsigned a,unsigned b,unsigned repeats,bool colored){frozen_region_body<bool(FROZEN_DIAG),1,true>(data,out,record,rw,dc,bias,a,b,repeats,colored);}
extern "C" __global__ void class8(const unsigned* data,unsigned long long* out,FrozenProbeRecord* record,unsigned rw,unsigned dc,unsigned bias,unsigned a,unsigned b,unsigned repeats,bool colored){frozen_region_body<bool(FROZEN_DIAG),8,true>(data,out,record,rw,dc,bias,a,b,repeats,colored);}
extern "C" __global__ void native1(const unsigned* data,unsigned long long* out,FrozenProbeRecord* record,unsigned rw,unsigned dc,unsigned bias,unsigned a,unsigned b,unsigned repeats,bool colored){frozen_region_body<bool(FROZEN_DIAG),1,false>(data,out,record,rw,dc,bias,a,b,repeats,colored);}
