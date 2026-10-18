from runtime import *
import sys
out=Path(sys.argv[1]);e=Engine();results=[]
for m,n,k,recipe,s in [(1,1024,160,0,4),(17,1536,2080,2,4),(33,320,1056,2,8)]:
 d=Data(m,n,k,s=s,seed=77,ring=2,workspace_words=m*n*s);d.splits=s;d.c.copy_(torch.linspace(-1,1,m*n,device='cuda').reshape(m,n));c=dict(recipe=recipe,s=s)
 for chunk in [512,1024]:
  for grid in [56,112]:
   jobs,b=build_jobs(e,d,c,chunk,grid,seed=1)
   for pol in POLICIES:
    # Existing LIB API is alpha=1,beta=0; numerical below uses its baseline.
    for slot,j in enumerate(jobs[pol]):results.append(dict(M=m,N=n,K=k,chunk=chunk,grid=grid,policy=pol,slot=slot,numerical=numeric(j,d)))
   for _ in range(20):
    for pol in POLICIES:repeat(jobs[pol][_ % 2],1)
   assert not b['counters']['fused'].count_nonzero().item()
   close_jobs(jobs)
  # Non-default alpha/beta, including queue reset and last-arrival fused stores.
  for kind in [10,11,12]:
   counter=b['counters']['fused' if kind==12 else 'queue'];j=Job(e,d,recipe=recipe,s=s,kind=kind,slab=chunk,submit_reverse=56,task_reverse=1,mapping=b['lists']['plain'],counters=counter,alpha=.75,beta=-.25);j.run();results.append(dict(M=m,N=n,K=k,chunk=chunk,kind=kind,alpha=.75,beta=-.25,numerical=d.numerical(0,.75,-.25)));j.close()
  jobs,b=build_jobs(e,d,c,chunk,56,1,diag=True);folder=out/f'{m}_{n}_{k}_{chunk}';folder.mkdir();results+=validate_traces(jobs,b,d,c,folder);close_jobs(jobs)
 d.close()
e.close();write(out/'qualification.json',results);print('QUALIFICATION_PASS',len(results))
