"""Prepare the local research handoff. CPU/file operations only."""
from common import *
import shutil, difflib, collections

A=REPO/'T10_RESEARCH_FINAL'
def copy(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def doc(name,body):
 p=A/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body.strip()+'\n')
def tree(src,dst):
 shutil.copytree(src,dst,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))

doc('reusable/FAST_GQA.md',r'''
# 唯一推荐的GQA入口：第19阶段LocalityPlan

保留原实现与默认规则，未把本轮CAP切入默认。原位置为 `numa-locality-scheduling-t10/src/locality_plan.py`；随包副本在 `last_run/numa-locality-scheduling-t10/`。这是有限形状的工程资产，不是模型框架插件或成熟专用decode库的替代证明。

```python
import sys
sys.path.insert(0, 'T10_RESEARCH_FINAL/last_run/numa-locality-scheduling-t10/src')
from locality_plan import LocalityPlan
# q, k, v, table, lengths已由调用者按下面合同准备在同一CUDA设备。
plan = LocalityPlan(q, k, v, table, lengths, new_k, new_v, policy='DEPLOY')
out = plan.launch()  # 异步；读取CPU结果前需等待对应stream
```

工作形状：D=128，页长16；B/Hq/Hkv/最大容量依次为1/32/8/1024、1/32/8/8192、1/32/4/8192、4/32/8/4096。最后一项历史测试长度为[4096,3073,2049,1027]，不是任意ragged长度的性能保证。SHORT与RAGGED默认VECTOR_DIRECT，LONG和GQA8默认VECTOR_BLIND。DEPLOY是确认后部署门槛，不是独立留出路由结果。

- q为[B,Hq,128]；k/v为[physical_pages,Hkv,16,128]，FP16连续CUDA张量；内部FP32累加，输出FP16。table为[B,capacity_pages]、lengths为[B]的连续int32；缓存k/v须16字节对齐。所有张量同设备，引用活到最后一次执行完成。
- table内每个映射页必须有效，1≤length≤capacity_pages×16；页分配、table及缓存指针在plan生命周期内保持固定。搬迁或扩容要重建plan。长度值可在设备侧更新，但须有stream依赖；跨页增长必须已有正确映射与足够容量。本轮并未执行64步增长验证。
- new_k/new_v同时有或同时无，形状[B,Hkv,128]。append写当前length−1位置，不自行增加length。多序列共享只读页时，写末页须私有或由上层完成COW，不能让同批多序列无保护地写共享末页。
- 每个并发stream/在途请求使用私有plan、counter、partial和output；同plan只允许同stream顺序复用。输出buffer会被下一次launch覆盖。调用者负责跨stream输入依赖与缓存生命周期；有限sanitizer不构成任意并发保证。
- 构造器包含CPU列表、分配、动态库加载和同步，不放在热循环或Graph capture内。构造完成后launch可被CUDA Graph capture；图复放要求指针存活、可写工作区不被并发复用。初始化费用与steady-state计时分开。
- 未测形状抛ValueError；布局/类型主要由assert检查，不能使用python -O作为完整校验接口。页索引检查仅在构造列表的路径出现，DIRECT不会全面检查每个页号/长度。调用者必须验证边界，错误输入不是安全回退。

完整入口会预加载5个库：attention.so、vector.so、vector_append.so、legacy/attention.so、legacy/append.so。FULL随包；SMALL只有源、build元数据和hash。CUDA12.0 nvcc、g++12.4、sm_75、当前580.178.04驱动；Python/PyTorch、运行时库版本以环境和旧stage19报告为准。本轮未更换依赖。

`source_snapshot/n19/`保留源与freeze，`source_snapshot/legacy_decode/`保留旧append来源。构建脚本与build.json记录实际编译命令；它们含本机leetgpu-lab、CUDA/PyTorch include/lib和RPATH绝对路径。搬迁需要把这些路径映射到兼容安装；第三方CUDA/PyTorch、lgjudge辅助模块不随包，FULL不承诺在任意机器直接加载。先CPU复算，GPU运行需独立建立环境和验证，不能用旧时间替代新测量。
''')
doc('reusable/TOPOLOGY_READER.md',r'''
# 真实拓扑只读入口

原入口 `gpc-mask-t10/src/read_topology.c`，构建脚本`src/build.sh`，可执行文件`gpc-mask-t10/read_topology`。自有源/构建脚本与当前二进制hash随包；FULL另含二进制。用法为直接运行可执行文件，JSON写stdout，诊断写stderr；没有输出文件位置参数。

```bash
./read_topology > topology.json 2> topology.log
```

它调用NVIDIA RM控制接口读取GPC/TPC/SM映射和floorsweep信息，不写mask、不修改驱动或频率。依赖本机580.178.04对应的open-gpu-kernel-modules头文件及ABI；build.sh实际-I路径已保留，第三方完整源码未重复装包。换驱动须核对ABI并新取快照，不能直接重用旧映射。

本轮初始两进程与最终快照相同：物理GPC0–5为10/12/12/10/0/12 SM。逻辑SM ID到物理GPC/TPC的表见last_run本轮environment/topology_0.json。快照仅对该设备、驱动、启动与当前暴露配置有效；资源查询及实际kernel位置检查同时使用。它证明非均匀资源分布，不证明芯片平面距离、屏蔽原因或地址的物理home。
''')
doc('reusable/MEASUREMENT.md',r'''
# 测量与原值合同

本轮在实际请求555、540、525MHz后都未满足预定状态标准，按CONTROL_LIMITED完成，最后-rgc恢复。100W功耗上限不等于固定频率；不得把动态两块重标成固定状态或精细硬件结论。管理操作日志与原始状态样本在last_run的environment、raw/P1_*；无密码/token文件。

应用主指标是C++提交至完整输出ready时间；GPU外层event span为辅助。五个Green producer、依赖、原merge和join全部计入；一次Graph提交不等于一个kernel。BATCH32只给整批总时间，不反推单请求ready或p99。样本、窗口、进程块、同计划alias分别记录，进程块是比较单位。

四个输入槽位轮换；正式窗口前相同提交节奏预热≥32次且≥100ms。ABBA/BAAB成对窗口内不做正确性检查。开发期冻结规则，确认不重新选择。CAP权重来自两个开发进程的一次并发容量估计；WRONG固定左轮转。计时阶段152个、主逐请求25072条；另有状态资格1829120个原始请求记录，二者用途不同。

统一时间变化为100×(T候选/T对照−1)，负数更快。跨块几何均值；两动态块不给伪造置信区间，旧阶段置信区间保留原定义。旧报告有些以时间节省为正，不能直接把正负号混合。跨阶段收益不能相加；同一raw衍生多报告不是新增独立证据。

CPU复算：`python3 last_run/final-gpc-capacity-t10/src/recompute_final.py`，需要NumPy，不导入torch或启动CUDA。会复算派生结果并比较已有hash；输出PASS才是复算通过。历史19/22/26的CPU复核及其他REPORT_ONLY范围见index，完整新计划的未执行条件逐行标NA。

构造资源和Graph、校准、部署请求摊销见COST_ACCOUNTING.json；它不包括生产系统所有冷启动/数据准备。本轮CAP对N19没有正steady-state节省，不能宣称H=1/100/1000有限回本。保留所有失败worker及修复前代码，冻结文件中的来源字符串笔误用追加correction说明，不篡改冻结数值。
''')
doc('reusable/deprecated_paths.md',r'''
# 不再默认开启的探索路径

保留全部旧原件，只是不再自动扩展搜索。

|路径|当前处理|原因/边界|
|0x33地址偏好、KV复制、地址页队列|实验入口；默认关闭|同队列/更强快核下未建立净收益，复制还有生命周期成本|
|Softmax邮箱配对及真实核采样选择器|当前路线已收束|BASE54保留为实验强静态基线；采样扣费后未超越它|
|旧10/46共置、q/k/布局搜索|不再默认扩展|份额/尾部释放有局部作用，未胜冻结强串行；确认后不能改选PACK|
|GEMM地址归并及资源选择器|保留研究源，非部署默认|原CUTLASS/库和状态稳定性对照未通过|
|本轮CAP/WRONG/SM_PROP/EQUAL五分组|实验比较入口，非生产默认|受限两块CAP输N19；完整固定状态留出长程未执行|
|N19 LocalityPlan DEPLOY|唯一推荐GQA工程入口|四个已测形状；普通向量化/任务组织收益，不称NUMA收益|

跨阶段别名、合成输入、强制split、确认后默认选择等限制见stage_catalog和各原报告。下一位无需把已经输给强基线的探索重新当成未经测试的主张；未知项见index/unresolved_questions.md。
''')

