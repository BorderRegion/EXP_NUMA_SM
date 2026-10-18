from common import *
import sys
model=read(Path(sys.argv[1]));dest=ROOT/'src/policy.hpp'
def literal(x):
 if isinstance(x,list):return '{'+','.join(literal(v) for v in x)+'}'
 return format(float(x),'.17g')
models=[];means=[];scales=[];dims=[]
for mode in ['SHAPE','RESOURCE']:
 b=[];m=[];s=[];d=[]
 for action in ACTIONS:
  x=model['models'][mode][action];n=len(x['means']);d.append(n);b.append(x['beta']+[0.]*(16-len(x['beta'])));m.append(x['means']+[0.]*(15-n));s.append(x['scales']+[1.]*(15-n))
 models.append(b);means.append(m);scales.append(s);dims.append(d)
bids=sorted(model['bins']);cfg=[[model['bins'][b]['single_recipe'],model['bins'][b]['split_recipe'],model['bins'][b]['split_S']] for b in bids]
setup=[[model['action_setup_us_by_bin'][b][a] for a in ACTIONS] for b in bids]
margin=[[model['paired_error_margin_us'][mode].get(a,0) for a in ACTIONS] for mode in ['SHAPE','RESOURCE']];baseerr=[0]+[model['base_error_to_lib_us']['SHAPE'][a] for a in ACTIONS[1:3]]
prefix='''#pragma once
#include <cmath>
#include <algorithm>
#include <chrono>
namespace sr_policy {
struct Choice { int base=0,action=0,reason=0; double pred[9]={0},required=0; };
'''
for decl,val in [('double B[2][9][16]',models),('double MU[2][9][15]',means),('double SD[2][9][15]',scales),('int DIM[2][9]',dims),('int CONFIG[6][3]',cfg),('double SETUP[6][9]',setup),('double MARGIN[2][9]',margin),('double BASEERR[3]',baseerr),('double DIST_SCALE[3]',model['shape_distance_scales']),('double REP[4][3]',model['representative_log_shapes']),('double CARD[2][4][6][4]',model['static_resource_features'])]:prefix+='inline const '+decl+'='+literal(val)+';\n'
prefix+=f'inline const double SELECT_US={model["selection_us"]:.17g};\n'
prefix+='''
inline int bin(int m,int n){return (m<=8?0:m<=64?1:2)*2+(n>4096);}
inline bool inside(int m,int n,int k){return m>=1&&m<=512&&n>=1024&&n<=12288&&k>=4096&&k<=32768;}
inline void predict(int m,int n,int k,int policy,double*out){
 int bi=bin(m,n),mode=policy>=3,perm=policy==4;double w[4],d[4];int order[4]={0,1,2,3};double logs[3]={std::log2(m),std::log2(n),std::log2(k)};
 double w0=0.,w1=0.;
 if(mode){
  for(int r=0;r<4;r++){d[r]=0;for(int j=0;j<3;j++){double z=(logs[j]-REP[r][j])/DIST_SCALE[j];d[r]+=z*z;}}
  for(int i=1;i<4;i++){int key=order[i],j=i;while(j>0&&d[key]<d[order[j-1]]){order[j]=order[j-1];--j;}order[j]=key;}
  w0=1/std::max(d[order[0]],1e-12);w1=1/std::max(d[order[1]],1e-12);w0/=(w0+w1);w1=1-w0;
 }
 for(int a=0;a<9;a++){
  int recipe=CONFIG[bi][a<2?0:1],split=a<2?1:CONFIG[bi][2],bm=recipe==0?32:recipe==2?64:128,bn=recipe==0?64:128;double tiles=double((m+bm-1)/bm)*((n+bn-1)/bn);
  double x[15]={logs[0],logs[1],logs[2],std::log2(1.+2.*m*n*k),std::log2(1.+2.*k*(m+n)),a==0?0:std::log2(1.+4.*m*n*split),std::log2(1.+tiles),std::log2(1.+tiles*split/56.),1.-double(m)*n/(tiles*bm*bn),std::log2(split),a==0?0.:1.,0,0,0,0};
  if(mode&&a>=3)for(int f=0;f<4;f++)x[11+f]=w0*CARD[perm][order[0]][a-3][f]+w1*CARD[perm][order[1]][a-3][f];
  double y=B[mode][a][0];for(int f=0;f<DIM[mode][a];f++)y+=B[mode][a][f+1]*(x[f]-MU[mode][a][f])/SD[mode][a][f];out[a]=std::exp(y);
 }
}
inline Choice choose(int m,int n,int k,int policy,int horizon){
 Choice o;if(policy==0){o.reason=1;return o;}if(!inside(m,n,k)){o.reason=2;return o;}
 int bi=bin(m,n),mode=policy>=3,H=std::max(1,horizon);predict(m,n,k,policy,o.pred);double best=o.pred[0];
 for(int a=1;a<3;a++){double score=o.pred[a]+std::max({.5,.01*o.pred[0],BASEERR[a]})+SELECT_US+std::max(0.,SETUP[bi][a]-SETUP[bi][0])/H;if(score<best){best=score;o.base=a;}}
 o.action=o.base;if(policy==1){o.reason=3;return o;}best=o.pred[o.base];
 for(int a=3;a<9;a++){double req=std::max({.5,.01*o.pred[o.base],MARGIN[mode][a]})+SELECT_US+std::max(0.,SETUP[bi][a]-SETUP[bi][o.base])/H;double score=o.pred[a]+req;if(score<best){best=score;o.action=a;o.required=req;}}
 o.reason=o.action==o.base?3:4;return o;
}
} // namespace
extern "C" inline void sr_export_choice(int m,int n,int k,int policy,int horizon,double*out){auto c=sr_policy::choose(m,n,k,policy,horizon);out[0]=c.base;out[1]=c.action;out[2]=c.reason;for(int a=0;a<9;a++)out[3+a]=c.pred[a];out[12]=c.required;}
'''
dest.write_text(prefix)
(ROOT/'src/policy_cpu.cpp').write_text('''#include "policy.hpp"
extern "C" void sr_choose_cpu(int m,int n,int k,int p,int h,double*out){sr_export_choice(m,n,k,p,h,out);}
extern "C" double sr_choice_bench(int m,int n,int k,int p,int h,int count){double out[13];auto t=std::chrono::steady_clock::now();volatile double guard=0;for(int i=0;i<count;i++){sr_export_choice(m,n,k,p,h,out);guard+=out[1]+out[12];}return std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-t).count()/count;}
''')
print(dest)
