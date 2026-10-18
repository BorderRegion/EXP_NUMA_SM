"""One finite CPU-only finalization after all planned GPU workers settle."""
import json,shutil,subprocess,time
from common import *
r=runroot();required=['fine_shift_3','p4_native_b7','micro_order_qualification','micro_b7','compiled_lifecycle_b3']
while True:
 by={x['key']:x for x in [json.loads(z) for z in (r/'ledger.jsonl').read_text().splitlines()]}
 for key in required:
  if key in by and by[key]['status']!='COMPLETED':raise RuntimeError('Failed final prerequisite: '+key)
 if all(key in by for key in required):break
 time.sleep(15)
scripts=['analyze_fine.py','fine_coverage_audit.py','analyze_native.py','analyze_micro.py','analyze_lifecycle.py','rule_scope_audit.py','summarize_runtime.py','audit_micro_code.py','phase_order_audit.py','plot_campaign.py','plot_exceptions.py','plot_supplement.py','preview_render_outputs.py','write_bottleneck_cards.py','finalize_control.py']
for script in scripts:
 print('CPU_FINAL',script,utc(),flush=True);subprocess.run([PYTHON,str(ROOT/'src'/script)],check=True)
subprocess.run([PYTHON,str(ROOT/'src/audit_campaign.py'),'--final'],check=True)
initial=r/'INITIAL_RUN_MANIFEST.json'
if not initial.exists():shutil.copy2(r/'manifest.json',initial)
manifest=json.loads((r/'manifest.json').read_text());manifest.update(status='COMPLETED_WITH_EXPLICIT_NA',gpu_workers_finished_at=max(x['released_at'] for x in by.values()),cpu_finalized_at=utc(),completion_audit='derived/COMPLETION_AUDIT.json',restoration='RESTORATION_REPORT.json');write(r/'manifest.json',manifest)
subprocess.run([PYTHON,str(ROOT/'src/write_report.py')],check=True)
write(r/'FINAL_ANALYSIS_SOURCES.json',dict(generated_at=utc(),sources={p.name:sha(p) for p in (ROOT/'src').glob('*') if p.is_file()},scope='Final CPU analysis/reporting source hashes. GPU bodies/host builds are bound by compiled snapshots and perworker manifests; analysis evolved while GPU code remained frozen, apart from documented pre-formal host-order amendment.'))
runtime=json.loads((r/'derived/RUNTIME_SUMMARY.json').read_text());audit=json.loads((r/'derived/COMPLETION_AUDIT.json').read_text())
(ROOT/'STATUS.md').write_text(f'''# NUMA-first V3：GPU 实验已结束\n\n更新：{utc()}。\n\n- 新账本 {runtime['worker_hours']:.3f}/24 GPU-worker 小时；所有计划执行分支完成，条件式 NA 明确列出。\n- P1 6次主分配；P2 3整块；P4 native 8整块（20条件）；细化移位版4分配；编译micro 8正式分配块、576主phase；生命周期4块、36主session。\n- 所有正式数值检查通过；初始renderer资格的CPU回调错误及修复记录保留。\n- 100W配置/保护服务未更改，最终只读恢复核查通过。\n- 报告：NUMA_FIRST_V3_T10_REPORT.md；完整覆盖：runs/t10/20261016T021032Z/derived/COMPLETION_AUDIT.json。\n- 等待最后人工式审阅图表、打包与压缩包CPU复算验证；此状态本身不等于审阅包已交付。\n''')
write(r/'CPU_FINALIZATION_READY.json',dict(finished_at=utc(),status='READY_FOR_FINAL_VISUAL_REVIEW_AND_PACKAGING',worker_hours=runtime['worker_hours'],coverage=audit['coverage']))
print('CPU_FINALIZATION_READY',utc(),flush=True)
