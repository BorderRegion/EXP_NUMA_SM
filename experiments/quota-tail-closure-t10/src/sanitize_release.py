from campaign_runtime import *
folder=Path(os.environ['T10_WORKER_DIR']);rows=[]
for cid in ['LONG','RAGGED']:
 s=Suite(cid,2)
 for k in [1,31]:
  p=s.plan(action('SPREAD',28,'RELEASE',k));s.d.reset();p.run(4);rows.append(dict(case=cid,k=k,check=p.check()))
 s.close()
write(folder/'CHECKS.json',rows);write(folder/'COMPLETE.json',dict(status='PASS',scope='Four full-job release plans at k1/k31; not every formal request'));print('SANITIZER_RELEASE_NUMERICAL_PASS',flush=True)
