from range_runtime import *
folder=Path(os.environ['T10_WORKER_DIR']);block=int(sys.argv[1]);c=Control();d=GQAData(shape('A02'),211700+block,32768*block)
sets=[p for p in read(RUN/'freeze/resource_subsets.json')['resource_sets'] if p['block']==block and (p['gpc'],p['sm_count']) in [(0,10),(1,8),(1,10),(1,12),(2,12)]]
sets.append(dict(gpc=None,sm_count=56,sm_ids=list(range(56))));rows=[];ph=[];checks=[];ref=NativePlan(c,d,False,'E56',True);raw=[]
for s in range(4):d.reset();ref.run(1,s);raw.append(d.out.cpu().clone())
ref.close()
for resource in sets:
 g=c.create(resource['sm_ids']) if resource['gpc'] is not None else 0
 if g:c.verify(g,resource['sm_ids'])
 p=RangePlan(c,d,False,[g],[dict(task_begin=0,task_count=d.B*d.HK*32,physical_gpc=resource['gpc'])]);checks.append(dict(resource=resource,checks=qualify(p,raw)));warm(p);a=p.run(64)
 for i,v in enumerate(a):rows.append(dict(block=block,resource=resource,request=i,slot=i%4,gpu_us=float(v[0]),ready_us=float(v[1])))
 ph.append(dict(block=block,recipe='GQA4_LONG',resource=resource,gpu_us=float(a[:,0].mean()),ready_us=float(a[:,1].mean()),requests=len(a),scope='attention-only same DIRECT full task set, primary merge; whole operator not isolated producer'))
 p.close()
 if g:c.drop(g)
write(folder/'PHASES.json',ph);write(folder/'CHECKS.json',checks)
with gzip.open(folder/'REQUESTS.json.gz','wt') as f:json.dump(rows,f)
write(folder/'DONE.json',dict(status='PASS',labels=len(ph)))
