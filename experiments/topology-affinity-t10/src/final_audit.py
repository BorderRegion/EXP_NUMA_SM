from common import *
from audit import run as initial_audit,ordered_nodes
from topology_math import DT
import numpy as np,pandas as pd

def run():
    assert read(ROOT/'reports/FAST_GPU_COMPLETE.json')['status']=='COMPLETE'
    initial_audit();base=read(ROOT/'derived/AUDIT.json')
    impl=read(ROOT/'freeze/FAST_IMPLEMENTATION.json')
    for name,h in impl['hashes'].items():assert sha(ROOT/name)==h,(name,'fast source changed')
    assert sha(ROOT/'freeze/FAST_SETUP_PROTOCOL.json')==impl['protocol_sha256']
    count=0;test=0;graphs=0;inputs=[];net_requests=0;net_graphs=0;setup=[]
    for worker in sorted(RUN.glob('fast_[0-9]')):
        assert read(worker/'complete.json')['status']=='PASS'
        alloc=read(worker/'allocations.json')['131072'];inputs+=alloc['input_hashes']
        maps=read(worker/'micro/allocation_maps.json');mcomplete=read(worker/'micro/complete.json')
        assert maps['flags_va']==alloc['flags_va']
        assert sha(worker/'micro/allocation_maps.json')==mcomplete['map_sha256']
        assert maps['training_sha256']==sha(worker/'micro/latin.bin')
        plans=np.load(worker/'micro/latin_plans.npy');perms=np.load(worker/'micro/latin_permutations.npy')
        rr=np.fromfile(worker/'micro/latin.bin',dtype=DT).reshape(-1,28)
        assert len(plans)==len(perms)==168
        assert np.all(rr['src_begin']==np.arange(0,56,2)) and np.array_equal(rr['dst_begin'],2*perms+1)
        coverage=np.zeros((2,3,28,28),dtype=int)
        for p,a in zip(plans,perms):coverage[p[1],[0,17,257].index(p[3]),np.arange(28),a]+=1
        assert (coverage==1).all()
        setup.append(dict(process=worker.name,**read(worker/'micro/setup.json')))
        for m in maps['maps']:
            perm=(np.array(m['consumer_per_producer'])-1)//2;assert sorted(perm)==list(range(28))
        for q in worker.glob('V*/page*/*/graphs.json'):
            d=read(q);assert list(d)==['SHARED'];order=ordered_nodes(d['SHARED']);scope=q.parent.name
            batch=PROTOCOL['scopes'][scope]['batch'];fresh=PROTOCOL['scopes'][scope]['fresh']
            assert len(order)==batch*(2 if fresh else 1)
            assert sum('paired' in x['function'] for x in order)==batch;graphs+=1
            x=pd.read_csv(q.with_name('timing.csv.gz'));count+=len(x);test+=(x.phase=='test').sum()
            identities=read(q.with_name('handles.json'));assert len(identities)==4
            assert len({x['exec'] for x in identities})==4
        for q in worker.glob('net/*/chunks.csv.gz'):
            x=pd.read_csv(q);assert x.groupby('policy').requests.sum().eq(1048576).all()
            net_requests+=int(x.requests.sum());net_graphs+=int(x.graph_replays.sum())
    assert len(inputs)==len(set(inputs))==24
    prior_inputs=[]
    for prefix in ['dev_','confirm_','shared_']:
        for p in RUN.glob(prefix+'[0-9]'):
            for a in read(p/'allocations.json').values():prior_inputs+=a['input_hashes']
    assert len(prior_inputs+inputs)==len(set(prior_inputs+inputs))==112
    for name in ['fs_qualification','fs_memcheck']:
        p=RUN/name;assert read(p/'complete.json')['status']=='PASS'
        assert read(p/'complete.json')['solver_checks']==16
    assert 'ERROR SUMMARY: 0 errors' in (RUN/'fs_memcheck/stdout.log').read_text()+(RUN/'fs_memcheck/stderr.log').read_text()
    base.update(timing_observations=base['timing_observations']+count,test_observations=int(base['test_observations']+test),
        graphs_checked=base['graphs_checked']+graphs,independent_input_hashes=base['independent_input_hashes']+len(inputs),
        fixed_session_operator_requests=net_requests,fixed_session_graph_replays=net_graphs,
        fast_setup_ms=[x['total_setup_ms'] for x in setup],fast_fit_ms=[x['fit_ms'] for x in setup],
        supplemental_notes=['Fast setup learned from concurrent Latin sweeps; no isolated validation tensor exists.',
            'Original generic analyze.py wrote fast operator output then failed on missing validation_cycles; dedicated analyze_fast.py handles actual format.',
            'Early CPU shared-graph compile used older header and was repaired before any shared-graph GPU execution; both logs preserved.'])
    write(ROOT/'derived/FINAL_AUDIT.json',base);write(ROOT/'derived/FAST_SETUP_TIMES.json',setup)
    print(json.dumps(base,indent=2))
if __name__=='__main__':run()
