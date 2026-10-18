from common import *
import numpy as np,pandas as pd

def run():
    model=[];choices=[];costs=[]
    for p in sorted(RUN.glob('dev_[0-9]')):
        for scope in PROTOCOL['scopes']:
            q=p/scope;c=q/'calibration';sel=read(c/'selected.json');ids=np.load(c/'screen_ids.npy');s=np.load(c/'screen.npy')[:,1:].reshape(16,2,2)[:,1,0]/32
            x=pd.read_csv(q/'timing.csv.gz');a=x[x.phase=='test'].groupby('choice').gpu_us.median().reindex(ids).values/32
            model.append(dict(worker=p.name,scope=scope,choices=ids.tolist(),screen_us=s.tolist(),independent_short_us=a.tolist(),pearson=float(np.corrcoef(s,a)[0,1]),spearman=float(np.corrcoef(pd.Series(s).rank(),pd.Series(a).rank())[0,1]),selected=sel['mapping']['TUNED']))
    for p in sorted(RUN.glob('confirm_[0-9]')):
        for scope in PROTOCOL['scopes']:
            q=p/scope;m=read(q/'calibration/selected.json');pol=read(q/'policy_choices.json')
            choices.append(dict(worker=p.name,scope=scope,setup_ms=m['setup_ms'],fallback=m['fit']['fallback'],choice=pol['TUNED'],plan=m['choices'][pol['TUNED']],same_as_tuned={k:v==pol['TUNED'] for k,v in pol.items()}))
    write(ROOT/'derived/MODEL_TRANSFER.json',model);write(ROOT/'derived/SELECTION_DIAGNOSTICS.json',choices)
    for p in sorted(RUN.glob('*_[0-9]')):
        for q in p.glob('*/calibration/selected.json'):
            m=read(q);s=np.load(q.parent/'screen.npy');r=np.load(q.parent/'refine.npy')
            stages=[s[:,1:].reshape(-1,2,2),r[:,1:].reshape(-1,3,2)]
            costs.append(dict(worker=p.name,scope=q.parents[1].name,setup_ms=m['setup_ms'],scan_updates_ms=float((s[:,0].sum()+r[:,0].sum())/1000),screen_refine_gpu_ms=float(sum(x[:,:,0].sum() for x in stages)/1000),screen_refine_host_ms=float(sum(x[:,:,1].sum() for x in stages)/1000),note='Recorded scan components only; final set+2Graph conditioning, fitting, allocation/wrapping and call overhead are included in setup but not separately timed. GPU and host intervals overlap; do not add them.'))
    write(ROOT/'derived/CALIBRATION_COMPONENTS.json',costs)
    # Descriptive amortization only: extrapolation assumes measured raw speed
    # remains constant. Negative or zero raw savings has no finite break-even.
    out=[]
    for r in read(ROOT/'derived/NET_RESULTS.json'):
        if r['requests']!=1048576 or r['metric']!='outer_s' or r['candidate']!='TUNED' or r['control'] not in ['BASE','STATIC','SHADOW']:continue
        saved=r['control_accounted_s']-r['candidate_raw_s']
        out.append(dict(scope=r['scope'],control=r['control'],estimated_requests=(r['setup_s']/saved*1048576 if saved>0 else None),observed_gross_gain_pct=r['gross_gain_pct'],note='Postprocessing of frozen full-horizon data; arithmetic-mean time extrapolation, not a validated lifetime or extra trial. All warmup/update cost rates assumed unchanged.'))
    write(ROOT/'derived/AMORTIZATION.json',out)
    from topology_math import hungarian
    sm=read(ROOT/'freeze/HARDWARE_TOPOLOGY.json')['global_sm_order']['entries']
    g=np.array([r['gpc'] for r in sm]);t=np.array([r['global_tpc'] for r in sm]);inside=np.empty(28,dtype=int)
    for group in sorted(set(g)):
        ix=np.flatnonzero(g[::2]==group);inside[ix]=np.roll(ix,-1)
    same=g[::2,None]==g[None,1::2]
    cross=hungarian(np.random.default_rng(610001).random((28,28))+same*100)
    families=dict(IDENTITY=np.arange(28),SAME_GPC=inside,CROSS_GPC=cross,RND07=np.random.default_rng(610107).permutation(28))
    topology=[];src=np.arange(0,56,2)
    for name,p in families.items():
        dst=2*p+1;topology.append(dict(family=name,same_tpc=int((t[src]==t[dst]).sum()),same_gpc_other_tpc=int(((g[src]==g[dst])&(t[src]!=t[dst])).sum()),cross_gpc=int((g[src]!=g[dst]).sum()),pairs=list(zip(src.tolist(),dst.tolist()))))
    write(ROOT/'derived/FAMILY_TOPOLOGY.json',topology)
    v=PROTOCOL['V'];stride=56*128
    count=[v//stride*128+max(0,min(128,v%stride-i*128)) for i in range(56)]
    assert sum(count)==v
    write(ROOT/'derived/WORK_DISTRIBUTION.json',dict(V=v,elements_per_sm=count,source='Exact original striped indexing sm*128+thread+i*56*128',note='Work distribution unchanged across all plans. Pair choices can affect waiting for unequal arrivals; a faster family alone does not identify shorter physical communication.'))
    from analyze import stats
    replication=[]
    for r in read(ROOT/'derived/STATIC_CONTROLS.json'):
        if r['candidate']=='LEGACY' and r['requests']==1048576:
            replication.append(dict(scope=r['scope'],metric=r['metric'],candidate='BASE54',control='LEGACY11',role='Reversal of already-reported static comparison; not a new trial',**stats(-np.log1p(np.array(r['process_gains_pct'])/100))))
    write(ROOT/'derived/BASELINE_REPLICATION.json',replication)
    print('DIAGNOSTICS COMPLETE')
if __name__=='__main__':run()
