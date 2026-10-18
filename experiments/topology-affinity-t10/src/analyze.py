from common import *
import numpy as np,pandas as pd
from topology_math import DT,residual,corr

def paths(phase):return sorted(p for p in RUN.glob(phase+'_*') if (p/'complete.json').exists())
def key(V,page,scope):return f'{V}/{page}/{scope}'
def intervals(logs,confidence=.95,seed=921):
    x=np.asarray(logs,float);rng=np.random.default_rng(seed)
    means=x[rng.integers(0,len(x),size=(30000,len(x)))].mean(axis=1)
    alpha=(1-confidence)/2
    lo,hi=np.quantile(100*np.expm1(means),[alpha,1-alpha])
    return [float(lo),float(hi)]
def result(logs):
    logs=np.asarray(logs)
    return dict(gain_pct=float(100*np.expm1(logs.mean())),ci95=intervals(logs),
        ci_primary=intervals(logs,1-.05/32),positive_processes=int((logs>0).sum()),
        processes=len(logs),process_gains_pct=(100*np.expm1(logs)).tolist())
def load_operator(phase):
    frames=[]
    for p in paths(phase):
        for q in p.glob('V*/page*/*/timing.csv.gz'):
            x=pd.read_csv(q);x['process']=p.name;frames.append(x)
    assert frames
    return pd.concat(frames,ignore_index=True)
def operator(phase,select=False):
    raw=load_operator(phase);test=raw[raw.phase=='test']
    # Each timing is a complete graph: one or 32 complete operators, including
    # the copy in fresh scopes. Ratios use the same batch size on both sides.
    median=test.groupby(['V','page','scope','process','block','policy'])[['gpu_us','host_us']].median()
    if select:
        choices={}
        for (V,p,s),f in test.groupby(['V','page','scope']):
            scores={n:float(np.log(g.gpu_us).mean()) for n,g in f[f.policy.str.startswith('RND')].groupby('policy')}
            choices[key(V,p,s)]=min(scores,key=scores.get)
        write(ROOT/'freeze/RANDOM_BEST.json',dict(created_utc=utc(),choices=choices,
             source=[dict(worker=p.name,timing_hashes={str(f.relative_to(p)):sha(f) for f in p.glob('V*/page*/*/timing.csv.gz')}) for p in paths(phase)]))
    frozen=read(ROOT/'freeze/RANDOM_BEST.json')['choices']
    rows=[]
    for (V,p,s),g in median.groupby(level=['V','page','scope']):
        for metric in ['gpu_us','host_us']:
            table=g[metric].unstack('policy')
            for candidate in ['GPC_ADDR','ALL_ADDR','SAME_GPC','CROSS_GPC','ALIAS_IDENTITY']:
                prefix=candidate.split('_')[0]
                controls=['IDENTITY']
                if candidate in ['GPC_ADDR','ALL_ADDR']:controls += [frozen[key(V,p,s)],prefix+'_WRONG',prefix+'_POOL']
                for control in controls:
                    log=np.log(table[control]/table[candidate]).groupby(level='process').mean()
                    denom=1 if s in ['ready','fresh'] else 32
                    rows.append(dict(V=int(V),page=int(p),scope=s,metric=metric,candidate=candidate,control=control,
                        control_role='RANDOM_BEST' if control.startswith('RND') else control,
                        candidate_us_per_request=float(table[candidate].mean()/denom),control_us_per_request=float(table[control].mean()/denom),
                        **result(log.values)))
    write(ROOT/f'derived/{phase}_operator.json',rows)
    # Preserve observations at every position; do not drop inconvenient firsts.
    cadence=raw.groupby(['V','page','scope','process','policy','phase'])[['gpu_us','host_us']].median().reset_index()
    cadence.to_csv(ROOT/f'derived/{phase}_cadence.csv',index=False)
    print(phase,'OPERATOR',[{k:x[k] for k in ['candidate','scope','gain_pct','ci95','positive_processes']}
        for x in rows if x['V']==131072 and x['page']==17 and x['control']=='IDENTITY' and x['metric']=='gpu_us' and x['candidate'].endswith('_ADDR')],flush=True)
    return rows
