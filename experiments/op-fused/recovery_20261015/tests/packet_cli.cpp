#include "adapter_contract.hpp"
#include <iostream>
#include <limits>
#include <vector>

int main() {
  using namespace opf;
  unsigned cases;
  if (!(std::cin >> cases)) return 2;
  while (cases--) {
    unsigned bm,bn,bk,workers,qcap,waves,kind,n;
    u64 budget;
    if (!(std::cin >> bm >> bn >> bk >> workers >> qcap >> waves >> budget >> kind >> n)) return 2;
    if (!bm || !bn || !bk || !workers || !waves || !budget ||
        (qcap!=1 && qcap!=2 && qcap!=4) || kind>2 || n>1000) return 2;
    NativeMathConfig c{bm,bn,bk,0,0,workers,16,32,16,false,
                       "CPU_SYNTHETIC", "NOT_QUALIFIED", "row_major", "NOT_QUALIFIED"};
    WorkPolicy w{static_cast<Policy>(kind),qcap,waves,budget};
    std::vector<ProblemShape> shapes(n);
    u64 total=0;
    for (auto &p:shapes) {
      if (!(std::cin >> p.m >> p.n >> p.k) || !p.k || p.m>1000000 ||
          p.n>1000000 || p.k>1000000) return 2;
      total += ceil_div(p.m,bm)*ceil_div(p.n,bn);
    }
    if (total>1000000) return 2; // Test harness only: bound emitted output.
    DeviceProblemView v{shapes.data(),nullptr,nullptr,nullptr,nullptr,nullptr,nullptr,nullptr,n,7};
    ReadyMetadata r{total,7,MetadataScope::StaticOperator};
    Packet out;
    for (unsigned worker=0;worker<workers;++worker) {
      VisitorState state{worker,workers};
      while (next_complete_packet(state,v,c,w,r,out))
        std::cout << worker << ',' << out.expert << ',' << out.n << ','
                  << out.m_first << ',' << out.length << ';';
    }
    r.generation=8;
    if (decode_packet(0,v,c,w,r,out)) return 3;
    std::cout << '\n';
  }
}
