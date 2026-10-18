from pathlib import Path
import datetime,hashlib,json,os,time
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent
PYTHON='/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3'
UUID='GPU-8cfbc08d-0090-bc29-db9a-b2a2f7261ca5'
INPUT=ROOT/'input/T10_TRANSIENT_AND_F4_DIAG_20261017'
PRIOR=REPO/'selective-reorder-repair-v2-t10'
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def append(p,x):
 Path(p).parent.mkdir(parents=True,exist_ok=True)
 with Path(p).open('a') as f:f.write(json.dumps(x,ensure_ascii=False,allow_nan=False)+'\n')
def lines(p):return [json.loads(x) for x in Path(p).read_text().splitlines()] if Path(p).exists() else []
def runroot():
 p=Path((ROOT/'CURRENT_RUN.txt').read_text().strip());local=ROOT/'runs'/p.name
 return local if local.exists() else p
def elapsed():return time.monotonic()-read(ROOT/'BEGIN_EXECUTION.json')['budget_started_monotonic']
def budget_check():
 if elapsed()>495*60:raise RuntimeError('RESERVE_FINAL_45_MINUTES')
 if 'SR_GPU_DEADLINE' in os.environ and time.monotonic()>float(os.environ['SR_GPU_DEADLINE'])-5:raise RuntimeError('GPU_BUDGET_STOP')
ACTIONS=['LIB','SINGLE','SPLIT','PC0_0','PC0_1','PC1_0','PC1_1','PC2_0','PC2_1']
POLICIES=['LIB_ALWAYS','BASE','SHAPE','RESOURCE','PERMUTED_RESOURCE']
TILES={0:(32,64),2:(64,128),3:(128,128)}
def bin_id(c):return str(0 if c['M']<=8 else 1 if c['M']<=64 else 2)+'_'+str(int(c['N']>4096))
def note(issue,**extra):append(ROOT/'reports/ENGINEERING_NOTES.jsonl',dict(at=utc(),issue=issue,**extra))
