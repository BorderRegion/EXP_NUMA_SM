from common import *
import numpy as np,pandas as pd,itertools,sys

def interval(logs,confidence=.95):
    a=np.asarray(logs,dtype=float);n=len(a)
    if n<=6:
        ids=np.array(list(itertools.product(range(n),repeat=n)));means=a[ids].mean(axis=1)
    else:
        rng=np.random.default_rng(921);means=a[rng.integers(0,n,size=(50000,n))].mean(axis=1)
    tail=(1-confidence)/2;return np.quantile(100*np.expm1(means),[tail,1-tail]).tolist()
def stats(logs):
    a=np.asarray(logs,dtype=float)
    return dict(gain_pct=float(100*np.expm1(a.mean())),ci95=interval(a),ci_primary=interval(a,1-.05/16),positive_processes=int((a>0).sum()),processes=len(a),process_gains_pct=(100*np.expm1(a)).tolist())
def load(phase):
    frames=[]
    for p in sorted(RUN.glob(phase+'_[0-9]')):
        assert read(p/'complete.json')['status']=='PASS'
        for scope in PROTOCOL['scopes']:
            x=pd.read_csv(p/scope/'timing.csv.gz');x['worker']=p.name;frames.append(x)
    return pd.concat(frames,ignore_index=True)
def select():
    f=load('dev');m=f[f.phase=='test'].groupby(['scope','worker','block','choice']).gpu_us.median()
    rows=[];choices={}
    for scope,g in m.groupby(level='scope'):
        scores=np.log(g).groupby(level=['worker','choice']).mean().groupby(level='choice').mean();winner=int(scores.idxmin());choices[scope]=winner
        rows += [dict(scope=scope,choice=int(k),log_time=float(v)) for k,v in scores.items()]
    write(ROOT/'derived/DEVELOPMENT.json',rows)
    write(ROOT/'freeze/BLIND_BEST.json',dict(created_utc=utc(),choices=choices,source_hashes={str(p.relative_to(ROOT)):sha(p) for p in RUN.glob('dev_[0-9]/*/timing.csv.gz')},selection='minimum equal-process/block median GPU log time across all132 fixed candidates; no confirmation used'))
    print('BLIND FROZEN',choices,flush=True)
def short():
    f=load('confirm');m=f[f.phase=='test'].groupby(['scope','worker','block','policy'])[['gpu_us','host_us']].median();rows=[]
    for scope,g in m.groupby(level='scope'):
        for metric in ['gpu_us','host_us']:
            a=g[metric].unstack('policy')
            contrasts=[(p,'IDENTITY') for p in PROTOCOL['net_policies'] if p!='IDENTITY']+[(p,c) for p in ['JOINT','PLACE_ONLY'] for c in PROTOCOL['net_policies'] if c not in [p,'IDENTITY']]
            for candidate,control in contrasts:
                logs=np.log(a[control]/a[candidate]).groupby(level='worker').mean()
                rows.append(dict(scope=scope,metric=metric,candidate=candidate,control=control,candidate_us_per_request=float(a[candidate].mean()/32),control_us_per_request=float(a[control].mean()/32),**stats(logs)))
    write(ROOT/'derived/SHORT_RESULTS.json',rows)
    pd.DataFrame(rows).to_csv(ROOT/'derived/SHORT_RESULTS.csv',index=False)
    f.groupby(['scope','worker','policy','phase'])[['gpu_us','host_us']].median().reset_index().to_csv(ROOT/'derived/CADENCE.csv',index=False)
    return rows
