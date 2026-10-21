#include "../tools/worker_range.hpp"
#include <iostream>
int main() {
  long long checked=0;
  for (int B : {1,4,8}) for (int HK : {4,8}) for (int W : {16,32,64}) {
    long long N=1LL*B*HK*W;
    long long cuts[6]={0,N/5,2*N/5,3*N/5,4*N/5,N};
    for(int g=0;g<5;g++) for(long long i=0;i<cuts[g+1]-cuts[g];i++) {
      auto t=decode_task(i,cuts[g],cuts[g+1]-cuts[g],W,HK);
      if(t.task != (t.batch*HK+t.kv_head)*W+t.worker || t.batch>=B) return 1;
      checked++;
    }
  }
  bool caught=false;
  try {decode_task(1,0,1,32,8);} catch(const std::invalid_argument&) {caught=true;}
  if(!caught) return 2;
  std::cout << "CPU mapping checks=" << checked << "\n";
}
