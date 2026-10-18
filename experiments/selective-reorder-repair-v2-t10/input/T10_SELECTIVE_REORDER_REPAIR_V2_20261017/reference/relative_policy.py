"""CPU reference for V2 relative prediction. No GPU code or measured coefficients.

Input JSON for the CLI:
 {cases:[{id,M,N,K,cohort}], bins:{...}, card:{representatives:[...]},
  pairs:[{case_id,action,block,round,protocol_id,state_epoch,
          cohort,log_ratio,reference_geomean_us}]}
Only the newly measured development pairs belong here. Test rows are rejected.
Card format reuses the local project: representative case/shape/samples containing
matrix_us, P_us, R_us. Missing physical counters are not synthesized.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from collections import defaultdict
import argparse, json, math, statistics
from pathlib import Path
from typing import Mapping
import numpy as np
from paired_stats import quantile, latency_bucket, error_card, margin_value

ACTIONS=('LIB','SINGLE','SPLIT','PC0_0','PC0_1','PC1_0','PC1_1','PC2_0','PC2_1')
BASE=ACTIONS[:3]
PARTS=(((0,1),(2,3)),((0,2),(1,3)),((0,3),(1,2)))
TILES={0:(32,64),2:(64,128),3:(128,128)}

@dataclass
class Linear:
    means:list[float]
    scales:list[float]
    beta:list[float]
    def predict(self,x):
        if len(x)!=len(self.means) or any(not math.isfinite(t) for t in x):raise ValueError('feature vector')
        y=self.beta[0]+sum(b*(v-m)/s for b,v,m,s in zip(self.beta[1:],x,self.means,self.scales))
        if not math.isfinite(y):raise ValueError('nonfinite model prediction')
        return y
    def to_dict(self):return asdict(self)

def fit_linear(xs,ys,lam=1.):
    x=np.asarray(xs,dtype=float);y=np.asarray(ys,dtype=float)
    if x.ndim!=2 or len(x)<2 or y.shape!=(len(x),) or not np.isfinite(x).all() or not np.isfinite(y).all() or lam<=0:
        raise ValueError('finite training matrix / targets required')
    mu=x.mean(0);sd=x.std(0);sd=np.where(sd<1e-8,1.,sd)
    z=np.column_stack([np.ones(len(x)),(x-mu)/sd]);pen=np.eye(z.shape[1])*lam;pen[0,0]=0.
    beta=np.linalg.solve(z.T@z+pen,z.T@y)
    return Linear(mu.tolist(),sd.tolist(),beta.tolist())

def additive_features(sample,part,pi):
    t=np.asarray(sample['matrix_us'],float);p=np.asarray(sample['P_us'],float);r=np.asarray(sample['R_us'],float)
    if t.shape!=(4,4) or p.shape!=(4,) or r.shape!=(4,) or not all(np.isfinite(v).all() and (v>0).all() for v in (t,p,r)):
        raise ValueError('actual positive PC/P/R times required; do not fill missing counters with guesses')
    g=PARTS[part];res=t-t.mean(1)[:,None]-t.mean(0)[None,:]+t.mean()
    def im(v):
        cap=[sum(1/v[j] for j in side) for side in g]
        return abs(cap[0]-cap[1])/sum(cap)
    d=[res[i,j] for b in (0,1) for i in g[b] for j in g[b^pi]]
    return [im(p),im(r),float(np.mean(d)/t.mean())]

class FeatureBank:
    def __init__(self,cases,bins,card):
        self.cases={c['id']:c for c in cases};self.bins=bins;self.card=card
    def shape_vector(self,cid,action):
        c=self.cases[cid];m,n,k=(int(c[q]) for q in ('M','N','K'))
        if min(m,n,k)<=0:raise ValueError('positive dimensions')
        b=self.bins[f'{0 if m<=8 else 1 if m<=64 else 2}_{int(n>4096)}']
        rec=b['single_recipe'] if action in BASE[:2] else b['split_recipe'];bm,bn=TILES[rec]
        s=1 if action in BASE[:2] else int(b['split_S']);nt=math.ceil(m/bm)*math.ceil(n/bn)
        partial=0 if action=='LIB' else 4*m*n*s
        return [math.log2(m),math.log2(n),math.log2(k),math.log2(1+2*m*n*k),math.log2(1+2*k*(m+n)),
                math.log2(1+partial),math.log2(1+nt),math.log2(1+nt*s/56),1-m*n/(nt*bm*bn),math.log2(s),float(action!='LIB')]
    def resource_vector(self,cid,action,scale,exclude=None,permuted=False):
        if not action.startswith('PC'):return [0.]*4
        c=self.cases[cid];logs=np.log2([c[q] for q in ('M','N','K')]);rows=[]
        for rep in self.card['representatives']:
            if rep['case']==exclude:continue  # no self-card leakage in LOSO
            f=[]
            for raw in rep['samples']:
                s=raw
                if permuted:
                    ids=[2,0,3,1];s=dict(raw,matrix_us=np.asarray(raw['matrix_us'])[np.ix_(ids,ids)].tolist(),
                                      P_us=np.asarray(raw['P_us'])[ids].tolist(),R_us=np.asarray(raw['R_us'])[ids].tolist())
                f.append(additive_features(s,int(action[2]),int(action[4])))
            a=np.asarray(f,float)
            if len(a)<2:raise ValueError('resource card requires repeated observations')
            v=np.append(a.mean(0),np.mean(np.abs(a-np.median(a,axis=0))))
            dist=float(np.sum(((logs-np.log2(rep['shape']))/scale)**2));rows.append((dist,rep['case'],v))
        if len(rows)<2:raise ValueError('need >=2 non-held-out resource representatives')
        rows.sort(key=lambda x:(x[0],x[1]));a,b=rows[:2];wa=1/max(a[0],1e-12);wb=1/max(b[0],1e-12);wa/=wa+wb
        return (wa*a[2]+(1-wa)*b[2]).tolist()
    def vector(self,cid,action,mode,scale,exclude=None,permuted=False):
        v=self.shape_vector(cid,action)
        return v+self.resource_vector(cid,action,scale,exclude,permuted) if mode=='RESOURCE' and action.startswith('PC') else v

def aggregate_pairs(pairs):
    if not pairs:raise ValueError('no new paired development rows')
    protocols={p['protocol_id'] for p in pairs};states={p['state_epoch'] for p in pairs}
    if len(protocols)!=1 or len(states)!=1:raise ValueError('do not silently mix timing protocols or power/clock epochs')
    grouped=defaultdict(list);libs=defaultdict(list);seen=set()
    for p in pairs:
        if p['cohort']!='development_remeasured':raise ValueError('test/regression rows may not train this model')
        a=p['action'];cid=p['case_id']
        if a not in ACTIONS[1:]:raise ValueError('pair must compare one supported candidate with LIB')
        key=(cid,a,int(p['block']),int(p['round']))
        if key in seen:raise ValueError('duplicate pair or selected retry; handle raw attempts outside training')
        seen.add(key)
        z=float(p['log_ratio']);t=float(p['reference_geomean_us'])
        if not math.isfinite(z) or not math.isfinite(t) or t<=0:raise ValueError('finite log ratio / positive LIB time')
        grouped[key[:3]].append(z);libs[(cid,int(p['block']))].append(math.log(t))
    blockmean={k:statistics.mean(v) for k,v in grouped.items()};ids=sorted({k[0] for k in blockmean})
    obs={};tl={}
    for cid in ids:
        obs[cid]={'LIB':0.}
        blocks_by_action=[]
        for a in ACTIONS[1:]:
            vals=[v for (c,aa,b),v in blockmean.items() if c==cid and aa==a]
            if len(vals)<2:raise ValueError('incomplete paired shape; retain NA instead of filling it')
            blocks_by_action.append({b for c,aa,b in blockmean if c==cid and aa==a})
            obs[cid][a]=statistics.mean(vals)
        if any(b!=blocks_by_action[0] for b in blocks_by_action):raise ValueError('actions are not contemporaneously paired')
        tl[cid]=math.exp(statistics.mean(statistics.mean(v) for (c,b),v in libs.items() if c==cid))
    return ids,obs,tl

def train(payload):
    ids,truth,libtime=aggregate_pairs(payload['pairs'])
    if len(ids)<8:raise ValueError('too few independent development shapes')
    fb=FeatureBank(payload['cases'],payload['bins'],payload['card'])
    if any(fb.cases[c]['cohort']!='development_remeasured' for c in ids):raise ValueError('case split mismatch')
    def fit_subset(fitids,exclude):
        scale=np.std(np.log2([[fb.cases[c][q] for q in ('M','N','K')] for c in fitids]),axis=0)
        scale=np.where(scale<1e-8,1.,scale)
        lm=fit_linear([fb.shape_vector(c,'LIB') for c in fitids],[math.log(libtime[c]) for c in fitids])
        models={'SHAPE':{},'RESOURCE':{}}
        for a in ACTIONS[1:]:
            m=fit_linear([fb.vector(c,a,'SHAPE',scale,exclude) for c in fitids],[truth[c][a] for c in fitids])
            models['SHAPE'][a]=m
            models['RESOURCE'][a]=m if a in BASE else fit_linear([fb.vector(c,a,'RESOURCE',scale,exclude) for c in fitids],[truth[c][a] for c in fitids])
        return scale,lm,models
    oof=[]
    for held in ids:
        fitids=[c for c in ids if c!=held];sc,lm,md=fit_subset(fitids,held)
        predlib=math.exp(lm.predict(fb.shape_vector(held,'LIB')))
        row={'case_id':held,'predicted_lib_us':predlib,'observed':truth[held],'predicted':{}}
        for mode in ('SHAPE','RESOURCE'):
            z={'LIB':0.}
            for a in ACTIONS[1:]:z[a]=md[mode][a].predict(fb.vector(held,a,mode,sc,held))
            row['predicted'][mode]=z
        oof.append(row)
    margins={}
    for mode in ('SHAPE','RESOURCE'):
        margins[mode]={}
        for a in ACTIONS[1:]:
            bases=('LIB',) if a in BASE else BASE
            for b in bases:
                err=[]
                for r in oof:
                    pred=r['predicted'][mode]
                    tbase=r['predicted_lib_us']*math.exp(pred[b])
                    e=(r['observed'][a]-r['observed'][b])-(pred[a]-pred[b])
                    err.append((tbase,e))
                margins[mode][a+'/'+b]=error_card(err)
    scale,lm,models=fit_subset(ids,None)
    return dict(status='CPU_FIT_ONLY_REQUIRES_NEW_INDEPENDENT_T10_TEST',target='log(T_action/T_LIB)',
                models={m:{a:v.to_dict() for a,v in d.items()} for m,d in models.items()},
                lib_scale_model=lm.to_dict(),distance_scale=scale.tolist(),margins=margins,oof=oof,
                n_independent_shapes=len(ids),n_raw_pair_rows=len(payload['pairs']),
                card_self_excluded_in_loso=True,coverage_guarantee=False,lambda_ridge=1.,
                source_protocol=payload['pairs'][0]['protocol_id'],state_epoch=payload['pairs'][0]['state_epoch'])

@dataclass(frozen=True)
class Decision:
    base_action:str
    chosen_action:str
    reason:str
    upper_ratio:float
    cost_ratio:float

def _score(logs,a,b,margin,setup,horizon,selection_delta,lib_us):
    if a not in logs or b not in logs or a not in setup or b not in setup:return None
    q=margin.get((a,b))
    if q is None or setup[a] is None or setup[b] is None:return None
    vals=[logs[a],logs[b],q,setup[a],setup[b],selection_delta,lib_us]
    if any(not math.isfinite(v) for v in vals) or min(q,setup[a],setup[b],selection_delta)<0 or lib_us<=0:return None
    if not -40<logs[a]-logs[b]+q<40 or not -40<logs[b]<40:return None
    tb=lib_us*math.exp(logs[b]);extra=max(0.,setup[a]-setup[b])/horizon
    ratio=math.exp(logs[a]-logs[b]+q);cost=(selection_delta+extra)/tb
    return ratio+cost,ratio,cost

def decide(logs:Mapping[str,float], margins:Mapping[tuple[str,str],float], setup_us:Mapping[str,float|None],
           predicted_lib_us:float, expected_reuse:int|None, selection_delta_us:float=0.,
           mode='RESOURCE',in_envelope=True,frozen_base:str|None=None)->Decision:
    """Use SHAPE base models/margins for the shared first-level choice.
    Call once with BASE, then pass frozen_base to RESOURCE/SHAPE if needed.
    No percentage or global absolute-us threshold is added here.
    """
    if not in_envelope or mode=='LIB_ALWAYS':return Decision('LIB','LIB','DIRECT_LIB',1.,0.)
    if mode not in ('BASE','SHAPE','RESOURCE'):raise ValueError('unknown policy')
    if expected_reuse is not None and (isinstance(expected_reuse,bool) or not isinstance(expected_reuse,int) or expected_reuse<1):raise ValueError('invalid reuse')
    h=expected_reuse if expected_reuse is not None else 1
    if frozen_base is not None and frozen_base not in BASE:raise ValueError('base must be a non-placement action')
    base=frozen_base or 'LIB';best=1.;base_rr=1.;base_cc=0.
    if frozen_base is None:
        for a in BASE[1:]:
            s=_score(logs,a,'LIB',margins,setup_us,h,selection_delta_us,predicted_lib_us)
            if s and s[0]<best:base=a;best,base_rr,base_cc=s
    if mode=='BASE':return Decision(base,base,'BASE_SELECTED' if base!='LIB' else 'KEEP_LIB',base_rr,base_cc)
    chosen=base;best=1.;rr=1.;cc=0.
    for a in ACTIONS[3:]:
        s=_score(logs,a,base,margins,setup_us,h,selection_delta_us,predicted_lib_us)
        if s and s[0]<best:chosen=a;best,rr,cc=s
    return Decision(base,chosen,'PC_NET_PREDICTION' if chosen!=base else 'KEEP_BASE',rr,cc)

def export_linear_header(model_json:dict)->str:
    """Straight-line host predictions. Caller supplies frozen features; no GPU LUT."""
    lines=['#pragma once','#include <cmath>','namespace relative_generated {']
    allmodels={'lib_log_us':model_json['lib_scale_model']}
    for mode,md in model_json['models'].items():
        allmodels.update({mode+'_'+a:d for a,d in md.items()})
    for name,d in allmodels.items():
        expr=format(d['beta'][0],'.17g')
        for i,(b,mu,sd) in enumerate(zip(d['beta'][1:],d['means'],d['scales'])):
            expr+=f' + ({b:.17g})*((x[{i}]-({mu:.17g}))/({sd:.17g}))'
        lines.append(f'inline double {name}(const double* x) noexcept {{ return {expr}; }}')
    lines.append('}');return '\n'.join(lines)+'\n'

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('output');ap.add_argument('--header')
    args=ap.parse_args();result=train(json.loads(Path(args.input).read_text()))
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    if args.header:Path(args.header).write_text(export_linear_header(result))
