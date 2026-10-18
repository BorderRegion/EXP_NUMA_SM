"""Strict paired summary of completed phase means; does not infer correctness or missing values.
Input CSV columns: block_id,case_id,policy,role,mean_us,status.
One primary mean per block/case/policy. Resolve documented aliases before export.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'reference'))
from layout_and_stats import bootstrap_blocks

def load_pairs(path: Path, candidate: str, reference: str):
    records={}
    with path.open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['role']!='primary' or row['policy'] not in [candidate,reference]:continue
            if row['status']!='PASS':
                raise ValueError(f"Invalid/unsupported row present; declare analysis scope first: {row}")
            key=(row['block_id'],row['case_id'],row['policy'])
            if key in records:raise ValueError(f'Duplicate primary row {key}')
            records[key]=float(row['mean_us'])
    keys={(b,c) for b,c,_ in records}
    if not keys:raise ValueError('No eligible rows')
    out={}
    for b,c in sorted(keys):
        if (b,c,candidate) not in records or (b,c,reference) not in records:
            raise ValueError(f'Missing paired value {b,c}; no automatic dropping')
        a=records[(b,c,candidate)];r=records[(b,c,reference)]
        if a<=0 or r<=0:raise ValueError('Nonpositive timing')
        out.setdefault(b,{})[c]=a/r
    return out

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('csv',type=Path);ap.add_argument('--candidate',default='M');ap.add_argument('--reference',default='G')
    ap.add_argument('--alpha',type=float,default=.025);ap.add_argument('--samples',type=int,default=20000)
    ap.add_argument('--seed',type=int,default=20261016);ap.add_argument('--out',type=Path)
    args=ap.parse_args();pairs=load_pairs(args.csv,args.candidate,args.reference)
    result=bootstrap_blocks(pairs,args.samples,args.seed,args.alpha)
    result.update({'comparison':f'{args.candidate}/{args.reference}','input':str(args.csv),
                   'scope':'fixed shared cases; paired whole-superblock bootstrap; no GPU verification',
                   'percentage_faster':100*(1-result['ratio'])})
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.out:args.out.write_text(text,encoding='utf-8')
    print(text,end='')
if __name__=='__main__':main()
