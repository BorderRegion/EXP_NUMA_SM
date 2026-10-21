from pathlib import Path
from datetime import datetime, timezone
import json, hashlib
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parent
RUN=ROOT/'runs'/Path((ROOT/'CURRENT_RUN.txt').read_text().strip()).name
PYTHON='/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3'
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()
