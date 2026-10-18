import hashlib,json,pathlib,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
DEST=pathlib.Path('/home/ubuntu/桌面/GPU双卡拓扑实验_交付_20261014')
def main():
 title='OP_FUSED_T10_REVIEW_AND_BASELINES_20261015'
 files=[]
 for dirname in ['config','contracts','preregistration','protocol','reports','src','tools','registry','runs','derived']:
  for p in (ROOT/dirname).rglob('*'):
   if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.cubin','.so') and p.name not in ('package_validation.json','execution_handoff.json'):files.append(p)
 files += [ROOT/n for n in ['STATUS.md','WORKLOG.md','DECISIONS.md']]
 combined='\n\n'.join('FILE: '+p.name+'\n'+p.read_text() for p in [ROOT/'reports/OPERATOR_FUSED_SCHEDULING_REPORT_t10.md',ROOT/'reports/QUESTIONS_FOR_PAPER_REVIEW.md',ROOT/'reports/PLAN_REVIEW_t10.md',ROOT/'reports/LOCAL_RESOURCE_GAPS.md',ROOT/'reports/CONTRIBUTION_CARD.md'])
 manifest=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(set(files))]
 target=DEST/(title+'.zip')
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in sorted(set(files)):z.write(p,title+'/'+str(p.relative_to(ROOT)))
  z.writestr(title+'/FILES_SHA256.json',json.dumps(manifest,ensure_ascii=False,indent=2))
  z.writestr(title+'/GPT_READ_FIRST.txt',combined)
  z.writestr(title+'/PACKAGE_SCOPE.txt','This package includes recorded scalar measurements, source snapshots, protocol, generated reports, and limited profiler traces. It excludes local model weights, installed libraries/toolchain, JIT cache, and GPU binaries. Synthetic input tensors are recreated from saved seeds and source; they were not serialized. No candidate scheduler was implemented. All FULL comparisons are NA.\n')
 with zipfile.ZipFile(target) as z:
  assert z.testzip() is None
  for x in manifest:assert hashlib.sha256(z.read(title+'/'+x['path'])).hexdigest()==x['sha256']
 h=hashlib.sha256(target.read_bytes()).hexdigest();target.with_suffix('.zip.sha256').write_text(h+'  '+target.name+'\n')
 (DEST/(title+'_GPT_READ_FIRST.txt')).write_text(combined)
 result=dict(path=str(target),bytes=target.stat().st_size,sha256=h,files=len(manifest),crc='PASS',all_hashes='PASS')
 (ROOT/'reports/package_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
