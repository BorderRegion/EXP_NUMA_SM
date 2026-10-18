"""CPU audit of seed overlap and sensitivity on confirmation processes 2..5.

Post-run audit: the six-process primary result is retained unchanged. The four
process subset is chosen solely because its input seeds were absent in the two
development workers, never by observed timings. It is not a new experiment.
"""
from common import *
from analyze import load_groups, inference
import numpy as np

def main():
    selections = read(ROOT/'freeze/TUNED_RECIPES.json')['cases']
    evidence = []
    for first, second, tuning in [('development', 'confirmation', False),
                                  ('tune_development', 'tune_confirmation', True)]:
        for proc in range(2):
            dev = read(RUN/f'{first}_{proc}'/'numerical.json')
            conf = read(RUN/f'{second}_{proc}'/'numerical.json')
            for case, choice in selections.items():
                native = 'N_r%d_s%d' % tuple(choice['native']) if tuning else 'NATIVE'
                label = 'TUNED_NATIVE' if tuning else 'NATIVE'
                key = 'label' if tuning else 'policy'
                for slot in range(4):
                    a = next(x for x in dev if x['case']==case and x['slot']==slot
                             and x['stage']=='before' and x[key]==native)
                    b = next(x for x in conf if x['case']==case and x['slot']==slot
                             and x['stage']=='before' and x[key]==label)
                    assert a['output_sha256']==b['output_sha256']
                    evidence.append(dict(stage=second, process=proc, case=case,
                                         slot=slot, same_native_output_sha256=a['output_sha256']))
    results = {}
    for phase, pairs in [
        ('confirmation', [('QUEUE_SELECTED','NATIVE'),('QUEUE_SELECTED','QUEUE_BLIND'),('FUSED','NATIVE')]),
        ('tune_confirmation', [('TUNED_NATIVE','LIB'),('TUNED_NATIVE','OLD_NATIVE'),
                               ('TUNED_FUSED','TUNED_NATIVE'),('FROZEN_ROUTE','LIB')])]:
        blocks = []
        for proc in range(2,6):
            for f in sorted((RUN/f'{phase}_{proc}').glob('*/*/requests.csv.gz')):
                rows, g = load_groups(f)
                case = rows[0]['case']
                alias = read(f.parent/'selection.json')['selected'] if phase=='confirmation' else selections[case]['route']
                for b in range(30):
                    times = {label: v for (p, block, label), v in g.items() if p=='test' and block==b}
                    times['QUEUE_SELECTED' if phase=='confirmation' else 'FROZEN_ROUTE'] = times[alias]
                    blocks.append(dict(process=proc,case=case,times=times))
        results[phase] = {}
        for metric in ['gpu_us','host_us']:
            results[phase][metric] = {}
            for case in ['ALL',*selections]:
                contrasts = {}
                for a,b in pairs:
                    logs = [float(np.mean([np.log(x['times'][a][metric]/x['times'][b][metric])
                                for x in blocks if x['process']==proc and (case=='ALL' or x['case']==case)]))
                            for proc in range(2,6)]
                    contrasts[a+'/'+b] = inference(logs)
                results[phase][metric][case] = contrasts
    # Timing-state sensitivity: A/A by shape and both cuBLAS anchors, retaining
    # every block. Log-linear interpolation is diagnostic, not a noise model.
    anchor_rows = []
    for proc in range(6):
        for f in sorted((RUN/f'tune_confirmation_{proc}').glob('*/*/requests.csv.gz')):
            rows,g = load_groups(f)
            case = rows[0]['case']
            for b in range(30):
                test = [x for x in rows if x['phase']=='test' and int(x['block'])==b]
                pos = {x['label']:int(x['position']) for x in test}
                for metric in ['gpu_us','host_us']:
                    times = {label:v[metric] for (phase,block,label),v in g.items() if phase=='test' and block==b}
                    weight = pos['TUNED_NATIVE']/pos['LIB_B']
                    interp = np.exp((1-weight)*np.log(times['LIB_A'])+weight*np.log(times['LIB_B']))
                    anchor_rows.append(dict(process=proc,case=case,metric=metric,
                        position=pos['TUNED_NATIVE'],aa=100*(times['LIB_B']/times['LIB_A']-1),
                        logratios={base:float(np.log(times['TUNED_NATIVE']/control)) for base,control in
                            [('LIB',times['LIB']),('LIB_A',times['LIB_A']),('LIB_B',times['LIB_B']),('INTERPOLATED_LIB',interp)]}))
    anchors={}
    for metric in ['gpu_us','host_us']:
        anchors[metric]={}
        for case in selections:
            rr=[x for x in anchor_rows if x['metric']==metric and x['case']==case]
            aa=np.array([x['aa'] for x in rr])
            contrasts={base:inference([float(np.mean([x['logratios'][base] for x in rr if x['process']==p]))
                for p in range(6)]) for base in ['LIB','LIB_A','LIB_B','INTERPOLATED_LIB']}
            positions={str(pos):100*(1-float(np.exp(np.mean([x['logratios']['LIB'] for x in rr if x['position']==pos]))))
                for pos in sorted(set(x['position'] for x in rr))}
            anchors[metric][case]=dict(aa_pairs=len(rr),aa_abs_over_5pct=int((abs(aa)>5).sum()),
                aa_p95_abs_pct=float(np.quantile(abs(aa),.95)),contrasts=contrasts,
                by_candidate_position_reduction_pct=positions)
    result = dict(status='PASS', explanation=__doc__, overlap_processes=[0,1],
                  confirmation_only_input_seed_processes=[2,3,4,5],
                  seed_rules={'first_stage':210000,'tuning':310000},
                  matching_output_hashes=evidence, sensitivity=results,
                  tuning_anchor_sensitivity=anchors)
    write(ROOT/'derived/CONFIRMATION_AUDIT.json', result)
    print('CONFIRMATION_SEED_AUDIT_PASS',len(evidence),'matched outputs')
    print('D13 four-seed GPU:', results['tune_confirmation']['gpu_us']['D13']['TUNED_NATIVE/LIB'])

if __name__=='__main__':
    main()
