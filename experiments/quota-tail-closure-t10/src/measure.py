from control import *
import gzip,csv
def capture_ring(control,g,job,batch):
 t=time.perf_counter();graphs=[control.capture(g,[job.op((s+i)%4) for i in range(batch)]) for s in range(4)]
 return graphs,(time.perf_counter()-t)*1000
def warm(control,graphs,batch):
 total=0.0;n=0
 while n<32 or total<50000:
  x=control.run(graphs,4);total+=float(x[:,1].sum());n+=4*batch
 return dict(requests=n,host_us=total)
def measure(control,graphs,batch,requests=64):
 warmup=warm(control,graphs,batch);data=control.run(graphs,requests//batch)
 return data,warmup
def save_csv(path,rows):
 with gzip.open(path,'wt',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
