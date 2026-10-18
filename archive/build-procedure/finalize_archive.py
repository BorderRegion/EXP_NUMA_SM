from pathlib import Path
import json,hashlib,shutil,re,subprocess,datetime,os
OUT=Path(__file__).parent;R=OUT.parent/'EXP_NUMA_SM';S=OUT.parent/'numa_gpu';A=OUT/'release-assets'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*2**20),b''):h.update(b)
 return h.hexdigest()
i=json.loads((R/'archive/INDEX.json').read_text())
for item in i['archives']:
 q=json.loads((OUT/'verified-groups'/(item['asset']+'.json')).read_text())
 assert q['members_verified']==item['files'] and q['source_bytes_verified']==item['source_bytes']

# Materialize images linked by original reports in Git without modifying original report text.
extra=[]
for p in list((R/'experiments').rglob('*.md')):
 for target in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',p.read_text(errors='replace')):
  target=target.split(' "')[0].strip('<>')
  if target.startswith(('https:','http:','data:')):continue
  q=(p.parent/target).resolve() if not target.startswith('/') else Path(target)
  if q.is_relative_to(R/'experiments'):src=S/q.relative_to(R/'experiments');dst=q
  elif q.is_relative_to(S):src=q;dst=R/'experiments'/q.relative_to(S)
  else:continue
  if src.is_file() and not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);extra.append(dst.relative_to(R).as_posix())
# Include immutable per-run source snapshots in the archives; browsable copies stay selective.
git_covered=set()
for r in i['archives']:
 print('FINALIZE',r['asset'],flush=True)
 mf=R/r['manifest'];rows=[json.loads(s) for s in mf.read_text().splitlines()]
 for row in rows:
  p=Path(row['path'])
  if p.parts[0]=='numa_gpu' and row['type']=='file':
   g=R/'experiments'/Path(*p.parts[1:])
   if g.is_file():assert sha(g)==row['sha256'];row['git_path']=g.relative_to(R).as_posix();git_covered.add(row['git_path'])
 r['git_files']=sum('git_path' in x for x in rows)
 mf.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in rows))
 # GitHub release asset files are deliberately bounded to 1 GiB.
 p=A/r['asset']
 if r['compressed_bytes']>1024**3:
  limit=1024**3;count=(r['compressed_bytes']+limit-1)//limit
  journal_path=OUT/(r['asset']+'.split-journal.json')
  journal=json.loads(journal_path.read_text()) if journal_path.exists() else {}
  # Split this newly generated archive from its end, freeing copied bytes only
  # after a flushed, independently hashed part exists. Original experiments are untouched.
  for part_index in reversed(range(count)):
   offset=part_index*limit;size=min(limit,r['compressed_bytes']-offset)
   q=p.with_name(p.name+f'.part{part_index+1:03d}');key=str(part_index)
   if key in journal:
    assert q.stat().st_size==size and sha(q)==journal[key]['sha256']
   else:
    assert p.exists() and p.stat().st_size>=offset+size
    with p.open('rb') as f:f.seek(offset);data=f.read(size)
    assert len(data)==size
    with q.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    h=hashlib.sha256(data).hexdigest();assert sha(q)==h
    journal[key]={'asset':q.name,'bytes':size,'sha256':h}
    with journal_path.open('w') as f:json.dump(journal,f,indent=2);f.flush();os.fsync(f.fileno())
   print('PART VERIFIED',q.name,size,flush=True)
   if p.exists() and p.stat().st_size>offset:
    assert p.stat().st_size==offset+size
    with p.open('r+b') as f:f.truncate(offset);f.flush();os.fsync(f.fileno())
  parts=[journal[str(k)] for k in range(count)]
  joined=hashlib.sha256()
  for part in parts:
   with (A/part['asset']).open('rb') as f:
    for data in iter(lambda:f.read(4*2**20),b''):joined.update(data)
  assert joined.hexdigest()==r['sha256'],'Split does not reproduce original archive bytes'
  r['parts']=parts
  if p.exists():assert p.stat().st_size==0;p.unlink()
