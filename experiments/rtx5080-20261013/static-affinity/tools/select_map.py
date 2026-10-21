from pathlib import Path
import json,sys,hashlib,datetime
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
FIELDS=['pool_span_bytes','recipe','active_lanes','cache','steps']
def load(label):
    p=ROOT/'results/derived'/label
    with np.load(p/'matrices.npz') as data: arrays={k:data[k] for k in data.files}
    return arrays,json.loads((p/'dispatches.json').read_text())
def mean_observed(a):
    n=np.sum(np.isfinite(a),axis=0);s=np.nansum(a,axis=0)
    return np.divide(s,n,out=np.full(s.shape,np.nan),where=n>0)
def condition(r):return tuple(r[k] for k in FIELDS)
def select(data,records,c,rounds):return data['residual'][[i for i,r in enumerate(records) if condition(r)==c and r['round'] in rounds]]
def balanced_assign(cost):
    # Fixed bounded greedy assignment; task counts differ by at most one.
    n,k=cost.shape;capacity=np.full(k,n//k);capacity[:n%k]+=1;home=np.full(n,-1,dtype=int)
    for flat in np.argsort(cost,axis=None,kind='stable'):
        t,g=divmod(int(flat),k)
        if home[t]<0 and capacity[g]>0:home[t]=g;capacity[g]-=1
    assert np.all(home>=0);return home
def clusters(x,k):
    if not np.all(np.isfinite(x)):raise ValueError('No imputation permitted')
    u,_,_=np.linalg.svd(x,full_matrices=False);rank=np.argsort(u[:,0],kind='stable')
    centers=np.array([np.mean(x[group],axis=0) for group in np.array_split(rank,k)])
    previous=None
    for _ in range(24):
        cost=np.sum((x[:,None,:]-centers[None,:,:])**2,axis=2);label=balanced_assign(cost)
        if previous is not None and np.array_equal(previous,label):break
        centers=np.array([np.mean(x[label==g],axis=0) for g in range(k)]);previous=label.copy()
    return label
def group_cost(matrix,labels,k):return np.array([mean_observed(matrix[labels==g]) for g in range(k)]).T
def evaluate(early,late,labels,k,columns):
    fit=group_cost(early,labels,k)[columns];test=group_cost(late,labels,k)[columns]
    if not np.all(np.isfinite(fit)) or not np.all(np.isfinite(test)):return None
    home=balanced_assign(fit);idx=np.arange(len(columns));matched=float(np.mean(test[idx,home]));permuted=float(np.mean(test[idx,(home+1)%k]));
    return {'benefit_percent':100*(1-np.exp(matched-permuted)),'matched_log_cost':matched,'permuted_log_cost':permuted,'home':home.tolist(),'group_tasks':np.bincount(home,minlength=k).tolist()}
if __name__=='__main__':
    if sys.argv[1]!='development':raise SystemExit('development only')
    datasets=[load('e1_dev_'+str(i)) for i in range(3)]
    smids=datasets[0][0]['smids'];assert all(np.array_equal(d[0]['smids'],smids) for d in datasets)
    conditions=sorted({condition(r) for r in datasets[0][1] if r['recipe']<2})
    candidates=[]
    for c in conditions:
        training=mean_observed(np.concatenate([select(d,r,c,range(3)) for d,r in datasets]))
        usable=np.all(np.isfinite(training[:,:32]),axis=1)
        if usable.sum()<.8*84:continue
        for k in [2,4]:
            labels=clusters(training[usable,:32],k)
            scores=[];held=[];noise=[]
            for d,r in datasets:
                early=mean_observed(select(d,r,c,range(3)))[usable];late=mean_observed(select(d,r,c,range(3,6)))[usable]
                scores.append(evaluate(early,late,labels,k,np.arange(32)))
                held.append(evaluate(early,late,labels,k,np.arange(32,64)))
                ctrl=(c[0],2,*c[2:]);ce=mean_observed(select(d,r,ctrl,range(3)))[usable];cl=mean_observed(select(d,r,ctrl,range(3,6)))[usable]
                noise.append(evaluate(ce,cl,labels,k,np.arange(32)))
            if any(v is None for v in scores):continue
            values=np.array([v['benefit_percent'] for v in scores]);score=float(np.mean(values)-2*np.std(values,ddof=1))
            candidates.append({'condition':dict(zip(FIELDS,c)),'K':k,'smids':smids[usable].tolist(),'groups':labels.tolist(),'development_fit_region_scores':scores,'new_region_diagnostic':held,'arithmetic_control':noise,'selection_score':score,'mean_benefit_percent':float(np.mean(values)),'allocation_sd_percent':float(np.std(values,ddof=1))})
    assert candidates
    winner=max(candidates,key=lambda x:x['selection_score'])
    out=ROOT/'results/derived';(out/'MAP_CANDIDATES.json').write_text(json.dumps(candidates,indent=2)+'\n')
    winner.update(frozen_at=datetime.datetime.now().astimezone().isoformat(),selection_regions=list(range(32)),confirmation_allocations_not_run=True,algorithm='balanced k-means on early-round nuisance-adjusted SM-by-fit-region residuals; balanced greedy home assignment; cyclic label permutation',negative_gate='Confirmation must exceed 3% average, be positive in both allocations and exceed arithmetic-control noise; otherwise do not proceed to application affinity specialization.',analysis_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (ROOT/'MAP_FREEZE.json').write_text(json.dumps(winner,indent=2)+'\n')
    print(json.dumps({k:winner[k] for k in ['condition','K','selection_score','mean_benefit_percent','allocation_sd_percent']},indent=2))
