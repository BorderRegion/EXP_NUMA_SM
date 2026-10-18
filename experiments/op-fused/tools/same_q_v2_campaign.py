"""Sequential finite campaign; fixed old registry prefix and shared worker lock."""
import argparse,json,math,os,pathlib
from same_q_v2_worker import run,ROOT,RUN_ROOT
from native_bench import utc

def job(stage,key,script,args=()):
    record=run(stage,'sameq_v2_'+key,ROOT/'tools'/script,args)
    if record['status']!='COMPLETED':raise RuntimeError('Worker failed: '+key)
    return ROOT/record['path']
def gmean(xs):return math.exp(sum(math.log(x) for x in xs)/len(xs))
def select(paths):
    samples={};results=[]
    for p in paths:
        for f in sorted(p.glob('v2-dev-*.json')):
            data=json.loads(f.read_text());assert data['status']=='PASS';results.append(data)
            for row in data['phases']:
                if row['phase_role']=='primary':samples.setdefault(row['variant'],[]).append(row['device_interval_ms'])
    assert len(results)==36 and all(len(xs)==36 for xs in samples.values())
    means={k:gmean(v) for k,v in samples.items()}
    best=min(means[f'CORE_r{r}'] for r in range(4))
    recipe=next(r for r in range(4) if means[f'CORE_r{r}']<=best*1.005)
    best=min(means[f'CACHE_r{recipe}_q{q}'] for q in [1,2,4])
    q=next(q for q in [1,2,4] if means[f'CACHE_r{recipe}_q{q}']<=best*1.005)
    lib=min(['PER_EXPERT_GRAPH','NATIVE_GROUPED_GRAPH'],key=lambda n:means[n])
    protocol=json.loads((RUN_ROOT/'PROTOCOL_V2.json').read_text())
    ratio=means[f'CORE_r{recipe}']/means[lib];weak=ratio>protocol['weak_backbone_threshold']
    result=dict(frozen_at=utc(),recipe=recipe,fixed_q=q,library=lib,layer_library=lib,
      all_development_geomeans_ms=means,development_core_library_ratio=ratio,
      weak_backbone=weak,regression_ids=protocol['weak_backbone_regression_ids'] if weak else protocol['regression_ids'],
      layer_ids=protocol['layer_regression_ids'],selection_rule=protocol['recipe_selection'],
      fixed_q_rule=protocol['fixed_q_selection'],library_rule=protocol['library_selection'],
      development_records=36,confirmation_not_yet_run=True,scope='GLOBAL_RECIPE_NO_SHAPE_BIN')
    target=RUN_ROOT/'BODY_AND_BASELINE_FREEZE_V2.json'
    assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n')
    print('FREEZE',json.dumps(result),flush=True)
    return result
def main(a):
    if a.stage=='operators':
        job('S1','sanitizer','same_q_v2_qualify.py',['--sanitizer'])
        paths=[job('S2',f'develop_{b}','same_q_v2_bench.py',['--phase','develop','--block',b]) for b in range(3)]
        for b in range(3):job('S2',f'diagnose_{b}','same_q_v2_bench.py',['--phase','diagnose','--block',b])
        if not (RUN_ROOT/'BODY_AND_BASELINE_FREEZE_V2.json').exists():select(paths)
        for b in range(6):job('S3',f'formal_{b}','same_q_v2_bench.py',['--phase','formal','--block',b])
    elif a.stage=='layers':
        job('S1','raw_bit_qualification','same_q_v2_bitprobe.py')
        qualified=job('S4','layer_qualification','same_q_v2_layer.py',['--phase','qualify'])
        enabled=json.loads((qualified/'activation_qualification.json').read_text())['status']=='PASS'
        flags=['--fusion-enabled'] if enabled else []
        for b in range(6):job('S4',f'layer_{b}','same_q_v2_layer.py',['--phase','formal','--block',b])
        for b in range(3):job('S4',f'fusion_{b}','same_q_v2_layer.py',['--phase','fusion','--block',b,*flags])
        for b in range(3):job('S4',f'ring_{b}','same_q_v2_layer.py',['--phase','ring','--block',b,*flags])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['operators','layers'],required=True);main(p.parse_args())
