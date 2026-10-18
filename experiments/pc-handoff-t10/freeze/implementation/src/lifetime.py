from backend import *
import sys
out=Path(sys.argv[1]);block=int(sys.argv[2]);sel=json.loads((ROOT/'freeze/selection.json').read_text());rule=json.loads((ROOT/'freeze/pc_rule.json').read_text());cases=[sel['representatives'][i] for i in [0,1,2,5]]
for c in cases:
 for policy in ['LIB','G','M']:
  t=time.perf_counter();e=Engine(mode=-2 if policy=='LIB' else rule['partition']);d=Data(c['M'],c['N'],c['K'],s=c['S'],ring=4,seed=98000+int(c['case_id'][1:]));groups=e.halves[rule['partition']]
  kw=dict(recipe=c['recipe'],s=c['S'],kind=3 if policy=='LIB' else 1,slab=0 if policy=='LIB' else 1,pg=groups,cg=groups[::-1] if policy=='M' and rule['pi'] else groups)
  jobs=[Job(e,d,slot=i,**kw) for i in range(4)];setup=(time.perf_counter()-t)*1000;first=jobs[0].run();num=d.numerical(0);[j.batch(32) for j in jobs];batch=jobs[0].batch(max(16,min(1024,round(100000/c['lib_us']))))
  append(out/'lifetime.jsonl',dict(block=block,case=c['case_id'],policy=policy,total_input_generation_and_setup_ms=setup,engine_init_ms=e.init_ms,roster_validation_ms=e.roster_ms,resource_setup=e.setup_costs,input_and_workspace_allocation_ms=d.init_ms,graphs_ms=sum(j.build_ms for j in jobs),first_gpu_us=first[0],first_cpu_us=first[1],warm_batch_us=batch[0]/max(16,min(1024,round(100000/c['lib_us']))),numerical=num,scope='Per-policy fresh resources and allocation. Input generation common cost listed separately; research PC matrix is not charged as per-request work. Frozen rule can be reused only after exact resource validation.'))
  for j in jobs:j.close()
  d.close();e.close()
write(out/'complete.json',dict(status='PASS',sessions=12))
