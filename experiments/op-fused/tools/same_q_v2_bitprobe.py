"""Raw FP16-bit samples complement phase-level torch.equal value checks.

torch.equal on half values does not distinguish signed zero; do not mislabel
those earlier immutable phase summaries as an exhaustive raw-bit comparison.
This qualification has no performance phases and does not alter any selection.
"""
import argparse,gc,json,pathlib
import torch
from native_bench import ROOT,grouped
from same_q_v2_backend import CutlassGrouped
from same_q_v2_common import setup,write,seed
def main(a):
    setup();freeze=json.loads((a.run_root/'BODY_AND_BASELINE_FREEZE_V2.json').read_text())
    cases=[json.loads(s) for s in (ROOT/'preregistration/plan.jsonl').read_text().splitlines()]
    cases=[c for c in cases if c['case_id'] in ['grouped-003','grouped-057']]
    results=[]
    for block in range(6):
        for case in cases:
            torch.manual_seed(seed(case,block));fn,validate,ledger,storage=grouped(case,block)
            aa,bb,cc=[storage[k] for k in ['inputs','weights','outputs']]
            core=CutlassGrouped(aa,bb,cc,freeze['recipe'],0);core();torch.cuda.synchronize()
            expected=[c.clone().view(torch.int16) for c in cc]
            for mode in [1,2,3]:
                op=CutlassGrouped(aa,bb,cc,freeze['recipe'],mode,1,2 if mode==2 else 1)
                op();torch.cuda.synchronize()
                mismatches=sum(int((c.view(torch.int16)!=e).sum()) for c,e in zip(cc,expected))
                checks=validate();assert mismatches==0 and all(x['pass'] for x in checks)
                results.append(dict(case_id=case['case_id'],block=block,input_seed=seed(case,block),mode=mode,
                  raw_half_bit_mismatches=mismatches,element_count=sum(c.numel() for c in cc),checks=checks))
                op.close()
            core.close();del op,core,expected,fn,validate,storage,aa,bb,cc
            gc.collect();torch.cuda.empty_cache()
    write(a.out/'raw_bit_qualification.json',dict(status='PASS',samples=results,
      scope='Two preselected representative formal cases with each of six actual payload seeds; raw int16 comparison; no timing'))
    print('RAW_FP16_BIT_PROBE_PASS',len(results),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--run-root',type=pathlib.Path,required=True);main(p.parse_args())