def net():
    sessions=[]
    for p in sorted(RUN.glob('confirm_[0-9]')):
        for scope in PROTOCOL['scopes']:
            setup=read(p/scope/'calibration/selected_before_validation.json')['setup_ms']/1000
            q=p/scope/'net';x=pd.read_csv(q/'chunks.csv.gz')
            for policy,g in x.groupby('policy'):
                assert len(g)==PROTOCOL['net_blocks'] and g.timed_requests.sum()==PROTOCOL['net_requests']
                for r in g.itertuples():
                    v=np.load(q/f'b{r.block:02d}_{policy}.npy');assert v.shape==(2050,2) and np.isfinite(v).all() and (v>0).all()
                    assert abs(v[:,0].sum()-r.gpu_sum_us)<1e-6 and abs(v[:,1].sum()-r.host_sum_us)<1e-6
                sessions.append(dict(worker=p.name,scope=scope,policy=policy,choice=int(g.choice.iloc[0]),setup_s=setup,
                    outer_s=float(g.outer_wall_us.sum()/1e6),gpu_s=float(g.gpu_sum_us.sum()/1e6),host_s=float(g.host_sum_us.sum()/1e6),update_s=float(g.update_us.sum()/1e6),requests=int(g.timed_requests.sum()),conditioning_requests=int(g.conditioning_requests.sum())))
    write(ROOT/'derived/NET_SESSIONS.json',sessions);f=pd.DataFrame(sessions);rows=[]
    for scope,g in f.groupby('scope'):
        for candidate in ['JOINT','PLACE_ONLY','PAIR_ONLY']:
            a=g[g.policy==candidate].set_index('worker')
            for control in [p for p in PROTOCOL['net_policies'] if p!=candidate]:
                b=g[g.policy==control].set_index('worker').loc[a.index]
                for metric in ['outer_s','gpu_s','host_s']:
                    # Outer includes updates+conditioning. Diagnostic GPU/host
                    # sums add measured update wall separately, without double debit.
                    ca=a[metric].values+(0 if metric=='outer_s' else a.update_s.values)
                    cb=b[metric].values+(0 if metric=='outer_s' else b.update_s.values)
                    aa=ca+a.setup_s.values;bb=cb+(b.setup_s.values if candidate=='JOINT' and control=='JOINT_AA' else 0)
                    raw=np.log(cb/ca);logs=np.log(bb/aa)
                    primary=(candidate=='JOINT' and control in ['IDENTITY','BLIND','WRONG','POOL','SHADOW']) or (candidate=='PLACE_ONLY' and control in ['IDENTITY','BLIND','SHADOW'])
                    rows.append(dict(scope=scope,candidate=candidate,control=control,metric=metric,primary=primary,
                        candidate_raw_s=float(ca.mean()),candidate_with_setup_s=float(aa.mean()),control_accounted_s=float(bb.mean()),setup_s=float(a.setup_s.mean()),gross_gain_pct=float(100*np.expm1(raw.mean())),**stats(logs)))
    write(ROOT/'derived/NET_RESULTS.json',rows);pd.DataFrame(rows).to_csv(ROOT/'derived/NET_RESULTS.csv',index=False)
    print('NET',[{k:r[k] for k in ['scope','candidate','control','gain_pct','ci_primary','positive_processes']} for r in rows if r['metric']=='outer_s' and r['primary']],flush=True)
    return rows
def micro():
    rows=[];selections=[]
    for phase in ['dev','confirm']:
        for p in sorted(RUN.glob(phase+'_[0-9]')):
            for scope in PROTOCOL['scopes']:
                q=p/scope/'calibration';m=read(q/'selected_before_validation.json');final=read(q/'complete.json');a=np.load(q/'train_costs.npy');b=np.load(q/'validation_costs.npy')
                scores=np.array(m['train_scores']);h=len(b)//2;validation=np.maximum(np.median(b[:h],axis=0),np.median(b[h:],axis=0));corr=float(np.corrcoef(scores,validation)[0,1])
                for policy,idx in final['mapping'].items():
                    rows.append(dict(worker=p.name,phase=phase,scope=scope,policy=policy,choice=idx,train_ns=float(scores[idx]),validation_ns=float(validation[idx]),validation_vs_identity_pct=float(100*(validation[m['mapping']['IDENTITY']]/validation[idx]-1)),train_validation_correlation=corr))
                selections.append(dict(worker=p.name,phase=phase,scope=scope,setup_ms=m['setup_ms'],flags_va=m['flags_va'],shadow_flags_va=final['shadow_flags_va'],delay_min_ns=min(m['delay_ns']),delay_max_ns=max(m['delay_ns']),mapping={k:dict(index=i,**m['choices'][i]) for k,i in final['mapping'].items()}))
    write(ROOT/'derived/MICRO_VALIDATION.json',rows);write(ROOT/'derived/SELECTED_PLANS.json',selections)
if __name__=='__main__':
    if sys.argv[1]=='select':select()
    else:short();net();micro()