# Exact source snapshots and necessary baseline dependencies.
N=REPO/'numa-locality-scheduling-t10';Ndst=A/'last_run'/N.name
nfiles=['common.py','locality_plan.py','attention.cu','legacy_attention.cu','vector_attention.cu','vector_append.cu','build.py','build_vector.py','build_vector_append.py']
for f in nfiles:
 copy(N/'src'/f,Ndst/'src'/f);copy(N/'src'/f,A/'reusable/source_snapshot/n19/src'/f)
for f in (N/'freeze').glob('*.json'):
 copy(f,Ndst/'freeze'/f.name);copy(f,A/'reusable/source_snapshot/n19/freeze'/f.name)
copy(N/'CURRENT_RUN.txt',Ndst/'CURRENT_RUN.txt')
for f in (N/'build').rglob('*'):
 if f.is_file() and f.suffix in ['.so','.json','.log']:copy(f,Ndst/'build'/f.relative_to(N/'build'))
L=REPO/'llm-decode-locality-t10'
for f in ['common.py','attention.cu','append_attention.cu','build.py','build_append.py']:
 copy(L/'src'/f,A/'reusable/source_snapshot/legacy_decode/src'/f)
for f in ['build/build.json','build/append/build.json']:
 copy(L/f,A/'reusable/source_snapshot/legacy_decode'/f)
