
#include <cstdlib>
#include <new>
#include <cstdio>
#include <cmath>
#include <chrono>
static size_t allocations=0;static bool tracking=false;
void*operator new(size_t n){if(tracking)allocations++;void*p=malloc(n);if(!p)throw std::bad_alloc();return p;}
void*operator new[](size_t n){return operator new(n);}
void operator delete(void*p)noexcept{free(p);}void operator delete[](void*p)noexcept{free(p);}
void operator delete(void*p,size_t)noexcept{free(p);}void operator delete[](void*p,size_t)noexcept{free(p);}
#include "legacy_renamed.hpp"
#include "policy.hpp"
extern "C" size_t check(int m,int n,int k,int p,int h,double*old,double*now,size_t*before){
 tracking=true;allocations=0;old_export_choice(m,n,k,p,h,old);*before=allocations;
 allocations=0;sr_export_choice(m,n,k,p,h,now);tracking=false;return allocations;}
