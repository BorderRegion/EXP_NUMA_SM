from common import *
from topology_math import DT,residual,corr
from analyze import result
import numpy as np,pandas as pd
sm=read(ROOT/'freeze/HARDWARE_TOPOLOGY.json')['global_sm_order']['entries']
gpc=np.array([x['gpc'] for x in sm]);tpc=np.array([x['global_tpc'] for x in sm])
sameg=gpc[:,None]==gpc[None,:];samet=(tpc[:,None]==tpc[None,:])&~np.eye(56,dtype=bool)
valid=~np.eye(56,dtype=bool);classes={'same_tpc':samet,'same_gpc_other_tpc':sameg&~samet&valid,'cross_gpc':~sameg}
ii,jj=np.where(valid);features=np.column_stack([np.ones(len(ii)),np.eye(56)[ii,1:],np.eye(56)[jj,1:],samet[ii,jj],classes['same_gpc_other_tpc'][ii,jj]])
assert np.linalg.matrix_rank(features)==features.shape[1]
def run():
    rows=[];matrices={};frame=[]
    for worker in sorted(RUN.glob('full_*')):
        assert read(worker/'complete.json')['status']=='PASS'
        plans=np.load(worker/'full_direction_plans.npy');r=np.fromfile(worker/'full_direction.bin',dtype=DT)
        assert len(plans)==len(r)==18480
        for unit in ['cycles','ns']:
            a=np.full((2,3,56,56),np.nan)
            for p,x in zip(plans,r):
                page=int(p[3]-p[4]//2);a[p[1],PROTOCOL['micro']['pages'].index(page),p[4],p[5]]=x[unit]/p[6]
            assert np.isfinite(a[:,:,valid]).all()
            matrices[worker.name+'_'+unit]=a
            for pi,page in enumerate(PROTOCOL['micro']['pages']):
                y=a[:,pi].mean(axis=0);coef=np.linalg.lstsq(features,y[valid],rcond=None)[0]
                means={k:np.array([y[s,m[s]].mean() for s in range(56)]) for k,m in classes.items()}
                for kind in ['same_tpc','same_gpc_other_tpc']:
                    rows.append(dict(process=worker.name,page=page,unit=unit,comparison=kind+'/cross_gpc',
                        log_advantage=float(np.log(means['cross_gpc']/means[kind]).mean()),
                        class_mean=float(means[kind].mean()),cross_mean=float(means['cross_gpc'].mean()),
                        fixed_effect_difference_vs_cross=float(coef[-2 if kind=='same_tpc' else -1]),
                        round_residual_correlation=corr(residual(a[0,pi],True),residual(a[1,pi],True))))
                for pg in sorted(set(gpc)):
                    ix=gpc==pg
                    for kind,m in classes.items():frame.append(dict(process=worker.name,page=page,unit=unit,source_logical_gpc=int(pg),class_name=kind,mean=float(means[kind][ix].mean())))
    np.savez_compressed(ROOT/'derived/FULL_MATRICES.npz',**matrices)
    write(ROOT/'derived/full_processes.json',rows);write(ROOT/'derived/full_gpc_groups.json',frame)
    summary=[]
    for (page,unit,kind),x in pd.DataFrame(rows).groupby(['page','unit','comparison']):
        summary.append(dict(page=int(page),unit=unit,comparison=kind,**result(x.log_advantage.values),
            class_mean=float(x.class_mean.mean()),cross_mean=float(x.cross_mean.mean()),
            fixed_effect_difference_vs_cross=float(x.fixed_effect_difference_vs_cross.mean()),
            fixed_effect_process_values=x.fixed_effect_difference_vs_cross.tolist(),residual_correlations=x.round_residual_correlation.tolist()))
    write(ROOT/'derived/full_summary.json',summary)
    print('FULL DIRECTION SUMMARY',[{k:x[k] for k in ['page','comparison','gain_pct','ci95','positive_processes']} for x in summary if x['unit']=='ns'])
if __name__=='__main__':run()
