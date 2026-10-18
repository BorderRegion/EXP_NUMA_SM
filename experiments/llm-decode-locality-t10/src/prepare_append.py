from common import *
s=(ROOT/'freeze/implementation/attention.cu').read_text()
s=s.replace('int B,HK,NP,W,mode;};','int B,HK,NP,W,mode;const half *new_k,*new_v;};')
needle='long long base=((long long)physical*p.HK+hk)*16*D;'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
   // This CTA uniquely owns the page for this (sequence, KV head). Publish
   // the newest token before using that page. Other CTAs consume other pages.
   if(p.new_k&&page==(p.length[b]-1)/16){int token=(p.length[b]-1)%16;
    for(int d=threadIdx.x;d<D;d+=blockDim.x){((half*)p.k)[base+token*D+d]=p.new_k[head*D+d];((half*)p.v)[base+token*D+d]=p.new_v[head*D+d];}
    __syncthreads();
   }
''')
needle='c[2],c[3],c[4],c[5],c[6]};';assert s.count(needle)==1;s=s.replace(needle,'c[2],c[3],c[4],c[5],c[6],(half*)a[10],(half*)a[11]};')
s+='''
__global__ void append_only(half*k,half*v,const half*nk,const half*nv,const int*table,const int*len,int HK,int NP,int D){int head=blockIdx.x,b=head/HK,h=head%HK,pos=len[b]-1,physical=table[b*NP+pos/16];long long base=((long long)physical*HK+h)*16*D+(pos%16)*D;for(int d=threadIdx.x;d<D;d+=blockDim.x){k[base+d]=nk[head*D+d];v[base+d]=nv[head*D+d];}}
extern "C" int ll_append(void**a,const int*c,unsigned long long stream){append_only<<<c[2]*c[3],128,0,(cudaStream_t)stream>>>((half*)a[1],(half*)a[2],(half*)a[10],(half*)a[11],(int*)a[3],(int*)a[4],c[3],c[4],c[0]);auto e=cudaGetLastError();if(e!=cudaSuccess){err=cudaGetErrorString(e);return -1;}return 0;}
'''
(ROOT/'src/append_attention.cu').write_text(s)
print('APPEND_SOURCE_PREPARED')
