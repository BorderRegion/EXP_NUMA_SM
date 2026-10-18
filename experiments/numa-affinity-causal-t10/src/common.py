from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent
RUN=ROOT/'runs'/Path((ROOT/'CURRENT_RUN.txt').read_text().strip()).name
UUID='GPU-8cfbc08d-0090-bc29-db9a-b2a2f7261ca5'
PYTHON='/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3'
def utc():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def read(p):return json.loads(Path(p).read_text())
