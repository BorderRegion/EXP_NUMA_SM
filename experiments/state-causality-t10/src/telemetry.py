from nvml_state import *
from common import *
import sys,signal,threading,os
out=Path(sys.argv[1]);modefile=out/'telemetry_hz.txt';nv=NVML();stop=False;wake=threading.Event()
(out/'telemetry.pid').write_text(str(os.getpid()))
signal.signal(signal.SIGUSR1,lambda *_:wake.set())
signal.signal(signal.SIGTERM,lambda *_:globals().__setitem__('stop',True))
next_full=0
with (out/'telemetry.jsonl').open('w') as f:
 while not stop:
  start=time.monotonic();hz=float(modefile.read_text()) if modefile.exists() else 20
  full=start>=next_full;row=nv.snapshot() if full else nv.fast();row['full_snapshot']=full
  if full:next_full=start+1
  row['requested_hz']=hz;f.write(json.dumps(row)+'\n');f.flush()
  wake.wait(max(0,1/hz-(time.monotonic()-start)));wake.clear()
nv.close()
