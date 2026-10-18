from real_runtime import *
import sys
def run(out,phase,process):
    verify_topology(out);seed=PROTOCOL['seed_development' if phase=='dev' else 'seed_confirmation']+process*1000000
    rng=np.random.default_rng(seed);w=Workspace();d=Data(PROTOCOL['V'],seed,w);write(out/'allocations.json',d.meta)
    checks=[];order=list(SCOPES);rng.shuffle(order);write(out/'scope_order.json',order)
    for scope in order:
        q=out/scope;q.mkdir();jobs=[SharedJob(d,s,scope) for s in range(4)]
        write(q/'handles.json',[j.identity for j in jobs]);write(q/'graph.json',jobs[0].dag)
        target=calibrate(jobs[0],q/'calibration',seed+100+list(SCOPES).index(scope)*10000)
        checks.append(dict(scope=scope,kind='target_calibration',**jobs[0].check()))
        # Same input/output, operator and Graph; only flags allocation changes.
        shadow=Workspace();jobs[0].w=shadow
        other=calibrate(jobs[0],q/'shadow',seed+200+list(SCOPES).index(scope)*10000)
        checks.append(dict(scope=scope,kind='shadow_calibration',**jobs[0].check()));jobs[0].w=w
        mapping=target['mapping'].copy();mapping['SHADOW']=other['mapping']['TUNED'];mapping['FROZEN']=PROTOCOL['frozen_best'][scope]
        write(q/'calibration_seal.json',dict(target=sha(q/'calibration/selected.json'),shadow=sha(q/'shadow/selected.json'),created_utc=utc(),mapping=mapping))
        if phase=='dev':policies={f'C{i:03d}':i for i in CANDIDATES};blocks=PROTOCOL['development_blocks']
        else:
            mapping['STATIC']=read(ROOT/'freeze/STATIC.json')['choices'][scope];policies=mapping;blocks=PROTOCOL['confirmation_blocks']
        write(q/'policy_choices.json',policies)
        for name,k in policies.items():jobs[0].set(k);jobs[0].run();checks.append(dict(scope=scope,policy=name,slot=0,when='before',**jobs[0].check()))
        rows=[]
        for block in range(blocks):
            job=jobs[block%4]
            for pos,name in enumerate(rng.permutation(list(policies))):
                begin=time.perf_counter_ns();update=job.set(policies[name]);v=job.run(2+PROTOCOL['replays']);wall=(time.perf_counter_ns()-begin)/1000
                for k,x in enumerate(v):rows.append(dict(scope=scope,block=block,slot=block%4,position=pos,policy=name,choice=policies[name],phase='conditioning' if k<2 else 'test',replay=k,gpu_us=x[0],host_us=x[1],update_us=update,outer_wall_us=wall))
        save_rows(q/'timing.csv.gz',rows)
        for name,k in policies.items():
            for slot,job in enumerate(jobs):job.set(k);job.run();checks.append(dict(scope=scope,policy=name,slot=slot,when='after',**job.check()))
        write(out/'numerical.json',checks)
        if phase=='confirm':
            nq=q/'net';nq.mkdir();job=jobs[0];rows=[];n=PROTOCOL['net_requests']//32//PROTOCOL['net_blocks']
            write(nq/'config.json',dict(policies=policies,handles=job.identity,requests=PROTOCOL['net_requests'],blocks=16,warmup_graphs_per_chunk=2))
            for block in range(16):
                for pos,name in enumerate(rng.permutation(PROTOCOL['net_policies'])):
                    begin=time.perf_counter_ns();wall_begin=time.time_ns();update=job.set(policies[name]);v=job.run(n+2);wall=(time.perf_counter_ns()-begin)/1000
                    np.save(nq/f'b{block:02d}_{name}.npy',v)
                    rows.append(dict(block=block,scope=scope,position=pos,policy=name,choice=policies[name],wall_begin_ns=wall_begin,update_us=update,outer_wall_us=wall,gpu_sum_us=float(v[:,0].sum()),host_sum_us=float(v[:,1].sum()),timed_requests=n*32,conditioning_requests=64))
                print('net',process,scope,block,'PASS',flush=True)
            save_rows(nq/'chunks.csv.gz',rows)
            for name,k in policies.items():job.set(k);job.run();checks.append(dict(scope=scope,policy=name,slot=0,when='net_after',**job.check()))
            write(out/'numerical.json',checks);write(nq/'complete.json',dict(status='PASS',chunks=len(rows)))
        for job in jobs:job.close()
        del shadow
        write(q/'complete.json',dict(status='PASS',scope=scope,setup_ms=target['setup_ms']));print(phase,process,scope,'COMPLETE',flush=True)
    write(out/'complete.json',dict(status='PASS',numerical_checks=len(checks),phase=phase,process=process))
if __name__=='__main__':run(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3]))
