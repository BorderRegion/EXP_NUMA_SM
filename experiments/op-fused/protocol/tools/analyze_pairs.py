"""Analyze independent block means. No raw cross-platform pooling allowed.

Input CSV columns: platform,case_id,block_id,variant,phase_role,status,elapsed_ms.
Only an explicitly selected candidate and reference are paired. Anchors are
excluded from the primary estimate but their rows remain counted in the audit.
This is a helper; it does not prove the validity of the input experiments.
"""
from pathlib import Path
import argparse,csv,json
from collections import defaultdict,Counter
from reference import paired_effect


def analyze(rows,candidate,reference,draws=20000,seed=2026101509):
    platforms={r['platform'] for r in rows}
    if len(platforms)!=1:raise ValueError('exactly one platform per analysis')
    audit=Counter(); buckets=defaultdict(dict)
    for r in rows:
        if r['phase_role']!='primary':audit['non_primary_rows']+=1;continue
        if r['status']!='COMPLETED':audit['non_completed_rows']+=1;continue
        if r['variant'] not in (candidate,reference):audit['other_variant_rows']+=1;continue
        key=(r['case_id'],r['block_id']);v=r['variant']
        if v in buckets[key]:raise ValueError(f'duplicate primary {key} {v}; aggregate within block explicitly first')
        buckets[key][v]=float(r['elapsed_ms'])
    grouped=defaultdict(list);unpaired=[]
    for (case,block),d in sorted(buckets.items()):
        if set(d)!={candidate,reference}:
            unpaired.append({'case_id':case,'block_id':block,'present':sorted(d)});continue
        grouped[case].append((block,d[candidate],d[reference]))
    effects={};insufficient=[]
    for case,vals in grouped.items():
        if len(vals)<2:insufficient.append(case);continue
        effects[case]=paired_effect([x[1] for x in vals],[x[2] for x in vals],draws,seed)
        effects[case]['block_ids']=[x[0] for x in vals]
    return {'platform':next(iter(platforms)),'candidate':candidate,'reference':reference,
            'effects_by_case':effects,'unpaired_blocks':unpaired,'insufficient_cases':insufficient,
            'row_audit':dict(audit),'scope':'supplied primary independent block means; not GPU validation'}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',required=True,type=Path);ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--candidate',required=True);ap.add_argument('--reference',required=True)
    a=ap.parse_args()
    if a.out.exists():ap.error('output exists; do not overwrite derived versions silently')
    with a.input.open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
    result=analyze(rows,a.candidate,a.reference)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
