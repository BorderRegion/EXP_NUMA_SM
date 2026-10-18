from pathlib import Path
import datetime,hashlib,json,os
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent;PYTHON='/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3';UUID='GPU-8cfbc08d-0090-bc29-db9a-b2a2f7261ca5'
INPUT=ROOT/'input/T10_PC_HANDOFF_LLM_20261016'
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def runroot():return Path((ROOT/'CURRENT_RUN.txt').read_text().strip())
def append(p,x):
 with Path(p).open('a') as f:f.write(json.dumps(x,ensure_ascii=False,allow_nan=False)+'\n');f.flush()
