from runtime import *
from calibrate import run as calibrate
import sys

def run(out,phase,process):
    verify_topology(out);cfg=PROTOCOL['development' if phase=='dev' else 'confirmation']
    rng=np.random.default_rng(cfg['seed']+process);w=Workspace()
    data={V:Data(V,cfg['seed']+process*1000000+V,w) for V in [131072,65536]}
    write(out/'allocations.json',{V:d.meta for V,d in data.items()})
    calibrate(w,out/'micro',cfg['seed']+process*1000000+777)
    order=list(PROTOCOL['conditions']);rng.shuffle(order);write(out/'condition_order.json',order)
    checks=[]
    names=PROTOCOL['policies']
    for case in order:
        V,page,scope=case['V'],case['page'],case['scope'];d=data[V]
        q=out/f'V{V}'/f'page{page}'/scope;q.mkdir(parents=True)
        jobs={n:[Job(d,slot,n,page,scope) for slot in range(4)] for n in names}
        # Keep policy order/slots randomized, but apply identical per-observation
        # GPU warmups. No compression/disk writing occurs between timed blocks.
        write(q/'graphs.json',{n:js[0].dag for n,js in jobs.items()})
        write(q/'setup.json',{n:[j.setup_ms for j in js] for n,js in jobs.items()})
        for n,js in jobs.items():
            for slot,j in enumerate(js):checks.append(dict(**case,policy=n,slot=slot,when='before',**j.check()))
        rows=[]
        warm=max(1,PROTOCOL['cadence']['warmup_requests_per_observation']//SCOPES[scope]['batch'])
        for block in range(cfg['blocks']):
            slot=block%4
            for position,name in enumerate(rng.permutation(names)):
                job=jobs[name][slot];start=time.monotonic_ns()
                values=job.run(1+warm+cfg['replays'])
                end=time.monotonic_ns()
                for k,values_k in enumerate(values):
                    stage='first_after_switch' if k==0 else 'conditioning' if k<=warm else 'test'
                    rows.append(dict(**case,phase=stage,block=block,slot=slot,position=position,
                        policy=name,replay=k,batch=job.batch,gpu_us=values_k[0],host_us=values_k[1],begin_ns=start,end_ns=end))
        save_rows(q/'timing.csv.gz',rows)
        for n,js in jobs.items():
            for slot,j in enumerate(js):
                checks.append(dict(**case,policy=n,slot=slot,when='after',**j.check()));j.close()
        write(out/'numerical.json',checks)
        write(q/'complete.json',dict(status='PASS',observations=len(rows),test_observations=cfg['blocks']*cfg['replays']*len(names)))
        print(phase,process,V,page,scope,'PASS',flush=True)
    write(out/'complete.json',dict(status='PASS',conditions=len(order),numerical_checks=len(checks)))
if __name__=='__main__':run(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3]))
