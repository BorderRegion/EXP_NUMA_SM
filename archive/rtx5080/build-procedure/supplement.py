import hashlib,json,os,re,shutil,stat,subprocess,tarfile
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
W=Path('/home/ws/Documents/Codex/2026-10-21/new-chat-2/work/rtx5080')
R=Path('/home/ws/work/exp_numa_sm')
S=Path('/home/ws/文档/ChatGPT/EXP_NUMA')
assets=W/'assets';assets.mkdir(exist_ok=True)
known={}
rounds={'render-opportunity':'','render-scheduling-v2':'affinity-render-5080/','render-scheduling':'affinity-render-5080/','static-affinity':'static-affinity-5080/','static-affinity-causal':'static-affinity-causal-5080/'}
for key,prefix in rounds.items():
    mf=R/f'archive/manifests/rtx5080-{key}.jsonl'
    for line in mf.read_text().splitlines():
        e=json.loads(line);parts=e['path'].split('/',1)
        known.setdefault(prefix+parts[1],set()).add(e['sha256'])
patterns={
    'github_token':re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})'),
    'openai_key':re.compile(rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}'),
    'aws_access_key':re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'private_key':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
}
exclude_dirs={'.git','__pycache__','.pytest_cache','.analysis_libs','offline_inbox','artifacts'}
entries=[];excluded=Counter();stats=Counter();findings=[];matched=0
for base,dirs,names in os.walk(S,followlinks=False):
    for d in list(dirs):
        if d in exclude_dirs or (Path(base)/d).is_symlink():
            dirs.remove(d);excluded[str((Path(base)/d).relative_to(S))]+=1
    for n in sorted(names):
        p=Path(base)/n;rel=p.relative_to(S).as_posix()
        if p.is_symlink() or not p.is_file() or p.suffix in {'.pyc','.pyo'}:continue
        h=hashlib.sha256();size=0;tail=b''
        with p.open('rb') as f:
            for chunk in iter(lambda:f.read(4<<20),b''):
                h.update(chunk);size+=len(chunk)
                data=tail+chunk
                for kind,pattern in patterns.items():
                    if pattern.search(data):findings.append({'path':rel,'kind':kind})
                tail=data[-256:]
        sha=h.hexdigest()
        if sha in known.get(rel,set()):matched+=1;continue
        arc='EXP_NUMA/'+rel
        e={'path':arc,'source_rel':rel,'bytes':size,'sha256':sha,'type':'file','mode':stat.S_IMODE(p.stat().st_mode),'mtime_ns':p.stat().st_mtime_ns}
        # Browser evidence retains current source and small records; large outputs stay in Release.
        if size<=2<<20 and p.suffix.lower() not in {'.bin','.npz','.so','.a','.o','.zip','.gz','.zst'} and b'\x00' not in p.read_bytes()[:8192]:
            dest=R/'experiments/rtx5080-20261013/local-supplement'/rel
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
            e['git_path']=dest.relative_to(R).as_posix()
        entries.append(e);stats[rel.split('/')[0]]+=size
entries.sort(key=lambda e:e['path'])
summary={'created_utc':datetime.now(timezone.utc).isoformat(),'matched_package_files':matched,'supplement_files':len(entries),'supplement_bytes':sum(e['bytes'] for e in entries),'by_root':dict(stats),'excluded_directories':list(excluded),'high_confidence_secret_findings':findings}
(W/'supplement_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False),flush=True)
if findings:raise SystemExit('Credential pattern found; publication halted before packing')
manifest=R/'archive/manifests/rtx5080-local-supplement.jsonl'
manifest.write_text(''.join(json.dumps(e,ensure_ascii=False,separators=(',',':'))+'\n' for e in entries))
arcpath=assets/'RTX5080_LOCAL_SUPPLEMENT_20261021.tar.zst'
with arcpath.open('wb') as out:
    proc=subprocess.Popen(['zstd','-T4','-3','-q','-c'],stdin=subprocess.PIPE,stdout=out)
    with tarfile.open(mode='w|',fileobj=proc.stdin,format=tarfile.PAX_FORMAT) as tf:
        for e in entries:tf.add(S/e['source_rel'],arcname=e['path'],recursive=False)
    proc.stdin.close()
    if proc.wait()!=0:raise SystemExit('zstd failed')
print('packed',arcpath.name,arcpath.stat().st_size,flush=True)
