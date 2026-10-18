#!/usr/bin/env python3
"""Extract relevant records from an explicitly supplied old run root, CPU only.
Usage: python tools/extract_prior_focus.py --run-root /exact/old/run --out /new/evidence
No GPU-library imports, no whole-disk search, no changes to input files.
"""
from __future__ import annotations
import argparse,csv,json
from collections import Counter
from pathlib import Path
from analyze_focus import trace_account,quartet

def read_rows(path:Path):
    with path.open(encoding='utf-8') as f:
        for ln,text in enumerate(f,1):
            if text.strip():
                try:yield ln,json.loads(text)
                except json.JSONDecodeError as e:raise ValueError(f'{path}:{ln}: {e}') from e

def extract(root:Path,out:Path)->dict:
    raw=root/'raw'
    if not raw.is_dir():raise ValueError('Expected explicitly selected run_root/raw; do not guess another run')
    if out.exists() and any(out.iterdir()):raise ValueError('Output must be new or empty; no overwrite')
    out.mkdir(parents=True,exist_ok=True);count=Counter();effects=[];phases={};traces=[]
    with (out/'anchors_preserved.jsonl').open('w',encoding='utf-8') as dst:
        for f in sorted(raw.rglob('anchors.jsonl')):
            for ln,x in read_rows(f):
                x={'_source_file':str(f.relative_to(root)),'_source_line':ln,**x}
                dst.write(json.dumps(x,ensure_ascii=False,allow_nan=False)+'\n');count['anchor_rows']+=1
                ww=x.get('windows',[])
                if len(ww)==4:
                    e=quartet(''.join(w['label'] for w in ww),[w['mean_cpu_us'] for w in ww])
                    e.update(case_id=x.get('case_id',x.get('case')),block=x.get('block'),anchor=x.get('anchor'),quartet_id=x.get('quartet_id'),source_file=x['_source_file'])
                    effects.append(e)
                    count['anchor_request_values_present']+=sum(len(w.get('samples',[])) for w in ww)
    with (out/'ffn_phases_and_aliases.jsonl').open('w',encoding='utf-8') as dst:
        for f in sorted(raw.rglob('phases.jsonl')):
            for ln,x in read_rows(f):
                pid=x.get('phase_id')
                if pid:
                    key=(str(f.parent),str(pid))
                    if key in phases:raise ValueError(f'duplicate phase {key}')
                    phases[key]=x
                if x.get('stage')=='S5_FFN':
                    dst.write(json.dumps({'_source_file':str(f.relative_to(root)),'_source_line':ln,**x},ensure_ascii=False,allow_nan=False)+'\n');count['ffn_phases']+=1
        for f in sorted(raw.rglob('aliases.jsonl')):
            for ln,x in read_rows(f):
                if x.get('stage')=='S5_FFN':
                    dst.write(json.dumps({'_source_file':str(f.relative_to(root)),'_source_line':ln,'record_type':'ALIAS',**x},ensure_ascii=False,allow_nan=False)+'\n');count['ffn_aliases']+=1
    with (out/'trace_request_rows.jsonl').open('w',encoding='utf-8') as dst:
        for f in sorted(raw.rglob('samples.jsonl')):
            for ln,x in read_rows(f):
                ph=phases.get((str(f.parent),str(x.get('phase_id'))))
                if not ph or ph.get('stage')!='S5_TRACE':continue
                ids=ph.get('signature_ids');samples=x.get('samples')
                if not isinstance(ids,list) or not isinstance(samples,list):
                    count['trace_missing_signature_or_samples']+=1;continue
                normalized=[]
                for s in samples:
                    si=int(s['signature'])
                    if not 0<=si<len(ids):raise ValueError('signature index outside recorded signature_ids')
                    row={**s,'case_id':ids[si],'phase_id':ph['phase_id'],'block':ph.get('block'),'policy':ph.get('policy'),'trace':ph.get('case'),'source_file':str(f.relative_to(root))}
                    normalized.append(row);dst.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
                a=trace_account(float(ph['total_completion_us']),normalized)
                traces.append({'phase_id':ph['phase_id'],'block':ph.get('block'),'policy':ph.get('policy'),'trace':ph.get('case'),**a})
                count['trace_phases']+=1;count['trace_requests']+=len(normalized)
    result={'run_root':str(root),'counts':dict(count),'aa_from_explicit_raw':effects,'trace_accounting':traces,
            'limitations':['Old window warmups without recorded request values remain missing.','Counts indicate only files actually present, not completeness of a GPU campaign.','No GPU output or physical NUMA validation performed.']}
    (out/'FOCUS_EXTRACTION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=extract(a.run_root.resolve(),a.out.resolve());print(json.dumps(r['counts']))
if __name__=='__main__':main()
