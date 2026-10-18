from backend import *
import sys,random
out=Path(sys.argv[1]);bins=read(ROOT/'freeze/bins.json');cases=read(INPUT/'plans/cases.json');reps=[next(c for c in cases if c['split']=='development' and bin_id(c)==bid) for bid in sorted(bins)]
for c in reps:
 d=Data(c['M'],c['N'],c['K'],ring=4,seed=200000+int(c['id'][1:]));actions=ACTIONS.copy();random.Random(2000+int(c['id'][1:])).shuffle(actions)
 for action in actions:
  budget_check();t=time.perf_counter();e=Engine();kw=config(action,c,bins,e);words=workspace_for(action,c,bins);d.wsize=words;d.w=torch.empty(words,device='cuda',dtype=torch.float32) if words else None
  jobs=[Job(e,d,slot=s,**kw) for s in range(d.ring)];setup_observed_us=(time.perf_counter()-t)*1e6;diagnostic_metadata_us=sum(j.metadata_ms for j in jobs)*1000;setup_us=setup_observed_us-diagnostic_metadata_us
  first=jobs[0].run();tv=time.perf_counter();num=d.numerical(0);validation_us=(time.perf_counter()-tv)*1e6;v=jobs[0].batch(16)
  row=dict(setup_observed_us=setup_observed_us,diagnostic_metadata_us=diagnostic_metadata_us,scientific_validation_us=validation_us,case=c['id'],bin=bin_id(c),action=action,setup_us=setup_us,engine_ms=e.init_ms,roster_ms=e.roster_ms,graph_ms=sum(j.build_ms for j in jobs),input_generation_ms=d.init_ms,workspace_bytes=words*4,runtime_state=e.state(),first_cpu_us=first[1],warm_cpu_us=v[1]/16,numerical=num,scope='Already initialized CUDA; new primary runtime/selected resources, partial allocation and four input-slot graphs; explicit DAG/node observation subtracted and reported separately. Common input generation separate. One deployment cost sample per bin/action; no robust cold-start guarantee.')
  append(out/'setup_costs.jsonl',row)
  for j in jobs:j.close()
  e.close();d.w=None;torch.cuda.empty_cache()
 d.close()
write(out/'complete.json',dict(status='PASS'))
