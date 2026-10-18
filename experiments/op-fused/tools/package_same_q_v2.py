"""Content-addressed source snapshots keep the audit package small."""
import datetime,hashlib,json,pathlib,shutil,subprocess,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
RUN=pathlib.Path((ROOT/'implementation_same_q_v2/CURRENT_RUN.txt').read_text().strip())
NAME='OP_FUSED_T10_SAME_Q_AND_BACKBONE_COMPLETE_20261016'
RESTORE='''from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
for row in json.loads((root/'SOURCE_BLOB_MAP.json').read_text()):
    data=(root/'source_blobs'/row['sha256']).read_bytes()
    assert hashlib.sha256(data).hexdigest()==row['sha256']
    p=root/row['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
run=root/'op-fused'/json.loads((root/'PACKAGE_INFO.json').read_text())['run_relative']
(root/'op-fused/implementation_same_q_v2/CURRENT_RUN.txt').write_text(str(run)+'\\n')
print('Source snapshots restored. CPU analysis: python3 op-fused/tools/analyze_same_q_v2.py')
'''
def main():
    entries={};mapping=[];blobs={}
    def add(path,name):
        data=path.read_bytes();entries[name]=data
    # Small human-facing run tree, including supplied review and fixed protocol.
    for p in RUN.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and 'package' not in p.parts:
            add(p,'op-fused/'+str(p.relative_to(ROOT)))
    for directory in ['tools','src','preregistration','config','protocol']:
        for p in (ROOT/directory).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':add(p,'op-fused/'+str(p.relative_to(ROOT)))
    add(ROOT/'registry/runs.jsonl','op-fused/registry/runs.jsonl')
    add(ROOT/'vendor/cutlass/LICENSE.txt','op-fused/vendor/cutlass/LICENSE.txt')
    records=[json.loads(s) for s in (ROOT/'registry/runs.jsonl').read_text().splitlines()]
    for record in records[92:]:
        folder=ROOT/record['path']
        for p in folder.rglob('*'):
            if not p.is_file():continue
            relative=str(p.relative_to(ROOT))
            if '/frozen/op-fused/vendor/' in relative:continue
            if '/frozen/op-fused/' in relative and p.name!='FROZEN_SOURCE_MANIFEST.json':
                data=p.read_bytes();digest=hashlib.sha256(data).hexdigest();blobs[digest]=data
                mapping.append(dict(path='op-fused/'+relative,sha256=digest,bytes=len(data)))
            else:add(p,'op-fused/'+relative)
    for p in ROOT.glob('build/same_q*/*'):
        if p.is_file() and p.suffix!='.so':add(p,'op-fused/'+str(p.relative_to(ROOT)))
    # CPU source reconstruction is explicit; full CUTLASS is an existing pinned dependency.
    entries['RESTORE_SOURCES.py']=RESTORE.encode()
    entries['SOURCE_BLOB_MAP.json']=(json.dumps(mapping,indent=2)+'\n').encode()
    for digest,data in blobs.items():entries['source_blobs/'+digest]=data
    info=dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),run_relative=str(RUN.relative_to(ROOT)),
      raw_runs=len(records)-92,source_blobs=len(blobs),snapshot_files=len(mapping),
      tensor_payloads_included=False,vendor_checkout_included=False,installed_toolchain_included=False,
      scope='All new raw summaries/logs and source snapshots; historical 92-record ledger prefix, not all old raw run data')
    entries['PACKAGE_INFO.json']=(json.dumps(info,indent=2)+'\n').encode()
    entries['START_HERE.txt']=('先读 op-fused/'+str(RUN.relative_to(ROOT))+'/reports/T10_SAME_Q_AND_BACKBONE_REPORT.md\n'
      '以及 MENTOR_UPDATE.md 与 ALL_CASE_RESULTS.md。\n'
      '这是同 q 与主体复核的新结果，旧结果不覆盖。\n'
      'CPU 复算：解包后 python3 RESTORE_SOURCES.py，再 python3 op-fused/tools/analyze_same_q_v2.py（需要 NumPy）。\n'
      '不可变源快照去重放在 source_blobs/，恢复脚本不联网、不运行 GPU。\n'
      'CUDA/GPU 重跑需本机已有 CUTLASS pin、nvcc/torch/driver；本包不带完整 vendor/模型/tensor。\n'
      '旧性能 ZIP 继续作为独立历史附件；这里保留完整旧账本前缀及新原始数据。\n').encode()
    manifest=[dict(path=n,sha256=hashlib.sha256(d).hexdigest(),bytes=len(d)) for n,d in sorted(entries.items())]
    entries['FILE_MANIFEST.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    target=ROOT/'exports'/(NAME+'.zip');target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(entries.items()):z.writestr(NAME+'/'+name,data)
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for entry in manifest:
            data=z.read(NAME+'/'+entry['path']);assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
    receipt=dict(path=str(target),bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
      entries=len(entries),crc_and_manifest='PASS',**info)
    target.with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    destination=pathlib.Path('/home/ubuntu/下载')/target.name;shutil.copyfile(target,destination)
    shutil.copyfile(target.with_suffix('.receipt.json'),destination.with_suffix('.receipt.json'))
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
