from shared_runtime import *
import itertools
fitlib=C.CDLL(str(ROOT/'build/fast_fit.so'))
fitlib.fit_bottleneck.argtypes=[C.POINTER(C.c_double),C.POINTER(C.c_ubyte),I,C.POINTER(I)]
def compiled_fit(cost,allowed=None):
    cost=np.ascontiguousarray(cost,dtype=np.float64);n=len(cost)
    allowed=np.ascontiguousarray(np.ones_like(cost,dtype=np.uint8) if allowed is None else allowed,dtype=np.uint8)
    answer=np.zeros(n,dtype=np.int32)
    rc=fitlib.fit_bottleneck(cost.ctypes.data_as(C.POINTER(C.c_double)),allowed.ctypes.data_as(C.POINTER(C.c_ubyte)),n,answer.ctypes.data_as(C.POINTER(I)))
    assert rc==0,rc
    return answer
def solver_qualification():
    rng=np.random.default_rng(1260001)
    for n in [3,4,5,28]:
        for k in range(4):
            a=rng.random((n,n));m=(rng.random((n,n))>.4)|np.eye(n,dtype=bool)
            fast=compiled_fit(a,m);slow=bottleneck(a,m)
            assert np.array_equal(fast,slow)
            if n<=5:
                truth=min(max(a[i,p[i]] for i in range(n)) for p in itertools.permutations(range(n)) if all(m[i,p[i]] for i in range(n)))
                assert abs(max(a[np.arange(n),fast])-truth)<1e-12
    return 16
def run(w,out,seed):
    out.mkdir(parents=True,exist_ok=True);start=time.perf_counter_ns();started_utc=utc();rng=np.random.default_rng(seed)
    # Each randomized Latin schedule contains all28 sources and destinations.
    # Across its28 shifts, every edge appears once with28 active pairs.
    schedules=[];plans=[];perms=[]
    for rd in range(2):
        jobs=[]
        for pi,page in enumerate(PAGES):
            src_order=rng.permutation(28);dst_order=rng.permutation(28)
            for shift in range(28):
                perm=np.empty(28,dtype=int);perm[src_order]=np.roll(dst_order,shift)
                arr=np.full(512,-1,dtype=np.int32)
                for i,j in enumerate(perm):arr[4*i]=i;arr[4*i+1]=0;arr[4*j+2]=i;arr[4*j+3]=1
                jobs.append((page,perm,arr))
        rng.shuffle(jobs)
        for page,perm,arr in jobs:
            plans.append([3,rd,1,page,0,0,64,0,len(plans)])
            schedules.append(arr);perms.append(perm)
    schedules=np.stack(schedules);perms=np.stack(perms)
    maps_gpu=torch.tensor(schedules,device='cuda');records=torch.zeros(len(plans)*28*DT.itemsize,device='cuda',dtype=torch.uint8)
    st=torch.cuda.current_stream().cuda_stream;e0=torch.cuda.Event(enable_timing=True);e1=torch.cuda.Event(enable_timing=True);e0.record()
    for k,p in enumerate(plans):
        a=(I*9)(*p)
        assert probe.probe_launch(w.flags.data_ptr(),records.data_ptr()+k*28*DT.itemsize,a,maps_gpu.data_ptr()+k*512*4,st)==0,probe.probe_error()
    e1.record();torch.cuda.synchronize();queue_ms=e0.elapsed_time(e1)
    raw=records.cpu().numpy().tobytes();r=np.frombuffer(raw,dtype=DT).reshape(-1,28)
    assert np.all(r['errors']==0) and np.array_equal(r['src_begin'],r['src_end']) and np.array_equal(r['dst_begin'],r['dst_end'])
    assert np.all(r['src_begin']==np.arange(0,56,2)) and np.array_equal(r['dst_begin'],2*perms+1)
    assert np.all(r['src_value']==80) and np.all(r['dst_value']==80)
    assert np.all(np.sort(r[:,0]['roster_begin'],axis=1)==np.arange(56)) and np.array_equal(r[:,0]['roster_begin'],r[:,0]['roster_end'])
    costs=np.full((2,3,28,28),np.nan)
    for k,p in enumerate(plans):costs[p[1],PAGES.index(p[3]),np.arange(28),perms[k]]=r[k]['cycles']/64
    assert np.isfinite(costs).all();robust=costs.max(axis=0);pool=robust.mean(axis=0)
    fit_start=time.perf_counter_ns();generated=[]
    for pi,page in enumerate(PAGES):
        for prefix,mask in [('GPC',SAME_GPC),('ALL',None)]:
            for suffix,cost in [('ADDR',robust[pi]),('WRONG',robust[(pi+1)%3]),('POOL',pool)]:
                perm=compiled_fit(cost,mask);name=prefix+'_'+suffix;w.perms[page,name]=perm;w.maps[page,name]=(I*56)(*map_from_perm(perm))
                generated.append(dict(page=page,policy=name,consumer_per_producer=(2*perm+1).tolist(),map=map_from_perm(perm)))
    fit_ms=(time.perf_counter_ns()-fit_start)/1e6
    # Endpoint is usable host launch schedules; no reporting/serialization is
    # needed for deployment, so it follows this measured setup interval.
    setup_ms=(time.perf_counter_ns()-start)/1e6;end_utc=utc()
    (out/'latin.bin').write_bytes(raw);np.save(out/'latin_plans.npy',np.array(plans,dtype=np.int32));np.save(out/'latin_permutations.npy',perms)
    np.savez(out/'matrices.npz',train_cycles=costs)
    write(out/'latin_audit.json',dict(status='PASS',launches=len(plans),records=r.size,flags_va=w.flags.data_ptr(),source_clock_rtt=True))
    write(out/'allocation_maps.json',dict(created_utc=end_utc,flags_va=w.flags.data_ptr(),training_sha256=sha(out/'latin.bin'),maps=generated,
          static_maps=[dict(page=p,policy=n,map=map_from_perm(a)) for (p,n),a in w.perms.items() if not n.startswith(('ALL_','GPC_'))]))
    write(out/'setup.json',dict(started_utc=started_utc,ended_utc=end_utc,total_setup_ms=setup_ms,fit_ms=fit_ms,submission_queue_ms=queue_ms,
          description='Includes Latin schedule generation, device allocations/upload, profiling, download, correctness checks, CPU fit and host parameter installation; excludes later research serialization.'))
    write(out/'complete.json',dict(status='PASS',records=r.size,setup_ms=setup_ms,map_sha256=sha(out/'allocation_maps.json')))
    print('FAST CALIBRATION PASS',round(setup_ms,3),'ms; CPU fit',round(fit_ms,3),'ms',flush=True)
