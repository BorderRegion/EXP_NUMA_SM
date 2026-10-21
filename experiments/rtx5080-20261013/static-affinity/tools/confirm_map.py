from select_map import *
frozen=json.loads((ROOT/'MAP_FREEZE.json').read_text());c=tuple(frozen['condition'][x] for x in FIELDS);k=frozen['K'];labels=np.array(frozen['groups']);smids=np.array(frozen['smids'])
dev,dr=load('e1_dev_0');ix=np.searchsorted(dev['smids'],smids)
old=mean_observed(select(dev,dr,c,range(3)))[ix]
oldhome={str(start):balanced_assign(group_cost(old,labels,k)[start:start+32]).tolist() for start in [0,32]}
records=[]
for epoch in [3,4]:
    data,meta=load('e1_confirm_'+str(epoch));ix=np.searchsorted(data['smids'],smids)
    early=mean_observed(select(data,meta,c,range(3)))[ix]
    late=select(data,meta,c,range(3,6))[:,ix,:]
    ctrl=(c[0],2,*c[2:]);ce=mean_observed(select(data,meta,ctrl,range(3)))[ix];cl=select(data,meta,ctrl,range(3,6))[:,ix,:]
    for start in [0,32]:
        columns=np.arange(start,start+32);values=[];noise=[];stale=[]
        for matrix,control in zip(late,cl):
            values.append(evaluate(early,matrix,labels,k,columns))
            noise.append(evaluate(ce,control,labels,k,columns))
            group=group_cost(matrix,labels,k)[columns];home=np.array(oldhome[str(start)]);idx=np.arange(32)
            stale.append(100*(1-np.exp(np.mean(group[idx,home]-group[idx,(home+1)%k]))))
        paired=[v['benefit_percent'] for v in values]
        same=mean_observed(late);mask=np.isfinite(early[:,columns])&np.isfinite(same[:,columns])
        rank=lambda x:np.argsort(np.argsort(x,kind='stable'),kind='stable')
        corr=float(np.corrcoef(rank(early[:,columns][mask]),rank(same[:,columns][mask]))[0,1])
        records.append({'epoch':epoch,'regions':'fit_addresses' if start==0 else 'new_addresses_with_own_initialization','benefit_percent_by_round':paired,'mean_benefit_percent':float(np.mean(paired)),'arithmetic_control_benefit_percent':[x['benefit_percent'] for x in noise],'stale_map_benefit_percent_by_round':stale,'mean_stale_map_benefit_percent':float(np.mean(stale)),'residual_rank_correlation':corr,'early_late_joint_cell_coverage':float(np.mean(mask)),'group_task_counts':values[0]['group_tasks']})
rng=np.random.default_rng(2026101304);strata=[r['benefit_percent_by_round'] for r in records if r['regions']=='fit_addresses'];boot=[]
for _ in range(20000):
    ids=rng.integers(0,2,2);boot.append(np.mean([np.mean(rng.choice(strata[i],3,replace=True)) for i in ids]))
mean=float(np.mean(strata));noise=[abs(x) for r in records for x in r['arithmetic_control_benefit_percent']];noise95=float(np.quantile(noise,.95));ci=np.quantile(boot,[.025,.975]).tolist()
actionable=mean>=3 and all(np.mean(x)>0 for x in strata) and mean>noise95
result={'frozen_condition':frozen['condition'],'K':k,'confirmation':records,'fit_address_mean_benefit_percent':mean,'hierarchical_exploratory_ci95_percent':ci,'control_absolute_noise_p95_percent':noise95,'bootstrap_unit':'Allocation, then heldout round. Only two confirmation allocations; descriptive exploratory interval.','actionable':bool(actionable),'outcome':'PROCEED_E2' if actionable else 'NO_ACTIONABLE_AFFINITY_IN_TESTED_SCOPE','scope':'This pointer-chase sampling and cache/concurrency scope; not a proof that RTX 5080 lacks any memory nonuniformity. Predicted local timing benefit is not measured end-to-end speedup.'}
(ROOT/'results/derived/CONFIRMATION.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
