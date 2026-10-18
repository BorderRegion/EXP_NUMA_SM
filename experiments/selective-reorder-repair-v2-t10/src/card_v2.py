from paired import *
import random
out=Path(sys.argv[1]);block=int(sys.argv[2]);bins=read(ROOT/'freeze/bins.json');cases=[c for c in read(INPUT/'plans/cases.json') if c['id'] in ['D03','D10','D17','D24']];e=Engine(mode=-3,diagnostic=True);write(out/'roster.json',dict(groups=e.membership,quad=e.quad,halves=e.halves,state=e.state()))
for c in cases:
 cid=c['id'];b=bins[bin_id(c)];d=Data(c['M'],c['N'],c['K'],ring=1,seed=290000+block*100+int(cid[1:]),workspace_words=workspace_for('PC0_0',c,bins),workspace_slots=2);jobs={};stage_jobs={};native=Job(e,d,kind=3);science_us=0;build_us=native.build_ms*1000
 for w in range(2):
  for p in range(4):
   for q in range(4):
    kw=dict(kind=2,recipe=b['split_recipe'],s=b['split_S'],slab=1,pg=[e.quad[p]]*2,cg=[e.quad[q]]*2,wslot=w);j=Job(e,d,**kw);jobs[w,p,q]=j;build_us+=j.build_ms*1000;tv=time.perf_counter();j.run();append(out/'correctness.jsonl',dict(case=cid,W=w,P=p,C=q,when='BEFORE',numerical=d.numerical(0)));science_us+=(time.perf_counter()-tv)*1e6
    if w==0:stage_jobs[p,q]=Job(e,d,**kw,stages=1);build_us+=stage_jobs[p,q].build_ms*1000
 condition_jobs([native],out,cid,30);opts=list(jobs);random.Random(2910+block+int(cid[1:])).shuffle(opts)
 for order,(w,p,q) in enumerate(opts):
  budget_check();j=jobs[w,p,q];z=windows([j],[j],16,'A')[0];append(out/'phases.jsonl',dict(phase_id=f'{block}_{cid}_{w}_{p}_{q}',case=cid,case_id=cid,block=block,W=w,P=p,C=q,workspace_address=d.w.data_ptr()+w*d.wsize*4,stage='S2_CARD',order=order,gpu_us=z['mean_gpu_us'],cpu_ready_us=z['mean_cpu_us'],window=z,protocol_id='CARD_CLEAN_CPP_READY_V2',state_epoch=STATE['state_epoch'],metadata=job_meta([j],e,d)))
 for (p,q),j in stage_jobs.items():
  z=windows([j],[j],8,'A')[0];v=np.mean(z['samples'],axis=0);append(out/'stages.jsonl',dict(case=cid,block=block,P=p,C=q,P_us=float(v[2]),R_us=float(v[3]),chain_us=float(v[0]),window=z,scope='SEPARATE_STAGE_INSTRUMENTED_REAL_PRODUCER_REDUCER'));j.close()
 for (w,p,q),j in jobs.items():
  tv=time.perf_counter();j.run();append(out/'correctness.jsonl',dict(case=cid,W=w,P=p,C=q,when='AFTER',numerical=d.numerical(0)));science_us+=(time.perf_counter()-tv)*1e6;j.close()
 append(out/'cost_components.jsonl',dict(case_id=cid,block=block,numerical_scientific_us=science_us,graph_build_us=build_us,input_generation_us=d.init_ms*1000,scope='Actual card setup/qualification components. Graph extraction, Python bookkeeping and process cold start not individually isolated.'))
 native.close();d.close();print('CARD',block,cid,flush=True)
e.close();write(out/'complete.json',dict(status='PASS',episodes=128,block=block))
