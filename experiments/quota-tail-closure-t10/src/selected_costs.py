from campaign_runtime import *
folder=Path(os.environ['T10_WORKER_DIR']);chosen=read(RUN/'freeze/SELECTION.json');rows=[];aliases=[]
# Normalize process-wide primary module state before fresh-object cost accounting.
for cid in ['LONG','RAGGED']:
 warm=Suite(cid,2);wp=warm.plan(native('SERIAL_GQA_FIRST'));warm.d.reset();wp.run(4);wp.check();warm.close()
for cid in ['LONG','RAGGED']:
 actions={label:native(label) for label in BASELINES}
 for label in ['Q_ONLY','SIMPLE_SPREAD','JOINT_POOL']:actions[label]=chosen[cid][label]['action']
 seen={}
 for label,a in actions.items():
  key=canonical(a)
  if key in seen:aliases.append(dict(case=cid,label=label,source=seen[key]));continue
  seen[key]=label;t=time.perf_counter();s=Suite(cid,2);suite_ms=(time.perf_counter()-t)*1000
  t=time.perf_counter();p=s.plan(a);construction_ms=(time.perf_counter()-t)*1000
  s.d.reset();p.run(4);check=p.check()
  rows.append(dict(case=cid,label=label,action=a,suite_including_data_and_references_ms=suite_ms,common_enumeration_ms=s.enumeration_ms,complete_plan_construction_ms=construction_ms,setup_for_algebra_ms=s.enumeration_ms+construction_ms,meta=p.meta,check=check,scope='Primary math modules prewarmed uniformly; fresh resource/Graph objects per distinct action. Includes resource verification and capture prelaunches; not a cold process or production minimum. Input/reference setup reported separately and excluded from algebra estimate. No H-job workloads run.'))
  s.close()
write(folder/'COSTS.json',rows);write(folder/'ALIASES.json',aliases);write(folder/'COMPLETE.json',dict(status='PASS',distinct_plans=len(rows)));print('SELECTED_COSTS_COMPLETE',flush=True)
