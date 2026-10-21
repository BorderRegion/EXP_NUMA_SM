from campaign_runtime import *
folder=Path(os.environ['T10_WORKER_DIR']);results=[];c=Control();rosters=[]
z.qt_sm_count.argtypes=[I]
assert ck(z.qt_sm_count(0))==56
for item in read(RUN/'freeze/resource_sets.json')['plans']:
 groups=[]
 for key in ['foreground_sm_ids','background_sm_ids']:
  sms=item[key];g=c.create(sms);groups.append(g);got=c.verify(g,sms);count=ck(z.qt_sm_count(g));assert count==len(sms)
  rosters.append(dict(block=item['block'],family=item['family'],quota=item['foreground_sms'],side=key,observed=got,driver_sm_count=count))
 for g in groups:c.drop(g)
write(folder/'ROSTERS.json',rosters)
with gzip.open(folder/'RESOURCE_TRACE.json.gz','wt') as f:json.dump(c.observations,f)
del c
for cid in ['LONG','RAGGED']:
 s=Suite(cid,0);n19=s.solo('FG','PRIMARY56','N19');e56=s.solo('FG','PRIMARY56')
 s.d.reset();r=n19.run(4);q=n19.check();ref=s.d.out.cpu().clone();results.append(dict(case=cid,kind='N19_REGRESSION',times=r.tolist(),check=q))
 s.d.reset();r=e56.run(4);q=e56.check();raw_equal=torch.equal(ref,s.d.out.cpu());assert raw_equal or cid=='LONG';results.append(dict(case=cid,kind='E56_REGRESSION',times=r.tolist(),check=q,raw_bit_equal=raw_equal,non_determinism_allowed=cid=='LONG'))
 for qsm in [10,46]:
  for k in [1,6,31]:
   p=s.plan(action('SPREAD',qsm,'RELEASE',k),diagnostic=True)
   for slot in range(4):
    s.d.reset();s.c.run([p.fgs[slot]],1);prefix=s.d.check_mode(True,(slot+k-1)%4)
    s.c.run([p.suffixes[slot]],1);suffix=s.d.check_mode(True,(slot+31)%4)
    results.append(dict(case=cid,kind='SEPARATE_BOUNDARY_STATE',q=qsm,k=k,start_slot=slot,prefix=prefix,suffix=suffix))
   s.d.reset();r=p.run(4);chk=p.check();assert (r[:,6]+2>=np.maximum(r[:,4],r[:,2])).all();assert (r[:,5]>0).all()
   results.append(dict(case=cid,kind='ACTUAL_DEVICE_RELEASE',q=qsm,k=k,times=r.tolist(),check=chk,primary_suffix=True,meta=p.meta))
  fg,bg,fs,bs=s.placement(action('SPREAD',qsm,'FIXED'))
  # Separate trace sibling at each source and full-primary destination.
  trace=GQAJob(s.d,True,'E56',trace=True)
  for g,allowed in [(fg,fs),(0,list(range(56)))]:
   s.d.reset();s.d.trace.zero_();torch.cuda.synchronize();s.c.current(g);trace.op(0)(s.c.stream(g));s.c.sync(g);s.c.current(0)
   a=s.d.trace.cpu().numpy().reshape(s.d.B*s.d.HK,s.d.NP,5);assert (a[:,:,4]==1).all() and set(np.unique(a[:,:,0])).issubset(allowed)
   results.append(dict(case=cid,kind='TRACE_RESOURCE',driver_sm_count=ck(z.qt_sm_count(g)),observed_sms=np.unique(a[:,:,0]).tolist(),allowed_sms=allowed,all_pages_exactly_once=True))
 write(folder/f'{cid}_PROVENANCE.json',s.provenance());s.close();print('QUALIFIED',cid,flush=True)
write(folder/'NUMERICAL.json',results);write(folder/'COMPLETE.json',dict(status='PASS',resource_rosters=len(rosters),checks=len(results),no_formal_performance_data=True));print('S0_QUALIFICATION_PASS',flush=True)
