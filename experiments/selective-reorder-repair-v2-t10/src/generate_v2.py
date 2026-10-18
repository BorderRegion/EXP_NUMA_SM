from common import *
import numpy as np,sys
sys.path.insert(0,str(ROOT/'reference'))
from relative_policy import additive_features,export_linear_header
model=read(ROOT/'freeze/POLICY_FREEZE.json')
(ROOT/'src/relative_generated.hpp').write_text(export_linear_header(model))
import shutil
shutil.copy2(ROOT/'reference/decision_core.hpp',ROOT/'src/decision_core.hpp')
def lit(v):
 if isinstance(v,(list,tuple)):return '{'+','.join(lit(x) for x in v)+'}'
 return format(float(v),'.17g')
card=[]
for perm in [False,True]:
 reps=[]
 for rep in model['card']['representatives']:
  actions=[]
  for a in ACTIONS[3:]:
   ff=[]
   for raw in rep['samples']:
    s=raw
    if perm:
     ix=[2,0,3,1];s=dict(raw,matrix_us=np.array(raw['matrix_us'])[np.ix_(ix,ix)].tolist(),P_us=np.array(raw['P_us'])[ix].tolist(),R_us=np.array(raw['R_us'])[ix].tolist())
    ff.append(additive_features(s,int(a[2]),int(a[4])))
   ff=np.array(ff);actions.append(np.append(ff.mean(0),np.mean(np.abs(ff-np.median(ff,axis=0)))).tolist())
  reps.append(actions)
 card.append(reps)
q=[]
for mode in ['SHAPE','RESOURCE']:
 q.append([[[model['margins'][mode][a+'/'+b]['buckets'][str(k)]['q_log'] if a+'/'+b in model['margins'][mode] else 0. for k in range(3)] for b in ACTIONS[:3]] for a in ACTIONS])
cfg=[[v[k] for k in ['single_recipe','split_recipe','split_S']] for _,v in sorted(model['bins'].items())]
source='''#pragma once
#include <cmath>
#include <algorithm>
#include <chrono>
#include "decision_core.hpp"
#include "relative_generated.hpp"
namespace sr_policy {
struct Choice {int base=0,action=0,reason=0;double pred[9]={0},required=0,logs[9]={0},upper_ratio=1,cost_ratio=0;};
'''
for decl,val in [('int CONFIG[6][3]',cfg),('double SETUP[6][9]',[[model['action_setup_us_by_bin'][b][a] for a in ACTIONS] for b in sorted(model['bins'])]),('double DIST_SCALE[3]',model['distance_scale']),('double REP[4][3]',[np.log2(x['shape']).tolist() for x in model['card']['representatives']]),('double CARD[2][4][6][4]',card),('double Q[2][9][3][3]',q),('double AA[3]',[model['aa_floor_log'][str(x)] for x in range(3)]),('double SELECT_DELTA',model['dynamic_selection_delta_us'])]:source+='inline const '+decl+'='+lit(val)+';\n'
source+='''
inline int bin(int m,int n){return (m<=8?0:m<=64?1:2)*2+(n>4096);}
inline bool inside(int m,int n,int k){return m>=1&&m<=512&&n>=1024&&n<=12288&&k>=4096&&k<=32768;}
inline int bucket(double t){return t<250?0:t<2000?1:2;}
inline void features(int m,int n,int k,int a,double*x){
 int bi=bin(m,n),recipe=CONFIG[bi][a<2?0:1],s=a<2?1:CONFIG[bi][2],bm=recipe==0?32:recipe==2?64:128,bn=recipe==0?64:128;double nt=double((m+bm-1)/bm)*((n+bn-1)/bn);
 double f[11]={std::log2(m),std::log2(n),std::log2(k),std::log2(1.+2.*m*n*k),std::log2(1.+2.*k*(m+n)),a==0?0:std::log2(1.+4.*m*n*s),std::log2(1.+nt),std::log2(1.+nt*s/56),1.-double(m)*n/(nt*bm*bn),std::log2(s),double(a!=0)};
 for(int i=0;i<11;i++)x[i]=f[i];for(int i=11;i<15;i++)x[i]=0;
}
inline double predict(int m,int n,int k,int policy,double*logs){
 double w0=0,w1=0,d[4];int order[4]={0,1,2,3};int mode=policy>=3,perm=policy==4;
 if(mode){double l[3]={std::log2(m),std::log2(n),std::log2(k)};for(int r=0;r<4;r++){d[r]=0;for(int f=0;f<3;f++){double z=(l[f]-REP[r][f])/DIST_SCALE[f];d[r]+=z*z;}}
 for(int i=1;i<4;i++){int key=order[i],j=i;while(j>0&&d[key]<d[order[j-1]]){order[j]=order[j-1];--j;}order[j]=key;}
 w0=1/std::max(d[order[0]],1e-12);w1=1/std::max(d[order[1]],1e-12);w0/=(w0+w1);w1=1-w0;}
 double x[15];features(m,n,k,0,x);double tlib=std::exp(relative_generated::lib_log_us(x));logs[0]=0;
'''
for ai,a in enumerate(ACTIONS[1:],1):
 source+=f'features(m,n,k,{ai},x);'
 if ai>=3:source+=f'if(mode)for(int f=0;f<4;f++)x[11+f]=w0*CARD[perm][order[0]][{ai-3}][f]+w1*CARD[perm][order[1]][{ai-3}][f];'
 source+=f'logs[{ai}]=mode?relative_generated::RESOURCE_{a}(x):relative_generated::SHAPE_{a}(x);\n'