# The bundle contains original author/history. No original commit is rewritten.
bundle=A/'original-history.bundle'
i['additional_assets']=[{'asset':bundle.name,'bytes':bundle.stat().st_size,'sha256':sha(bundle),'purpose':'Original Git refs/history, unchanged authors'}]
i['git_evidence_files']=len(git_covered)
i['archive_file_limit_bytes']=1024**3
i['archive_verified_at_utc']=None
(R/'archive/INDEX.json').write_text(json.dumps(i,ensure_ascii=False,indent=2)+'\n')
segments=[]
for r in i['archives']:segments+=r.get('parts',[{'asset':r['asset'],'sha256':r['sha256'],'bytes':r['compressed_bytes']}])
segments+=i['additional_assets']
checks=''.join(f"{s['sha256']}  {s['asset']}\n" for s in segments)
(A/'SHA256SUMS').write_text(checks);(R/'archive/SHA256SUMS').write_text(checks)
# Release-ready metadata is separate from scientific, frozen results.
(OUT/'upload_assets.json').write_text(json.dumps(segments,indent=2)+'\n')
text=['# 全部原始记录的归档','',f"保存 **{i['total_entries']:,} 个文件/符号链接条目**，原始常规文件共 **{i['total_source_bytes']:,} 字节**（含历史交付副本）；压缩数据 **{i['total_archive_bytes']:,} 字节**，另保留原始Git历史。浏览用Git证据副本 **{i['git_evidence_files']:,} 文件**。这些是文件数量，不是独立实验样本量。",'', '[完整数据发布页](https://github.com/BorderRegion/EXP_NUMA_SM/releases/tag/records-2026-10-18) · [机器可读清单](INDEX.json) · [SHA256SUMS](SHA256SUMS)','', '发布状态以GitHub release实际存在的资产为准；本地准备不等于已经上传。归档按原目录分组，大于1 GiB的归档被分片，所有分片必须齐全。每个文件的哈希、大小和原路径都在 manifests；原始Git历史在 original-history.bundle。','', '## 下载、验证与恢复','', '```bash','python3 tools/download_archives.py --dest /path/to/release-assets','python3 tools/verify_archive.py --assets /path/to/release-assets','python3 tools/verify_archive.py --assets /path/to/release-assets --extract /path/to/empty-restored','```','', '需要 Python 3 与 `zstd` 命令。恢复只写普通文件，不自动创建可能指向旧主机外部的符号链接；符号链接目标在清单中保留。工具不执行数据包内脚本，不改系统服务。若只需要一轮，可加 `--only topology-real-t10.tar.zst`；依赖/共享输入可能仍需其他包。','', '完整恢复后保留 `numa_gpu/` 原目录布局和 `handoffs/` 原任务/交付文件。无需为了浏览报告下载全部大型模型/输出；但复核完整原始证据时不能拿Git摘要代替缺失包。','', '## 分包目录','', '| 目录归档 | 文件/链接 | 原始 MiB | 压缩 MiB | 完整文件清单 |','|---|---:|---:|---:|---|']
for r in i['archives']:
 links='、'.join(f"[{s['asset']}](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/{s['asset']})" for s in r.get('parts',[{'asset':r['asset']}]))
 text.append(f"| {links} | {r['files']:,} | {r['source_bytes']/2**20:,.2f} | {r['compressed_bytes']/2**20:,.2f} | [JSONL](../{r['manifest']}) |")
text+=['','## 明确的排除项','','只排除Git内部数据库（主项目另有可恢复bundle，第三方源码和版本来源保留）、Python字节码和可再生成的解释器/测试缓存，以及指定实验目录之外的无关个人文件。失败实验、负结果、早期有缺陷的实现、旧报告、未执行说明和重复交付包都保留。恢复的是已有文件，不是操作系统、驱动和Python环境的整机镜像。','']
(R/'archive/README.md').write_text('\n'.join(text))
(R/'archive/PREPARATION.json').write_text(json.dumps({'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'extra_report_images':extra,'git_evidence_files':len(git_covered),'assets_count':len(segments),'source_index_preserved':hashlib.sha256((S/'.git/index').read_bytes()).hexdigest()==json.loads((OUT/'source_git_state_before.json').read_text())['index_sha256'],'gpu_experiments_run':0},ensure_ascii=False,indent=2)+'\n')
print('Finalized',len(segments),'assets',len(git_covered),'Git evidence files',flush=True)
