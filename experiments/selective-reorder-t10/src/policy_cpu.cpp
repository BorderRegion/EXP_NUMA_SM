#include "policy.hpp"
extern "C" void sr_choose_cpu(int m,int n,int k,int p,int h,double*out){sr_export_choice(m,n,k,p,h,out);}
extern "C" double sr_choice_bench(int m,int n,int k,int p,int h,int count){double out[13];auto t=std::chrono::steady_clock::now();volatile double guard=0;for(int i=0;i<count;i++){sr_export_choice(m,n,k,p,h,out);guard+=out[1]+out[12];}return std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-t).count()/count;}
