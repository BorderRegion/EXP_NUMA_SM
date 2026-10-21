// All mathematical graphs are unchanged. Only host-submitted device dependencies differ.
struct TailJob { CUevent begin, fg_end, bg_end, end, prefix_end, suffix_start; int mode, diagnostic; };
extern "C" void* qt_create(int mode,int diagnostic){try{
 auto*p=new TailJob;p->mode=mode;p->diagnostic=diagnostic;
 ck(cuCtxSetCurrent(primary),"tail primary");
 for(auto*x:{&p->begin,&p->fg_end,&p->bg_end,&p->end})ck(cuEventCreate(x,0),"tail timing event");
 ck(cuEventCreate(&p->prefix_end,diagnostic?0:CU_EVENT_DISABLE_TIMING),"prefix dependency event");
 ck(cuEventCreate(&p->suffix_start,diagnostic?0:CU_EVENT_DISABLE_TIMING),"suffix diagnostic event");
 return p;
}catch(std::exception&e){error=e.what();return nullptr;}}
extern "C" int qt_run(void*ptr,void**fgs,void**bgs,void**suffixes,int ring,int count,double*out){TRY{
 auto*p=(TailJob*)ptr;
 for(int i=0;i<count;i++){
  Graph*f=(Graph*)fgs[i%ring];Graph*b=(Graph*)bgs[i%ring];auto&parent=groups.at(0);
  ck(cuCtxSetCurrent(primary),"tail start primary");auto t=std::chrono::steady_clock::now();
  ck(cuEventRecord(p->begin,parent.stream),"tail begin");
  auto issue=[&](Graph*q,CUevent done,CUevent wait){auto&g=groups.at(q->group);ck(cuCtxSetCurrent(g.ctx),"tail graph context");ck(cuStreamWaitEvent(g.stream,wait,0),"tail graph wait");ck(cuGraphLaunch(q->exec,g.stream),"tail graph launch");ck(cuEventRecord(done,g.stream),"tail graph completed");};
  if(p->mode==3){
   issue(f,p->prefix_end,p->begin);issue(b,p->bg_end,p->begin);
   Graph*s=(Graph*)suffixes[i%ring];if(s->group!=0)throw std::runtime_error("Suffix must run on primary56 group0");
   ck(cuCtxSetCurrent(primary),"suffix primary");
   ck(cuStreamWaitEvent(parent.stream,p->prefix_end,0),"suffix waits prefix");
   ck(cuStreamWaitEvent(parent.stream,p->bg_end,0),"suffix waits background");
   if(p->diagnostic)ck(cuEventRecord(p->suffix_start,parent.stream),"suffix diagnostic start");
   ck(cuGraphLaunch(s->exec,parent.stream),"suffix launch primary56");
   ck(cuEventRecord(p->fg_end,parent.stream),"all foreground finished");
  }else if(p->mode==2){issue(b,p->bg_end,p->begin);issue(f,p->fg_end,p->bg_end);}
  else{issue(f,p->fg_end,p->begin);issue(b,p->bg_end,p->mode==1?p->fg_end:p->begin);}
  ck(cuCtxSetCurrent(primary),"tail final primary");
  ck(cuStreamWaitEvent(parent.stream,p->fg_end,0),"tail join foreground");ck(cuStreamWaitEvent(parent.stream,p->bg_end,0),"tail join background");
  ck(cuEventRecord(p->end,parent.stream),"tail end");ck(cuStreamSynchronize(parent.stream),"tail both outputs ready");
  out[i*7+3]=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-t).count();
  float total,ft,bt;ck(cuEventElapsedTime(&total,p->begin,p->end),"tail total");ck(cuEventElapsedTime(&ft,p->begin,p->fg_end),"tail foreground");ck(cuEventElapsedTime(&bt,p->begin,p->bg_end),"tail background");
  out[i*7]=total*1000;out[i*7+1]=ft*1000;out[i*7+2]=bt*1000;out[i*7+4]=out[i*7+5]=out[i*7+6]=-1;
  if(p->mode==3&&p->diagnostic){float pt,st,ss;ck(cuEventElapsedTime(&pt,p->begin,p->prefix_end),"prefix diagnostic time");ck(cuEventElapsedTime(&st,p->suffix_start,p->fg_end),"suffix diagnostic span");ck(cuEventElapsedTime(&ss,p->begin,p->suffix_start),"suffix start diagnostic time");out[i*7+4]=pt*1000;out[i*7+5]=st*1000;out[i*7+6]=ss*1000;}
 }
 return 0;
}CATCH}
extern "C" int qt_drop(void*ptr){TRY{auto*p=(TailJob*)ptr;for(auto x:{p->begin,p->fg_end,p->bg_end,p->end,p->prefix_end,p->suffix_start})ck(cuEventDestroy(x),"tail event destroy");delete p;return 0;}CATCH}
