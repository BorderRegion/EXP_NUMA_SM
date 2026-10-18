#pragma once
#include <stdint.h>
struct ProbeState { uint32_t index, sum; };
struct ProbeRecord { uint64_t ticks; uint32_t sm_begin,sm_end,first,last,sum,loads; };
struct TaskRecord { uint64_t ticks; uint32_t sm_begin,sm_end,visits,pad; };
