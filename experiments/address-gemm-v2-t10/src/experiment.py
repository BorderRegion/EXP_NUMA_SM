from runtime import *
import sys,itertools

def run(out,phase,process):
 prot=read(ROOT/'freeze/PROTOCOL.json');rng=np.random.default_rng(612000+process);cases=prot['cases'];allrows=[];num=[];placement=[];setups=[]
 if phase=='development':geometries=list(itertools.product(prot['chunks_candidates'],prot['grid_candidates']))
 else:
  freeze=read(ROOT/'freeze/SELECTED_GEOMETRY.json');geometries=[(freeze['chunk'],freeze['grid'])]
 e=Engine()
 for c in cases:
  cid=c['id'];cd=out/cid;cd.mkdir();m,n,k=c['M'],c['N'],c['K'];d=Data(m,n,k,s=c['s'],seed=210000+process,ring=4,workspace_words=m*n*c['s']+(69632+4096)//4);d.splits=c['s'];base=d.w;align=(-base.data_ptr())%4096
  for offset in prot['workspace_offsets_bytes']:
   d.w=base[(offset+align)//4:(offset+align)//4+m*n*c['s']];assert d.w.data_ptr()%4096==0
   for chunk,grid in geometries:
    tag=f'o{offset}_c{chunk}_g{grid}';q=cd/tag;q.mkdir();start=time.perf_counter();jobs,b=build_jobs(e,d,c,chunk,grid,seed=1800+process);setup_ms=(time.perf_counter()-start)*1000
    write(q/'mapping.json',b['meta']);write(q/'graphs.json',{pol:[j.dag for j in js] for pol,js in jobs.items()})
    for pol,js in jobs.items():
     for slot,j in enumerate(js):num.append(dict(case=cid,offset=offset,chunk=chunk,grid=grid,stage='before',policy=pol,slot=slot,**numeric(j,d)))
    records=[]
    def observe(label,phase_name,block,pos,slot,replays):
     pol='NATIVE' if label.startswith('NATIVE_') else label;begin=time.monotonic_ns();v=repeat(jobs[pol][slot],replays);end=time.monotonic_ns()
     for i,a in enumerate(v):records.append(dict(case=cid,offset=offset,chunk=chunk,grid=grid,phase=phase_name,block=block,position=pos,label=label,policy=pol,slot=slot,request=i,gpu_us=a[0],host_us=a[1],p_us=a[2],r_us=a[3],observation_begin_ns=begin,observation_end_ns=end))
    deadline=time.monotonic()+.3;seq=0
    while time.monotonic()<deadline:
     for pos,pol in enumerate(POLICIES):observe(pol,'conditioning',seq,pos,seq%4,1)
     seq+=1
    # Confirmation orientation is fitted to complete, concurrent GEMM runs only.
    selected=None;cal_ms=0
    if phase=='confirmation':
     t=time.perf_counter()
     for block in range(prot['confirmation_calibration_blocks']):
      for pos,pol in enumerate(rng.permutation(['QUEUE_MATCH','QUEUE_INVERT','QUEUE_BLIND'])):observe(pol,'calibration',block,pos,block%4,prot['confirmation_calibration_replays'])
     cal_ms=(time.perf_counter()-t)*1000;score={}
     for pol in ['QUEUE_MATCH','QUEUE_INVERT']:
      ratios=[]
      for block in range(prot['confirmation_calibration_blocks']):
       a=np.median([r['gpu_us'] for r in records if r['phase']=='calibration' and r['block']==block and r['policy']==pol]);basev=np.median([r['gpu_us'] for r in records if r['phase']=='calibration' and r['block']==block and r['policy']=='QUEUE_BLIND']);ratios.append(np.log(a/basev))
      score[pol]=float(np.mean(ratios))
     selected=min(score,key=lambda p:(score[p],p));write(q/'selection.json',dict(selected=selected,training_log_ratio_to_blind=score,calibration_ms=cal_ms,frozen_ns=time.monotonic_ns(),future_test_not_used=True))
    blocks=prot['development_blocks'] if phase=='development' else prot['confirmation_blocks'];replays=prot['development_replays'] if phase=='development' else prot['replays_per_block']
    for block in range(blocks):
     order=['NATIVE_A']+rng.permutation(POLICIES).tolist()+['NATIVE_B']
     for pos,pol in enumerate(order):observe(pol,'test',block,pos,block%4,replays)
     # Save every complete randomized block; no time-based exclusions.
     save_rows(q/'requests.csv.gz',records)
    for pol,js in jobs.items():
     for slot,j in enumerate(js):num.append(dict(case=cid,offset=offset,chunk=chunk,grid=grid,stage='after',policy=pol,slot=slot,**numeric(j,d)))
    assert not b['counters']['fused'].count_nonzero().item()
    # Separate instrumented placement replay; no trace in primary time.
    close_jobs(jobs);jdiag,bd=build_jobs(e,d,c,chunk,grid,1800+process,diag=True);pr=validate_traces(jdiag,bd,d,c,q);placement.extend([dict(case=cid,offset=offset,chunk=chunk,grid=grid,**r) for r in pr]);close_jobs(jdiag)
    setups.append(dict(case=cid,offset=offset,chunk=chunk,grid=grid,graphs_and_lists_ms=setup_ms,calibration_ms=cal_ms,selected=selected,data_init_ms=d.init_ms,alignment_bytes=align,workspace_va=d.w.data_ptr(),workspace_bytes=d.w.numel()*4,queue_counter_bytes=b['meta']['counter_bytes'],no_per_request_CPU_scheduler=True))
    write(out/'numerical.json',num);write(out/'placement.json',placement);write(out/'setup.json',setups);write(q/'complete.json',dict(status='PASS',test_requests=blocks*10*replays,phase=phase));print(phase,process,cid,tag,selected,'PASS',flush=True)
  d.w=base;d.close()
 e.close();write(out/'complete.json',dict(status='PASS',phase=phase,process=process))
if __name__=='__main__':run(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3]))
