"""Generate phase_plan.jsonl only. Does not execute GPU code or change the host."""
from pathlib import Path
import argparse, itertools, json, random
from reference import williams

def build(c):
    rows=[]
    def emit(stage,block,case,policy,rank,**extra):
        
        if stage == 'S4':
            extra.setdefault('scope','BALANCED56SM')
            extra.setdefault('profile','H1')
            extra.setdefault('cache','HOT_SAME_POLICY')
        rows.append(dict(stage=stage,block=block,case_id=case,policy=policy,phase_rank=rank,**extra))
    sizes=c['sizes_mib']; scopes=['PAIR4SM','BALANCED56SM']
    for block in range(c['blocks']):
        cases=list(itertools.product(sizes,scopes,c['execution_profiles']))
        random.Random(c['seed']+block).shuffle(cases)
        for size,scope,profile in cases:
            for rank,i in enumerate(williams(6,block)):
                emit('S2',block,f'{size}MiB_{scope}_{profile}',c['actions'][i],rank,
                     size_mib=size,scope=scope,profile=profile,cache='COMMON_PRIME',diagnostic=False)
        mech=list(c['mechanism_profiles'])
        random.Random(c['seed']+100+block).shuffle(mech)
        for p in mech:
            for rank,i in enumerate(williams(6,block)):
                emit('S3',block,p['name'],c['actions'][i],rank,size_mib=2,profile='H1',
                     diagnostic=False,**{k:v for k,v in p.items() if k!='name'})
        variants=[(p,d) for p in c['diagnostic_comparison']['policies'] for d in (False,True)]
        cases=list(itertools.product(sizes,[1,4]))
        random.Random(c['seed']+200+block).shuffle(cases)
        for size,repeats in cases:
            case=f'{size}MiB_HOT_repeat{repeats}'
            emit('S4',block,case,'N',-1,size_mib=size,inner_repeats=repeats,diagnostic=False,role='anchor_head')
            for rank,i in enumerate(williams(8,block)):
                p,d=variants[i]
                emit('S4',block,case,p,rank,size_mib=size,inner_repeats=repeats,diagnostic=d,role='main')
            emit('S4',block,case,'N',8,size_mib=size,inner_repeats=repeats,diagnostic=False,role='anchor_tail')
    for index,r in enumerate(rows): r['plan_id']=f'T10-FR-{index:04d}'
    return rows

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default=str(Path(__file__).resolve().parents[1]/'campaign.json'))
    parser.add_argument('--out',required=True,help='New local JSONL file; existing file will not be overwritten')
    a=parser.parse_args();c=json.loads(Path(a.config).read_text())
    rows=build(c)
    expected=c['counts']['main_and_anchor_total']
    if len(rows)!=expected: raise RuntimeError((len(rows),expected))
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8') as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+'\n')
    print(json.dumps({'status':'PLAN_ONLY','phases':len(rows),'out':str(out)},ensure_ascii=False))
if __name__=='__main__': main()
