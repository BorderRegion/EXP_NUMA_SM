"""Finite frozen-graph submission/pacing interventions. No fitting or new kernel."""
import os
os.environ['TEARDOWN_CUPTI']='0';os.environ['DISABLE_CUPTI_LAZY_REINIT']='1'
from diag import *
from nvml_state import NVML
import sys,signal,contextlib
class Packet(C.Structure):_fields_=[(x,C.c_int64) for x in ['begin','submitted','ready','end','first','count']]+[('gpu_us',C.c_double)]
lib.state_run.argtypes=[C.POINTER(P),I,C.c_double,C.c_int64,RP,I,C.POINTER(Packet),I,LP]
CAP=250000;PCAP=4096
MODES={'A':0,'B':1,'C':2,'D':3}
def dump_requests(path,rr,mode,phase):
 def values():
  for v in rr:
   yield dict(phase=phase,mode=mode,global_request=v.global_index,slot=v.slot,begin_ns=v.begin,context_ns=v.context,launch_ns=v.launch,ready_ns=v.ready if v.ready else '',event_read_end_ns=v.end,graph_id=hex(v.graph),cpu_ready_us=(v.ready-v.begin)/1000 if v.ready else '',gpu_span_us=v.gpu if v.gpu>=0 else '',launch_us=(v.launch-v.context)/1000,wait_us=(v.ready-v.launch)/1000 if v.ready else '',event_read_us=(v.end-v.ready)/1000 if v.ready else '',requested_idle_us=100 if mode=='B' else 1000 if mode=='C' else 0)
 with gzip.open(path,'wt',newline='') as f:
  it=values();first=next(it);w=csv.DictWriter(f,fieldnames=list(first));w.writeheader();w.writerow(first);w.writerows(it)
def run(out,kind,block):
 protocol=read(ROOT/'freeze/PROTOCOL.json');cid='R_G002' if kind=='control' else 'R_G017';case=next(x for x in read(PRIOR/'input/T10_SELECTIVE_REORDER_REPAIR_V2_20261017/plans/cases.json') if x['id']==cid)
 if kind=='main':order=protocol['orders'][block];cond=30;seconds=8
 elif kind=='control':order=protocol['orders'][block*5];cond=10;seconds=4
 elif kind=='confirm':order=protocol['orders'][block*5];cond=10;seconds=4
 elif kind=='observer':order=protocol['observer_order'][block];cond=10;seconds=6
 elif kind=='profile':order=protocol['orders'][block*5];cond=30;seconds=1.5
 elif kind=='smoke':order='ABCDA';cond=1;seconds=.2
 else:raise ValueError(kind)
 if kind=='confirm':
  (out/'telemetry_hz.txt').write_text('1')
  if (out/'telemetry.pid').exists():os.kill(int((out/'telemetry.pid').read_text()),signal.SIGUSR1)
 e=Engine();d=Data(case['M'],case['N'],case['K'],seed=940000+block+(100 if kind=='control' else 0),ring=4)
 js=[Job(e,d,slot=s,**config('LIB',case,read(ROOT/'freeze/bins.json'),e)) for s in range(4)]
 qualify({'LIB':js},d,out,'ALL','BEFORE');write(out/'graphs.json',meta(js,e,d));nv=NVML()
 # Allocate all buffers before conditioning, no append/JSON/ref computation in timed loops.
 buffers=[((Record*CAP)(),(Packet*PCAP)(),(C.c_int64*6)()) for _ in range(len(order)+1)]
 phase_data=[];ordinal=0
 def one(index,label,duration,measured):
  nonlocal ordinal
  raw,pk,info=buffers[index];budget_check()
  if kind=='observer':
   hz=1 if label=='A' or not measured else 20;(out/'telemetry_hz.txt').write_text(str(hz))
   if (out/'telemetry.pid').exists():os.kill(int((out/'telemetry.pid').read_text()),signal.SIGUSR1)
  host_before=host_state()
  mode='A' if kind=='observer' else label
  check(lib.state_run(ptr(js),MODES[mode],duration,ordinal,raw,CAP,pk,PCAP,info));host_after=host_state();ordinal=info[4]
  rec=dict(phase=index-1,label=label,mode=mode,kind=kind,block=block,case=cid,measured=measured,requested_seconds=duration,requested_hz=(1 if label=='A' or not measured else 20) if kind=='observer' else (1 if kind=='confirm' else 20),start_ns=info[0],end_ns=info[1],requests=info[2],packets=info[3],ordinal_end=info[4],host_before=host_before,host_after=host_after)
  phase_data.append(rec)
 one(0,'A',cond,False)
 prof=torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,torch.profiler.ProfilerActivity.CUDA]) if kind=='profile' else None
 entry_begin=time.monotonic_ns()
 with prof if prof else contextlib.nullcontext():
  active=time.monotonic_ns()
  for index,label in enumerate(order,1):one(index,label,seconds,True)
  capture_end=time.monotonic_ns()
 if prof:
  prof.export_chrome_trace(str(out/'activity.chrome.json'));write(out/'profile_scope.json',dict(entry_begin_ns=entry_begin,active_ns=active,capture_end_ns=capture_end,conditioning_not_captured=True,scope='Separate observed7phase replay; full per-request host bounds; no claim identical formalhistory'))
 for rec,(raw,pk,info) in zip(phase_data,buffers):
  prefix='condition' if not rec['measured'] else 'phase_'+str(rec['phase'])
  dump_requests(out/(prefix+'.requests.csv.gz'),raw[:info[2]],rec['mode'],rec['phase'])
  packets=[{k:getattr(v,k) for k,_ in Packet._fields_} for v in pk[:info[3]]];write(out/(prefix+'.packets.json'),packets);rec['raw_file']=prefix+'.requests.csv.gz';rec['packet_file']=prefix+'.packets.json';append(out/'phases.jsonl',rec)
 qualify({'LIB':js},d,out,'ALL','AFTER');nv.close()
 for j in js:j.close()
 d.close();e.close();write(out/'complete.json',dict(status='PASS',kind=kind,block=block,case=cid,order=order,all_conditioning_requests_preserved=True,phases=len(phase_data)))
 print(kind,block,cid,order,[(x['label'],x['requests'],round((x['end_ns']-x['start_ns'])/1e9,3)) for x in phase_data],flush=True)
if __name__=='__main__':run(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3]))
