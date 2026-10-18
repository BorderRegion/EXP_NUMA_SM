from common import *
import subprocess,ctypes as C
s=(ROOT/'support/legacy_policy_original.hpp').read_text().replace('namespace sr_policy','namespace old_policy').replace('sr_policy::','old_policy::').replace('sr_export_choice','old_export_choice')
(ROOT/'support/legacy_renamed.hpp').write_text(s)
source=r'''
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
#include "legacy_policy_patched.hpp"
extern "C" size_t check(int m,int n,int k,int p,int h,double*old,double*now,size_t*before){
 tracking=true;allocations=0;old_export_choice(m,n,k,p,h,old);*before=allocations;
 allocations=0;sr_export_choice(m,n,k,p,h,now);tracking=false;return allocations;}
'''
(ROOT/'support/legacy_check.cpp').write_text(source)
cmd=['g++','-std=c++17','-O3','-shared','-fPIC','-Wl,-Bsymbolic','-I'+str(ROOT/'support'),'-I'+str(ROOT/'src'),str(ROOT/'support/legacy_check.cpp'),'-o',str(ROOT/'build/legacy_check.so')]
subprocess.run(cmd,check=True);lib=C.CDLL(str(ROOT/'build/legacy_check.so'));lib.check.argtypes=[C.c_int]*5+[C.POINTER(C.c_double)]*2+[C.POINTER(C.c_size_t)];lib.check.restype=C.c_size_t
cases=read(ROOT/'support/legacy_cases.json');rows=[]
for c in cases:
 for p in range(5):
  for h in [0,1,32,256,1024,4096]:
   a=(C.c_double*13)();b=(C.c_double*13)();old=C.c_size_t();n=lib.check(c['M'],c['N'],c['K'],p,h,a,b,C.byref(old));err=max(abs(x-y) for x,y in zip(a,b));assert err==0 and n==0,(c,p,h,err,n)
   rows.append(dict(case=c['id'],policy=p,H=h,old=list(a),patched=list(b),max_difference=err,patched_cpp_allocations=n,original_cpp_allocations=old.value))
write(ROOT/'reports/LEGACY_CPU_EQUIVALENCE.json',dict(status='PASS',comparisons=len(rows),horizons=[0,1,32,256,1024,4096],rows=rows,scope='operator new/new[] hook with local binding; includes stable_sort allocations, not driver allocator proof'))
print('PASS',len(rows),'original C++ allocations',sum(x['original_cpp_allocations'] for x in rows),'patched',sum(x['patched_cpp_allocations'] for x in rows))
