"""Generate design-only cases, no CUDA, network, or measured results."""
from pathlib import Path
import itertools
import json
ROOT = Path(__file__).resolve().parents[1]

def main():
    out = ROOT / 'plans'; out.mkdir(exist_ok=True)
    gemm = []
    tuples = list(itertools.product([1,8,32,128,512,2048], [1024,4096,8192], [4096,16384]))
    tuples += [(m,n,8192) for m,n in itertools.product([3,17,65,257],[1536,4096,11008])]
    for i,(m,n,k) in enumerate(tuples):
        gemm.append({'case_id':f'G{i+1:03d}','source':'DESIGNED_SYNTHETIC_NOT_MODEL_TRACE',
                     'split':'development' if i%3==0 else 'test','M':m,'N':n,'K':k,
                     'dtype_in':'fp16','accumulator':'fp32','output':'fp32',
                     'split_candidates':[1,2,4,8,16], 'measured':False})
    attention=[]
    for i,(b,l,heads) in enumerate(itertools.product([1,4,16],[1024,4096,16384],
                                      [(16,16,64),(32,8,128),(32,4,128),(32,32,128)])):
        hq,hkv,d=heads
        attention.append({'case_id':f'A{i+1:03d}','source':'DESIGNED_SYNTHETIC_NOT_MODEL_TRACE',
                          'split':'development' if i%3==0 else 'test','batch':b,'kv_length':l,
                          'query_length':1,'query_heads':hq,'kv_heads':hkv,'head_dim':d,
                          'dtype_in':'fp16','partial_accumulator':'fp32','measured':False})
    for name,data in [('gemm_cases.json',gemm),('attention_cases.json',attention)]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Fixed reduced branch spans the test list without selecting by measured outcome.
    indices=[0,2,4,7,10,13,16,19,22,25,28,31]
    tests=[c['case_id'] for c in gemm if c['split']=='test']
    ats=[c['case_id'] for c in attention if c['split']=='test']
    (out/'reduced_confirmation.json').write_text(json.dumps({
        'gemm':[tests[i] for i in indices],
        'attention':[ats[i] for i in range(0,24,2)],
        'rule':'fixed indices before any results, not chosen winners',
        'measured':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__': main()
