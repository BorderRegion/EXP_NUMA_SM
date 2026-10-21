from range_runtime import *
c=Control();gs,_=groups_create(c)
for cid in ['A01','A03','A04']:
 d=GQAData(shape(cid),211900+int(cid[1:]),0)
 p=RangePlan(c,d,True,gs,ranges_for(d,[10,12,12,10,12]));qualify(p);p.close();d.close();print('SANITIZER_CASE_PASS',cid,flush=True)
for g in gs:c.drop(g)
