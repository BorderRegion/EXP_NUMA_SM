from common import *
from topology_math import DT,hungarian
import numpy as np,gzip,csv
from datetime import datetime

def ordered_nodes(dag):
    nodes={x['id']:x for x in dag['nodes']};children={k:[] for k in nodes};incoming={k:0 for k in nodes}
    assert len(dag['edges'])==len(nodes)-1
    for a,b in dag['edges']:children[a].append(b);incoming[b]+=1
    roots=[k for k,v in incoming.items() if v==0];assert len(roots)==1
    result=[];k=roots[0]
    while True:
        result.append(nodes[k]);assert len(children[k])<=1
        if not children[k]:break
        k=children[k][0]
        assert len(result)<len(nodes)
    assert len(result)==len(nodes)
    return [{k:v for k,v in x.items() if k!='id'} for x in result]
def run():
    assert read(ROOT/'reports/GPU_COMPLETE.json')['status']=='COMPLETE'
    assert read(ROOT/'reports/SHARED_GPU_COMPLETE.json')['status']=='COMPLETE'
    impl=read(ROOT/'freeze/IMPLEMENTATION.json')
    for name,h in impl['hashes'].items():assert sha(ROOT/name)==h,(name,'implementation changed')
    assert sha(ROOT/'freeze/PROTOCOL.json')==impl['protocol_sha256']
    for name,h in PROTOCOL['baseline_hashes'].items():assert sha(ROOT/name)==h
    shared_epoch=read(ROOT/'freeze/SHARED_GRAPH_IMPLEMENTATION.json')
    for name,h in shared_epoch['hashes'].items():assert sha(ROOT/name)==h,(name,'shared implementation changed')
    ledger=[json.loads(x) for x in (RUN/'ledger.jsonl').read_text().splitlines()]
    assert all(x['status']=='COMPLETED' and x['returncode']==0 for x in ledger)
    assert sum(x['worker_seconds'] for x in ledger)<PROTOCOL['worker_budget_seconds']
    before=read(ROOT/'freeze/RANDOM_BEST.json')['created_utc']
    for x in ledger:
        if x['key'].startswith('confirm_'):assert x['started']>before
    top=read(ROOT/'freeze/HARDWARE_TOPOLOGY.json');gpu=np.array([x['gpc'] for x in top['global_sm_order']['entries']]);same=(gpu[::2,None]==gpu[None,1::2])
    numerical=0;graphs=0;timing_count=0;test_count=0;temps=[];limits=[];input_hashes=[];setups=[];micro_records=0;micro_launches=0
    for row in ledger:
        p=RUN/row['key'];assert read(p/'complete.json')['status']=='PASS'
        assert read(p/'topology_query.json')==top
        for line in (p/'telemetry.jsonl').read_text().splitlines():
            s=json.loads(line);temps.append(s['temperature_c']['value']);limits.append(s['limit_mw']['value'])
        if (p/'numerical.json').exists():
            vals=read(p/'numerical.json');assert all(x['status']=='PASS' for x in vals);numerical+=len(vals)
        for q in p.rglob('*_audit.json'):
            a=read(q);assert a['status']=='PASS';micro_records+=a['records'];micro_launches+=a['launches']
            name=q.name.removesuffix('_audit.json');records=np.fromfile(q.with_name(name+'.bin'),dtype=DT)
            plans=np.load(q.with_name(name+'_plans.npy'))
            stride=28 if np.all(plans[:,0]==3) else 1
            assert len(records)==len(plans)*stride==a['records']
            assert np.all(records['errors']==0)
            assert np.array_equal(records['src_begin'],records['src_end'])
            assert np.array_equal(records['dst_begin'],records['dst_end'])
            first=records[::stride];assert np.all(np.sort(first['roster_begin'],axis=1)==np.arange(56))
            assert np.array_equal(first['roster_begin'],first['roster_end'])
            assert np.all(records['src_value']==np.repeat(plans[:,6]+16,stride))
            assert np.array_equal(records['src_value'],records['dst_value'])
        if row['key'].startswith(('dev_','confirm_','shared_')):
            allocations=read(p/'allocations.json')
            for d in allocations.values():input_hashes.extend(d['input_hashes'])
            maps=read(p/'micro/allocation_maps.json');mc=read(p/'micro/complete.json')
            assert sha(p/'micro/allocation_maps.json')==mc['map_sha256']
            assert all(d['flags_va']==maps['flags_va']==mc['flags_va'] for d in allocations.values())
            assert maps['training_sha256']==sha(p/'micro/train.bin')
            for m in maps['maps']:
                perm=(np.array(m['consumer_per_producer'])-1)//2;assert sorted(perm)==list(range(28))
                if m['policy'].startswith('GPC_'):assert same[np.arange(28),perm].all()
                if m['policy'] in ['IDENTITY','ALIAS_IDENTITY']:assert np.array_equal(perm,np.arange(28))
                expected=np.arange(56)//2
                for i,j in enumerate(perm):expected[2*j+1]=i
                assert np.array_equal(expected,m['map'])
            # Archive timestamp provenance now, before ZIP extraction can round
            # timestamps. This includes conditioning, CPU parsing and research
            # I/O; use as a conservative gross setup interval, not GPU-only time.
            start_ns=(p/'allocations.json').stat().st_mtime_ns
            end_ns=int(datetime.fromisoformat(maps['created_utc']).timestamp()*1e9)
            setup=read(p/'micro/setup_costs.json')
            setups.append(dict(process=row['key'],start_ns=start_ns,end_ns=end_ns,
                gross_setup_ms=(end_ns-start_ns)/1e6,queue_plus_fit_lower_bound_ms=setup['deployment_setup_ms'],
                definition='Gross: allocation metadata write to frozen usable maps, including conditioning and research I/O. Lower bound omits host copying/checking/serialization.'))
            assert setups[-1]['gross_setup_ms']>=setups[-1]['queue_plus_fit_lower_bound_ms']
            for q in p.glob('V*/page*/*/graphs.json'):
                dd=read(q);scope=q.parent.name;batch=PROTOCOL['scopes'][scope]['batch'];fresh=PROTOCOL['scopes'][scope]['fresh']
                expected=None
                for n,dag in dd.items():
                    order=ordered_nodes(dag);assert len(order)==batch*(2 if fresh else 1)
                    for i,node in enumerate(order):
                        assert node['type']==0
                        assert ('copy_logits' in node['function']) == (fresh and i%2==0)
                        if not (fresh and i%2==0):assert 'paired' in node['function'] and node['shared_bytes']==49152
                    if expected is None:expected=order
                    else:assert order==expected
                    graphs+=1
                with gzip.open(q.with_name('timing.csv.gz'),'rt') as f:
                    for x in csv.DictReader(f):
                        assert float(x['gpu_us'])>0 and float(x['host_us'])>0
                        timing_count+=1;test_count+=x['phase']=='test'
    assert len(input_hashes)==len(set(input_hashes)), 'Input seed/data overlap'
    assert all(x==100000 for x in limits) and max(temps)<82
    for name in ['memcheck','synccheck','racecheck','sg_memcheck']:
        p=RUN/name;s=(p/'stdout.log').read_text()+(p/'stderr.log').read_text()
        assert ('ERROR SUMMARY: 0 errors' in s) or ('0 hazards displayed (0 errors, 0 warnings)' in s)
    write(ROOT/'derived/SETUP_COST_BOUNDS.json',setups)
    result=dict(status='PASS',workers=len(ledger),worker_seconds=sum(x['worker_seconds'] for x in ledger),
        budget_seconds=PROTOCOL['worker_budget_seconds'],numerical_checks=numerical,graphs_checked=graphs,
        timing_observations=timing_count,test_observations=test_count,micro_launches=micro_launches,micro_records=micro_records,
        independent_input_hashes=len(input_hashes),temperature_min=min(temps),temperature_max=max(temps),power_limit_w=100,
        baseline_exact_binary=True,implementation_unchanged=True,random_selection_before_confirmation=True,
        note='One initial CPU analysis failure due missing pandas preserved. Installation/resume made no GPU-code or map-algorithm change.')
    write(ROOT/'derived/AUDIT.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':run()
