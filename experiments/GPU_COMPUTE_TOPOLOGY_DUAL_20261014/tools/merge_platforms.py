"""Offline merge of MANUALLY COPIED summaries; never contacts either host."""
from pathlib import Path
import argparse,json

def merge(summaries:list[dict])->dict:
    issues=[];seen=set()
    for s in summaries:
        p=s.get('platform')
        if p not in ('t10','rtx5070ti'): issues.append('Unknown or missing platform')
        if p in seen: issues.append('Duplicate platform summary')
        seen.add(p)
    for field in ('protocol_hash','method_source_hash','inputs_manifest_hash'):
        vals=[s.get(field) for s in summaries]
        if any(not x for x in vals):issues.append(f'{field}: UNKNOWN')
        elif len(set(vals))>1:issues.append(f'{field}: DIFFERENT; keep separate cohorts')
    if set(seen)!={'t10','rtx5070ti'}:issues.append('Both platform results not present')
    return {'scope':'side-by-side only; no pooled raw-time speedup',
      'compatibility':'REVIEW_REQUIRED' if issues else 'METADATA_MATCHED_NOT_CAUSAL_PROOF',
      'issues':issues,'platform_reports':summaries}
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--inputs',nargs='+',required=True);a.add_argument('--out',required=True);x=a.parse_args()
    out=merge([json.loads(Path(p).read_text(encoding='utf-8')) for p in x.inputs]);p=Path(x.out);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
