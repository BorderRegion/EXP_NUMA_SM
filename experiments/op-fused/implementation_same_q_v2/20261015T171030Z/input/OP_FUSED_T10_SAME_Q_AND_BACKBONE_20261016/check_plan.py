"""CPU-only plan checks and tile mapping reference. No GPU or network operations."""
from pathlib import Path
import json, math

def tile_walk(gm:int,gn:int,q:int=1):
    if gm<0 or gn<0 or q not in (1,2,4):
        raise ValueError('gm, gn must be nonnegative and q in 1,2,4')
    if gm==0 or gn==0:return []
    q=min(q, 4 if gm>=4 else 2 if gm>=2 else 1)
    pp=(gm+q-1)//q
    result=[]
    for packet in range(gn*pp):
        n=packet//pp; start=(packet%pp)*q
        for i in range(min(q,gm-start)):result.append((start+i,n))
    return result

def native_walk(gm:int,gn:int):
    if gm<0 or gn<0:raise ValueError('negative size')
    return [(m,n) for m in range(gm) for n in range(gn)]

def model_full_q(gm,total,workers,waves,k,bk=32,qcap=1,budget=128):
    if workers<=0 or waves<=0 or k<=0 or bk<=0:raise ValueError('invalid dimensions')
    cap=min(qcap,max(1,gm),max(1,total//(workers*waves)),max(1,budget//((k+bk-1)//bk)))
    return 4 if cap>=4 else 2 if cap>=2 else 1

def validate(root:Path):
    cfg=json.loads((root/'campaign.json').read_text())
    cases=json.loads((root/'cases_v2.json').read_text())['cases']
    assert sum(cfg['stages_minutes'].values())==cfg['planned_work_minutes']==390
    assert cfg['hard_work_minutes']==420 and cfg['planned_work_minutes']<=cfg['hard_work_minutes']
    remaining=cfg['historical_total_gpu_worker_hours']-cfg['reported_used_gpu_worker_hours']
    assert cfg['new_gpu_worker_cap_minutes']/60<=remaining
    assert len({r['case_id'] for r in cases})==18
    assert sum(r['split']=='development' for r in cases)==12
    assert sum(r['split']=='confirmation' for r in cases)==6
    assert not set(r['seed'] for r in cases if r['split']=='development') & set(r['seed'] for r in cases if r['split']=='confirmation')
    for r in cases:
        assert len(r['rows_per_expert'])==r['experts']
        assert sum(r['rows_per_expert'])==r['total_routed_rows']
        assert min(r['rows_per_expert'])>=0 and r['k']%8==r['n']%8==0
    formal=cfg['operator_confirm_cases']*cfg['independent_blocks']*(cfg['operator_unique_strategies_max']+cfg['lib_anchors_per_case'])
    layer=cfg['layer_cases']*cfg['independent_blocks']*(cfg['layer_unique_strategies_max']+cfg['lib_anchors_per_case'])
    assert formal==864 and layer==144
    return {'status':'CPU_PLAN_VALID','planned_work_minutes':390,'hard_work_minutes':420,
       'gpu_worker_cap_minutes':240,'original_remaining_hours_from_supplied_record':remaining,
       'planned_operator_phases_max':formal,'planned_layer_phases_max':layer,
       'optional_fusion_phases_max':48,'optional_ring_phases_max':36,
       'case_counts':{'development':12,'confirmation':6},
       'notice':'Counts are plans, not executed GPU experiments. Model mappings are not compiled-kernel verification.'}
if __name__=='__main__':
    print(json.dumps(validate(Path(__file__).resolve().parent),ensure_ascii=False,indent=2))
