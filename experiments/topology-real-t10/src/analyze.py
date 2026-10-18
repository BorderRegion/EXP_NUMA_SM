from common import *
import numpy as np,pandas as pd,itertools,sys,functools
@functools.lru_cache(None)
def bootstrap_ids(n):return np.array(list(itertools.product(range(n),repeat=n)))
def stats(logs):
    a=np.asarray(logs,float);n=len(a);means=100*np.expm1(a[bootstrap_ids(n)].mean(axis=1))
    def ci(c):return np.quantile(means,[(1-c)/2,1-(1-c)/2]).tolist()
    return dict(gain_pct=float(100*np.expm1(a.mean())),ci95=ci(.95),ci_primary=ci(1-.05/20),positive_processes=int((a>0).sum()),processes=n,process_gains_pct=(100*np.expm1(a)).tolist())
def load(phase):
    f=[]
    for p in sorted(RUN.glob(phase+'_[0-9]')):
        assert read(p/'complete.json')['status']=='PASS'
        for scope in PROTOCOL['scopes']:
            x=pd.read_csv(p/scope/'timing.csv.gz');x['worker']=p.name;f.append(x)
    return pd.concat(f,ignore_index=True)
def development(save_static=True):
    f=load('dev');m=f[f.phase=='test'].groupby(['scope','worker','block','choice']).gpu_us.median();choices={};rows=[]
    for scope,g in m.groupby(level='scope'):
        scores=np.log(g).groupby(level=['worker','choice']).mean().groupby(level='choice').mean();choices[scope]=int(scores.idxmin())
        rows += [dict(scope=scope,choice=int(k),log_time=float(v)) for k,v in scores.items()]
    write(ROOT/'derived/DEVELOPMENT.json',rows)
    if save_static:write(ROOT/'freeze/STATIC.json',dict(created_utc=utc(),choices=choices,source_hashes={str(p.relative_to(ROOT)):sha(p) for p in RUN.glob('dev_[0-9]/*/timing.csv.gz')},selection='minimum equal-process/block median GPU log time among16 fixed candidates; no confirmation used'))
    else:assert choices==read(ROOT/'freeze/STATIC.json')['choices']
    print('STATIC',choices,flush=True)
def short():
    f=load('confirm');m=f[f.phase=='test'].groupby(['scope','worker','block','policy'])[['gpu_us','host_us']].median();rows=[]
    for scope,g in m.groupby(level='scope'):
        for metric in ['gpu_us','host_us']:
            a=g[metric].unstack('policy')
            pairs=[(p,'BASE') for p in PROTOCOL['net_policies'] if p!='BASE']+[(p,c) for p in ['TUNED','PLACE_ONLY'] for c in PROTOCOL['net_policies'] if c not in [p,'BASE']]
            for p,c in pairs:
                logs=np.log(a[c]/a[p]).groupby(level='worker').mean();rows.append(dict(scope=scope,metric=metric,candidate=p,control=c,candidate_us=float(a[p].mean()/32),control_us=float(a[c].mean()/32),**stats(logs)))
    write(ROOT/'derived/SHORT_RESULTS.json',rows);pd.DataFrame(rows).to_csv(ROOT/'derived/SHORT_RESULTS.csv',index=False)
