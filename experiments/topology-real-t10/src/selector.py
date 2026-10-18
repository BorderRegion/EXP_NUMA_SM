"""Pure CPU deterministic sampler decision; no confirmation feedback."""
from common import *
import numpy as np
NAMES=PROTOCOL['policies']
PLACEMENTS=[(o,p) for o in PROTOCOL['offset_pages'] for p in PROTOCOL['micro']['pages']]
CHOICES=[dict(offset=o,page=p,family=n) for o,p in PLACEMENTS for n in NAMES]
CANDIDATES=PROTOCOL['candidate_indices'];BASE=PROTOCOL['baseline_choice']

def shortlist(screen_ids,screen_gpu):
    score=dict(zip(map(int,screen_ids),map(float,screen_gpu)))
    others=sorted((i for i in CANDIDATES if i!=BASE),key=lambda i:(score[i],i))[:3]
    return [BASE]+others

def decide(screen_ids,screen_gpu,refine_ids,refine_gpu):
    screen=dict(zip(map(int,screen_ids),map(float,screen_gpu)))
    finalists=shortlist(screen_ids,screen_gpu);r=np.asarray(refine_gpu)
    per_round=[]
    for rd in range(2):
        d={int(i):float(np.median(v)) for i,v in zip(refine_ids[rd*4:(rd+1)*4],r[rd*4:(rd+1)*4])}
        assert set(d)==set(finalists);per_round.append(d)
    gains={i:[per_round[rd][BASE]/per_round[rd][i]-1 for rd in range(2)] for i in finalists}
    eligible=[i for i in finalists if i!=BASE and min(gains[i])>0 and np.expm1(np.log1p(gains[i]).mean())>PROTOCOL['calibration']['min_gain']]
    tuned=min(eligible,key=lambda i:(np.log1p(gains[i]).mean()*-1,i)) if eligible else BASE
    offset=CHOICES[tuned]['offset'];row=PROTOCOL['offset_pages'].index(offset)
    families=['IDENTITY','SAME_GPC','CROSS_GPC','RND07']
    index=lambda o,n:next(i for i in CANDIDATES if CHOICES[i]['offset']==o and CHOICES[i]['family']==n)
    best=lambda ids:min(ids,key=lambda i:(screen[i],i))
    nxt=PROTOCOL['offset_pages'][(row+1)%4]
    wrong_family=CHOICES[best([index(nxt,n) for n in families])]['family']
    pooled=min(families,key=lambda n:(np.mean([screen[index(o,n)] for o in PROTOCOL['offset_pages']]),families.index(n)))
    mapping=dict(BASE=BASE,LEGACY=PROTOCOL['legacy_choice'],TUNED=tuned,TUNED_AA=tuned,
        PAIR_ONLY=best([index(17,n) for n in families]),PLACE_ONLY=best([index(o,'RND07') for o in PROTOCOL['offset_pages']]),
        WRONG=index(offset,wrong_family),POOL=index(offset,pooled))
    return mapping,dict(finalists=finalists,round_gains={str(k):v for k,v in gains.items()},eligible=eligible,fallback=tuned==BASE)
