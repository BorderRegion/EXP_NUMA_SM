from common import *
from selector import CANDIDATES,CHOICES,BASE,decide,shortlist
import numpy as np,pandas as pd

def calibration(q):
    m=read(q/'selected.json');s=np.load(q/'screen.npy');r=np.load(q/'refine.npy');si=np.load(q/'screen_ids.npy');ri=np.load(q/'refine_ids.npy')
    assert s.shape==(16,5) and r.shape==(8,7) and si.shape==(16,) and ri.shape==(8,)
    assert sorted(si)==sorted(CANDIDATES) and np.isfinite(s).all() and np.isfinite(r).all() and (s>0).all() and (r>0).all()
    score=s[:,1:].reshape(16,2,2)[:,1,0];final=shortlist(si,score)
    assert set(ri[:4])==set(ri[4:])==set(final) and len(final)==4 and BASE in final
    mapping,fit=decide(si,score,ri,r[:,1:].reshape(8,3,2)[:,1:,0])
    assert m['mapping']==mapping and m['fit']==fit and m['choices']==CHOICES
    # Independently interpret the prose acceptance rule, not only re-call it.
    screen_by_id={int(k):float(v) for k,v in zip(si,score)}
    expected=[BASE]+sorted((i for i in CANDIDATES if i!=BASE),key=lambda i:(screen_by_id[i],i))[:3]
    assert expected==fit['finalists']
    per_round=[{int(ri[j]):float((r[j,3]+r[j,5])/2) for j in range(rd*4,rd*4+4)} for rd in range(2)]
    eligible=[]
    for k in expected:
        ratios=[d[BASE]/d[k] for d in per_round]
        geometric=(ratios[0]*ratios[1])**.5
        if k!=BASE and min(ratios)>1 and geometric>1.0015:eligible.append((geometric,k))
    expected_tuned=sorted(eligible,key=lambda x:(-x[0],x[1]))[0][1] if eligible else BASE
    assert expected_tuned==mapping['TUNED']==mapping['TUNED_AA']
    subset=lambda pred:[k for k in CANDIDATES if pred(CHOICES[k])]
    best=lambda ids:min(ids,key=lambda k:(screen_by_id[k],k))
    assert mapping['PAIR_ONLY']==best(subset(lambda c:c['offset']==17))
    assert mapping['PLACE_ONLY']==best(subset(lambda c:c['family']=='RND07'))
    assert m['setup_ms']>0 and m['calibration_operator_calls']==1856
    assert m['started']<m['ended']
    return m

def graph(dag):
    nodes={n['id']:n for n in dag['nodes']};fresh=len(nodes)==64
    assert len(nodes) in [32,64] and len(dag['edges'])==len(nodes)-1
    inc={i:0 for i in nodes};succ={}
    for u,v in dag['edges']:assert u in nodes and v in nodes and u not in succ;succ[u]=v;inc[v]+=1
    heads=[i for i,v in inc.items() if v==0];assert len(heads)==1 and max(inc.values())==1
    seq=[];i=heads[0]
    while i not in seq:
        seq.append(i)
        if i not in succ:break
        i=succ[i]
    assert len(seq)==len(nodes)
    expected=(['copy_logits','paired'] if fresh else ['paired'])*32
    for i,name in zip(seq,expected):
        n=nodes[i];assert n['type']==0 and name in n['function']
        if name=='paired':assert n['grid']==[56,1,1] and n['block']==[128,1,1] and n['shared_bytes']==49152
    return fresh

