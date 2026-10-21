from common import *
import shutil,re,collections
A=REPO/'T10_RESEARCH_FINAL';catalog=[json.loads(x) for x in (A/'index/stage_catalog.jsonl').read_text().splitlines()];run_id=RUN.name
uid='stage-'+hashlib.sha256(('final-gpc-capacity-t10::'+run_id).encode()).hexdigest()[:20]
new=dict(stage_uid=uid,display_ordinal='28',date_display='2026-10-21',timezone='Asia/Shanghai',run_id=[run_id],original_stage_root=str(ROOT),purpose_hypothesis='同GPC容量饱和与真实GQA静态完整worker分工；最后一次有限验证及归档',execution_status='COMPLETED_CONTROL_LIMITED_BRANCH; full fixed-state protocol NOT_RUN',hardware_driver_state=dict(gpu='Tesla T10',driver='580.178.04',sm_counts=[10,12,12,10,0,12],power_cap_w=100,state='dynamic restored after three failed fixed-state candidates'),workload_reality='synthetic FP16 paged GQA complete operator; changing last-token KV values, fixed lengths; no real model or growth sequence',implementation_entry='last_run/final-gpc-capacity-t10/src/range_runtime.py',math_body_launcher_hash={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'src/range_gqa.cu',ROOT/'src/range_extensions.inc',ROOT/'build/range_gqa.so',ROOT/'build/bridge_capacity.so']},baselines=['N19','E56_DIRECT','SM_PROP','EQUAL_GPC','WRONG_CAP'],metric_definition='host C++ submit-to-output-ready us primary; event span secondary; batch32 separate; change=100*(Tcandidate/Treference-1)',raw_paths=[str(RUN/'raw')],recomputable_scope='all 152 saved request phase means, 48 calibration phases, frozen weights and simple choices, finite numerical/hash audits, 12 state-load streams',verification_level='GPU_RERUN',conclusion='CAP slower than N19 on all four anchors in two dynamic blocks; full fixed-state hypothesis condition-limited',counterevidence='some partition contrasts positive, but not beyond N19; read-service total capacity nearly flat10→12 in these samples; no strong inference',unfinished_items=['qualified fixed state','full 6-block curves','8 holdout shapes','64-step growth','early/late 3-hour sessions','60-minute long run','native GEMM bypass controls'],next_stage_use='STOP_AUTOMATIC_EXPANSION; preserve N19 and archive',source_report={'local_path':str(RUN/'reports/FINAL_RESEARCH_REPORT.md'),'archive_path':'FINAL_RESEARCH_REPORT.md','sha256':sha(A/'FINAL_RESEARCH_REPORT.md')})
assert len(catalog)==27;catalog.append(new);(A/'index/stage_catalog.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in catalog))
# Precise mandatory claim links. Historical report paragraphs remain separately scoped.
claims=[json.loads(x) for x in (A/'index/claims_and_evidence.jsonl').read_text().splitlines()]
src=A/'sources/task_reference/HISTORY_CPU_GPC_LINK.md';src.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'input/T10_FINAL_GPC_CAPACITY_AND_ARCHIVE_20261021/sources/HISTORY_CPU_GPC_LINK.md',src)
def claim(cid,file,needle,statement,status,scope,not_implied,raw,absolute=None):
 ls=(A/file).read_text().splitlines();line=next(i+1 for i,s in enumerate(ls) if needle in s)
 claims.append(dict(claim_id=cid,statement=statement,status=status,scope=scope,source_file=file,source_lines=[line,line],raw_run=raw,metric_definition='See exact source paragraph; cross-stage speed metrics not pooled',comparison=None,absolute_values=absolute,uncertainty='Two dynamic blocks for new performance; historical scope per source',counterevidence='strong baseline and dynamic-state limits retained',not_implied=not_implied,verification_level='RAW_RECOMPUTED' if cid in ['C01','C02','C03'] else 'REPORT_ONLY' if cid=='C04' else 'GPU_RERUN'))
