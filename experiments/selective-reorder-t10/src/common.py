from pathlib import Path
import datetime,hashlib,json,os
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent;PYTHON='/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3';UUID='GPU-8cfbc08d-0090-bc29-db9a-b2a2f7261ca5'
INPUT=ROOT/'input/T10_SELECTIVE_REORDER_8H5_20261017'
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def runroot():return Path((ROOT/'CURRENT_RUN.txt').read_text().strip())
def append(p,x):
 with Path(p).open('a') as f:f.write(json.dumps(x,ensure_ascii=False,allow_nan=False)+'\n');f.flush()

def worker_key(key):
 p=ROOT/'freeze/worker_retry_map.json';return json.loads(p.read_text()).get(key,key) if p.exists() else key
def worker_dir(key):return runroot()/'raw'/worker_key(key)

import time
ACTIONS=['LIB','SINGLE','SPLIT','PC0_0','PC0_1','PC1_0','PC1_1','PC2_0','PC2_1']
TILES={0:(32,64),2:(64,128),3:(128,128)}
def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(x) for x in Path(p).read_text().splitlines()] if Path(p).exists() else []
def elapsed():return time.monotonic()-read(ROOT/'BEGIN_EXECUTION.json')['budget_started_monotonic']
def budget_check():
 if elapsed()>535*60:raise RuntimeError('WALL_BUDGET_STOP_BEFORE_NEW_PHASE')
 if 'SR_GPU_DEADLINE' in os.environ and time.monotonic()>float(os.environ['SR_GPU_DEADLINE'])-30:raise RuntimeError('GPU_BUDGET_STOP_BEFORE_NEW_PHASE')
def bin_id(c):return str(0 if c['M']<=8 else 1 if c['M']<=64 else 2)+'_'+str(int(c['N']>4096))
