"""Final CPU metadata only. Refuses to mark a still-running campaign complete."""
import csv,datetime,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 s=json.loads((ROOT/'reports/summary_t10.json').read_text());audit=json.loads((ROOT/'reports/SOURCE_PROVENANCE_AUDIT.json').read_text())
 assert s['campaign_execution_complete'],s.get('stage_blocks_completed')
 assert not audit['pending_manifests'],audit['pending_manifests']
 assert not audit['worker_lock_overlap'] and not audit['warmup_violations']
 assert s['worker_occupied_s']<57600
 reg=[json.loads(x) for x in (ROOT/'registry/runs.jsonl').read_text().splitlines()];observations=[]
 for m in reg:
  x={k:m[k] for k in ['run_id','key','process_started_at','process_ended_at']}
  for when in ['before','after']:
   p=ROOT/m['path']/('device_'+when+'.csv')
   with p.open() as f:x[when]=next(csv.DictReader(f,skipinitialspace=True))
  observations.append(x)
 (ROOT/'reports/power_configuration_observations.json').write_text(json.dumps(observations,indent=2))
 health=dict(recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),gpu=subprocess.check_output(['nvidia-smi','--query-gpu=uuid,name,temperature.gpu,memory.used,memory.free,power.limit,ecc.errors.uncorrected.volatile.total','--format=csv'],text=True),compute_processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv'],text=True),existing_thermal_service=subprocess.check_output(['systemctl','is-active','t10-quiet-fan.service'],text=True).strip())
 (ROOT/'reports/final_health.json').write_text(json.dumps(health,indent=2))
 strong=s['strong_library'];total=s['formal_phases']+s['layer_request_phases']+strong['phases']
 (ROOT/'STATUS.md').write_text(f'''# OP-FUSED T10 — 本轮有限执行结束

研究状态：**IMPLEMENTATION_OR_RESOURCE_LIMITED**。FULL候选没有可修改且合格的SM75 Tensor Core主体，未实现；不是NO_INCREMENT或NUMA阴性。

原生基线{s['baseline_cases']}形状，其中{s['complete_six_block_cases']}形状各6进程块；补充逐请求层{s['layer_request_case_blocks']}个有效case-block；独立原生grouped强库对照{strong['case_blocks']}个case-block。合计{total}个正式测量phase。

正式case失败{s['total_formal_case_failure_records']}条，保留raw与原因。另有未通过保守显存余量检查的形状：{s['memory_headroom_audit']['flagged_case_ids']}。温控功耗125/100W条件、所有锚漂移、3组输入seed循环和未执行模型均披露。

GPU-worker用时{s['worker_occupied_s']/3600:.3f}小时，上限16小时；无worker重叠。各阶段实际预算见reports/summary_t10.json。本轮没有下载/安装或改动驱动、频率、功耗、风扇服务，没有改写旧实验raw。

从reports/OPERATOR_FUSED_SCHEDULING_REPORT_t10.md与reports/QUESTIONS_FOR_PAPER_REVIEW.md开始复核。
''')
 with (ROOT/'WORKLOG.md').open('a') as f:f.write(f"\n- 有限执行结束：{total}个正式phase，GPU-worker {s['worker_occupied_s']:.1f}秒；全部进程结束后进行CPU复算、source/raw审计、图表与包校验。最终研究状态仍为实现/资源受限。\n")
 print(json.dumps(dict(formal_phases=total,worker_hours=s['worker_occupied_s']/3600,health=health),indent=2))
if __name__=='__main__':main()
