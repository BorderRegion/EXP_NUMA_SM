"""Generate prospective, synthetic case records; does not run any experiment."""
from pathlib import Path
import argparse
import json
from collections import Counter
from reference import apportioned_counts, attention_lengths, canonical_hash


def build_matrix():
    rows=[]
    kns=[(1024,2048),(2048,4096),(4096,11008)]
    for ki,(k,n) in enumerate(kns):
        for total in (32,128,512,2048):
            for e in (8,32):
                for d in ('uniform','zipf','one_heavy','sparse_active'):
                    cal=ki<2 and total in (32,128,512) and d in ('uniform','zipf')
                    rows.append(dict(suite='grouped',split='calibration' if cal else 'test',
                        k=k,n=n,total_routed_rows=total,experts=e,distribution=d,
                        rows_per_expert=list(apportioned_counts(total,e,d))))
    for i,(k,n) in enumerate(kns):
        for j,m in enumerate((1,8,32,64,128,256,1024,2048)):
            rows.append(dict(suite='dense_control',split='calibration' if j%2==0 else 'test',m=m,n=n,k=k))
    for i in range(12):
        rows.append(dict(suite='heterogeneous_k',split='calibration' if i<6 else 'test',
            experts=4+(i%3)*4,k_per_problem=[(256,1024,4096)[(j+i)%3] for j in range(4+(i%3)*4)],
            m=64*(1+i//3),n=512*(1+i%2),origin_note='general grouped mechanism, not homogeneous MoE'))
    for b in (1,4,16,32):
        for length in (128,1024,4096):
            for d in ('uniform','long_tail','staggered','order_permuted'):
                cal=b in (1,16) and length in (128,1024)
                rows.append(dict(suite='attention_decode',split='calibration' if cal else 'test',
                    batch=b,mean_kv=length,lengths=list(attention_lengths(b,length,d,2026101517)),
                    distribution=d,q_heads=32,kv_heads=8,head_dim=128,query_length=1))
    for qi,q in enumerate((64,256,1024)):
        for b,l in ((1,1024),(4,1024),(1,4096),(4,4096)):
            rows.append(dict(suite='prefill_control',split='calibration' if qi==0 else 'test',
                batch=b,kv_length=l,query_length=q,q_heads=32,kv_heads=8,head_dim=128))
    for i,(h,mid,e) in enumerate(((1024,2048,8),(2048,4096,8),(4096,11008,32))):
        for tokens in (16,64,256,1024):
            for top in (1,2):
                cal=i==0 and tokens in (16,64,256)
                rows.append(dict(suite='moe_layer',split='calibration' if cal else 'test',
                    hidden=h,intermediate=mid,experts=e,tokens=tokens,top_k=top))
    counts=Counter()
    for row in rows:
        counts[row['suite']]+=1
        row['case_id']=f"{row['suite']}-{counts[row['suite']]:03d}"
        row['origin']='SYNTHETIC_MECHANISM'
        row['dtype']='FP16_INPUT_FP32_ACCUM'
        row['status']='PLANNED_NOT_EXECUTED'
        sig={k:v for k,v in row.items() if k not in ('case_id','status','split')}
        row['plan_signature']=canonical_hash(sig)
    return rows


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    if args.out.exists():
        ap.error('refusing to overwrite an existing plan')
    rows=build_matrix()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8') as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    print(json.dumps({'status':'PLANNING_ONLY','total_plans':len(rows),
                      'counts':dict(Counter(x['suite'] for x in rows))},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
