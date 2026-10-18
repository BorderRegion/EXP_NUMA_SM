"""Fit two same-complexity CPU reference selectors from DEVELOPMENT rows only.
Input JSONL rows: cohort,case_id,action,cpu_ready_us,shape_features,resource_features.
One row per phase; repeated blocks are collapsed per shape before fitting.
No test outcomes are accepted. Local backend must supply the actual features.
"""
from __future__ import annotations
import argparse,json,math,statistics
from pathlib import Path
from collections import defaultdict
from selection_math import fit_ridge,quantile,compile_ridge_header,BASE_ACTIONS

def train(rows):
    grouped=defaultdict(list)
    for row in rows:
        if row.get('cohort')!='development':raise ValueError('Only development rows may enter training')
        for key in ('case_id','action','cpu_ready_us','shape_features','resource_features'):
            if key not in row:raise ValueError('Missing '+key)
        t=row['cpu_ready_us']
        if t<=0 or not math.isfinite(t):raise ValueError('nonfinite/invalid training time')
        grouped[(row['case_id'],row['action'])].append(row)
    collapsed={}
    for key,rep in grouped.items():
        first=rep[0]
        # A hardware feature must be from a frozen initialization card, not the
        # matching measured phase. Different cards require different cohorts.
        if any(r['shape_features']!=first['shape_features'] or r['resource_features']!=first['resource_features'] for r in rep):
            raise ValueError('Feature/card changes within one training signature')
        collapsed[key]=dict(time=math.exp(statistics.mean(math.log(r['cpu_ready_us']) for r in rep)),shape=first['shape_features'],hw=first['resource_features'])
    cases=sorted({c for c,a in collapsed});actions=sorted({a for c,a in collapsed})
    if len(cases)<4:raise ValueError('Need at least four distinct development shapes')
    if any((c,a) not in collapsed for c in cases for a in actions):raise ValueError('Use a declared common feasible action subset; do not impute missing timings')
    if 'LIB' not in actions:raise ValueError('LIB required')
    fitted={};cv={};margins={};base_margins={}
    for mode in ('SHAPE','RESOURCE'):
        models={};pred={}
        def feats(d,a):
            # Base action predictions must be identical across selectors.
            return d['shape']+(d['hw'] if mode=='RESOURCE' and a not in BASE_ACTIONS else [])
        for action in actions:
            ds=[collapsed[(c,action)] for c in cases]
            models[action]=fit_ridge([feats(d,action) for d in ds],[d['time'] for d in ds])
            for hold in cases:
                traincases=[c for c in cases if c!=hold]
                trainvalues=[collapsed[(c,action)] for c in traincases]
                model=fit_ridge([feats(d,action) for d in trainvalues],[d['time'] for d in trainvalues])
                pred[(hold,action)]=model.predict_us(feats(collapsed[(hold,action)],action))
        er=defaultdict(list)
        for case in cases:
            base=min((a for a in actions if a in BASE_ACTIONS),key=lambda a:pred[(case,a)])
            for action in actions:
                if action in BASE_ACTIONS:continue
                for reference in (a for a in actions if a in BASE_ACTIONS):
                    error=(pred[(case,action)]-pred[(case,reference)])-(collapsed[(case,action)]['time']-collapsed[(case,reference)]['time'])
                    er[action].append(abs(error))
        margins[mode]={a:quantile(v,.9) for a,v in er.items()}
        base_margins[mode]={a:quantile([abs((pred[(c,a)]-pred[(c,'LIB')])-(collapsed[(c,a)]['time']-collapsed[(c,'LIB')]['time'])) for c in cases],.9) for a in actions if a in BASE_ACTIONS and a!='LIB'}
        cv[mode]=[{'case':c,'action':a,'predicted_us':pred[(c,a)],'observed_us':collapsed[(c,a)]['time']} for c in cases for a in actions]
        fitted[mode]=models
    return fitted,{'method':'fixed ridge lambda=1; leave-one-whole-shape-out','cases':cases,'actions':actions,'models':{k:{a:m.to_dict() for a,m in v.items()} for k,v in fitted.items()},'paired_error_margin_us':margins,'base_error_to_lib_us':base_margins,'loso':cv}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('development_jsonl');ap.add_argument('output_dir');args=ap.parse_args()
    rows=[json.loads(x) for x in Path(args.development_jsonl).read_text().splitlines() if x.strip()]
    models,result=train(rows);out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    (out/'POLICY_MODEL.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    for mode,ms in models.items():(out/(mode.lower()+'_model.hpp')).write_text(compile_ridge_header(ms))
    print('Wrote fitted CPU models. No GPU deployment has been performed by this script.')
