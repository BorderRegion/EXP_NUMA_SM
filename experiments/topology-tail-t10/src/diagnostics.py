"""Descriptive model-transfer diagnostics; never changes frozen plans."""
from common import *
import numpy as np,pandas as pd
from analyze import stats

def run():
    model=[];arrival=[]
    for p in sorted(RUN.glob('dev_[0-9]')):
        for scope in PROTOCOL['scopes']:
            q=p/scope;c=q/'calibration';sel=read(c/'selected_before_validation.json');v=np.load(c/'validation_costs.npy')
            predicted=np.median(v,axis=0)
            timing=pd.read_csv(q/'timing.csv.gz');actual=timing[timing.phase=='test'].groupby('choice').gpu_us.median().reindex(range(132)).values/32
            model.append(dict(worker=p.name,scope=scope,pearson=float(np.corrcoef(predicted,actual)[0,1]),spearman=float(np.corrcoef(pd.Series(predicted).rank(),pd.Series(actual).rank())[0,1]),
                predicted_ns=predicted.tolist(),actual_operator_us=actual.tolist(),selected=sel['mapping']['JOINT']))
    for p in sorted(RUN.glob('*_[0-9]')):
        for q in p.glob('*/calibration/arrival_trace.npy'):
            a=np.load(q);local=a[:,:,1]-a[:,:,0];pair=a[:,:,2]-a[:,:,1];wait=a[:,:,4]-a[:,:,3]
            collectors=np.argmax(a[:,:,6],axis=1)
            stamps=np.unique(a[:,:,:6]);quantum=int(np.gcd.reduce(np.diff(stamps)))
            arrival.append(dict(worker=p.name,scope=q.parents[1].name,observed_stamp_difference_gcd_ns=quantum,median_local_ns=np.median(local,axis=0).tolist(),median_pair_ns=np.median(pair,axis=0).tolist(),median_wait_ns=np.median(wait,axis=0).tolist(),collectors=collectors.tolist(),note='Instrumented diagnostic; timing and register pressure differ from formal original binary. Not a causal nanosecond attribution. Stamp-difference GCD describes observed data granularity, not a universal timer guarantee.'))
    write(ROOT/'derived/MODEL_TRANSFER.json',model);write(ROOT/'derived/ARRIVAL_DIAGNOSTICS.json',arrival)
    sessions=pd.DataFrame(read(ROOT/'derived/NET_SESSIONS.json'));rows=[]
    for scope,g in sessions.groupby('scope'):
        a=g[g.policy=='BLIND'].set_index('worker');b=g[g.policy=='IDENTITY'].set_index('worker').loc[a.index]
        for metric in ['outer_s','gpu_s','host_s']:
            aa=a[metric].values+(0 if metric=='outer_s' else a.update_s.values);bb=b[metric].values+(0 if metric=='outer_s' else b.update_s.values)
            rows.append(dict(scope=scope,candidate='BLIND',control='IDENTITY',metric=metric,role='secondary static-rule transfer; offline development cost excluded and separately disclosed; not an address-specific causal effect',**stats(np.log(bb/aa))))
    write(ROOT/'derived/STATIC_RULE_TRANSFER.json',rows)
    # Post-outcome descriptive inspection of every arm, without deleting events
    # or replacing the frozen primary metric. Declared in POSTHOC_DIAGNOSTICS.
    tails=[]
    for p in sorted(RUN.glob('confirm_[0-9]')):
        for scope in PROTOCOL['scopes']:
            for policy in PROTOCOL['net_policies']:
                v=np.concatenate([np.load(p/scope/'net'/f'b{i:02d}_{policy}.npy') for i in range(16)])
                ix=np.argsort(v[:,1])[-5:][::-1]
                tails.append(dict(worker=p.name,scope=scope,policy=policy,gpu_sum_s=float(v[:,0].sum()/1e6),host_sum_s=float(v[:,1].sum()/1e6),
                    host_minus_event_sum_s=float((v[:,1]-v[:,0]).sum()/1e6),host_median_us=float(np.median(v[:,1])),gpu_median_us=float(np.median(v[:,0])),
                    top_host_replays=[dict(block=int(i//2050),replay=int(i%2050),conditioning=bool(i%2050<2),gpu_us=float(v[i,0]),host_us=float(v[i,1])) for i in ix],
                    note='Post-hoc descriptive timing tails. Host-minus-event is not separately measured CPU execution time; no scheduler trace was collected. No samples removed.'))
    write(ROOT/'derived/TIMING_TAILS.json',tails)
    print('DIAGNOSTICS COMPLETE',flush=True)
if __name__=='__main__':run()
