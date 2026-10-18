"""Package immutable research evidence and verify a fresh CPU-only extraction."""
from common import *
import zipfile, tempfile, subprocess, time, os

def make_zip(name, selected):
    path=Path('/home/ubuntu/下载')/(name+'.zip')
    manifest={str(p.relative_to(ROOT)):sha(p) for p in selected}
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in selected:z.write(p,name+'/'+str(p.relative_to(ROOT)))
        z.writestr(name+'/MANIFEST_SHA256.json',json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for rel,dig in manifest.items():assert hashlib.sha256(z.read(name+'/'+rel)).hexdigest()==dig
    return dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path),manifest_entries=len(manifest),crc='PASS',hashes='PASS')

def main():
    excluded={'MANIFEST_SHA256.json','PACKAGE_QA.json','PACKAGE_QA.log','DELIVERY_INDEX.md','PACKAGING.log'}
    files=sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in excluded)
    name='T10_LLM_DECODE_KERNEL_OPT_20261017'
    full=make_zip(name,files)
    smallfiles=[p for p in files if p.relative_to(ROOT).parts[0] in ['src','reports','derived','freeze','support'] or p.name in ['README.md','STATUS.md','CURRENT_RUN.txt']]
    small=make_zip(name+'_SMALL',smallfiles)
    parent=Path(tempfile.mkdtemp(prefix='t10-llm-decode-qa-'))
    with zipfile.ZipFile(full['path']) as z:z.extractall(parent)
    extracted=parent/name;t=time.monotonic()
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    p=subprocess.run([PYTHON,str(extracted/'src/recompute.py')],capture_output=True,text=True,env=env)
    (ROOT/'reports/PACKAGE_QA.log').write_text(p.stdout+p.stderr)
    assert p.returncode==0,p.stderr
    assert p.stdout.splitlines()[-1]=='ALL_FROZEN_SOURCES_RAW_RESULTS_AND_CORRECTNESS_RECOMPUTED_PASS'
    for rel,dig in read(extracted/'MANIFEST_SHA256.json').items():assert sha(extracted/rel)==dig,rel
    qa=dict(status='PASS',full=full,small=small,extracted_directory=str(extracted),CPU_only_returncode=p.returncode,
        CPU_only_seconds=time.monotonic()-t,CPU_only_stdout_last=p.stdout.splitlines()[-1],post_recompute_all_hashes='PASS')
    write(ROOT/'reports/PACKAGE_QA.json',qa)
    (ROOT/'reports/DELIVERY_INDEX.md').write_text(f'''# 2026-10-17 交付索引

报告：`REPORT.md`。六组 GQA 解码 Attention 核心完整 GPU 用时减少 33.554%～55.323%，相对本机预选库基线；不是整模型或 SOTA 声明。地址偏好仍无净收益。KV 写入融合另以原核强控制验证，五组减少约 0.8%～5.6%，GQA8_LONG 默认保留独立写入。

- 完整包：`{full['path']}`，{full['bytes']:,} 字节，{full['manifest_entries']} 项哈希。
- 网页版 GPT 小包：`{small['path']}`，{small['bytes']:,} 字节；没有原始请求、遥测和 GPU 二进制，不能独立复算。
- 完整包 SHA256：`{full['sha256']}`
- 小包 SHA256：`{small['sha256']}`
- 两包 ZIP CRC 与所有文件哈希通过；完整包独立解压后的 CPU 复算通过，复算后全部交付文件哈希仍一致。
- QA：`PACKAGE_QA.json`、`PACKAGE_QA.log`；QA 与本索引在打包后生成，保存在工作目录，避免自引用。
''')
    print(json.dumps(qa,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
