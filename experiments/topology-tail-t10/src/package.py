from common import *
import zipfile,os,subprocess,tempfile,shutil

def files():
    return sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'
        and p.name not in ['FILE_MANIFEST.json','FILE_TIMES.json','DELIVERY.json','ARCHIVE_QA.json','ARCHIVE_RECOMPUTE.log'])

def run():
    dest=Path('/home/ubuntu/下载');stem='T10_TOPOLOGY_TAIL_PLACEMENT_20261018'
    selected=files()
    write(ROOT/'FILE_TIMES.json',{str(p.relative_to(ROOT)):p.stat().st_mtime_ns for p in selected})
    selected.append(ROOT/'FILE_TIMES.json')
    write(ROOT/'FILE_MANIFEST.json',{str(p.relative_to(ROOT)):sha(p) for p in selected})
    selected.append(ROOT/'FILE_MANIFEST.json')
    package=dest/(stem+'.zip')
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in selected:z.write(p,ROOT.name+'/'+str(p.relative_to(ROOT)))
    with zipfile.ZipFile(package) as z:
        assert z.testzip() is None
        for p in selected:assert hashlib.sha256(z.read(ROOT.name+'/'+str(p.relative_to(ROOT)))).hexdigest()==sha(p)
    print('FULL ZIP CRC/HASH PASS',len(selected),package.stat().st_size,flush=True)
    check=Path(tempfile.mkdtemp(prefix='t10-tail-placement-archive-'))
    try:
        with zipfile.ZipFile(package) as z:z.extractall(check)
        extracted=check/ROOT.name
        env=os.environ.copy();env['OPENBLAS_NUM_THREADS']='2';env['PYTHONDONTWRITEBYTECODE']='1'
        with (ROOT/'reports/ARCHIVE_RECOMPUTE.log').open('w') as log:
            p=subprocess.run([PYTHON,str(extracted/'src/recompute.py')],cwd=extracted,stdout=log,stderr=subprocess.STDOUT,env=env)
        assert p.returncode==0,'independent archive CPU recompute failed; see ARCHIVE_RECOMPUTE.log'
        for name,h in read(extracted/'FILE_MANIFEST.json').items():assert sha(extracted/name)==h,name
        write(ROOT/'reports/ARCHIVE_QA.json',dict(status='PASS',full_files=len(selected),full_sha256=sha(package),crc=True,per_file_hash=True,independent_cpu_recompute=True,post_recompute_hash=True))
        print('INDEPENDENT EXTRACTED CPU RECOMPUTATION PASS',flush=True)
    finally:shutil.rmtree(check)
    small=[]
    for p in selected:
        rel=p.relative_to(ROOT);top=rel.parts[0]
        if top in ['src','freeze'] or p.name in ['CURRENT_RUN.txt','README_REPRODUCE.md']:small.append(p)
        elif top=='reports' and p.suffix in ['.md','.json','.png']:small.append(p)
        elif top=='derived' and p.suffix in ['.json','.csv']:small.append(p)
        elif top=='support' and p.suffix in ['.c','.cu','.csv','.json']:small.append(p)
    review=dest/(stem+'_SMALL.zip')
    note='阅读评审包：包含报告、质疑、全部条件汇总、协议、实现和图；不含逐次原始记录与二进制，不能独立重算。完整包文件名：'+package.name+'\n'
    with zipfile.ZipFile(review,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr(ROOT.name+'/SMALL_PACKAGE_NOTE.txt',note)
        for p in small:z.write(p,ROOT.name+'/'+str(p.relative_to(ROOT)))
        z.write(ROOT/'reports/ARCHIVE_QA.json',ROOT.name+'/reports/ARCHIVE_QA.json')
    with zipfile.ZipFile(review) as z:
        assert z.testzip() is None
        for p in small:assert hashlib.sha256(z.read(ROOT.name+'/'+str(p.relative_to(ROOT)))).hexdigest()==sha(p)
    write(ROOT/'reports/DELIVERY.json',dict(status='PASS',full=dict(path=str(package),bytes=package.stat().st_size,sha256=sha(package),files=len(selected)),
        small=dict(path=str(review),bytes=review.stat().st_size,sha256=sha(review),files=len(small)+2),checks='CRC, per-file SHA256, full independent extracted CPU recompute, post-recompute hashes'))
    print(json.dumps(read(ROOT/'reports/DELIVERY.json'),ensure_ascii=False,indent=2))
if __name__=='__main__':run()
