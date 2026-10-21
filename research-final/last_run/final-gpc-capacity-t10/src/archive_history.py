"""Read-only historical catalog assembly; copying reports is not numerical verification."""
from common import *
import shutil,re,csv,collections
ARCHIVE=REPO/'T10_RESEARCH_FINAL';PUB=REPO.parent/'EXP_NUMA_SM';catalog=read(PUB/'docs/CAMPAIGNS.json')
for ordinal,root,title,report,result,boundary in [
 ('26','gpc-contention-gqa-t10','GPC竞争、地址相关性与GQA共置','reports/T10_GPC_CONTENTION_GQA_REPORT.md','热读分散有局部优势；完整GQA效应小；10/46静态共置不能越过强简单基线。','同卡动态100W；局部SM数及工作集不同，不能推广物理NUMA。'),
 ('27','quota-tail-closure-t10','资源份额与尾部释放收束','reports/T10_QUOTA_TAIL_CLOSURE_REPORT.md','LONG释放/固定耗时−24.972%；冻结JOINT/最强原生+0.633%，97.5%区间跨零；PACK/NEUTRAL−1.601%。','PACK对强串行区间跨零；确认后不重新选择；RAGGED冻结为串行alias。')]:
 rr=Path((REPO/root/'CURRENT_RUN.txt').read_text().strip());rr=rr if rr.is_absolute() else REPO/root/'runs'/rr
 rp=rr/report
 if not rp.exists():
  candidates=list((rr/'reports').glob('*.md'));rp=next(p for p in candidates if 'REPORT' in p.name)
 catalog.append(dict(id=ordinal,date='10-19',title=title,report=str(rp.relative_to(REPO)),archive=root,result=result,boundary=boundary))
