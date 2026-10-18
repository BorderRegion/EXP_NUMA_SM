#include "policy.hpp"
extern "C" void sr_choose_cpu(int m,int n,int k,int p,int h,double*out){sr_export_choice(m,n,k,p,h,out);}
extern "C" void v2_choose_cpu(int m,int n,int k,int p,int h,int dynamic,double*out){sr_export_choice(m,n,k,p,h,out,dynamic);}
extern "C" double sr_choice_bench(int m,int n,int k,int p,int h,int count){double out[13];volatile int shape[3]={m,n,k};auto t=std::chrono::steady_clock::now();volatile double guard=0;for(int i=0;i<count;i++){sr_export_choice(shape[0],shape[1],shape[2],p,h,out,true);guard+=out[1]+out[12];}return std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-t).count()/count;}
