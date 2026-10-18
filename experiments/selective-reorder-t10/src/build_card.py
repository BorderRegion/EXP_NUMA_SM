from common import *
from selection_math import additive_pc,pc_features,PARTITIONS
import numpy as np
cases={c['id']:c for c in read(INPUT/'plans/cases.json')};reps=read(INPUT/'plans/resource_representatives.json')['case_ids'];all_rows=[];all_stages=[];rosters=[]
for b in range(2):
 folder=worker_dir(f'S2_card_{b}');rows=lines(folder/'phases.jsonl');assert len(rows)==128;all_rows+=rows;all_stages+=lines(folder/'stages.jsonl');rosters.append(read(folder/'roster.json'))
assert rosters[0]['groups']==rosters[1]['groups'];cards=[];profile_blocks=[]
for b in range(2):
 features=[]
 for cid in reps:
  rr=[x for x in all_stages if x['block']==b and x['case']==cid];pp=[np.mean([x['P_us'] for x in rr if x['P']==p]) for p in range(4)];cc=[np.mean([x['R_us'] for x in rr if x['C']==q]) for q in range(4)];tt=[np.mean([x['gpu_us'] for x in all_rows if x['block']==b and x['case']==cid and x['P']==p]) for p in range(4)];features.extend([np.array(v)/np.mean(v) for v in [pp,cc,tt]])
 profile_blocks.append(np.array(features).T)
for cid in reps:
 rows=[x for x in all_rows if x['case']==cid];st=[x for x in all_stages if x['case']==cid];samples=[]
 for b in range(2):
  pp=[float(np.mean([x['P_us'] for x in st if x['block']==b and x['P']==p])) for p in range(4)];cc=[float(np.mean([x['R_us'] for x in st if x['block']==b and x['C']==q])) for q in range(4)]
  for w in range(2):
   mat=[[next(x['gpu_us'] for x in rows if x['block']==b and x['W']==w and x['P']==p and x['C']==q) for q in range(4)] for p in range(4)]
   samples.append(dict(block=b,W=w,matrix_us=mat,P_us=pp,R_us=cc,residual_us=additive_pc(mat)))
 cards.append(dict(case=cid,shape=[cases[cid][x] for x in ['M','N','K']],samples=samples,matrix_us=np.mean([x['matrix_us'] for x in samples],axis=0).tolist(),P_us=np.mean([x['P_us'] for x in samples],axis=0).tolist(),R_us=np.mean([x['R_us'] for x in samples],axis=0).tolist()))
profile=np.mean(profile_blocks,axis=0);noise=float(np.median(np.abs(profile_blocks[0]-profile_blocks[1])));threshold=max(.01,2*noise)
def classify(p):
 dist=np.max(np.abs(p[:,None,:]-p[None,:,:]),axis=2);groups=[[i] for i in range(4)]
 while True:
  candidates=[(float(max(dist[x,y] for x in a for y in b)),i,j) for i,a in enumerate(groups) for j,b in enumerate(groups) if i<j]
  if not candidates:break
  value,i,j=min(candidates)
  if value>threshold:break
  groups[i]=sorted(groups[i]+groups[j]);groups.pop(j)
 return groups,dist.tolist()
groups,dist=classify(profile);renames=[];perm=[2,0,3,1];inv=np.argsort(perm).tolist()
# Consistent relabeling changes both card indices and actual partition membership.
for card in cards:
 for part in range(3):
  for pi in range(2):
   mat=np.array(card['matrix_us']);p=np.array(card['P_us']);q=np.array(card['R_us']);old=pc_features(mat.tolist(),p.tolist(),q.tolist(),part,pi,0)
   g=[[inv[x] for x in group] for group in PARTITIONS[part]];mp=mat[np.ix_(perm,perm)];pp=p[perm];qq=q[perm]
   def imb(v):
    cap=[sum(1/v[i] for i in b) for b in g];return abs(cap[0]-cap[1])/sum(cap)
   delta=np.array(additive_pc(mp.tolist()));new=[imb(pp),imb(qq),np.mean([delta[i,j] for b in range(2) for i in g[b] for j in g[b^pi]])/mp.mean(),0]
   error=float(np.max(np.abs(np.array(old)-new)));assert error<1e-12;renames.append(error)
result=dict(created_at=utc(),representatives=cards,roster=rosters[0],profiles_normalized=profile.tolist(),profiles_by_process=[x.tolist() for x in profile_blocks],classification=dict(classes=groups,count=len(groups),threshold=threshold,noise_median=noise,distance='max absolute component difference of within-representative group-mean-normalized P/R/chain profiles',distance_matrix=dist,block_classes=[classify(p)[0] for p in profile_blocks]),consistent_renaming_negative_control=dict(status='PASS',max_feature_difference=max(renames)),feature_identity_permutation=perm,scope='Real producer/reducer on four public14SM groups; groups/classes are not physical NUMA domains')
write(ROOT/'freeze/RESOURCE_CARD.json',result);print('RESOURCE_CARD',len(cards),'classes',groups)