def net():
    sessions=[];tails=[]
    for p in sorted(RUN.glob('confirm_[0-9]')):
        for scope in PROTOCOL['scopes']:
            q=p/scope/'net';x=pd.read_csv(q/'chunks.csv.gz');setup=read(p/scope/'calibration/selected.json')['setup_ms']/1000
            for policy,g in x.groupby('policy'):
                assert len(g)==16 and g.timed_requests.sum()==1048576
                arrays=[]
                for r in g.sort_values('block').itertuples():
                    v=np.load(q/f'b{r.block:02d}_{policy}.npy');assert v.shape==(2050,2) and np.isfinite(v).all() and (v>0).all()
                    assert abs(v[:,0].sum()-r.gpu_sum_us)<1e-6 and abs(v[:,1].sum()-r.host_sum_us)<1e-6;arrays.append(v)
                v=np.concatenate(arrays);ix=np.argsort(v[:,1])[-5:][::-1]
                tails.append(dict(worker=p.name,scope=scope,policy=policy,host_minus_event_s=float((v[:,1]-v[:,0]).sum()/1e6),top_host=[dict(block=int(i//2050),replay=int(i%2050),gpu_us=float(v[i,0]),host_us=float(v[i,1])) for i in ix]))
                for blocks in [4,16]:
                    z=g[g.block<blocks]
                    sessions.append(dict(worker=p.name,scope=scope,policy=policy,choice=int(g.choice.iloc[0]),setup_s=setup,outer_s=float(z.outer_wall_us.sum()/1e6),gpu_s=float(z.gpu_sum_us.sum()/1e6),host_s=float(z.host_sum_us.sum()/1e6),update_s=float(z.update_us.sum()/1e6),requests=int(z.timed_requests.sum()),conditioning_requests=int(z.conditioning_requests.sum())))
    write(ROOT/'derived/NET_SESSIONS.json',sessions);write(ROOT/'derived/TIMING_TAILS.json',tails);f=pd.DataFrame(sessions);rows=[]
    for (scope,requests),g in f.groupby(['scope','requests']):
        for candidate in ['TUNED','PLACE_ONLY','PAIR_ONLY']:
            a=g[g.policy==candidate].set_index('worker')
            for control in [p for p in PROTOCOL['net_policies'] if p!=candidate]:
                b=g[g.policy==control].set_index('worker').loc[a.index]
                for metric in ['outer_s','gpu_s','host_s']:
                    ca=a[metric].values+(0 if metric=='outer_s' else a.update_s.values);cb=b[metric].values+(0 if metric=='outer_s' else b.update_s.values)
                    aa=ca+a.setup_s.values;bb=cb+(b.setup_s.values if candidate=='TUNED' and control=='TUNED_AA' else 0)
                    primary=requests==1048576 and metric=='outer_s' and control in PROTOCOL['primary_comparators'].get(candidate,[])
                    rows.append(dict(scope=scope,requests=int(requests),candidate=candidate,control=control,metric=metric,primary=primary,candidate_raw_s=float(ca.mean()),candidate_with_setup_s=float(aa.mean()),control_accounted_s=float(bb.mean()),setup_s=float(a.setup_s.mean()),gross_gain_pct=float(100*np.expm1(np.log(cb/ca).mean())),**stats(np.log(bb/aa))))
    write(ROOT/'derived/NET_RESULTS.json',rows);pd.DataFrame(rows).to_csv(ROOT/'derived/NET_RESULTS.csv',index=False)
    print('PRIMARY',[{k:r[k] for k in ['scope','candidate','control','gain_pct','ci_primary','positive_processes']} for r in rows if r['primary']],flush=True)
    static=[]
    for (scope,requests),g in f.groupby(['scope','requests']):
        b=g[g.policy=='BASE'].set_index('worker')
        for c in ['LEGACY','FROZEN','STATIC']:
            a=g[g.policy==c].set_index('worker').loc[b.index]
            for metric in ['outer_s','gpu_s','host_s']:
                aa=a[metric].values+(0 if metric=='outer_s' else a.update_s.values);bb=b[metric].values+(0 if metric=='outer_s' else b.update_s.values)
                static.append(dict(scope=scope,requests=int(requests),candidate=c,control='BASE',metric=metric,**stats(np.log(bb/aa))))
    write(ROOT/'derived/STATIC_CONTROLS.json',static)
def calibration():
    from selector import decide
    rows=[]
    for phase in ['dev','confirm']:
        for p in sorted(RUN.glob(phase+'_[0-9]')):
            for scope in PROTOCOL['scopes']:
                for kind in ['calibration','shadow']:
                    q=p/scope/kind;m=read(q/'selected.json');s=np.load(q/'screen.npy');r=np.load(q/'refine.npy');si=np.load(q/'screen_ids.npy');ri=np.load(q/'refine_ids.npy')
                    mapping,fit=decide(si,s[:,1:].reshape(-1,2,2)[:,1,0],ri,r[:,1:].reshape(-1,3,2)[:,1:,0]);assert mapping==m['mapping'] and fit==m['fit']
                    rows.append(dict(worker=p.name,phase=phase,scope=scope,kind=kind,setup_ms=m['setup_ms'],flags_va=m['flags_va'],mapping=mapping,fit=fit,calibration_operator_calls=m['calibration_operator_calls']))
    write(ROOT/'derived/CALIBRATION.json',rows)
if __name__=='__main__':
    if sys.argv[1]=='select':development()
    else:short();net();calibration()