entries=[];claims=[];artifacts=[];key_paths=set()
for e in catalog:
 p=REPO/e['report'];text=p.read_text();lines=text.splitlines();rel=Path(e['report']);srcroot=(p.parent.parent if p.parent.name=='reports' else p.parent)
 if e['id'] in ['01','02']:srcroot=REPO
 if e['id'] in ['26','27']:srcroot=REPO/e['archive']
 # Stable original directory + observed run id/report identity, never use display ordinal as key.
 runs=sorted(set(re.findall(r'(?:frozen_rule_)?20\d{6}T\d{6}Z',text)))
 cur=srcroot/'CURRENT_RUN.txt'
 if cur.exists():runs=sorted(set(runs+[Path(cur.read_text().strip()).name]))
 run_id=runs if runs else ['REPORT_SCOPE_NO_SINGLE_RUN_ID']
 stable=str(srcroot.relative_to(REPO))+'::'+('|'.join(run_id))+'::'+p.name
 uid='stage-'+hashlib.sha256(stable.encode()).hexdigest()[:20]
 dst=ARCHIVE/'sources'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst);key_paths.add(p)
 raw_candidates=[srcroot/'runs',srcroot/'raw',srcroot/'derived',srcroot/'freeze']
 existing=[str(a) for a in raw_candidates if a.exists()]
 hashes={}
 for base in [srcroot/'src',srcroot/'build']:
  if base.exists():
   for f in base.iterdir():
    if f.is_file() and f.suffix in ['.cu','.cuh','.cpp','.c','.so','.py']:
     hashes[str(f.relative_to(REPO))]=sha(f);key_paths.add(f)
 freezes=[]
 fdir=srcroot/'freeze'
 if fdir.exists():
  for f in fdir.glob('*.json'):
   key_paths.add(f);freezes.append(str(f.relative_to(REPO)))
 metric_lines=[dict(line=i+1,text=s) for i,s in enumerate(lines) if any(v in s for v in ['100×','100 ×','T_candidate','时间比','百分比','output-ready','bootstrap'])][:10]
 real='真实3DGS场景与图CSR算子；单机T10' if e['id'] in ['01','02'] else '按原报告区分合成输入、LLM尺寸算子、算子链；非完整模型tokens/s'
 entry=dict(stage_uid=uid,display_ordinal=e['id'],date_display='2026-'+e['date'],timezone='Asia/Shanghai; original run IDs UTC',run_id=run_id,original_stage_root=str(srcroot),purpose_hypothesis=e['title'],execution_status='ARCHIVED_REPORT_AVAILABLE',hardware_driver_state={'hardware':'one Tesla T10, 56 SM','driver':'580.178.04 per original reports','operating_state':'see exact report; early stages may mix125/100W; later100W was cap, not locked clock'},workload_reality=real,implementation_entry={'source_directory':str(srcroot/'src'),'report':e['report']},math_body_launcher_hash=hashes,baselines='See original report exact named implementations; no cross-stage baseline equivalence implied',metric_definition=metric_lines,raw_paths=existing,recomputable_scope='Original raw paths retained locally; this catalog pass reads reports and hashes key code, does not revalidate numbers or tensors',verification_level='REPORT_ONLY',conclusion=e['result'],counterevidence=e['boundary'],unfinished_items=e['boundary'],next_stage_use=catalog[int(e['id'])]['title'] if int(e['id'])<len(catalog) else 'Final fixed-state/GPC capacity attempt',source_report={'local_path':str(p),'archive_path':str(dst.relative_to(ARCHIVE)),'sha256':sha(p)},frozen_metadata=freezes)
 entries.append(entry)
 # Exact paragraphs, not synthetic pooling of report, audit and notes.
 paragraphs=[];begin=None;buf=[]
 for i,line in enumerate(lines+['']):
  if line.strip() and not line.startswith('#') and not line.startswith('|') and not line.startswith('!['):
   if begin is None:begin=i+1
   buf.append(line)
  elif buf:
   s=' '.join(buf)
   if len(s)>=45:paragraphs.append((begin,i,s))
   begin=None;buf=[]
 chosen=[x for x in paragraphs if any(k in x[2] for k in ['结论','收益','没有','未','确认','减少','结果','状态'])][:3]
 for j,(lo,hi,s) in enumerate(chosen):claims.append(dict(claim_id=uid+'-report-'+str(j+1),statement=s,status='限制',scope=e['title'],stage_uid=uid,source_file=str(dst.relative_to(ARCHIVE)),source_lines=[lo,hi],raw_run=run_id,metric_definition=metric_lines,comparison='Exact source paragraph; no reinterpreted common denominator',absolute_values=None,uncertainty='As reported in exact source paragraph; not independently re-estimated by catalog assembly',counterevidence=e['boundary'],not_implied=['independent replication by another report','physical NUMA or floorsweep causation','cross-device or full-model deployment gain'],verification_level='REPORT_ONLY'))
 # One current checksum per essential source; large raw not rehashed wholesale.
for p in sorted(key_paths):
 dst=ARCHIVE/'sources'/p.relative_to(REPO);included=dst.exists()
 artifacts.append(dict(local_path=str(p),relative_to_original_root=str(p.relative_to(REPO)),sha256=sha(p),bytes=p.stat().st_size,included_in_review=included,archive_path=str(dst.relative_to(ARCHIVE)) if included else None,verification='HASHED_NOW_NOT_NUMERICALLY_VERIFIED'))
for p in sorted((PUB/'archive/manifests').glob('*.jsonl')):
 dst=ARCHIVE/'index/inherited_manifests'/p.name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
 artifacts.append(dict(local_path=str(p),sha256=sha(p),bytes=p.stat().st_size,included_in_review=True,archive_path=str(dst.relative_to(ARCHIVE)),verification='INHERITED_FILE_DIGESTS_INSIDE_MANIFEST_NOT_REHASHED',note='Manifest itself hashed now; listed historical payload may be local or missing, not included by a path reference'))
for name,rows in [('stage_catalog',entries),('claims_and_evidence',claims),('artifact_manifest',artifacts)]:
 with (ARCHIVE/'index'/(name+'.jsonl')).open('w') as f:
  for row in rows:f.write(json.dumps(row,ensure_ascii=False)+'\n')
write(RUN/'derived/HISTORY_CATALOG_BUILD.json',dict(stages=len(entries),claims=len(claims),key_artifacts=len(artifacts),verification='REPORT_ONLY until explicit CPU verification addendum',source_catalog=str(PUB/'docs/CAMPAIGNS.json')))
print('HISTORY_CATALOG',len(entries),len(claims),len(artifacts))
