import hashlib,json,os,shutil
from datetime import datetime,timezone
from pathlib import Path
W=Path('/home/ws/Documents/Codex/2026-10-21/new-chat-2/work/rtx5080')
R=Path('/home/ws/work/exp_numa_sm')
A=W/'assets'
records=json.loads(Path('/home/ws/work/rtx5080_build/authored/RTX5080_INDEX.json').read_text())['archives']
for r in records:
    original=Path('/home/ws/work/rtx5080_build/assets')/r['asset']
    target=A/r['asset']
    if not target.exists():target.symlink_to(original.resolve())
    r['format']='tar.gz' if r['asset'].endswith('.tar.gz') else 'zip'
    r['scope']='original_delivery_package'
supp=A/'RTX5080_LOCAL_SUPPLEMENT_20261021.tar.zst'
limit=1<<30;parts=[];whole=hashlib.sha256()
with supp.open('rb') as src:
    i=1
    while True:
        first=src.read(4<<20)
        if not first:break
        name=supp.name+f'.part{i:03d}';h=hashlib.sha256();n=0
        with (A/name).open('wb') as dst:
            chunk=first
            while chunk:
                dst.write(chunk);h.update(chunk);whole.update(chunk);n+=len(chunk)
                if n==limit:break
                chunk=src.read(min(4<<20,limit-n))
        parts.append({'asset':name,'sha256':h.hexdigest(),'bytes':n});i+=1
rows=[json.loads(l) for l in (R/'archive/manifests/rtx5080-local-supplement.jsonl').read_text().splitlines()]
records.append({'asset':supp.name,'format':'tar.zst','scope':'current_local_files_missing_from_original_packages','manifest':'archive/manifests/rtx5080-local-supplement.jsonl','files':len(rows),'source_bytes':sum(e['bytes'] for e in rows),'compressed_bytes':supp.stat().st_size,'sha256':whole.hexdigest(),'parts':parts,'git_files':sum('git_path' in e for e in rows),'git_bytes':sum(e['bytes'] for e in rows if 'git_path' in e)})
index={'snapshot_utc':datetime.now(timezone.utc).isoformat(),'source_root':'/home/ws/文档/ChatGPT/EXP_NUMA','destination':'https://github.com/BorderRegion/EXP_NUMA_SM','release_tag':'records-2026-10-13','archives':records,'exclusions':['Source .git internal database','Python bytecode and regenerable interpreter/test caches','affinity-render-5080/offline_inbox/: third-party CUDA toolchain, renderer checkout, and Train/Bonsai scene assets (source and version records retained; dependencies must be acquired separately)','affinity-render-5080/.analysis_libs/: external plotting runtime','artifacts/ distribution and extracted duplicate directories: the five original delivery packages are preserved separately; redundant local distribution copies are not re-archived','Symbolic links are not followed or restored; their external targets are not bundled'],'total_entries':sum(r['files'] for r in records),'total_source_bytes':sum(r['source_bytes'] for r in records),'total_archive_bytes':sum(r['compressed_bytes'] for r in records),'git_evidence_files':sum(r['git_files'] for r in records),'git_evidence_bytes':sum(r['git_bytes'] for r in records),'archive_file_limit_bytes':limit,'gpu_experiments_run':0}
D=R/'archive/rtx5080';D.mkdir(exist_ok=True)
(D/'INDEX.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
lines=[]
for r in records:
    for p in r.get('parts',[{'asset':r['asset'],'sha256':r['sha256']} ]):lines.append(p['sha256']+'  '+p['asset']+'\n')
(D/'SHA256SUMS').write_text(''.join(lines));shutil.copy2(D/'SHA256SUMS',A/'SHA256SUMS')
shutil.copy2(W/'supplement_summary.json',D/'LOCAL_INVENTORY.json')
shutil.copy2('/home/ws/work/rtx5080_build/authored/RTX5080_CAMPAIGNS.json',R/'docs/RTX5080_CAMPAIGNS.json')
for src,dest in [('extract.py','extract_original_packages.py'),('supplement.py','supplement.py'),('index.py','index.py')]:shutil.copy2(W/src,D/'build-procedure'/dest)
print(json.dumps({k:v for k,v in index.items() if k.startswith('total_') or k.startswith('git_')},ensure_ascii=False))
print('release_asset_count',len(lines)+1)
