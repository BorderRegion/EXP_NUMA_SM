#include "paired_runner.hpp"
#include <atomic>
#include <cstdlib>
#include <new>
#include <iostream>
static std::atomic<unsigned> allocations{0};
void* operator new(std::size_t n){++allocations;if(auto p=std::malloc(n))return p;throw std::bad_alloc();}
void operator delete(void*p) noexcept{std::free(p);}void operator delete(void*p,std::size_t) noexcept{std::free(p);}
t10_pair::Sample fake(void*p,unsigned){double t=*static_cast<double*>(p);return {t,t*.8};}
int main(){double a=100,b=80;t10_pair::Plan p{&a,fake},q{&b,fake};
 allocations=0;auto out=t10_pair::run(p,q,16,4,4,false);auto n=allocations.load();
 if(n || out.windows[0].label!='A' || out.windows[1].samples[0].cpu_ready_us!=80)return 1;
 std::cout<<"host_pair_runner_pass allocations="<<n<<" (synthetic callbacks, not GPU)\n";
}