def run():
    assert read(ROOT/'reports/GPU_COMPLETE.json')['status']=='COMPLETE'
    impl=read(ROOT/'freeze/IMPLEMENTATION.json')
    for n,h in impl['hashes'].items():assert sha(ROOT/n)==h,n
    assert sha(ROOT/'freeze/PROTOCOL.json')==impl['protocol_sha256']
    for n,h in PROTOCOL['baseline_hashes'].items():assert sha(ROOT/n)==h,n
    static=read(ROOT/'freeze/STATIC.json')
    for n,h in static['source_hashes'].items():assert sha(ROOT/n)==h,n
    ledger=[json.loads(s) for s in (RUN/'ledger.jsonl').read_text().splitlines()]
    assert len(ledger)==12 and all(r['status']=='COMPLETED' and r['returncode']==0 for r in ledger)
    assert len(set(r['key'] for r in ledger))==12
    assert sum(r['worker_seconds'] for r in ledger)<PROTOCOL['worker_budget_seconds']
    top=read(ROOT/'freeze/HARDWARE_TOPOLOGY.json');temps=[];checks=0;inputs=[];cal=0;graphs=0;short_count=0;short_test=0;requests=0;conditioning=0;chunks=0;cal_calls=0;selection=[]
    for r in ledger:
        p=RUN/r['key'];assert read(p/'complete.json')['status']=='PASS' and read(p/'topology_query.json')==top
        for n,h in impl['hashes'].items():
            if n.startswith('src/'):assert r['sources'][n]==h,(p,n)
        for s in (p/'telemetry.jsonl').read_text().splitlines():
            t=json.loads(s);assert t['limit_mw']['value']==100000;temps.append(t['temperature_c']['value'])
        numerical=read(p/'numerical.json');checks+=len(numerical);assert all(x['status']=='PASS' for x in numerical)
        for f in p.glob('*/calibration*/selected.json'):calibration(f.parent);cal+=1;cal_calls+=1856
        if not r['key'].startswith(('dev_','confirm_')):continue
        if r['key'].startswith('confirm_'):assert r['started']>static['created_utc']
        else:assert r['ended']<static['created_utc']
        meta=read(p/'allocations.json');inputs+=meta['input_hashes']
        for scope in PROTOCOL['scopes']:
            q=p/scope;a=calibration(q/'calibration');b=calibration(q/'shadow');cal+=1;cal_calls+=1856
            assert a['flags_va']==meta['flags_va'] and a['flags_va']!=b['flags_va'] and a['handles']==b['handles']
            seal=read(q/'calibration_seal.json');assert sha(q/'calibration/selected.json')==seal['target'] and sha(q/'shadow/selected.json')==seal['shadow']
            assert seal['created_utc']>a['ended'] and seal['created_utc']>b['ended']
            assert seal['mapping']['SHADOW']==b['mapping']['TUNED'] and seal['mapping']['FROZEN']==PROTOCOL['frozen_best'][scope]
            pol=read(q/'policy_choices.json');handles=read(q/'handles.json');assert len(handles)==4 and len({h['exec'] for h in handles})==4
            assert a['handles']==handles[0] and graph(read(q/'graph.json'))==PROTOCOL['scopes'][scope]['fresh'];graphs+=1
            t=pd.read_csv(q/'timing.csv.gz');blocks=8 if r['key'].startswith('dev_') else 16
            assert set(t.policy)==set(pol) and set(t.block)==set(range(blocks)) and set(t.replay)==set(range(10))
            assert not t.duplicated(['block','policy','replay']).any() and t.groupby(['block','policy']).size().eq(10).all()
            assert (t.phase==np.where(t.replay<2,'conditioning','test')).all()
            assert np.isfinite(t[['gpu_us','host_us','outer_wall_us','update_us']]).all().all() and (t.gpu_us>0).all()
            for name,i in pol.items():assert (t[t.policy==name].choice==i).all()
            short_count+=len(t);short_test+=int((t.phase=='test').sum())
            selection.append(dict(worker=p.name,scope=scope,target=a['mapping'],shadow=b['mapping'],policies=pol))
            if not r['key'].startswith('confirm_'):continue
            for n,i in seal['mapping'].items():assert pol[n]==i
            assert pol['STATIC']==static['choices'][scope] and set(pol)==set(PROTOCOL['net_policies'])
            nq=q/'net';cfg=read(nq/'config.json');assert cfg['handles']==handles[0] and cfg['policies']==pol
            t=pd.read_csv(nq/'chunks.csv.gz');assert len(t)==176 and not t.duplicated(['block','policy']).any()
            assert set(t.block)==set(range(16)) and set(t.policy)==set(pol) and set(t.position)==set(range(11))
            assert t.groupby('block').position.nunique().eq(11).all() and (t.timed_requests==65536).all() and (t.conditioning_requests==64).all()
            for row in t.itertuples():
                v=np.load(nq/f'b{row.block:02d}_{row.policy}.npy');assert v.shape==(2050,2) and np.isfinite(v).all() and (v>0).all()
                assert abs(v[:,0].sum()-row.gpu_sum_us)<1e-6 and abs(v[:,1].sum()-row.host_sum_us)<1e-6
                assert row.choice==pol[row.policy] and row.outer_wall_us>row.update_us
            requests+=int(t.timed_requests.sum());conditioning+=int(t.conditioning_requests.sum());chunks+=len(t)
    assert len(inputs)==len(set(inputs))==32 and max(temps)<82
    for n in ['memcheck','synccheck','racecheck_targeted']:
        s=(RUN/n/'stdout.log').read_text()+(RUN/n/'stderr.log').read_text()
        assert 'ERROR SUMMARY: 0 errors' in s or '0 hazards displayed (0 errors, 0 warnings)' in s,n
    rows=read(ROOT/'derived/NET_RESULTS.json');assert sum(r['primary'] for r in rows)==20
    out=dict(status='PASS',workers=len(ledger),worker_seconds=sum(r['worker_seconds'] for r in ledger),budget_seconds=PROTOCOL['worker_budget_seconds'],numerical_checks=checks,calibration_runs=cal,calibration_operator_calls=cal_calls,graph_dags_checked=graphs,short_observations=short_count,short_test_observations=short_test,net_chunks=chunks,net_operator_requests=requests,net_conditioning_requests=conditioning,independent_input_hashes=32,temperature_min=min(temps),temperature_max=max(temps),power_limit_w=100,exact_original_kernel=True,new_baseline_choice=BASE,static_frozen_before_confirmation=True,implementation_unchanged=True,notes='No performance data removed. Target and shadow use the same executable/input/output, differing flags allocation. Targeted racecheck covers one original paired launch, not full campaign. Calibration counts include qualification and shadow; candidate net bill includes target only. Common Graph construction excluded.')
    write(ROOT/'derived/AUDIT.json',out);write(ROOT/'derived/POLICY_CHOICES.json',selection);print(json.dumps(out,indent=2))
if __name__=='__main__':run()