for f in (REPO/'gpc-mask-t10/src').iterdir():
 if f.is_file():copy(f,A/'reusable/source_snapshot/topology/src'/f.name)
copy(REPO/'gpc-mask-t10/read_topology',A/'reusable/source_snapshot/topology/read_topology')
for f in ROOT.joinpath('src').glob('*'):
 if f.is_file() and f.suffix in ['.cu','.inc'] or (f.is_file() and f.name.startswith('build')):copy(f,A/'reusable/source_snapshot/final_capacity/src'/f.name)
patch=''.join(difflib.unified_diff((ROOT/'src/gqa_append.cu').read_text().splitlines(True),(ROOT/'src/range_gqa.cu').read_text().splitlines(True),fromfile='gqa_append.cu',tofile='range_gqa.cu'))
doc('reusable/source_snapshot/final_capacity/range_from_append.patch',patch)
# E56/micro binaries inherited without recompile: preserve their actual original build commands.
for name in ['gqa','gqa_append','micro','bridge_e4']:
 for tail in ['_build.json','_compile.log']:
  copy(REPO/'gpc-contention-gqa-t10/build'/(name+tail),ROOT/'build'/('inherited_'+name+tail))

def rec(path):
 return dict(original_path=str(path),sha256=sha(path),bytes=path.stat().st_size)
lineage={
 'default':'N19 LocalityPlan DEPLOY unchanged; CAP experimental',
 'compiler_versions':'last_run/final-gpc-capacity-t10/runs/'+RUN.name+'/environment/COMPILER_VERSIONS.json',
 'environment_limit':'third-party toolchain/runtime and all old raw are not bundled',
 'N19':{'source':[rec(N/'src'/f) for f in nfiles], 'binary':[rec(p) for p in sorted((N/'build').rglob('*.so'))], 'policy':rec(N/'freeze/DEPLOYMENT_POLICY.json'),'selection_scope':'post-confirmation deployment gate, no independent routing holdout'},
 'E56_inherited':{'source':[rec(ROOT/'src'/f) for f in ['gqa.cu','gqa_append.cu']], 'binary':[rec(ROOT/'build'/f) for f in ['gqa.so','gqa_append.so']], 'origin':'stage26 direct port of N19 math with resource-compatible launcher; not identical compiled entry'},
 'E56_DIRECT_range_and_CAP':{'source':[rec(ROOT/'src'/f) for f in ['range_gqa.cu','range_extensions.inc','bridge_e4.cu','range_runtime.py']], 'binary':[rec(ROOT/'build'/f) for f in ['range_gqa.so','bridge_capacity.so']], 'math':'DIRECT original QK/softmax/partial/merge and W; task range visitor only', 'difference':'E56_DIRECT one full56 producer; CAP five disjoint full workers plus original merge and dependency join', 'N19_difference':'SHORT last-arriver fusion and LONG/GQA8 BLIND retained in baseline; no claim five-launch overhead explains whole N19 gap'},
 'repairs':['freeze/DIAGNOSTIC_EVENT_REPAIR.json','freeze/CAP_WEIGHTS_PROVENANCE_CORRECTION.json','freeze/PORTABLE_CPU_PATH_FIX.json'],
 'topology_reader':rec(REPO/'gpc-mask-t10/read_topology')}
