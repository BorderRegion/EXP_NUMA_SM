import json,subprocess
from common import *
r=runroot();led=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()];by={x['key']:x for x in led};active=[];pending=[]
for p in (r/'raw').glob('*/manifest.json'):
 x=json.loads(p.read_text())
 if x['status']=='RUNNING':active.append({k:x.get(k) for k in ['key','stage','pid','process_started_at']})
 if x['status']=='REQUESTED':pending.append(x['key'])
def done(prefix):return sum(x['status']=='COMPLETED' and x['key'].startswith(prefix) for x in led)
x=dict(time=utc(),completed_workers=sum(v['status']=='COMPLETED' for v in led),failed_workers=[v['key'] for v in led if v['status']=='FAILED'],settled_worker_hours=sum(v['worker_s'] for v in led)/3600,active=active,pending=pending,counts=dict(P1_main=6,P2_native=done('p2_native_b'),P4_native=done('p4_native_b'),fine_shift=done('fine_shift_')-int('fine_shift_qualification' in by)-int('fine_shift_memcheck' in by),micro_formal=done('micro_b'),lifecycle_formal=done('compiled_lifecycle_b')));write(r/'PROGRESS_SNAPSHOT.json',x);print(json.dumps(x,ensure_ascii=False,indent=2))
if not (r/'CPU_FINALIZATION_READY.json').exists():
 (ROOT/'STATUS.md').write_text(f'''# NUMA-first V3\n\n执行中，最后更新 {x['time']}。当前运行 `runs/t10/20261016T021032Z`。\n\n- P0/P1 主实验已完成：6 次主分配、96 strata、18,874,368 CTA 记录。\n- P2 三族开发块：{x['counts']['P2_native']}/3；P4 三族正式块：{x['counts']['P4_native']}/8。\n- P3 等价移位细分控制：{x['counts']['fine_shift']}/4 个分配（前1开发后3确认）。原始除法版本额外 scout 完整保留。\n- 编译 Graph micro：{x['counts']['micro_formal']}/8 正式块。N/E/B/T/X/Y/M/P；T 不搬数据，独立测量，最终设计不是 M/T alias。正式前已将执行次序改为 Williams，GPU cubin 和重复数不变。\n- 实际释放/重分配/扩容：{x['counts']['lifecycle_formal']}/4 块，3事件×N/T/M；此为合成编译机制生命周期，不是完整真实模型生命周期。\n- 已结算新账本 {x['settled_worker_hours']:.3f}/24 GPU-worker 小时，正在运行另计。\n- 当前 worker：{', '.join(v['key'] for v in active)}；未开始的排队项：{', '.join(pending)}。\n- 两个终端外壳排队请求在测量前以143退出；原 manifest 归档，已恢复到有限本地独立进程。没有重跑成功块。另一次主动停止的是正式前顺序修正的未启动请求，详见 MICRO_ORDER_TRANSITION.json。\n- 100 W 与风扇/过温/低转速/看门狗保护持续生效；本轮未改系统控制。清理软件缓存留磁盘余量；实验数据与模型保留。\n''')
