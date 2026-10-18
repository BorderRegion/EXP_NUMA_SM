from backend import *
import csv,gzip,resource
class Record(C.Structure):
 _fields_=[(x,C.c_int64) for x in ['begin','context','launch','ready','end']]+[('gpu',C.c_double),('global_index',C.c_int64)]+[(x,C.c_int32) for x in ['window','phase','label','slot','action','reserved']]+[('graph',C.c_uint64)]
class Chunk(C.Structure):_fields_=[(x,C.c_int64) for x in ['begin','submitted','end','first','count']]
RP=C.POINTER(Record);CP=C.POINTER(Chunk);LP=C.POINTER(C.c_int64)
lib.diag_episode.argtypes=[C.POINTER(P),C.POINTER(P),I,C.c_double,I,I,C.POINTER(I),I,I,RP,RP,CP,I,LP]
lib.diag_trace.argtypes=[C.POINTER(P),C.POINTER(I),C.POINTER(I),I,I,RP,LP]
lib.diag_body_once.argtypes=[P]
lib.diag_identity.argtypes=[P,C.POINTER(C.c_uint64)]
PROFILES=['BURST_SLOT0','BURST_RING4','READY_SLOT0','READY_RING4']
def ptr(js):return (P*len(js))(*[j.ptr for j in js])
def output_rows(raw,ep,phase_override=None,ids=None):
 rows=[]
 for r in raw:
  assert r.begin<=r.context<=r.launch<=r.ready<=r.end
  row=dict(episode_id=ep['id'],process_block=ep.get('block',-1),case_id=ep['case'],fixture=ep.get('fixture','NATIVE_ONLY'),history_profile=ep.get('conditioning','TRACE_WARMUP'),timer_mode=ep.get('timer_mode','ORIGINAL_EVENT'),phase=phase_override or ['warmup','measure','conditioning'][r.phase],window=r.window,label='AB'[r.label],global_request_index=r.global_index,request=r.global_index,window_request_index=r.global_index%(ep.get('n',128)),input_slot=r.slot,request_begin_ns=r.begin,context_ready_ns=r.context,launch_return_ns=r.launch,ready_ns=r.ready,event_read_end_ns=r.end,cpu_ready_us=(r.ready-r.begin)/1000,gpu_span_us=r.gpu if r.gpu>=0 else '',context_us=(r.context-r.begin)/1000,launch_us=(r.launch-r.context)/1000,wait_us=(r.ready-r.launch)/1000,event_read_us=(r.end-r.ready)/1000,instrumented_us=(r.end-r.begin)/1000,action=ACTIONS[r.action],graph_id=hex(r.graph))
  if ids is not None:row['case_id']=ids[r.global_index%len(ids)];row['request']=r.global_index%len(ids)
  rows.append(row)
 return rows
