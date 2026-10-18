from fast_calibrate import run as calibrate, solver_qualification
from shared_runtime import *
import sys
def run(out,process,qualification=False):
    verify_topology(out);protocol=read(ROOT/'freeze/FAST_SETUP_PROTOCOL.json')
    seed=(1130000000 if qualification else protocol['seed']+process*1000000)
    rng=np.random.default_rng(seed);tests=solver_qualification() if qualification else 0
    w=Workspace();d=Data(131072,seed+131072,w);write(out/'allocations.json',{131072:d.meta})
    calibrate(w,out/'micro',seed+777);checks=[]
    # Short steady-state experiment: all18 policies,4 complete operator scopes.
    order=list(SCOPES);rng.shuffle(order);write(out/'scope_order.json',order)
    for scope in order:
        q=out/'V131072/page17'/scope;q.mkdir(parents=True);jobs=[SharedJob(d,s,17,scope,trace=qualification) for s in range(4)]
        write(q/'graphs.json',{'SHARED':jobs[0].dag});write(q/'handles.json',[j.identity for j in jobs])
        names=PROTOCOL['policies'] if not qualification else ['IDENTITY','GPC_ADDR','ALL_ADDR','ALL_WRONG']
        for name in names:
            for slot,job in enumerate(jobs):
                job.set(name);job.run();x=d.check(slot)
                if qualification:
                    tr=w.trace.cpu().view(56,2).numpy();assert np.array_equal(np.sort(tr[:,0]),np.arange(56)) and np.array_equal(tr[:,0],tr[:,1])
                checks.append(dict(scope=scope,policy=name,slot=slot,when='before',**x))
        rows=[];warm=max(1,64//SCOPES[scope]['batch'])
        if not qualification:
            for block in range(protocol['steady_blocks']):
                slot=block%4;job=jobs[slot]
                for pos,name in enumerate(rng.permutation(names)):
                    update_us=job.set(name);begin=time.monotonic_ns();values=job.run(1+warm+protocol['replays']);end=time.monotonic_ns()
                    for k,z in enumerate(values):
                        stage='first_after_switch' if k==0 else 'conditioning' if k<=warm else 'test'
                        rows.append(dict(V=131072,page=17,scope=scope,phase=stage,block=block,slot=slot,position=pos,policy=name,replay=k,batch=job.batch,gpu_us=z[0],host_us=z[1],update_us=update_us,begin_ns=begin,end_ns=end))
            save_rows(q/'timing.csv.gz',rows)
        for name in names:
            for slot,job in enumerate(jobs):job.set(name);job.run();checks.append(dict(scope=scope,policy=name,slot=slot,when='after',**d.check(slot)))
        for job in jobs:job.close()
        write(q/'complete.json',dict(status='PASS',observations=len(rows)));write(out/'numerical.json',checks)
        print('fast',process,scope,'PASS',flush=True)
    if not qualification:
        choices=read(ROOT/'freeze/RANDOM_BEST.json')['choices']
        netorder=['batch','freshbatch'];rng.shuffle(netorder);write(out/'net_scope_order.json',netorder)
        for scope in netorder:
            q=out/'net'/scope;q.mkdir(parents=True);job=SharedJob(d,0,17,scope)
            random_name=choices[f'131072/17/{scope}']
            names=['IDENTITY','ALL_ADDR','ALL_WRONG','ALL_POOL',random_name]
            write(q/'config.json',dict(policies=names,handles=job.identity,requests_per_policy=protocol['requests_per_policy'],blocks=protocol['net_blocks'],batch=32,graph_replays_per_block=protocol['requests_per_policy']//32//protocol['net_blocks']))
            rows=[]
            for block in range(protocol['net_blocks']):
                for pos,name in enumerate(rng.permutation(names)):
                    update_us=job.set(name);job.run(2)
                    t0=time.perf_counter_ns();values=job.run(protocol['requests_per_policy']//32//protocol['net_blocks']);wall_us=(time.perf_counter_ns()-t0)/1000
                    # Preserve every graph event/host measurement. Outer chunk
                    # wall includes ctypes preparation and result extraction.
                    np.save(q/f'b{block:02d}_{name}.npy',values)
                    rows.append(dict(scope=scope,block=block,position=pos,policy=name,update_us=update_us,
                        outer_wall_us=wall_us,gpu_sum_us=float(values[:,0].sum()),host_sum_us=float(values[:,1].sum()),
                        graph_replays=len(values),requests=len(values)*32))
                print('net',process,scope,block,'PASS',flush=True)
            save_rows(q/'chunks.csv.gz',rows)
            for name in names:job.set(name);job.run();checks.append(dict(scope='net_'+scope,policy=name,slot=0,when='after',**d.check(0)))
            job.close();write(out/'numerical.json',checks);write(q/'complete.json',dict(status='PASS',chunks=len(rows)))
    write(out/'complete.json',dict(status='PASS',conditions=4,numerical_checks=len(checks),solver_checks=tests,qualification=qualification))
if __name__=='__main__':run(Path(sys.argv[1]),int(sys.argv[2]) if sys.argv[2]!='qualify' else 0,sys.argv[2]=='qualify')