source+='''return tlib;}
inline Choice choose(int m,int n,int k,int policy,int horizon,bool dynamic=false){
 Choice o;if(policy==0){o.reason=1;return o;}if(!inside(m,n,k)){o.reason=2;return o;}
 int mode=policy>=3,bi=bin(m,n);double tlib=predict(m,n,k,policy,o.logs),q[9][3];
 for(int a=0;a<9;a++)for(int b=0;b<3;b++){int z=bucket(tlib*std::exp(o.logs[b]));q[a][b]=std::max(Q[a<3?0:mode][a][b][z],AA[z]);}
 double delta=dynamic?SELECT_DELTA:0.;auto base=t10_select_v2::choose(o.logs,q,SETUP[bi],tlib,horizon>0?horizon:1,delta,1);
 auto chosen=policy==1?base:t10_select_v2::choose(o.logs,q,SETUP[bi],tlib,horizon>0?horizon:1,delta,mode?3:2,true,base.base);
 o.base=chosen.base;o.action=chosen.action;o.reason=o.action==o.base?3:4;o.upper_ratio=chosen.upper_ratio;o.cost_ratio=chosen.cost_ratio;o.required=o.upper_ratio+o.cost_ratio;
 for(int a=0;a<9;a++)o.pred[a]=tlib*std::exp(o.logs[a]);return o;
}
}
extern "C" inline void sr_export_choice(int m,int n,int k,int policy,int horizon,double*out,bool dynamic=false){auto c=sr_policy::choose(m,n,k,policy,horizon,dynamic);out[0]=c.base;out[1]=c.action;out[2]=c.reason;for(int a=0;a<9;a++)out[3+a]=c.pred[a];out[12]=c.required;}
'''
(ROOT/'src/policy.hpp').write_text(source)
(ROOT/'src/policy_cpu.cpp').write_text('''#include "policy.hpp"
extern "C" void sr_choose_cpu(int m,int n,int k,int p,int h,double*out){sr_export_choice(m,n,k,p,h,out);}
extern "C" void v2_choose_cpu(int m,int n,int k,int p,int h,int dynamic,double*out){sr_export_choice(m,n,k,p,h,out,dynamic);}
extern "C" double sr_choice_bench(int m,int n,int k,int p,int h,int count){double out[13];volatile int shape[3]={m,n,k};auto t=std::chrono::steady_clock::now();volatile double guard=0;for(int i=0;i<count;i++){sr_export_choice(shape[0],shape[1],shape[2],p,h,out,true);guard+=out[1]+out[12];}return std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-t).count()/count;}
''')
print('V2_HOST_SOURCE_GENERATED')
