from common import *
import shutil
old=(ROOT/'src/legacy_attention.cu').read_text()
s=old.replace('int B,HK,NP,W,mode;','int B,HK,NP,W,mode,chunk;')
s=s.replace('template<int D,int G,bool Queue,bool Fused,bool Trace> __global__ void decode','template<int D,int G,int Kind,bool Fused,bool Trace> __global__ void decode')
s=s.replace('if(p.mode==3)pref^=1;','if(p.mode==3||p.mode==7)pref^=1; if(Kind==2){pref=p.mode==5?(worker&1):pref;if(p.mode==8)pref=((sm*17+13)^(sm>>2))&1;}')
s=s.replace('__shared__ int page,source,last;','__shared__ int page,source,last,next,end,active;')
s=s.replace('float am=-INFINITY,al=0;int iteration=0;','float am=-INFINITY,al=0;int iteration=0; if(threadIdx.x==0){next=0;end=0;active=pref;} __syncthreads();')
a=s.index('   if(Queue){');b=s.index('   if(Trace&&',a)
s=s[:a]+'''   if(Kind==1){
    const int*ls=p.list+head*(p.NP+2);
    if(next>=end){int which=active;unsigned i=atomicAdd(p.counter+head*3+which,p.chunk);if(i>=unsigned(ls[which])){which^=1;i=atomicAdd(p.counter+head*3+which,p.chunk);} active=which;next=i;end=min(int(i)+p.chunk,ls[which]);}
    page=next<end?ls[2+(active?ls[0]:0)+next++]:-1;source=active;
   } else {int idx=worker+iteration*p.W;if(p.mode==10||p.mode==11)idx=worker*((p.NP+p.W-1)/p.W)+iteration;
    bool valid=idx<p.NP&&(!(p.mode==10||p.mode==11)||iteration<(p.NP+p.W-1)/p.W);
    page=valid?(p.mode==11?p.list[head*(p.NP+2)+2+idx]:idx):-1;source=-1;
    if(Kind==2&&page>=0){int physical=p.table[b*p.NP+page];unsigned long long addr=(unsigned long long)(p.k+((long long)physical*p.HK+hk)*32*D);int color=__popcll((addr>>12)&0x33)&1;source=p.mode==9?color:pref;}
   }
''' +s[b:]
s=s.replace('tr[2]=Queue?pref:-1;','tr[2]=Kind?pref:-1;')
s=s.replace('long long base=((long long)physical*p.HK+hk)*16*D;','long long base=((long long)physical*p.HK+hk)*16*D;if(Kind==2){base*=2;unsigned long long addr=(unsigned long long)(p.k+base);int color=__popcll((addr>>12)&0x33)&1;int copy=p.mode==9?0:(color^pref);base+=copy*16*D;}')
a=s.index(' if(p.mode==0)decode');b=s.index(' if(!Fused)',a)
s=s[:a]+''' if(p.mode>=5&&p.mode<=9)decode<D,G,2,Fused,Trace><<<blocks,32*G,smem,stream>>>(p);
 else if(p.mode==0||p.mode>=10)decode<D,G,0,Fused,Trace><<<blocks,32*G,smem,stream>>>(p);
 else decode<D,G,1,Fused,Trace><<<blocks,32*G,smem,stream>>>(p);
''' +s[b:]
s=s.replace('c[2],c[3],c[4],c[5],c[6]};','c[2],c[3],c[4],c[5],c[6],c[9]};')
s=s.replace('else GO(256,4);','')
# A single append kernel maintains either one original or two replica caches.
append='''
__global__ void append_kv(half*k,half*v,const half*nk,const half*nv,const int*table,const int*length,int HK,int NP,int D,int copies){
 int head=blockIdx.x,b=head/HK,hk=head%HK,pos=length[b]-1,physical=table[b*NP+pos/16];
 for(int d=threadIdx.x;d<D;d+=blockDim.x)for(int c=0;c<copies;c++){long long off=(((long long)physical*HK+hk)*copies+c)*16*D+(pos%16)*D+d;k[off]=nk[head*D+d];v[off]=nv[head*D+d];}
}
extern "C" int ll_append(void**a,const int*c,unsigned long long stream){append_kv<<<c[2]*c[3],128,0,(cudaStream_t)stream>>>((half*)a[1],(half*)a[2],(half*)a[10],(half*)a[11],(int*)a[3],(int*)a[4],c[3],c[4],c[0],c[6]>=5&&c[6]<=9?2:1);auto e=cudaGetLastError();if(e!=cudaSuccess){err=cudaGetErrorString(e);return -1;}return 0;}
'''
s+=append
(ROOT/'src/attention.cu').write_text(s)
print('PREPARE_PASS')