write(A/'index/baseline_lineage.json',lineage)

# Improve primary evidence links, without changing historical report text.
rows=[json.loads(s) for s in (A/'index/claims_and_evidence.jsonl').read_text().splitlines()]
for r in rows:
 if r['claim_id']=='C01':
  r['uncertainty']='Three matching read-only RM snapshots; performance block uncertainty is not applicable to this count'
  r['additional_sources']=[{'source_file':'last_run/final-gpc-capacity-t10/runs/'+RUN.name+'/environment/topology_0.json','scope':'actual current RM read'}]
 if r['claim_id']=='C02':r['verification_level']='AGGREGATES_RECOMPUTED';r['uncertainty']='Historical dependent-load construction and later topology join; no contemporaneous stage15 RM snapshot'
 if r['claim_id']=='C03':
  r['additional_sources']=[{'source_file':r['source_file'],'source_lines':[126,126],'scope':'specialized decode / real-model gap'}]
  r['uncertainty']='Exact stage19 derived JSON reproduced on CPU; no new old-tensor GPU rerun and no specialized decode baseline'
 if r['claim_id']=='C04':
  r['additional_sources']=[{'source_file':'sources/topology-real-t10/reports/REPORT.md','source_lines':[3,12]},{'source_file':'sources/quota-tail-closure-t10/runs/20261019T064852Z/reports/T10_QUOTA_TAIL_CLOSURE_REPORT.md','source_lines':[7,13]}]
  r['uncertainty']='Original stage25/stage27 report intervals retained; these are not independently rerun this round'
(A/'index/claims_and_evidence.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
write(RUN/'reports/FIGURE_REVIEW.json',{'status':'PASS','method':'visual inspection of rendered PNGs by assistant','figures':['01_clock_state','02_capacity','03_application','exploration_28'],'limits':'No confidence intervals invented for two dynamic process blocks'})

# Current run snapshot; preserve original files, redact only the sharing copy.
Dst=A/'last_run'/ROOT.name
for name in ['src','build','input']:tree(ROOT/name,Dst/name)
copy(ROOT/'CURRENT_RUN.txt',Dst/'CURRENT_RUN.txt');tree(RUN,Dst/'runs'/RUN.name)
redactions=[]
for name in ['INITIAL_COMMANDS.json','FINAL_COMMANDS.json']:
 p=Dst/'runs'/RUN.name/'environment'/name;old=sha(p);data=read(p)
 for row in data:
  if row.get('command',[None])[0]=='ps':
   row['stdout']='[Sharing copy: unrelated full process arguments removed. Original retained locally.]\n';row['sharing_redaction']='Unrelated process full arguments; not GPU timing data'
  if row.get('command',[])[:2]==['systemctl','list-units']:
   row['stdout']='\n'.join(line for line in row['stdout'].splitlines() if any(w in line.lower() for w in ['t10','nvidia','gpu','fan','power']))+'\n';row['sharing_redaction']='Retained only GPU/fan/power service lines; relevant individual unit snapshots retained separately'
 write(p,data);redactions.append({'archive_path':str(p.relative_to(A)),'original_sha256':old,'shared_sha256':sha(p),'reason':'remove unrelated process arguments and unrelated system service inventory; original unchanged'})
write(A/'index/SHARING_REDACTIONS.json',redactions)

avail=read(A/'index/HISTORICAL_AVAILABILITY_SUMMARY.json');totals=collections.Counter()
for row in avail['manifests']:totals.update(row['counts'])
doc('index/HISTORICAL_AVAILABILITY.md',f'''
# 历史原件可用性

继承36份旧manifest；逐条检查132039项本地引用存在，471项外部交接路径未擅自重定位。存在性计数可含不同manifest重复引用，不是独立实验数。

1项缺失为 `numa_gpu/vendor/thrust/cub`（旧vendor引用）；没有下载或伪造补齐。逐条状态在historical_raw_availability.jsonl的exists字段。60个确定性抽验文件hash全部匹配；并非132039项全部重新hash或数值复核。关键旧报告/源码/二进制另见artifact_manifest的HASHED_NOW记录。

旧阶段19的原CPU复算得到三份完全一致的派生JSON；22重算RM映射；26重算派生CSV的GPC块均值。其余本轮仅复核报告/引用，不写成GPU重跑。
''')
print('ASSETS_PREPARED',dict(totals))
