"""Package the CPU/resource continuation; preserve the previous raw-data archive."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent.parent
DEST=Path('/home/ubuntu/桌面/GPU双卡拓扑实验_交付_20261014')
NAME='OP_FUSED_T10_RECOVERY_HANDOFF_20261015'
EXCLUDE={'__pycache__','build','.pytest_cache'}

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--name',default=NAME)
 args=parser.parse_args()
 if not args.name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in args.name):
  parser.error('Package name must be an ASCII filename stem')
 name=args.name
 state=json.loads((ROOT/'STATUS.json').read_text())
 state.setdefault('cpu_preparation_completed_at',state.get('packaged_at',state['updated_at']))
 state['packaged_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 (ROOT/'STATUS.json').write_text(json.dumps(state,indent=2)+'\n')
 (ROOT.parent/'CONTINUATION_STATUS.json').write_text(json.dumps(state,indent=2)+'\n')
 assert hashlib.sha256((ROOT.parent/'registry/runs.jsonl').read_bytes()).hexdigest()==state['old_registry_sha256']
 files=[]
 for path in ROOT.rglob('*'):
  if path.is_file() and not EXCLUDE.intersection(path.relative_to(ROOT).parts) and path.name!='package_validation.json':files.append(path)
 for relative in ['tools/worker.py','tools/frozen_source.py','preregistration/plan.jsonl',
                  'protocol/tools/reference.py','protocol/docs/02_OPERATOR_METHOD.md',
                  'protocol/docs/04_BASELINES_AND_ATTRIBUTION.md','protocol/configs/campaign.json',
                  'CONTINUATION_STATUS.json']:
  files.append(ROOT.parent/relative)
 payload={str(p.relative_to(PROJECT)):p.read_bytes() for p in sorted(set(files))}
 readfirst='\n\n'.join((ROOT/'reports'/n).read_text() for n in [
     'OPERATOR_FUSED_IMPLEMENTATION_REPORT_t10.md','MUTABLE_CORE_RESOURCE_REQUEST.md',
     'PACKET_APPLICABILITY.md','POWER_POLICY_DECISION.md'])
 payload['GPT_READ_FIRST.txt']=readfirst.encode()
 payload['PACKAGE_SCOPE.txt']=(
   'CPU/resource continuation only. No new GPU measurements. Full previous raw data stays in '
   'OP_FUSED_T10_REVIEW_AND_BASELINES_20261015.zip (SHA256 '
   '426187dda9b6ca95098029151f9aae422e20d01baecbd7de0f6e8a33a81c6450). '
   'This package contains the new uploaded review, new source/interfaces/reports, modified future '
   'worker and the original CPU reference/plan needed by tests. No weights, GPU binaries or complete '
   'previous raw campaign. A missing mutable Tensor Core body remains a real blocker.').encode()
 manifest=[dict(path=n,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()) for n,data in sorted(payload.items())]
 payload['FILE_MANIFEST.json']=json.dumps(manifest,indent=2).encode()
 DEST.mkdir(exist_ok=True)
 archive=DEST/(name+'.zip')
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for entry_name,data in sorted(payload.items()):z.writestr(name+'/'+entry_name,data)
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  for entry in manifest:
   data=z.read(name+'/'+entry['path'])
   assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
 digest=hashlib.sha256(archive.read_bytes()).hexdigest()
 archive.with_suffix('.zip.sha256').write_text(digest+'  '+archive.name+'\n')
 (DEST/(name+'_GPT_READ_FIRST.txt')).write_text(readfirst)
 result=dict(path=str(archive),bytes=archive.stat().st_size,sha256=digest,files=len(payload),
             zip_crc_pass=True,manifest_hashes_pass=True,includes_full_previous_raw=False)
 (ROOT/'reports/package_validation.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))

if __name__=='__main__':main()
