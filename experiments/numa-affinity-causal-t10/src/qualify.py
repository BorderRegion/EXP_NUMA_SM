from runtime import *
import sys
out=Path(sys.argv[1]);small='--small' in sys.argv;rows=[]
for V in ([131072] if small else [131072,129024]):
 d=Data(V,121000000+V,ring=1)
 for pattern in (['random'] if small else ['random','uniform','spike','extreme']):
  if pattern=='uniform':d.x[0].zero_()
  if pattern=='spike':d.x[0].fill_(-100);d.x[0][V//2]=100
  if pattern=='extreme':d.x[0].copy_(torch.linspace(-1000,1000,V,device='cuda'))
  d.source[0].copy_(d.x[0]);torch.cuda.synchronize();d.refs[0]=torch.softmax(d.x[0].cpu().double(),dim=0)
  for variant in VARIANTS:
   for page in ([17] if small else [0,17,257]):
    for policy in (['MINIMAX','IDENTITY'] if small else ['MINIMAX','IDENTITY','WRONG_ADDRESS','POOLED','RND00','NATIVE']):
     j=Job(d,0,variant,policy,page,trace=True);result=j.check()
     if policy!='NATIVE':
      tr=d.trace.cpu().view(56,2).numpy();pr=d.prof.cpu().numpy();assert np.array_equal(np.sort(tr[:,0]),np.arange(56)) and np.array_equal(tr[:,0],tr[:,1]);assert np.array_equal(pr[:,0],np.arange(56)) and np.array_equal(pr[:,0],pr[:,1]);assert pr[:,2].sum()==V
      if variant in ['BAL','BOTH']:assert np.ptp(pr[:,2])<=1
      col=np.flatnonzero(pr[:,6]);assert len(col)==1
      if variant in ['FIX','BOTH']:assert col.tolist()==[1]
      result.update(roster='PASS',work_min=int(pr[:,2].min()),work_max=int(pr[:,2].max()),collector_sm=int(col[0]));np.save(out/f'{V}_{pattern}_{variant}_{page}_{policy}.npy',pr)
     rows.append(dict(V=V,pattern=pattern,variant=variant,page=page,policy=policy,**result));j.close();write(out/'numerical.json',rows)
  for scope in ['fresh','batch','freshbatch']:
   for variant in VARIANTS:
    j=Job(d,0,variant,'MINIMAX',17,scope);d.x[0].fill_(-17);torch.cuda.synchronize()
    if not SCOPES[scope]['fresh']:d.x[0].copy_(d.source[0])
    rows.append(dict(V=V,pattern=pattern,variant=variant,scope=scope,**j.check()));j.close()
 d.close()
write(out/'numerical.json',rows);write(out/'complete.json',dict(status='PASS',checks=len(rows)));print('QUALIFIED',len(rows))
