"""Observed-cell analysis. Missing SM/region cells remain NaN, never imputed."""
from pathlib import Path
import csv,json,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
DTYPE=np.dtype([('ticks','<u8')]+[(n,'<u4') for n in ['checksum','sm_begin','sm_end','region','slot','block','first','reference']])
def residualize(y,labels,iterations=24):
    residual=np.array(y,dtype=np.float64,copy=True)
    counts=[np.bincount(g) for g in labels]
    for _ in range(iterations):
        largest=0.
        for g,n in zip(labels,counts):
            means=np.divide(np.bincount(g,weights=residual,minlength=len(n)),n,out=np.zeros(len(n)),where=n>0)
            largest=max(largest,float(np.max(np.abs(means))))
            residual-=means[g]
        if largest<1e-10:break
    return residual
def aggregate(values,indices,size):
    count=np.bincount(indices,minlength=size)
    sums=np.bincount(indices,weights=values,minlength=size)
    return np.divide(sums,count,out=np.full(size,np.nan),where=count>0),count
def build(label):
    p=ROOT/'results/raw'/label
    a=np.memmap(p/'samples.bin',dtype=DTYPE,mode='r')
    with (p/'dispatches.csv').open() as f:rows=list(csv.DictReader(f))
    smids=np.unique(a['sm_begin']);nsm=len(smids)
    raw=[];residual=[];counts=[];records=[];refs=[]
    for r in rows:
        offset,count=int(r['sample_offset']),int(r['sample_count']);s=a[offset:offset+count]
        ref=s[s['reference']!=0]
        if len(ref):refs.append({'dispatch':int(r['dispatch']),'mean_reference_ticks':float(np.mean(ref['ticks'])),'p95_reference_ticks':float(np.quantile(ref['ticks'],.95))})
        valid=(s['reference']==0)&(s['ticks']>0)&(s['sm_begin']==s['sm_end'])
        t=s[valid];si=np.searchsorted(smids,t['sm_begin']);ri=t['region'].astype(int)
        if int(r['errors']):raise ValueError('GPU checks failed')
        y=np.log(t['ticks'].astype(float)/int(r['steps']))
        adjusted=residualize(y,[si,ri,t['slot'].astype(int),(t['block']//84).astype(int)])
        index=si*64+ri
        mat,cnt=aggregate(y,index,nsm*64);res,_=aggregate(adjusted,index,nsm*64)
        raw.append(mat.reshape(nsm,64));residual.append(res.reshape(nsm,64));counts.append(cnt.reshape(nsm,64))
        r={k:float(v) if k in ['gpu_ms','primer_ms'] else int(v) for k,v in r.items()}
        r.update(sm_coverage=len(np.unique(si)),sm_region_coverage=float(np.mean(cnt>0)),migration_samples=int(np.sum(s['sm_begin']!=s['sm_end'])),invalid_timing_samples=int(np.sum(s['ticks']==0)),regions_per_observed_sm_min=int(np.min(np.sum(cnt.reshape(nsm,64)>0,axis=1))),sms_per_region_min=int(np.min(np.sum(cnt.reshape(nsm,64)>0,axis=0))))
        records.append(r)
    out=ROOT/'results/derived'/label;out.mkdir(exist_ok=True)
    np.savez_compressed(out/'matrices.npz',smids=smids,raw_log=np.array(raw,dtype=np.float32),residual=np.array(residual,dtype=np.float32),counts=np.array(counts,dtype=np.uint16))
    (out/'dispatches.json').write_text(json.dumps(records,indent=2)+'\n')
    (out/'reference_drift.json').write_text(json.dumps(refs,indent=2)+'\n')
    result={'label':label,'dispatches':len(records),'observed_sms':len(smids),'coverage_min':min(r['sm_region_coverage'] for r in records),'coverage_dense_min':min(r['sm_region_coverage'] for r in records if r['steps']==64),'coverage_denser_min':min(r['sm_region_coverage'] for r in records if r['steps']==512),'regions_per_sm_min':min(r['regions_per_observed_sm_min'] for r in records),'sms_per_region_min':min(r['sms_per_region_min'] for r in records),'migrations':sum(r['migration_samples'] for r in records),'max_kernel_ms':max(r['gpu_ms'] for r in records),'total_samples':len(a),'residual_scope':'Per-dispatch log cycles/load, adjusted jointly for SM/region/slot/block-wave main effects. All valid samples retained. Missing cells remain NaN.'}
    (out/'coverage.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':
    # A complete additive design must leave only numerical noise.
    sm=np.repeat(np.arange(4),12);region=np.tile(np.repeat(np.arange(6),2),4);slot=np.tile(np.arange(2),24)
    y=3+sm*.2+region*.1+slot*.03
    assert np.max(np.abs(residualize(y,[sm,region,slot])))<1e-8
    for label in sys.argv[1:]:build(label)
