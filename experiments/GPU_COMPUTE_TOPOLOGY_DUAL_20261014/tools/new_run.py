"""Minimal offline write-once run directory. Does NOT execute user commands/GPU."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,uuid,hashlib
R=Path(__file__).resolve().parents[1]
def create(root:Path,platform:str,stage:str,config:dict)->Path:
 if platform not in ('t10','rtx5070ti'):raise ValueError('Unknown platform')
 if stage not in ('E0','E1','E2','E3','E4','E5','E6'):raise ValueError('Unknown stage')
 now=datetime.now(timezone.utc);rid=f"{platform}-{stage}-{now.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid.uuid4().hex[:8]}"
 path=root/platform/rid;path.mkdir(parents=True,exist_ok=False)
 meta={'schema_version':'1.0','run_id':rid,'platform':platform,'stage':stage,'status':'PLANNED',
       'start_utc':None,'end_utc':None,'created_utc':now.isoformat(),
       'protocol_sha256':hashlib.sha256((R/'campaign.json').read_bytes()).hexdigest(),
       'gpu_executed':False,'worker_seconds':None,'actual_cost':None}
 for name,data in [('manifest.json',meta),('config.resolved.json',config)]:
  with (path/name).open('x',encoding='utf8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
 return path
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--platform',required=True);p.add_argument('--stage',required=True);p.add_argument('--config',required=True);a=p.parse_args()
 print(create(Path(a.root),a.platform,a.stage,json.loads(Path(a.config).read_text(encoding='utf8'))))
