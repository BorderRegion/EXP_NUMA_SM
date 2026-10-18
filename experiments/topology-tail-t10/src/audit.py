from common import *
import numpy as np,pandas as pd
DT=np.dtype([(x,'<u8',(56,)) for x in ['start','arrived','paired','done']]+[(x,'<u4',(56,)) for x in ['collector','observed','errors']]+[(x,'<f4',(56,)) for x in ['maximum','sum']])
assert DT.itemsize==2912
def run():
    assert read(ROOT/'reports/GPU_COMPLETE.json')['status']=='COMPLETE'
    impl=read(ROOT/'freeze/IMPLEMENTATION.json')
    for name,h in impl['hashes'].items():assert sha(ROOT/name)==h,name
    assert sha(ROOT/'freeze/PROTOCOL.json')==impl['protocol_sha256']
    for name,h in PROTOCOL['baseline_hashes'].items():assert sha(ROOT/name)==h,name
    ledger=[json.loads(s) for s in (RUN/'ledger.jsonl').read_text().splitlines()]
    assert sum(r['worker_seconds'] for r in ledger)<PROTOCOL['worker_budget_seconds']
    failures=[r['key'] for r in ledger if r['status']!='COMPLETED'];assert failures==['qualification','memcheck','racecheck_v3'],failures
    topology=read(ROOT/'freeze/HARDWARE_TOPOLOGY.json');temps=[];numerical=0;micro=0;smobs=0;traces=0;short_rows=0;short_test=0;graphs=0;inputs=[];net_requests=0;conditioning=0;net_rows=0;choices_seen=[]
    placements=[(o,p) for o in PROTOCOL['offset_pages'] for p in PROTOCOL['micro']['pages']]
    before=read(ROOT/'freeze/BLIND_BEST.json')['created_utc']
    blind=read(ROOT/'freeze/BLIND_BEST.json')
    for name,h in blind['source_hashes'].items():assert sha(ROOT/name)==h,name
    # Recompute development selection without rewriting its timestamp or choice.
    dev=[]
    for p in sorted(RUN.glob('dev_[0-9]')):
        for scope in PROTOCOL['scopes']:
            x=pd.read_csv(p/scope/'timing.csv.gz');x['worker']=p.name;dev.append(x)
    x=pd.concat(dev);g=x[x.phase=='test'].groupby(['scope','worker','block','choice']).gpu_us.median()
    for scope,v in g.groupby(level='scope'):
        scores=np.log(v).groupby(level=['worker','choice']).mean().groupby(level='choice').mean()
        assert int(scores.idxmin())==blind['choices'][scope]
    for r in ledger:
        p=RUN/r['key'];assert read(p/'topology_query.json')==topology
        for line in (p/'telemetry.jsonl').read_text().splitlines():
            s=json.loads(line);assert s['limit_mw']['value']==100000;temps.append(s['temperature_c']['value'])
        if r['status']!='COMPLETED':continue
        assert r['returncode']==0 and read(p/'complete.json')['status']=='PASS'
        numerical+=len(read(p/'numerical.json'));assert all(x['status']=='PASS' for x in read(p/'numerical.json'))
        if r['key'].startswith('confirm_'):assert r['started']>before
        if not r['key'].startswith(('dev_','confirm_')):continue
        meta=read(p/'allocations.json');inputs+=meta['input_hashes']
        for scope in PROTOCOL['scopes']:
            q=p/scope;cal=q/'calibration';sel=read(cal/'selected_before_validation.json');done=read(cal/'complete.json')
            assert sel['flags_va']==done['flags_va']==meta['flags_va'];assert sel['flags_va']!=done['shadow_flags_va']
            assert sha(cal/'selected_before_validation.json')==done['selected_sha256']
            assert len(sel['choices'])==132 and sel['setup_ms']>0
            arrival=np.load(cal/'arrival_trace.npy');assert arrival.shape==(16,56,8)
            assert (arrival[:,:,7]==np.arange(56)).all() and (arrival[:,:,6].sum(axis=1)==1).all();assert (np.diff(arrival[:,:,:6],axis=2)>=0).all();traces+=len(arrival)
            delay=np.load(cal/'delay.npy');local=np.median(arrival[:,:,1]-arrival[:,:,0],axis=0);assert np.array_equal(delay,(local-local.min()).astype(np.uint64));assert delay.max()<10000
            for kind,nround in [('train',12),('validation',8),('shadow',12)]:
                raw=np.fromfile(cal/(kind+'.bin'),dtype=DT);plans=np.load(cal/(kind+'_plans.npy'));cost=np.load(cal/(kind+'_costs.npy'))
                assert len(raw)==len(plans)==nround*132
                assert (raw['errors']==0).all() and (raw['observed']==np.arange(56)).all() and (raw['collector'].sum(axis=1)==1).all()
                assert (raw['done']>=raw['paired']).all() and (raw['paired']>=raw['arrived']).all() and (raw['arrived']>=raw['start']).all()
                assert np.max(abs(raw['maximum']-55/56))<1e-5
                total=np.sum((100+np.arange(56))*np.exp(np.arange(56)/56-55/56));assert np.max(abs(raw['sum']-total))/total<2e-6
                coverage=np.zeros((nround,132),int)
                for plan,rr in zip(plans,raw):
                    k=placements.index((int(plan[0]),int(plan[1])))*11+int(plan[2]);coverage[plan[3],k]+=1
                    assert cost[plan[3],k]==max(rr['done']-rr['start'])
                assert (coverage==1).all();micro+=len(raw);smobs+=len(raw)*56
            a=np.load(cal/'train_costs.npy');scores=np.maximum(np.median(a[:6],axis=0),np.median(a[6:],axis=0));assert np.array_equal(scores,sel['train_scores'])
            m=sel['mapping'];assert m['JOINT']==m['JOINT_AA']==int(scores.argmin())
            matrix=scores.reshape(12,11);j,k=divmod(m['JOINT'],11)
            assert m['PAIR_ONLY']==11+int(matrix[1].argmin()) and m['PLACE_ONLY']==int(matrix[:,0].argmin())*11
            assert m['WRONG']==j*11+int(matrix[(j+1)%12].argmin()) and m['POOL']==j*11+int(matrix.mean(axis=0).argmin())
            shadow=np.load(cal/'shadow_costs.npy');shadow_score=np.maximum(np.median(shadow[:6],axis=0),np.median(shadow[6:],axis=0));assert done['mapping']['SHADOW']==int(shadow_score.argmin())
            policies=read(q/'policy_choices.json')
            if r['key'].startswith('confirm_'):
                for name,v in done['mapping'].items():assert policies[name]==v
                assert policies['BLIND']==read(ROOT/'freeze/BLIND_BEST.json')['choices'][scope]
            dag=read(q/'graph.json');ns=dag['nodes'];fresh=PROTOCOL['scopes'][scope]['fresh']
            assert len(ns)==32*(2 if fresh else 1) and len(dag['edges'])==len(ns)-1
            assert sum('paired' in n['function'] for n in ns)==32
            assert sum('copy_logits' in n['function'] for n in ns)==(32 if fresh else 0)
            assert all(n['type']==0 for n in ns)
            # Verify a single dependency chain and copy-before-every-operator.
            nodes={n['id']:n for n in ns};successor={};incoming={i:0 for i in nodes}
            for u,v in dag['edges']:
                assert u in nodes and v in nodes and u not in successor
                successor[u]=v;incoming[v]+=1
            heads=[i for i,v in incoming.items() if v==0];assert len(heads)==1 and max(incoming.values())==1
            chain=[];i=heads[0]
            while i not in chain:
                chain.append(i)
                if i not in successor:break
                i=successor[i]
            assert len(chain)==len(ns)
            expected=(['copy_logits','paired'] if fresh else ['paired'])*32
            assert all(name in nodes[i]['function'] for i,name in zip(chain,expected))
            for n in ns:
                if 'paired' in n['function']:assert n['grid']==[56,1,1] and n['shared_bytes']==49152
            identities=read(q/'handles.json');assert len(identities)==4 and len({x['exec'] for x in identities})==4;graphs+=1
            t=pd.read_csv(q/'timing.csv.gz');assert np.isfinite(t[['gpu_us','host_us','outer_wall_us','update_us']]).all().all();assert (t.gpu_us>0).all();short_rows+=len(t);short_test+=(t.phase=='test').sum()
            blocks=6 if r['key'].startswith('dev_') else 16
            assert set(t.block)==set(range(blocks)) and set(t.policy)==set(policies)
            assert not t.duplicated(['block','policy','replay']).any()
            assert t.groupby(['block','policy']).size().eq(10).all()
            assert t.groupby(['block','policy']).replay.nunique().eq(10).all() and set(t.replay)==set(range(10))
            assert (t.phase==np.where(t.replay<2,'conditioning','test')).all()
            for name,idx in policies.items():assert (t[t.policy==name].choice==idx).all()
            choices_seen.append(dict(worker=p.name,scope=scope,mapping=policies))
            if not r['key'].startswith('confirm_'):continue
            nq=q/'net';t=pd.read_csv(nq/'chunks.csv.gz');assert set(t.policy)==set(PROTOCOL['net_policies'])
            assert not t.duplicated(['block','policy']).any() and set(t.block)==set(range(16))
            assert t.groupby('block').position.nunique().eq(9).all() and set(t.position)==set(range(9))
            assert (t.timed_requests==65536).all() and (t.conditioning_requests==64).all()
            assert t.groupby('policy').timed_requests.sum().eq(PROTOCOL['net_requests']).all();assert t.groupby('policy').size().eq(16).all()
            for row in t.itertuples():
                v=np.load(nq/f'b{row.block:02d}_{row.policy}.npy');assert v.shape==(2050,2) and np.isfinite(v).all() and (v>0).all()
                assert abs(v[:,0].sum()-row.gpu_sum_us)<1e-6 and abs(v[:,1].sum()-row.host_sum_us)<1e-6
                assert row.outer_wall_us>row.update_us and row.choice==policies[row.policy]
            net_requests+=int(t.timed_requests.sum());conditioning+=int(t.conditioning_requests.sum());net_rows+=len(t)
    assert max(temps)<82 and len(inputs)==len(set(inputs))==32
    for name in ['memcheck_v3','synccheck_v3','racecheck_targeted']:
        p=RUN/name;s=(p/'stdout.log').read_text()+(p/'stderr.log').read_text();assert 'ERROR SUMMARY: 0 errors' in s or '0 hazards displayed (0 errors, 0 warnings)' in s,name
    result=dict(status='PASS',workers=len(ledger),completed_workers=sum(r['status']=='COMPLETED' for r in ledger),failed_or_incomplete_workers=failures,budget_charge_seconds=sum(r['worker_seconds'] for r in ledger),measured_worker_seconds=sum(r['worker_seconds'] for r in ledger if r['status']!='INTERRUPTED_UNCONFIRMED'),unconfirmed_interruption_charge_seconds=240,budget_seconds=PROTOCOL['worker_budget_seconds'],numerical_checks=numerical,graphs_checked=graphs,trace_launches=traces,micro_launches=micro,micro_sm_records=smobs,short_observations=short_rows,short_test_observations=int(short_test),net_chunks=net_rows,net_operator_requests=net_requests,net_conditioning_requests=conditioning,independent_input_hashes=len(inputs),temperature_min=min(temps),temperature_max=max(temps),power_limit_w=100,exact_baseline=True,implementation_unchanged=True,blind_frozen_before_confirmation=True,notes='Two early host qualification failures and one interrupted broad racecheck retained. Targeted racecheck covers one new-tail launch, not the whole campaign. Sanitizer qualification caps synthetic delays only under instrumentation. Actual interrupted-worker end time unknown; full intended240s cap charged, not claimed measured. No formal performance observation dropped.')
    write(ROOT/'derived/AUDIT.json',result);write(ROOT/'derived/POLICY_CHOICES.json',choices_seen);print(json.dumps(result,indent=2))
if __name__=='__main__':run()
