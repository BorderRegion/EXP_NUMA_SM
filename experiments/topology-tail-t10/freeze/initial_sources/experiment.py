from tail_runtime import *
import sys
def run(out,phase,process):
    verify_topology(out);seed=PROTOCOL['seed_development' if phase=='dev' else 'seed_confirmation']+process*1000000
    rng=np.random.default_rng(seed);w=Workspace();d=Data(PROTOCOL['V'],seed,w);write(out/'allocations.json',d.meta)
    checks=[];order=list(SCOPES);rng.shuffle(order);write(out/'scope_order.json',order)
    for scope in order:
        q=out/scope;q.mkdir();maps,setup=calibrate(d,scope,q/'calibration',seed+100+list(SCOPES).index(scope)*10000)
        jobs=[SharedJob(d,s,scope) for s in range(4)];write(q/'handles.json',[j.identity for j in jobs]);write(q/'graph.json',jobs[0].dag)
        if phase=='dev':policies={f'C{i:03d}':i for i in range(len(CHOICES))};blocks=PROTOCOL['development_blocks']
        else:
            maps['BLIND']=read(ROOT/'freeze/BLIND_BEST.json')['choices'][scope];policies=maps;blocks=PROTOCOL['confirmation_blocks']
        write(q/'policy_choices.json',policies)
        for name,idx in policies.items():
            job=jobs[0];job.set(idx);job.run();checks.append(dict(scope=scope,policy=name,slot=0,when='before',**job.check()))
        rows=[]
        for block in range(blocks):
            job=jobs[block%4]
            for pos,name in enumerate(rng.permutation(list(policies))):
                begin=time.perf_counter_ns();update=job.set(policies[name]);values=job.run(2+PROTOCOL['replays']);wall=(time.perf_counter_ns()-begin)/1000
                for k,v in enumerate(values):rows.append(dict(process=process,scope=scope,block=block,slot=block%4,position=pos,policy=name,choice=policies[name],phase='conditioning' if k<2 else 'test',replay=k,gpu_us=v[0],host_us=v[1],update_us=update,outer_wall_us=wall,batch=32))
        save_rows(q/'timing.csv.gz',rows)
        for name,idx in policies.items():
            for slot,job in enumerate(jobs):job.set(idx);job.run();checks.append(dict(scope=scope,policy=name,slot=slot,when='after',**job.check()))
        for job in jobs:job.close()
        write(out/'numerical.json',checks)
        if phase=='confirm':
            nq=q/'net';nq.mkdir();job=SharedJob(d,0,scope);write(nq/'config.json',dict(policies=policies,handles=job.identity,requests=PROTOCOL['net_requests'],blocks=PROTOCOL['net_blocks'],warmup_graphs_per_chunk=2))
            rows=[];n=PROTOCOL['net_requests']//32//PROTOCOL['net_blocks']
            for block in range(PROTOCOL['net_blocks']):
                for pos,name in enumerate(rng.permutation(PROTOCOL['net_policies'])):
                    start=time.perf_counter_ns();update=job.set(policies[name]);v=job.run(n+2);wall=(time.perf_counter_ns()-start)/1000
                    np.save(nq/f'b{block:02d}_{name}.npy',v)
                    rows.append(dict(block=block,scope=scope,position=pos,policy=name,choice=policies[name],update_us=update,outer_wall_us=wall,gpu_sum_us=float(v[:,0].sum()),host_sum_us=float(v[:,1].sum()),timed_requests=n*32,conditioning_requests=64))
                print('net',process,scope,block,'PASS',flush=True)
            save_rows(nq/'chunks.csv.gz',rows)
            for name,idx in policies.items():job.set(idx);job.run();checks.append(dict(scope=scope,policy=name,slot=0,when='net_after',**job.check()))
            job.close();write(out/'numerical.json',checks)
            write(nq/'complete.json',dict(status='PASS',chunks=len(rows)))
        write(q/'complete.json',dict(status='PASS',scope=scope,setup_ms=setup,observations=len(rows)))
        print(phase,process,scope,'COMPLETE',flush=True)
    write(out/'complete.json',dict(status='PASS',numerical_checks=len(checks),phase=phase,process=process))
if __name__=='__main__':run(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3]))
