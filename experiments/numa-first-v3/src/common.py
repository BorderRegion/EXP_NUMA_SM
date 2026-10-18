import datetime, hashlib, json, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parent
PYTHON='/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3'
UUID='GPU-8cfbc08d-0090-bc29-db9a-b2a2f7261ca5'
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def runroot(): return Path(os.environ.get('NUMA_V3_RUN',(ROOT/'CURRENT_RUN.txt').read_text().strip()))