claim('C01','GPC_CAPACITY_REPORT.md','当前RM两次','当前有效GPC0–5配置为10/12/12/10/0/12 SM。','支持','current read-only RM topology',['manufacturing fuse reason','physical floorplan distance'],run_id,dict(sm_counts=[10,12,12,10,0,12]))
claim('C02','sources/task_reference/HISTORY_CPU_GPC_LINK.md','因此：类0','旧特定地址构造的34/22偏好与GPC集合{1,2,3}/{0,5}一致。','限制','specific historical dependent-load construction, later RM join',['arbitrary KV page 0x33 rule','physical home','contemporaneous stage15 RM snapshot'],'sm-topology-t10/20261017T121101Z; stage26 E1 CPU aggregate check')
claim('C03','sources/numa-locality-scheduling-t10/reports/REPORT.md','最终选定的 16','16B向量搬运取得普通GQA工程收益，不能归因NUMA；专用decode和模型基线仍有缺口。','支持','stage19 synthetic paged GQA, prior implementation baseline',['SOTA decode','full model tokens/s','topology contribution'],'numa-locality-scheduling-t10 current archived run; isolated CPU recomputation')
claim('C04','FINAL_RESEARCH_REPORT.md','Softmax地址采样','Softmax采样与当前静态共置未胜冻结强基线，保留已收束边界。','被更强基线解释','stage25 and stage27 specific prototypes',['all GPUs impossible','all scheduling impossible'],'stage25; stage27')
claim('C05','APPLICATION_REPORT.md','四锚、append','管理员控制实际执行但状态未达标；CAP有限两块均未胜N19，完整固定状态容量假设未定。','限制','four known anchors, synthetic Q/K/V, restored dynamic100W',['NUMA absent','fixed-state saturation proven','holdout or growth generalization'],run_id,{c:next(x['blocks'] for x in read(RUN/'derived/APPLICATION_COMPARISONS.json') if x['case']==c and x['reference']=='N19' and x['candidate']=='CAP' and x['metric']=='ready_us') for c in ['A01','A02','A03','A04']})
(A/'index/claims_and_evidence.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in claims))
lines=['# T10研究档案：28阶段总入口','','本轮已按任务书的 **CONTROL_LIMITED分支完成**。管理员入口已实际使用，555/540/525MHz均未通过状态标准，已恢复动态时钟；完整长程矩阵没有运行。四个GQA锚的CAP完整耗时都未胜原N19。默认保留第19阶段快核，不自动开下一轮。','','[最终研究报告](FINAL_RESEARCH_REPORT.md) · [导师简报](MENTOR_UPDATE.md) · [状态与恢复](ADMIN_AND_STATE.md) · [容量结果](GPC_CAPACITY_REPORT.md) · [真实算子结果](APPLICATION_REPORT.md)','','## 探索图','','![28阶段探索图](sources/figures/exploration_28.png)','','图表示问题演进，阶段数不是独立样本数；不同阶段正数不能相加。','','## 28阶段索引','','|显示编号|目的|结论与反例|本轮复核级别|','|---|---|---|---|']
for e in catalog:
 rp=e['source_report']['archive_path'];lines.append(f'|{e["display_ordinal"]}|[{e["purpose_hypothesis"]}]({rp})|{e["conclusion"]} {e["counterevidence"]}|{e["verification_level"]}|')
lines+=['','## 怎样检索和复算','','- `index/stage_catalog.jsonl`：稳定stage_uid、原目录/run、状态、数学体/入口hash、真实负载范围、限制及下一步。原编号只显示。','- `index/claims_and_evidence.jsonl`：结论、精确来源行、反例和不能推出什么；C01–C05是五个必须单列的主张。','- `index/artifact_manifest.jsonl`：关键旧文件hash与是否随包；`historical_raw_availability.jsonl`说明旧manifest中路径目前是否存在。旧大raw摘要为INHERITED，60个确定性抽样hash均匹配，不是全量数值复核。','- 第19阶段在隔离输出目录重跑原CPU复算，3份派生JSON完全一致；第22阶段重算原RM映射；第26阶段重算签名SM→GPC块均值。其余旧阶段明确REPORT_ONLY，原审计可追溯但本轮未伪称重跑。','- 本轮CPU入口：`python3 last_run/final-gpc-capacity-t10/src/recompute_final.py`。只解析已有raw，不启动CUDA；需要NumPy。','- 唯一推荐GQA接口见[FAST_GQA](reusable/FAST_GQA.md)，旧搜索路径见[deprecated_paths](reusable/deprecated_paths.md)。','','## 包的范围','','`REVIEW_SMALL.zip`含报告、索引、全部本轮主比较raw、NA/alias、源码和CPU复算，不含GPU二进制。`REPRODUCE_FULL.zip`再包含本轮与N19关键二进制。两者都通过CRC和逐文件manifest校验。','','**历史大raw以本地原件/旧归档manifest引用，不重复打包；FULL不是全部28阶段可离线独立复现包。** 没有下载缺失归档或上传GitHub/Drive。第三方CUDA/PyTorch/驱动/toolchain不随包。来源原件只读保留；分享副本只移除无关进程完整参数，脱敏记录见index/SHARING_REDACTIONS.json。']
(A/'README.md').write_text('\n'.join(lines)+'\n')
(A/'index/unresolved_questions.md').write_text('''# 已回答、仍未知、没做

已回答：当前GPC屏蔽不均匀；有限range干预数学与成员资格成立；CAP在本次两块四锚未胜N19；三档实际时钟控制未过预定门槛。

仍未知：支持频率在100W下是否存在可稳定且通过计数标准的工作点（本轮最多三档，不继续扫）；计数完整固件语义；物理地址/home映射；屏蔽状态反事实；内存/前端/调度及原生动态平衡各自的因果份额；N19与专用成熟decode的差距。

未做：完整固定状态六块曲线、有限地址偏移、八个留出形状、三小时早晚复验、64步跨页增长、60分钟长程、恢复态三块比较和新GEMM旁路控制。ALL_CONDITIONS.jsonl逐项NA，不把动态有限格子冒充固定状态结果。

不要重复：Softmax邮箱/配对扩搜、0x33拟合迁移到新KV、10/46共置份额/k重搜、旧选择器阈值迭代。不得把新报告引用旧同批raw算独立验证。

当前处理：保留N19工程资产与有限表征，停止本轮及当前T10路线的自动扩搜；未来新项目需单独目标与状态条件。
''')
(A/'REPRODUCE_FULL/README.md').write_text('''# 完整本轮材料与历史引用

FULL ZIP包含本轮全部raw/代码/关键二进制及报告、stage/claim索引、历史原件引用。历史大raw仍在original_stage_root及旧manifest指向的本地原件/先前发布归档，没有复制15GB归档或模型/vendor。

因此它不是全部历史可离线独立复现包。环境需兼容本机CUDA/PyTorch/driver，绝对include/lib/RPATH见各build.json，搬迁重编译需要对应调整。CPU复算本轮不需要CUDA。

本机根目录为 /home/ubuntu/文档/ChatGPT/numa_gpu；旧本地归档目录 /home/ubuntu/文档/ChatGPT/EXP_NUMA_SM_delivery_20261018/release-assets；是否存在以index/historical_raw_availability.jsonl为准，不以路径文字充当已打包文件。
''')
print('ARCHIVE_DOCS',len(catalog),len(claims))
