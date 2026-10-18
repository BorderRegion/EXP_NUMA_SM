"""Fixed preparation, identical inputs, unchanged host runtime and GPU math."""
from diag import *
import sys
class Packet(C.Structure):
 _fields_=[(x,C.c_int64) for x in ['begin','submitted','ready','end','first','count']]+[('gpu_us',C.c_double)]
lib.state_run.argtypes=[C.POINTER(P),I,C.c_double,C.c_int64,RP,I,C.POINTER(Packet),I,LP]
CAP=250000;PCAP=4096

def dump_requests(path,rr,mode,phase):
 def values():
  for v in rr:
   yield dict(phase=phase,mode=mode,global_request=v.global_index,slot=v.slot,begin_ns=v.begin,context_ns=v.context,launch_ns=v.launch,ready_ns=v.ready,event_read_end_ns=v.end,graph_id=hex(v.graph),cpu_ready_us=(v.ready-v.begin)/1000,gpu_span_us=v.gpu,launch_us=(v.launch-v.context)/1000,wait_us=(v.ready-v.launch)/1000,event_read_us=(v.end-v.ready)/1000,requested_idle_us=100 if mode=='B' else 0)
 with gzip.open(path,'wt',newline='') as f:
  it=values();first=next(it);w=csv.DictWriter(f,fieldnames=list(first));w.writeheader();w.writerow(first);w.writerows(it)

def run(out,kind,block,hz):
 protocol=read(ROOT/'freeze/PROTOCOL.json');smoke=kind=='smoke'
 if not smoke:assert hz==protocol['monitor_hz_order'][block]
 case=next(x for x in read(PRIOR/'input/T10_SELECTIVE_REORDER_REPAIR_V2_20261017/plans/cases.json') if x['id']=='R_G017')
 cond=1 if smoke else protocol['conditioning_s'];seconds=.2 if smoke else protocol['phase_s'];order='ABA' if smoke else protocol['order']
 assert int((out/'telemetry_hz.txt').read_text())==hz
 e=Engine();d=Data(case['M'],case['N'],case['K'],seed=protocol['seed'],ring=4)
 js=[Job(e,d,slot=s,**config('LIB',case,read(ROOT/'freeze/bins.json'),e)) for s in range(4)]
 write(out/'fixture.json',dict(shape=[d.m,d.n,d.k],seed=d.seed,input_hashes=[sha_bytes(x) for x in d.ha],weight_hash=sha_bytes(d.hb),kind=kind,block=block,monitor_hz=hz))
 qualify({'LIB':js},d,out,'ALL','BEFORE');write(out/'graphs.json',meta(js,e,d))
 buffers=[((Record*CAP)(),(Packet*PCAP)(),(C.c_int64*6)()) for _ in range(len(order)+1)]
 phase_data=[];ordinal=0
 for index,mode in enumerate('A'+order):
  budget_check();measured=index>0;duration=seconds if measured else cond;raw,pk,info=buffers[index];host_before=host_state()
  check(lib.state_run(ptr(js),int(mode=='B'),duration,ordinal,raw,CAP,pk,PCAP,info));host_after=host_state();ordinal=info[4]
  assert info[3]==0
  phase_data.append(dict(phase=index-1,kind=kind,block=block,case=case['id'],mode=mode,measured=measured,monitor_hz=hz,requested_seconds=duration,start_ns=info[0],end_ns=info[1],requests=info[2],ordinal_end=info[4],host_before=host_before,host_after=host_after))
 for rec,(raw,pk,info) in zip(phase_data,buffers):
  prefix='condition' if not rec['measured'] else 'phase_'+str(rec['phase']);filename=prefix+'.requests.csv.gz'
  dump_requests(out/filename,raw[:info[2]],rec['mode'],rec['phase']);rec['raw_file']=filename;append(out/'phases.jsonl',rec)
 qualify({'LIB':js},d,out,'ALL','AFTER')
 for j in js:j.close()
 d.close();e.close();write(out/'complete.json',dict(status='PASS',kind=kind,block=block,monitor_hz=hz,case=case['id'],order=order,conditioning_s=cond,phase_s=seconds))
 print(kind,block,hz,[(x['mode'],x['requests']) for x in phase_data],flush=True)
if __name__=='__main__':run(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3]),int(sys.argv[4]))
