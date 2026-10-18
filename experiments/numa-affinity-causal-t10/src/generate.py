from common import *
s=(ROOT/'support/softmax_const.cu').read_text()
s=s.replace('template<int V,bool Trace>', 'template<int V,bool Trace,bool Balanced,bool Fixed>')
s=s.replace('int page,int*trace){','int page,int*trace,unsigned long long*prof){')
s=s.replace('constexpr int R=(V+56*128-1)/(56*128);float reg[R],m=-INFINITY;', '''constexpr int R=(V+56*128-1)/(56*128);
 int count=Balanced?V/56+(sm<unsigned(V%56)):0;
 int start=sm*(V/56)+(sm<unsigned(V%56)?sm:V%56);
 if(Trace&&t==0){for(int j=0;j<10;j++)prof[sm*10+j]=0;prof[sm*10]=sm;prof[sm*10+2]=Balanced?count:((V>int(sm*128))?((V-sm*128)/(56*128))*128+min(128,int((V-sm*128)%(56*128))):0);prof[sm*10+3]=timer();prof[sm*10+9]=sm%2?schedule.consumer_for_sm[sm]:sm/2;}
 float reg[R],m=-INFINITY;''',1)
s=s.replace('int idx=sm*128+t+i*56*128;reg[i]=idx<V?x[idx]:-INFINITY;', 'int idx=Balanced?start+t+i*128:sm*128+t+i*56*128;bool valid=Balanced?(int(t+i*128)<count):(idx<V);reg[i]=valid?x[idx]:-INFINITY;')
s=s.replace('s=bsum(s,sh);\n if(t==0){','s=bsum(s,sh);\n if(Trace&&t==0)prof[sm*10+4]=timer();\n if(t==0){')
s=s.replace('islast=old==27;', 'if(!Fixed)islast=old==27;')
s=s.replace(' }\n __syncthreads();\n if(islast){', '''  if(Trace)prof[sm*10+5]=timer();
  if(Fixed&&sm==1){if(!waitfor(ctrl,28,deadline)){failed=1;atomicOr(ctrl+2,4);}islast=1;}
 }
 __syncthreads();
 if(islast){
  if(Trace&&t==0)prof[sm*10+6]=timer();''')
s=s.replace('release(ctrl+1,1);', 'release(ctrl+1,1);if(Trace)prof[sm*10+7]=timer();')
s=s.replace('int idx=sm*128+t+i*56*128;if(idx<V)y[idx]', 'int idx=Balanced?start+t+i*128:sm*128+t+i*56*128;if(Balanced?(int(t+i*128)<count):(idx<V))y[idx]')
s=s.replace('if(Trace&&t==0)trace[2*blockIdx.x+1]=smid();', 'if(Trace&&t==0){trace[2*blockIdx.x+1]=smid();prof[sm*10+1]=smid();prof[sm*10+8]=timer();}')
s=s.replace('int*trace,float*p,int mode,cudaStream_t stream)', 'int*trace,float*p,unsigned long long*prof,int mode,cudaStream_t stream)')
s=s.replace('paired<V,Trace>', 'paired<V,Trace,Balanced,Fixed>')
s=s.replace('&page,&trace};', '&page,&trace,&prof};')
s=s[:s.index('extern "C" int sf_launch')]+'''
template<int V,bool T> cudaError_t dispatch(void**a,int*c,unsigned long long st){
 #define EXEC(B,F) execute<V,T,B,F>((float*)a[0],(float*)a[1],(unsigned*)a[2],schedule,c[2],(int*)a[4],(float*)a[5],(unsigned long long*)a[6],c[1],(cudaStream_t)st)
 Schedule schedule;std::memcpy(&schedule,a[3],sizeof(schedule));
 if(c[1]<=1)return EXEC(false,false);
 if(c[1]==2)return EXEC(true,false);
 if(c[1]==3)return EXEC(false,true);
 if(c[1]==4)return EXEC(true,true);
 return cudaErrorInvalidValue;
 #undef EXEC
}
extern "C" int sf_launch(void**a,int*c,unsigned long long st){
 cudaError_t e=cudaErrorInvalidValue;
 #define CASE(V) if(c[0]==V){e=c[3]?dispatch<V,true>(a,c,st):dispatch<V,false>(a,c,st);}
 CASE(131072) else CASE(129024)
 if(e!=cudaSuccess){error_message=cudaGetErrorString(e);return -1;}return 0;
}
'''
(ROOT/'src/causal.cu').write_text(s)
print('GENERATED')