def save_csv(path,rows):
 with gzip.open(path,'wt',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def host_state():
 r=resource.getrusage(resource.RUSAGE_SELF)
 return dict(monotonic_ns=time.monotonic_ns(),wall_ns=time.time_ns(),pid=os.getpid(),affinity=sorted(os.sched_getaffinity(0)),proc_stat=Path('/proc/self/stat').read_text(),loadavg=Path('/proc/loadavg').read_text(),voluntary_context_switches=r.ru_nvcsw,involuntary_context_switches=r.ru_nivcsw)
def episode(ep,aa,bb,n,out,seconds=30):
 budget_check();ep={**ep,'n':n};nw=ep.get('windows',4);order=ep.get('order')
 if not order:order=('ABBA' if ep.get('block',0)%2==0 else 'BAAB')+('BAAB' if ep.get('block',0)%2==0 else 'ABBA')+('ABBA' if ep.get('block',0)%2==0 else 'BAAB')
 labels=order[:nw];raw=(Record*(nw*2*n))();hist=(Record*192)();chunks=(Chunk*65536)();info=(C.c_int64*12)();before=host_state()
 check(lib.diag_episode(ptr(aa),ptr(bb),PROFILES.index(ep.get('conditioning','READY_RING4')),seconds,n,nw,(I*nw)(*[int(x=='B') for x in labels]),int(ep.get('measured_slots')=='SLOT0'),int(ep.get('timer_mode')=='BODY_CPU_ONLY'),raw,hist,chunks,65536,info))
 after=host_state();rows=output_rows(raw,ep);save_csv(out/(ep['id']+'.requests.csv.gz'),rows)
 h=[r for r in hist if r.end];h.sort(key=lambda x:x.global_index)
 # Conditioning always uses aa; its actual fixed action is known from cfg.
 for r in h:r.action=1 if aa[0].cfg[5]==4 else 0
 if h:save_csv(out/(ep['id']+'.conditioning_edges.csv.gz'),output_rows(h,ep,'conditioning'))
 cc=[dict(start_ns=c.begin,submitted_ns=c.submitted,ready_ns=c.end,first_request=c.first,count=c.count) for c in list(chunks)[:info[3]]]
 write(out/(ep['id']+'.conditioning.json'),dict(profile=ep.get('conditioning','READY_RING4'),requested_seconds=seconds,actual_seconds=(info[1]-info[0])/1e9,start_ns=info[0],end_ns=info[1],replays=info[2],slot_histogram=list(info[4:8]),chunks=cc,edge_history_scope='READY first64 and final128; BURST only finite packet timestamps, no reused-event per-request claim'))
 summ=[]
 for wi in range(nw):
  for phase in ['warmup','measure']:
   rr=[r for r in rows if r['window']==wi and r['phase']==phase]
   summ.append(dict(window=wi,phase=phase,label=rr[0]['label'],n=len(rr),mean_cpu_ready_us=float(np.mean([r['cpu_ready_us'] for r in rr])),mean_gpu_span_us=float(np.mean([r['gpu_span_us'] for r in rr])) if rr[0]['gpu_span_us']!='' else None,start_ns=rr[0]['request_begin_ns'],end_ns=rr[-1]['event_read_end_ns']))
 result=dict(ep,labels=labels,windows_summary=summ,condition_end_ns=info[1],measurement_start_ns=info[8],measurement_end_ns=info[9],host_before=before,host_after=after,status='PASS',returncode=0)
 append(out/'episodes.jsonl',result);print(ep['id'],ep['case'],ep.get('conditioning'),[round(x['mean_cpu_ready_us'],1) for x in summ if x['phase']=='measure'],flush=True);return result
def meta(js,e,d):
 identities=[]
 for j in js:
  a=(C.c_uint64*7)();check(lib.diag_identity(j.ptr,a));identities.append(dict(zip(['context','stream','body','body_exec','timed_exec','start_event','end_event'],map(hex,a))))
 return dict(seed=d.seed,shape=[d.m,d.n,d.k],ring=d.ring,input_addresses=[x.data_ptr() for x in d.a],weight_address=d.b.data_ptr(),output_address=d.d.data_ptr(),activation_address=d.act.data_ptr() if d.chain else None,second_weight_address=d.b2.data_ptr() if d.chain else None,final_output_address=d.d2.data_ptr() if d.chain else None,workspace_words=d.wsize,math_sha256=sha(BUILD/'diag0.cubin'),runtime_state=e.state(),resource_roster=e.membership,graphs=[dict(cfg=j.cfg,dag=j.dag,ptr=hex(j.ptr),build_ms=j.build_ms,identity=identities[i]) for i,j in enumerate(js)])
def qualify(jobs,d,out,identity,when,all_slots=True):
 t=time.perf_counter();recs=[]
 for action,js in jobs.items():
  for slot,j in enumerate(js):
   if not all_slots and slot!=3:continue
   j.run();num=d.numerical(slot);sub=dict(first=d.d[:min(4,d.m),:8].cpu().tolist())
   if d.chain:sub.update(activation=d.act[:min(4,d.m),:8].cpu().tolist(),final=d.d2[:min(4,d.m),:8].cpu().tolist())
   recs.append(dict(identity=identity,when=when,action=action,slot=slot,numerical=num,output_sample=sub))
 for r in recs:append(out/'correctness.jsonl',r)
 append(out/'setup.jsonl',dict(identity=identity,when=when,numerical_qualification_us=(time.perf_counter()-t)*1e6))
def trace(ep,plans,seq,out,dynamic):
 sig=list(dict.fromkeys(seq));assert [p.c['id'] for p in plans]==sig
 ids=[sig.index(x) for x in seq];jobs=[j for p in plans for j in p.jobs];n=len(seq);raw=(Record*(2*n))();m=(C.c_int64*6)();before=host_state()
 check(lib.diag_trace(ptr(jobs),(I*n)(*ids),(I*len(plans))(*[ACTIONS.index(p.action) for p in plans]),n,int(dynamic),raw,m));after=host_state()
 ep={**ep,'n':n};rows=output_rows(raw,ep,ids=seq);save_csv(out/(ep['id']+'.requests.csv.gz'),rows)
 vals=[]
 for phase in range(2):
  rr=rows[phase*n:(phase+1)*n];s=sum(x['cpu_ready_us'] for x in rr);total=(m[phase*3+1]-m[phase*3])/1000
  vals.append(dict(phase=['warmup','measure'][phase],start_ns=m[phase*3],last_ready_ns=m[phase*3+1],end_ns=m[phase*3+2],total_completion_us=total,instrumented_us=(m[phase*3+2]-m[phase*3])/1000,sum_ready_us=s,other_host_intervals_us=total-s,sum_gpu_span_us=sum(x['gpu_span_us'] for x in rr)))
 result=dict(ep,status='PASS',phase_totals=vals,signature_ids=sig,plans=[p.metadata() for p in plans],graph_identities_and_addresses=[meta(p.jobs,p.e,p.d) for p in plans],host_before=before,host_after=after,dynamic_per_request=dynamic)
 append(out/'episodes.jsonl',result);print(ep['id'],ep['case'],ep['policy'],round(vals[1]['total_completion_us'],1),flush=True);return result
