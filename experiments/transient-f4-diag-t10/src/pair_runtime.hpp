// Host-only measurement adapter. Prepared graphs and caller-owned buffers.
// No heap allocation, graph setup, numerical reference, D2H or disk I/O here.
extern "C" int v2_windows(Job**a,Job**b,int ring,int n,int warm,const int*labels,int nw,double*out,double*meta){TRY
 if(n<1||n>128||ring<1||nw<1||nw>12)throw std::runtime_error("window bounds");
 auto ns=[](){return double(std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::system_clock::now().time_since_epoch()).count());};
 double v[5];
 for(int w=0;w<nw;w++){
  Job**p=labels[w]?b:a;meta[w*6]=ns();auto wt=Clock::now();
  for(int i=0;i<warm;i++)p[i%ring]->run(v);
  meta[w*6+1]=ns();meta[w*6+4]=ms(wt,Clock::now())*1000;
  meta[w*6+2]=ns();auto t=Clock::now();
  for(int i=0;i<n;i++){p[i%ring]->run(v);for(int f=0;f<5;f++)out[(w*n+i)*5+f]=v[f];}
  meta[w*6+3]=ns();meta[w*6+5]=ms(t,Clock::now())*1000;
 }
 CATCH}
