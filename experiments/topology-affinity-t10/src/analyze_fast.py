from common import *
from analyze import operator,result,intervals
import numpy as np,pandas as pd
def run():
    operator('fast')  # New Latin data has no isolated validation tensor.
    sessions=[]
    for worker in sorted(RUN.glob('fast_[0-9]')):
        assert read(worker/'complete.json')['status']=='PASS'
        setup=read(worker/'micro/setup.json')['total_setup_ms']
        for scope in ['batch','freshbatch']:
            q=worker/'net'/scope;x=pd.read_csv(q/'chunks.csv.gz')
            for name,g in x.groupby('policy'):
                assert g.requests.sum()==1048576 and len(g)==16
                saved=[]
                for row in g.itertuples():
                    a=np.load(q/f'b{row.block:02d}_{name}.npy');assert a.shape==(2048,2)
                    assert np.isfinite(a).all() and (a>0).all()
                    assert abs(a[:,0].sum()-row.gpu_sum_us)<1e-6
                    assert abs(a[:,1].sum()-row.host_sum_us)<1e-6
                    saved.append(dict(block=int(row.block),data_mtime_ns=(q/f'b{row.block:02d}_{name}.npy').stat().st_mtime_ns))
                sessions.append(dict(process=worker.name,scope=scope,policy=name,requests=int(g.requests.sum()),
                    setup_s=setup/1000,updates_s=float(g.update_us.sum()/1e6),
                    outer_wall_s=float(g.outer_wall_us.sum()/1e6),gpu_s=float(g.gpu_sum_us.sum()/1e6),
                    launch_to_output_s=float(g.host_sum_us.sum()/1e6),timestamps=saved))
    write(ROOT/'derived/NET_SESSIONS.json',sessions)
    f=pd.DataFrame([{k:v for k,v in x.items() if k!='timestamps'} for x in sessions]);rows=[]
    for scope,g in f.groupby('scope'):
        a=g[g.policy=='ALL_ADDR'].set_index('process')
        for control,ctrl in g[g.policy!='ALL_ADDR'].groupby('policy'):
            b=ctrl.set_index('process').loc[a.index]
            for metric in ['outer_wall_s','gpu_s','launch_to_output_s']:
                raw_a=a[metric].values;raw_b=b[metric].values
                extra=(a.setup_s+a.updates_s).values
                logs=np.log(raw_b/(raw_a+extra));rawlogs=np.log(raw_b/raw_a)
                saving=raw_b-raw_a
                be=[float(extra[i]/saving[i]*1048576) if saving[i]>0 else None for i in range(len(saving))]
                rows.append(dict(scope=scope,control=control,metric=metric,requests_per_arm=1048576,
                    candidate_raw_s=float(raw_a.mean()),candidate_with_setup_s=float((raw_a+extra).mean()),control_s=float(raw_b.mean()),
                    setup_plus_updates_s=float(extra.mean()),gross_gain_pct=float(100*np.expm1(rawlogs.mean())),
                    **result(logs),ci_net_family=intervals(logs,1-.05/8),break_even_requests_per_process=be))
    write(ROOT/'derived/NET_RESULTS.json',rows)
    print('NET RESULTS',[{k:x[k] for k in ['scope','control','gain_pct','ci95','ci_net_family','positive_processes']} for x in rows if x['metric']=='outer_wall_s'])
    if not (ROOT/'reports/FAST_GPU_COMPLETE.json').exists():
        ledger=[json.loads(x) for x in (RUN/'ledger.jsonl').read_text().splitlines()]
        finished=max(x['ended'] for x in ledger if x['key'].startswith('fast_'))
        write(ROOT/'reports/FAST_GPU_COMPLETE.json',dict(gpu_workers_ended_utc=finished,analysis_completed_utc=utc(),status='COMPLETE',
              note='GPU workers finished; Latin tensors analyzed by dedicated reader. Original generic analysis failure retained.'))
if __name__=='__main__':run()
