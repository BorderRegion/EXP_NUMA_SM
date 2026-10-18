"""Resume requests terminated before lock acquisition; no successful work rerun."""
import argparse,json,shutil
from common import *
from worker import run
p=argparse.ArgumentParser();p.add_argument('mode',choices=['fine','microqual']);a=p.parse_args();r=runroot()
keys=['fine_shift_1'] if a.mode=='fine' else ['micro_qualification']
for key in keys:
 path=r/'raw'/key
 if path.exists():
  old=json.loads((path/'manifest.json').read_text());assert old['status']=='REQUESTED' and not old.get('pid') and list(path.iterdir())==[path/'manifest.json']
  dest=r/'raw/abandoned_requests'/key;dest.parent.mkdir(exist_ok=True);shutil.move(path,dest)
  write(dest/'interruption.json',dict(observed_at=utc(),tool_process_exitcode=143,GPU_worker_never_started=True,charged_worker_seconds=0,reason='Invoking shell process received SIGTERM while waiting for GPU lock; exact source unverified. No GPU child for this request. Original manifest retained.',recovery='same unexecuted key requeued from detached finite coordinator'))
if a.mode=='microqual':
 run('P3','micro_qualification',[r/'compiled/micro/micro_campaign','--allocation','90','--out','{OUT}','--qualification','1','--probe-cubin',r/'compiled/fine_shift/probe_shift.cubin','--micro-cubin',r/'compiled/micro/micro.cubin'])
else:
 for i in range(1,4):run('P3',f'fine_shift_{i}',[PYTHON,ROOT/'src/fine_job.py','--allocation',i,'--out','{OUT}','--shift'])
