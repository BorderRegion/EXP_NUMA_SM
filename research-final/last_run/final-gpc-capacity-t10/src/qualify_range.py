from range_runtime import *
folder=Path(os.environ['T10_WORKER_DIR']);c=Control();gs,cost=groups_create(c);records=[]
for cid in ['A01','A02','A03','A04']:
 d=GQAData(shape(cid),211020+int(cid[1:]),0)
 for append in [False,True]:
  ref=NativePlan(c,d,append,'E56',True);qualify(ref);raw=[]
  for s in range(4):d.reset();ref.run(1,s);raw.append(d.out.cpu().clone())
  ref.close()
  for kind,w in [('E56_DIRECT',None),('SM_PROP',[10,12,12,10,12]),('EQUAL_GPC',[1]*5)]:
   ranges=ranges_for(d,w) if w else [dict(task_begin=0,task_count=d.B*d.HK*32 if cid!='A04' else d.B*d.HK*16)]
   plan=RangePlan(c,d,append,gs if w else [0],ranges)
   rec=qualify(plan,raw);records.append(dict(case=cid,append=append,kind=kind,checks=rec,info=plan.info));plan.close()
   if kind=='SM_PROP':
    tr=RangePlan(c,d,append,gs,ranges,trace=True);r=qualify(tr,raw,True);records.append(dict(case=cid,append=append,kind='TRACE_SIBLING',checks=r));tr.close()
  native=NativePlan(c,d,append);records.append(dict(case=cid,append=append,kind='N19',checks=qualify(native),info=native.info));native.close()
  print(cid,append,'PASS',flush=True);write(folder/'QUALIFICATION.json',dict(status='IN_PROGRESS',records=records))
 d.close()
write(folder/'QUALIFICATION.json',dict(status='PASS',resource_setup_ms=cost,records=records,unit_map=c.units));print('RANGE_QUALIFICATION_PASS',flush=True)
for g in gs:c.drop(g)
