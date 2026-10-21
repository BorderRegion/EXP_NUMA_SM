"""Finite registered campaign stages. Each label is write-once."""
from common import *
import csv, math, random, statistics, sys

SEED=50802026
SCENES=['train','bonsai']
def rows(out,name='frames.csv'):
    with (out/name).open() as f:return list(csv.DictReader(f))
def settings(values): return ','.join(':'.join(map(str,v)) for v in values)
def balanced(values,block,scene=0):
    v=list(values);random.Random(SEED+scene).shuffle(v)
    offset=(block if len(v)==3 else block*max(1,len(v)//5))%len(v)
    v=v[offset:]+v[:offset]
    return v
def key(r):return (int(r['policy']),int(r['q']),int(r['k']),float(r['alpha']))
def means(outputs):
    vals={}
    for out in outputs:
        groups={}
        for r in rows(out):groups.setdefault(key(r),[]).append(float(r['cpu_result_ready_ms']))
        for k,v in groups.items(): vals.setdefault(k,[]).append(statistics.fmean(v))
    return {k:math.exp(statistics.fmean(map(math.log,v))) for k,v in vals.items()}
def frozen():return json.loads((ROOT/'experiment/POLICY_FREEZE.json').read_text())
def selected(j,ids):return [j['settings'][str(p)] for p in ids]

stage=sys.argv[1]
if stage=='smoke':
    bench('harness_boundary_check','bonsai','calib',settings([(1,8,4,.5),(6,8,4,.5)]),2,8,0,'qual',W=321,H=181)
elif stage=='executor':
    candidates=[(p,8,k,.5) for p in [1,2] for k in [4,8]]
    outs=[]
    for block in range(2):
        for scene_id,scene in enumerate(SCENES):
            outs.append(bench(f'executor_{block}_{scene}',scene,'calib',settings(balanced(candidates,block,scene_id)),128,256,2,'calib',phase='executor'))
    m=means(outs)
    score={k:math.exp(statistics.fmean(math.log(v) for s,v in m.items() if s[2]==k)) for k in [4,8]}
    k=min(score,key=score.get)
    save(ROOT/'experiment/EXECUTOR_FREEZE.json',{'executor':'Q','executor_id':1,'k':k,'selection':'Equal-weight geometric mean CPU result-ready time over identity/spatial, two scenes, two fresh processes per scene.','scores_ms':score,'candidate_means_ms':{str(s):v for s,v in m.items()},'I_limitation':'I does not enforce the intra-bundle order required by this method.','frozen_at':stamp()})
elif stage=='calibration':
    k=json.loads((ROOT/'experiment/EXECUTOR_FREEZE.json').read_text())['k']
    candidates=[(p,8,k,.5) for p in range(4)]+[(p,q,k,.5) for p in [4,5] for q in [8,16]]+[(6,q,k,a) for q in [8,16] for a in [.25,.5,1]]
    outs=[]
    for block in range(2):
        for scene_id,scene in enumerate(SCENES):
            outs.append(bench(f'calibration_{block}_{scene}',scene,'calib',settings(balanced(candidates,block,scene_id)),128,256,2,'calib',phase='calibration'))
    m=means(outs);chosen={p:min([s for s in m if s[0]==p],key=m.get) for p in range(7)}
    best=min(range(1,6),key=lambda p:m[chosen[p]])
    for p in [7,8]:chosen[p]=(p,)+chosen[6][1:]
    save(ROOT/'experiment/POLICY_FREEZE.json',{'frozen_at':stamp(),'settings':chosen,'B_star':best,'B_star_pool':[1,2,3,4,5],'selection_metric':'Two scenes and two process repeats equally weighted; geometric mean of per-session mean CPU result-ready milliseconds.','calibration_frames':128,'M_configurations':6,'calibration_repeats':2,'test_used_for_tuning':False,'candidate_means_ms':{str(s):v for s,v in m.items()},'capacity_estimate_status':'UNKNOWN: footprint uses an unvalidated length-scaled sampled-overlap proxy. Evaluate as relative reuse heuristic; no validated capacity-aware claim.'})
elif stage=='pilot':
    j=frozen();policies=selected(j,[0,j['B_star'],6]);outs=[]
    for block in range(2):
        for scene_id,scene in enumerate(SCENES):
            outs.append(bench(f'pilot_{block}_{scene}',scene,'calib',settings(balanced(policies,block,scene_id)),128,256,2,'calib',phase='pilot'))
    m=means(outs);ratio0=m[tuple(j['settings']['6'])]/m[tuple(j['settings']['0'])];ratiob=m[tuple(j['settings']['6'])]/m[tuple(j['settings'][str(j['B_star'])])]
    branch='full' if ratio0<=.97 and ratiob<=.97 else 'negative'
    save(ROOT/'experiment/BRANCH_FREEZE.json',{'frozen_at':stamp(),'branch':branch,'pilot_M_B0_ratio':ratio0,'pilot_M_Bstar_ratio':ratiob,'rule':'Full only if geometric mean CPU time improves at least 3% versus both B0 and frozen B*. Otherwise the registered 36-session negative confirmation.','pilot_not_used_for_intervals':True})
elif stage=='qualification':
    j=frozen();policies=selected(j,list(range(1,9)))
    for scene in SCENES:
        for track in ['slow','fast']:
            bench(f'qualification_{scene}_{track}',scene,track,settings(policies),32,256,2,'qual',phase='qualification')
elif stage=='formal':
    j=frozen();branch=json.loads((ROOT/'experiment/BRANCH_FREEZE.json').read_text())['branch']
    ids=list(range(9)) if branch=='full' else [0,j['B_star'],6]
    policies=selected(j,ids);blocks=5 if branch=='full' else 3
    for block in range(blocks):
        for scene_id,scene in enumerate(SCENES):
            for track_id,track in enumerate(['slow','fast']):
                order=balanced(policies,block,scene_id*2+track_id)
                out=bench(f'formal_{block}_{scene}_{track}',scene,track,settings(order),512,256,2,'formal',phase='formal')
                baseline={int(r['frame']):(r['hash_x'],r['hash_sum'],r['finite']) for r in rows(out) if int(r['policy'])==0}
                wrong=[r for r in rows(out) if baseline[int(r['frame'])]!=(r['hash_x'],r['hash_sum'],r['finite'])]
                save(out/'HASH_COMPARISON.json',{'frames_per_policy':512,'policies':ids,'rows_checked':len(rows(out)),'mismatches':len(wrong)})
                if wrong:
                    save(ROOT/'recovery/GPU_STOP.json',{'state':'CORRECTNESS_STOP','label':out.name,'mismatches':wrong[:10]})
                    raise RuntimeError('Formal output hash mismatch')
elif stage=='sensitivity':
    j=frozen();policies=selected(j,[0,j['B_star'],6])
    for block in range(2):
        for scene_id,scene in enumerate(SCENES):
            bench(f'nodig_{block}_{scene}',scene,'fast',settings(balanced(policies,block,scene_id)),512,256,2,'nodig',phase='diagnostic_sensitivity')
else: raise SystemExit('Unknown stage')
