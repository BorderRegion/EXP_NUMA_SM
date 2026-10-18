#include "../reference/host_schedule.hpp"
#include <cassert>
#include <cstddef>
using namespace t10_diag;
int main() {
 for (auto mode:{Condition::BurstSlot0,Condition::BurstRing4,Condition::ReadySlot0,Condition::ReadyRing4}) {
  unsigned hist[4]={};int ready_count=0,enqueues=0,drains=0;std::uint64_t cursor=0;
  for(int b=0;b<3;b++)execute_condition_chunk(mode,cursor,64,4,
    [&](unsigned s){hist[s]++;enqueues++;},[&](){drains++;},[&](unsigned s){hist[s]++;ready_count++;});
  const bool burst=mode==Condition::BurstSlot0||mode==Condition::BurstRing4;
  const bool ring=mode==Condition::BurstRing4||mode==Condition::ReadyRing4;
  assert(cursor==192);assert(enqueues==(burst?192:0));assert(ready_count==(burst?0:192));assert(drains==(burst?3:0));
  if(ring)for(auto n:hist)assert(n==48);else assert(hist[0]==192 && hist[1]==0);
 }
 Stamp s{0,1000,2000,4000,5000};assert(s.ordered());assert(s.cpu_ready_us()==4);
 std::uint64_t c=0;bool threw=false;
 try {execute_condition_chunk(Condition::ReadyRing4,c,1,0,[](unsigned){},[]{},[](unsigned){});}catch(const std::invalid_argument&){threw=true;}
 assert(threw);return 0;
}
