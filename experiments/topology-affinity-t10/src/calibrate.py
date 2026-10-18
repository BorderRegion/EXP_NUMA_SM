from runtime import *

def plan_matrices(seed,rounds=2):
    rng=np.random.default_rng(seed);plans=[]
    for rd in range(rounds):
        part=[[1,rd,1,page+i,2*i,2*j+1,128,0,0] for page in PAGES for i in range(28) for j in range(28)]
        rng.shuffle(part);plans.extend(part)
    return plans
def matrix(plans,r,unit):
    result=np.full((2,3,28,28),np.nan)
    for row,x in zip(plans,r):
        i=row[4]//2;j=row[5]//2;page=row[3]-i
        result[row[1],PAGES.index(page),i,j]=x[unit]/row[6]
    assert np.isfinite(result).all()
    return result
def fit(w,train,out):
    start=time.perf_counter();cost=train.max(axis=0);pooled=cost.mean(axis=0);items={}
    for pi,page in enumerate(PAGES):
        for prefix,allowed in [('GPC',SAME_GPC),('ALL',None)]:
            items[page,prefix+'_ADDR']=bottleneck(cost[pi],allowed)
            items[page,prefix+'_WRONG']=bottleneck(cost[(pi+1)%3],allowed)
            items[page,prefix+'_POOL']=bottleneck(pooled,allowed)
    fit_ms=(time.perf_counter()-start)*1000;t=time.perf_counter();w.install(items);install_ms=(time.perf_counter()-t)*1000
    rows=[]
    for (page,name),perm in sorted(w.perms.items()):
        counts={key:int(mask[np.arange(28),perm].sum()) for key,mask in CLASSES.items()}
        rows.append(dict(page=page,policy=name,consumer_per_producer=(2*perm+1).tolist(),map=map_from_perm(perm),classes=counts))
    write(out/'allocation_maps.json',dict(created_utc=utc(),flags_va=w.flags.data_ptr(),fit_ms=fit_ms,install_and_upload_ms=install_ms,
          training_sha256=sha(out/'train.bin'),maps=rows,robust_cost_cycles=cost.tolist(),validation_not_yet_run=True))
    return fit_ms+install_ms
def run(w,out,seed):
    out.mkdir(parents=True,exist_ok=True)
    # Identical residency/payload preparation for training and validation; all
    # requests in each matrix round are randomized, with no file I/O mid-round.
    warm=[[1,0,1,17+i,2*i,2*i+1,128,0,0] for i in range(28)]
    w.micro(warm,out,'conditioning')
    plans=plan_matrices(seed)
    train,tinfo=w.micro(plans,out,'train');t=matrix(plans,train,'cycles')
    fit_ms=fit(w,t,out)
    frozen_hash=sha(out/'allocation_maps.json')
    valplans=plan_matrices(seed+1)
    valid,vinfo=w.micro(valplans,out,'validation');v=matrix(valplans,valid,'cycles')
    assert sha(out/'allocation_maps.json')==frozen_hash
    np.savez(out/'matrices.npz',train_cycles=t,validation_cycles=v,
             train_ns=matrix(plans,train,'ns'),validation_ns=matrix(valplans,valid,'ns'))
    # This compares complete ensembles of 28 active producer/consumer pairs.
    rng=np.random.default_rng(seed+2);con=[]
    for rd in range(PROTOCOL['micro']['concurrent_rounds']):
        part=[[3,rd,1,page,0,0,128,0,k] for page in PAGES for k in range(len(PROTOCOL['policies']))]
        rng.shuffle(part);con.extend(part)
    concurrent,cinfo=w.micro(con,out,'concurrent',concurrent=True)
    overview=[]
    for pi,page in enumerate(PAGES):
        training=t[:,pi].mean(axis=0);validation=v[:,pi].mean(axis=0)
        policy=[]
        for (p,n),perm in w.perms.items():
            if p!=page:continue
            vs=validation[np.arange(28),perm]
            policy.append(dict(policy=n,validation_mean_cycles=float(vs.mean()),validation_max_cycles=float(vs.max())))
        overview.append(dict(page=page,residual_correlation=corr(residual(training),residual(validation)),
            classes={k:dict(train_mean_cycles=float(training[m].mean()),validation_mean_cycles=float(validation[m].mean())) for k,m in CLASSES.items()},policy=policy))
    write(out/'overview.json',overview)
    write(out/'setup_costs.json',dict(calibration_wall_ms=tinfo['wall_ms'],calibration_gpu_queue_ms=tinfo['gpu_queue_ms'],
          fit_and_upload_ms=fit_ms,deployment_setup_ms=tinfo['wall_ms']+fit_ms,
          validation_wall_ms=vinfo['wall_ms'],concurrent_wall_ms=cinfo['wall_ms'],
          note='Deployment estimate uses all 3 pages x2 training rounds plus CPU fitting/upload; validation/concurrent audit excluded. No calibration performed per hot request.'))
    write(out/'complete.json',dict(status='PASS',flags_va=w.flags.data_ptr(),map_sha256=frozen_hash,
          launches=len(warm)+len(plans)+len(valplans)+len(con),records=len(warm)+len(train)+len(valid)+len(concurrent)))
    print('CALIBRATION PASS',[(x['page'],round(x['residual_correlation'],3)) for x in overview],flush=True)
