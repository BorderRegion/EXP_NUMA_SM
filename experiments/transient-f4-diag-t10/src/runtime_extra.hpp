#include "policy.hpp"
extern "C" int sr_choose(int m,int n,int k,int policy,int horizon,double*out){TRY sr_export_choice(m,n,k,policy,horizon,out);CATCH}
extern "C" int sr_choose_dynamic(int m,int n,int k,int policy,int horizon,double*out){TRY sr_export_choice(m,n,k,policy,horizon,out,true);CATCH}
extern "C" Job*sr_make_bound_action(Engine*e,int m,int n,int k,int action,void**ptr,size_t workspace_words,int chain){
 try{
  if(action<0||action>=9)throw std::runtime_error("invalid bound action");int bi=sr_policy::bin(m,n),recipe=0,split=1;
  if(action>0){recipe=sr_policy::CONFIG[bi][action==1?0:1];split=action==1?1:sr_policy::CONFIG[bi][2];}
  int kind=action==0?3:action==1?4:action==2?0:1;int cfg[20]={m,n,k,split,recipe,kind,action>=3,-1,-1,-1,-1,0,0,0,0,1,0,chain,k,0};
  int bm=recipe==0?32:recipe==2?64:128,bn=recipe==0?64:128;size_t need=action<2?0:action==2?size_t(m)*n*split:size_t((m+bm-1)/bm)*((n+bn-1)/bn)*bm*bn*split;
  if(need>workspace_words)throw std::runtime_error("insufficient selected-plan workspace");
  if(action>=3){int part=(action-3)/2,pi=(action-3)%2;e->ensure_resources(part);for(int i=0;i<2;i++){cfg[7+i]=e->halves[part][i];cfg[9+i]=e->halves[part][i^pi];}}
  // V2 adapter scope: the second FFN GEMM is the explicitly shared LIB action.
  auto j=std::make_unique<Job>(*e,cfg,ptr,1,0);j->build();return j.release();
 }catch(const std::exception&x){error=x.what();return nullptr;}
}
extern "C" int sr_job_config(Job*j,int*out){TRY std::copy(j->c,j->c+20,out);CATCH}
// The caller holds prepared signature bindings; current host input selects one.
// No allocations, GPU domain lookup tables, D2H decisions or intermediate waits.
extern "C" int sr_trace(Job**plans,const int*signature_ids,const int*bound_actions,int count,int policy,int horizon,int dynamic,double*out,double*totals){TRY
 auto all=Clock::now();double last_ready=0;
 for(int i=0;i<count;i++){
  int sig=signature_ids[i];Job*j=plans[sig*4+i%4];auto t=Clock::now();
  if(dynamic){auto c=sr_policy::choose(j->c[0],j->c[1],j->c[2],policy,horizon,true);if(c.action!=bound_actions[sig])throw std::runtime_error("frozen prediction / bound graph mismatch");}
  j->e.stream(-1);ck(cuGraphLaunch(j->exec,j->e.parent),"selected timed graph submission");ck(cuStreamSynchronize(j->e.parent),"caller output-ready boundary");auto ready=Clock::now();last_ready=ms(all,ready)*1000;out[3*i+1]=ms(t,ready)*1000;float span;ck(cuEventElapsedTime(&span,j->start,j->end),"request GPU span");out[3*i]=span*1000;out[3*i+2]=bound_actions[sig];
 }
 totals[0]=last_ready;totals[1]=ms(all,Clock::now())*1000;
 CATCH}
