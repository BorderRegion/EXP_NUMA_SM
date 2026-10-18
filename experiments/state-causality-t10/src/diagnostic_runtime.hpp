// Host-only diagnostic adapter. Original Job, body graphs, math and selector unchanged.
#include <cstdint>
struct DiagRecord {
 int64_t begin,context,launch,ready,end;
 double gpu;
 int64_t global_index;
 int32_t window,phase,label,slot,action,reserved;
 uint64_t graph;
};
struct DiagChunk {int64_t begin,submitted,end,first,count;};
inline int64_t diag_ns(){return std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now().time_since_epoch()).count();}
inline void diag_request(Job*j,DiagRecord&r,int timer,int slot,int action,int dynamic=0){
 r.begin=diag_ns();
 if(dynamic){auto c=sr_policy::choose(j->c[0],j->c[1],j->c[2],3,1024,true);if(c.action!=action)throw std::runtime_error("frozen dynamic action mismatch");}
 j->e.stream(-1);r.context=diag_ns();
 ck(cuGraphLaunch(timer?j->batch:j->exec,j->e.parent),"diag graph launch");r.launch=diag_ns();
 ck(cuStreamSynchronize(j->e.parent),"diag output ready");r.ready=diag_ns();r.gpu=-1;
 if(!timer){float t;ck(cuEventElapsedTime(&t,j->start,j->end),"diag elapsed completed request");r.gpu=double(t)*1000;}
 r.end=diag_ns();r.slot=slot;r.action=action;r.graph=reinterpret_cast<uint64_t>(timer?j->batch:j->exec);
}
// info: conditioning start/end, request count, chunk count, slot histogram,
// window loop start/end; first64 + last128 ready records are bounded and reused.
extern "C" int diag_episode(Job**a,Job**b,int mode,double seconds,int n,int nw,const int*labels,int fixed_slot,int timer,DiagRecord*out,DiagRecord*history,DiagChunk*chunks,int cap,int64_t*info){TRY
 if(n<1||n>128||nw<1||nw>12||mode<0||mode>3)throw std::runtime_error("diag bounds");
 std::fill(info,info+12,0);int64_t cnt=0,nc=0;info[0]=diag_ns();
 while(double(diag_ns()-info[0])*1e-9<seconds){
  if(nc>=cap)throw std::runtime_error("condition buffer capacity");auto&ch=chunks[nc++];ch.begin=diag_ns();ch.first=cnt;ch.count=64;
  if(mode<2)a[0]->e.stream(-1);
  for(int k=0;k<64;k++,cnt++){
   int slot=(mode%2)?int(cnt%4):0;info[4+slot]++;
   if(mode<2)ck(cuGraphLaunch(a[slot]->batch,a[slot]->e.parent),"finite body conditioning enqueue");
   else{DiagRecord r{};diag_request(a[slot],r,0,slot,0);r.global_index=cnt;r.window=-1;r.phase=2;r.label=0;
    if(cnt<64)history[cnt]=r;history[64+cnt%128]=r;}
  }
  ch.submitted=diag_ns();if(mode<2)ck(cuStreamSynchronize(a[0]->e.parent),"finite conditioning drain");ch.end=diag_ns();
 }
 info[1]=diag_ns();info[2]=cnt;info[3]=nc;info[8]=diag_ns();int64_t ix=0;
 for(int w=0;w<nw;w++)for(int phase=0;phase<2;phase++)for(int i=0;i<n;i++){
  int slot=fixed_slot?0:i%4;Job*j=(labels[w]?b:a)[slot];auto&r=out[ix];
  diag_request(j,r,timer,slot,j->c[5]==4?1:0);r.global_index=ix++;r.window=w;r.phase=phase;r.label=labels[w];
 }
 info[9]=diag_ns();CATCH}
extern "C" int diag_trace(Job**jobs,const int*ids,const int*actions,int count,int dynamic,DiagRecord*out,int64_t*meta){TRY
 if(count<1||count>1024)throw std::runtime_error("trace bounds");int ix=0;
 for(int phase=0;phase<2;phase++){
  meta[phase*3]=diag_ns();
  for(int i=0;i<count;i++){
   int sig=ids[i],slot=i%4;Job*j=jobs[sig*4+slot];auto&r=out[ix];diag_request(j,r,0,slot,actions[sig],dynamic);
   r.global_index=ix++;r.window=0;r.phase=phase;r.label=0;meta[phase*3+1]=r.ready;
  }
  meta[phase*3+2]=diag_ns();
 }
 CATCH}
extern "C" int diag_body_once(Job*j){TRY j->e.stream(-1);ck(cuGraphLaunch(j->batch,j->e.parent),"body CPU launch");ck(cuStreamSynchronize(j->e.parent),"body ready");CATCH}
extern "C" int diag_identity(Job*j,uint64_t*out){TRY
 j->e.stream(-1);CUcontext ctx=nullptr;ck(cuCtxGetCurrent(&ctx),"identity context");
 out[0]=reinterpret_cast<uint64_t>(ctx);out[1]=reinterpret_cast<uint64_t>(j->e.parent);
 out[2]=reinterpret_cast<uint64_t>(j->body);out[3]=reinterpret_cast<uint64_t>(j->batch);out[4]=reinterpret_cast<uint64_t>(j->exec);
 out[5]=reinterpret_cast<uint64_t>(j->start);out[6]=reinterpret_cast<uint64_t>(j->end);CATCH}
