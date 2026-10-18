#pragma once
#include <cmath>
#include <algorithm>
// Allocation-free CPU decision core. The host owns coefficients/metadata.
// These fixed action arrays are NOT per-tile GPU routing tables.
namespace t10_select_v2 {
struct Result { int base=0, action=0, reason=0; double upper_ratio=1.,cost_ratio=0.; };
struct Score { bool ok=false; double total=1.,ratio=1.,cost=0.; };
inline Score score(const double*log_ratio,const double q[9][3],const double*setup,
                   double tlib,unsigned long long horizon,double select_delta,int a,int b) noexcept {
    Score z; double qa=q[a][b];
    if(!std::isfinite(tlib)||!(tlib>0.)||!std::isfinite(select_delta)||select_delta<0.||
       !std::isfinite(log_ratio[a])||!std::isfinite(log_ratio[b])||
       !std::isfinite(qa)||qa<0.||!std::isfinite(setup[a])||!std::isfinite(setup[b])||setup[a]<0.||setup[b]<0.)return z;
    double exponent=log_ratio[a]-log_ratio[b]+qa;
    if(!(exponent>-40.&&exponent<40.)||!(log_ratio[b]>-40.&&log_ratio[b]<40.))return z;
    auto h=horizon?horizon:1ULL;
    double tb=tlib*std::exp(log_ratio[b]);
    z.ratio=std::exp(exponent);z.cost=(select_delta+std::max(0.,setup[a]-setup[b])/double(h))/tb;
    z.total=z.ratio+z.cost;z.ok=std::isfinite(z.total);return z;
}
// mode 0=LIB_ALWAYS, 1=BASE, 2=SHAPE, 3=RESOURCE.
// BASE from SHAPE must be shared; pass frozen_base to the second-level call.
inline Result choose(const double*logs,const double q[9][3],const double*setup,
                     double tlib,unsigned long long horizon,double selection_delta,
                     int mode,bool inside=true,int frozen_base=-1) noexcept {
    Result r;if(!inside||mode==0){r.reason=1;return r;}
    if(mode<1||mode>3||frozen_base>2||frozen_base< -1){r.reason=5;return r;}
    r.base=frozen_base<0?0:frozen_base;double best=1.,br=1.,bc=0.;
    if(frozen_base<0)for(int a=1;a<3;++a){auto s=score(logs,q,setup,tlib,horizon,selection_delta,a,0);if(s.ok&&s.total<best){best=s.total;r.base=a;br=s.ratio;bc=s.cost;}}
    r.action=r.base;
    if(mode==1){r.reason=r.base?3:2;r.upper_ratio=br;r.cost_ratio=bc;return r;}
    best=1.;for(int a=3;a<9;++a){auto s=score(logs,q,setup,tlib,horizon,selection_delta,a,r.base);if(s.ok&&s.total<best){best=s.total;r.action=a;r.upper_ratio=s.ratio;r.cost_ratio=s.cost;}}
    r.reason=r.action==r.base?3:4;return r;
}
}
