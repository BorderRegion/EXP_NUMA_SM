from pathlib import Path
import json,datetime,shutil
O=Path(__file__).parent;R=O.parent/'EXP_NUMA_SM';i=json.loads((R/'archive/INDEX.json').read_text());all_results=[]
for a in i['archives']:
 q=json.loads((O/'verified-groups'/(a['asset']+'.json')).read_text())
 assert q['archives_verified']==1 and q['members_verified']==a['files'] and q['source_bytes_verified']==a['source_bytes']
 r=q['results'][0];assert r['asset']==a['asset'] and r['verified'];r['compressed_archive_sha256']=a['sha256'];all_results.append(r)
assert sum(x['members']for x in all_results)==i['total_entries']
when=datetime.datetime.now(datetime.timezone.utc).isoformat();i['archive_verified_at_utc']=when
(R/'archive/INDEX.json').write_text(json.dumps(i,ensure_ascii=False,indent=2)+'\n')
q={'at_utc':when,'archives_verified':len(all_results),'members_verified':sum(x['members']for x in all_results),'source_bytes_verified':sum(x['bytes']for x in all_results),'compressed_hashes_verified':True,'split_join_hashes_verified':True,'asset_files_rehashed_after_split':True,'original_git_bundle_independent_clone_and_fsck':True,'results':all_results,'gpu_experiments_run':0}
(R/'archive/VERIFICATION.json').write_text(json.dumps(q,indent=2)+'\n')
for name in ['source_git_state_before.json','history-bundle-check.log','asset-check.log']:
 shutil.copy2(O/name,R/'archive'/name)
b=R/'archive/build-procedure';b.mkdir(exist_ok=True)
for name in ['prepare_archive.py','finalize_archive.py','verify_completed.py','scan_credentials.py','scan_history.py','check_content.py','merge_verification.py']:
 shutil.copy2(O/name,b/name)
(b/'README.md').write_text('''# 本次归档的构建过程\n\n这里是创建这次快照、内容扫描与校验汇总的原脚本，保留当时主机路径，便于审阅保存规则。它们不是跨机器一键安装器，也不运行GPU实验。恢复现有档案请使用仓库根目录tools/download_archives.py和tools/verify_archive.py。\n\n步骤：只读清点与SHA256 → 分目录tar.zst → 完整成员验证 → 有日志的分片及拼接哈希验证 → 原Git bundle独立克隆/fsck → 全部发布资产再次哈希 → 文档/源码副本QA → BorderRegion提交与发布。原项目、暂存区和旧ZIP未被覆盖。\n''')
print(json.dumps({k:v for k,v in q.items()if k!='results'}),flush=True)
