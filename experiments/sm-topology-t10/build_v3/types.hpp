#pragma once
#include <stdint.h>
constexpr int NSM=56;
// The roster is recorded for every launch, not inferred from blockIdx.
struct Record {
 uint64_t ns,cycles,peer_ns,peer_cycles;
 uint32_t src_begin,src_end,dst_begin,dst_end,errors,src_value,dst_value,reserved;
 uint16_t roster_begin[NSM],roster_end[NSM];
};
static_assert(sizeof(Record)==288);
struct Plan {int kind,round,mode,slot,src,dst,steps,region,policy;};
