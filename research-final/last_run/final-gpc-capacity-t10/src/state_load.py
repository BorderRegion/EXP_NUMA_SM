from gqa_runtime import *
from gemm_runtime import *
from micro_runtime import Micro
import os,subprocess,gzip,sys
folder=Path(os.environ['T10_WORKER_DIR']);state=sys.argv[1];c=Control();c.current(0)
def snapshot(name):
 p=subprocess.run(['nvidia-smi','-q','-x'],capture_output=True,text=True,check=True);(folder/(name+'.xml')).write_text(p.stdout)
for name in ['GQA_LONG','GEMM','STREAM128']:
 if name=='GQA_LONG':
  d=GQAData(dict(id='GQA4_LONG',B=1,H=32,HK=8,D=128,L=8192,lengths=[8192]),211000,0);j=GQAJob(d,False,'N19');check=lambda slot:d.check_mode(False,slot)
 elif name=='GEMM':
  d=GemmData(211001);j=GemmJob(d,0);check=d.check
 else:d=Micro('STREAM128_CG',240,211002);j=d;check=d.check
 gs=[c.capture(0,[j.op(s)]) for s in range(4)]
 c.run(gs,32);check(3);snapshot(name+'_before');t=time.monotonic();start=utc();chunks=[]
 while time.monotonic()-t<60:chunks.append(c.run(gs,128))
 end=utc();seconds=time.monotonic()-t;snapshot(name+'_after');check(3)
 with gzip.open(folder/(name+'_requests.json.gz'),'wt') as f:json.dump(np.concatenate(chunks).tolist(),f)
 write(folder/(name+'_interval.json'),dict(state=state,workload=name,start_utc=start,end_utc=end,elapsed_seconds=seconds,requests=sum(len(a) for a in chunks),columns=['gpu_us','ready_us'],ring=4,qualification='PASS'))
 print(name,seconds,flush=True);c.graph_drop(gs)
 if name=='GEMM':j.close()
 if hasattr(d,'close'):d.close()
 del d,j;gc.collect();torch.cuda.empty_cache()
