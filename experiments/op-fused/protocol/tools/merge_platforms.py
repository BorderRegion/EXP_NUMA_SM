"""Join compatible result summaries side by side, never pool raw milliseconds."""
from pathlib import Path
import argparse,json


def merge(a,b):
    for x in (a,b):
        if x.get('artifact_status')=='EMPTY_TEMPLATE_NOT_A_RESULT':
            raise ValueError('empty template is not a result')
        if x.get('platform') not in ('t10','rtx5070ti'):raise ValueError('unknown platform')
    if a['platform']==b['platform']:raise ValueError('two different platforms required')
    if a.get('protocol_id')!=b.get('protocol_id'):raise ValueError('different protocols require explicit separate review')
    same_method=a.get('method_logic_hash') is not None and a.get('method_logic_hash')==b.get('method_logic_hash')
    return {'mode':'SIDE_BY_SIDE_NO_LATENCY_POOLING','protocol_id':a['protocol_id'],
            'same_method_logic_hash':same_method,
            'method_warning':None if same_method else 'method identity unproved/different; stratify versions',
            'platform_results':{a['platform']:a,b['platform']:b}}
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('first',type=Path);ap.add_argument('second',type=Path);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists():ap.error('refusing to overwrite output')
    result=merge(json.loads(a.first.read_text()),json.loads(a.second.read_text()))
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
