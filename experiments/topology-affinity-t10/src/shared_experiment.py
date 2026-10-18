from shared_runtime import *
from calibrate import run as calibrate
import sys
def qualify(out):
    verify_topology(out);w=Workspace();d=Data(131072,910131072,w,ring=1);checks=[]
    for scope in SCOPES:
        job=SharedJob(d,0,17,scope,trace=True)
        for name in ['IDENTITY','SAME_GPC','CROSS_GPC','RND00','IDENTITY']:
            us=job.set(name);job.run();x=d.check(0)
            tr=w.trace.cpu().view(56,2).numpy();assert np.array_equal(np.sort(tr[:,0]),np.arange(56)) and np.array_equal(tr[:,0],tr[:,1])
            checks.append(dict(scope=scope,policy=name,update_us=us,handles=job.identity,**x))
        job.close()
    write(out/'numerical.json',checks);write(out/'complete.json',dict(status='PASS',checks=len(checks)))
    print('SHARED GRAPH QUALIFICATION PASS',len(checks),flush=True)
def run(out,process):
    verify_topology(out);protocol=read(ROOT/'freeze/SHARED_GRAPH_PROTOCOL.json')
    seed=protocol['seed']+process*1000000;rng=np.random.default_rng(seed)
    w=Workspace();d=Data(131072,seed+131072,w)
    write(out/'allocations.json',{131072:d.meta});calibrate(w,out/'micro',seed+777)
    checks=[];names=PROTOCOL['policies'];order=list(SCOPES);rng.shuffle(order);write(out/'scope_order.json',order)
    for scope in order:
        q=out/'V131072/page17'/scope;q.mkdir(parents=True);jobs=[SharedJob(d,s,17,scope) for s in range(4)]
        write(q/'graphs.json',{'SHARED':jobs[0].dag});write(q/'handles.json',[j.identity for j in jobs])
        for name in names:
            for slot,job in enumerate(jobs):job.set(name);job.run();checks.append(dict(scope=scope,policy=name,slot=slot,when='before',**d.check(slot)))
        rows=[];warm=max(1,64//SCOPES[scope]['batch'])
        for block in range(protocol['blocks']):
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
        print('shared',process,scope,'PASS',flush=True)
    write(out/'complete.json',dict(status='PASS',conditions=4,numerical_checks=len(checks)))
if __name__=='__main__':
    if sys.argv[2]=='qualify':qualify(Path(sys.argv[1]))
    else:run(Path(sys.argv[1]),int(sys.argv[2]))
