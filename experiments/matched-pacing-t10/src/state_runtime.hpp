// Host-only request pacing. All original GPU graphs and arithmetic unchanged.
#include <thread>
struct StatePacket { int64_t begin,submitted,ready,end,first,count;double gpu_us; };
extern "C" int state_run(Job**jobs,int mode,double seconds,int64_t ordinal,DiagRecord*out,int capacity,StatePacket*packets,int pcap,int64_t*info){TRY
 if(mode<0||mode>3||seconds<=0)throw std::runtime_error("state bounds");
 std::fill(info,info+6,0);info[0]=diag_ns();int64_t count=0,np=0;
 while(double(diag_ns()-info[0])*1e-9<seconds){
  if(count+(mode==3?64:1)>capacity)throw std::runtime_error("record capacity");
  if(mode!=3){
   int slot=int((ordinal+count)%4);auto&r=out[count];diag_request(jobs[slot],r,0,slot,0);r.global_index=ordinal+count;r.window=0;r.phase=0;r.label=0;++count;
   if(mode==1||mode==2)std::this_thread::sleep_for(std::chrono::microseconds(mode==1?100:1000));
  }else{
   if(np>=pcap)throw std::runtime_error("packet capacity");auto&pk=packets[np++];pk.begin=diag_ns();pk.first=ordinal+count;pk.count=64;
   auto st=jobs[0]->e.stream(-1);ck(cuEventRecord(jobs[0]->start,st),"packet start");
   for(int i=0;i<64;i++,count++){
    int slot=int((ordinal+count)%4);auto*j=jobs[slot];auto&r=out[count];r.begin=diag_ns();r.context=r.begin;
    ck(cuGraphLaunch(j->batch,st),"state body enqueue");r.launch=diag_ns();r.ready=0;r.end=r.launch;r.gpu=-1;r.global_index=ordinal+count;r.slot=slot;r.action=0;r.phase=0;r.window=0;r.label=0;r.graph=reinterpret_cast<uint64_t>(j->batch);
   }
   ck(cuEventRecord(jobs[0]->end,st),"packet end");pk.submitted=diag_ns();ck(cuStreamSynchronize(st),"packet output ready");pk.ready=diag_ns();float g;ck(cuEventElapsedTime(&g,jobs[0]->start,jobs[0]->end),"completed packet elapsed");pk.gpu_us=double(g)*1000;pk.end=diag_ns();
  }
 }
 info[1]=diag_ns();info[2]=count;info[3]=np;info[4]=ordinal+count;
 CATCH}
