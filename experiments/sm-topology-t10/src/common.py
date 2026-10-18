from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parent
RUN=Path((ROOT/'CURRENT_RUN.txt').read_text().strip())
UUID=json.loads((ROOT/'BEGIN_EXECUTION.json').read_text())['uuid']
PYTHON='/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3'
def utc():return datetime.now(timezone.utc).isoformat()
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
