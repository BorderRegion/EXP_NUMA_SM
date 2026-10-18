#pragma once
#include <stdint.h>
struct ProbeRecord {
 uint64_t ticks, sum;
 uint32_t sm_begin, sm_end, region, logical_position, first, last, loads, reserved;
};