def micro(phase):
    topo=read(ROOT/'freeze/HARDWARE_TOPOLOGY.json')['global_sm_order']['entries']
    gpc=np.array([x['gpc'] for x in topo]);tpc=np.array([x['global_tpc'] for x in topo])
    sameg=gpc[::2,None]==gpc[None,1::2];samet=tpc[::2,None]==tpc[None,1::2]
    classes={'same_tpc':samet,'same_gpc_other_tpc':sameg&~samet,'cross_gpc':~sameg}
    # Two-way source/destination fixed effects plus two hierarchy indicators.
    ii,jj=np.indices((28,28));features=np.column_stack([np.ones(784),np.eye(28)[ii.ravel(),1:],np.eye(28)[jj.ravel(),1:],samet.ravel(),(sameg&~samet).ravel()])
    assert np.linalg.matrix_rank(features)==features.shape[1]
    per=[];con=[];policy=[]
    for worker in paths(phase):
        m=worker/'micro';z=np.load(m/'matrices.npz');maps=read(m/'allocation_maps.json')['maps']
        for unit in ['cycles','ns']:
            train=z['train_'+unit];validation=z['validation_'+unit]
            for pi,page in enumerate(PROTOCOL['micro']['pages']):
                y=validation[:,pi].mean(axis=0);tr=train[:,pi].mean(axis=0)
                rowmeans={k:np.array([y[i,mask[i]].mean() for i in range(28)]) for k,mask in classes.items()}
                coef=np.linalg.lstsq(features,y.ravel(),rcond=None)[0]
                for c in ['same_tpc','same_gpc_other_tpc']:
                    per.append(dict(process=worker.name,page=page,unit=unit,comparison=c+'/cross_gpc',
                        log_advantage=float(np.log(rowmeans['cross_gpc']/rowmeans[c]).mean()),
                        class_mean=float(rowmeans[c].mean()),cross_mean=float(rowmeans['cross_gpc'].mean()),
                        fixed_effect_difference_vs_cross=float(coef[-2 if c=='same_tpc' else -1]),
                        residual_correlation=corr(residual(tr),residual(y))))
                for mapping in maps:
                    if mapping['page']!=page:continue
                    perm=(np.array(mapping['consumer_per_producer'])-1)//2
                    vv=y[np.arange(28),perm];ident=np.diag(y)
                    policy.append(dict(process=worker.name,page=page,unit=unit,policy=mapping['policy'],mean=float(vv.mean()),max=float(vv.max()),identity_mean=float(ident.mean()),identity_max=float(ident.max())))
        plans=np.load(m/'concurrent_plans.npy');r=np.fromfile(m/'concurrent.bin',dtype=DT).reshape(-1,28)
        for i,row in enumerate(plans):
            for unit in ['cycles','ns']:
                v=r[unit][i]/row[6]
                con.append(dict(process=worker.name,page=int(row[3]),round=int(row[1]),policy=PROTOCOL['policies'][row[8]],unit=unit,mean=float(v.mean()),max=float(v.max())))
    write(ROOT/f'derived/{phase}_micro_processes.json',per)
    write(ROOT/f'derived/{phase}_heldout_policy.json',policy)
    frame=pd.DataFrame(per);summary=[]
    for (page,unit,c),x in frame.groupby(['page','unit','comparison']):
        summary.append(dict(page=int(page),unit=unit,comparison=c,**result(x.log_advantage.values),
            class_mean=float(x.class_mean.mean()),cross_mean=float(x.cross_mean.mean()),
            fixed_effect_difference_vs_cross=float(x.fixed_effect_difference_vs_cross.mean()),
            fixed_effect_process_values=x.fixed_effect_difference_vs_cross.tolist(),residual_correlations=x.residual_correlation.tolist()))
    write(ROOT/f'derived/{phase}_micro_summary.json',summary)
    pd.DataFrame(con).to_csv(ROOT/f'derived/{phase}_concurrent.csv.gz',index=False)
    conframe=pd.DataFrame(con);cres=[]
    for (page,unit),g in conframe.groupby(['page','unit']):
        for metric in ['mean','max']:
            table=g.pivot(index=['process','round'],columns='policy',values=metric)
            for n in ['SAME_GPC','CROSS_GPC','GPC_ADDR','ALL_ADDR','ALIAS_IDENTITY']:
                logs=np.log(table.IDENTITY/table[n]).groupby('process').mean()
                cres.append(dict(page=int(page),unit=unit,metric=metric,candidate=n,control='IDENTITY',**result(logs)))
    write(ROOT/f'derived/{phase}_concurrent_summary.json',cres)
    return summary
if __name__=='__main__':
    import sys
    phase=sys.argv[1];operator(phase,'--select' in sys.argv);micro(phase)
