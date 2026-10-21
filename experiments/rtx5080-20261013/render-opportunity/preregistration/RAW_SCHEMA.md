# 原始证据合同

当前没有硬件访存样本或渲染 session。示例和 CPU 自检均带 SYNTHETIC 标记，
不得放入硬件汇总或触发 E2。

## affinity CSV（tools/analyze.py affinity）

必需列：

```text
gpu_uuid,driver_version,process_id,context_id,allocation_generation,allocation_base,allocation_range_bytes,cache_regime,load_kind,workset_bytes,epoch_id,run_id,split,dispatch_id,smid_begin,smid_end,region_id,region_offset_bytes,region_span_bytes,clock_cycles,loads,checksum_verified,source_kind
```

split 为 calibration / validation；source_kind 为 HARDWARE / SYNTHETIC。
每行是一次线程/block完整数据依赖链测量，不是链中单次 load。
clock_cycles 是该线程同次 clock64 相减值；loads为实际访问数；checksum_verified=1。
单位 cycles/load，不伪称纳秒。region offset/span 必须落在该自有 allocation range。
map identity包含上列 GPU/driver/process/context/generation/base/range/cache/load/workset/epoch。
run_id 可在同分配复测改变，split 的 run 集不能重叠。SM 编号可以稀疏。
同一 region_id 在一地图中必须唯一对应 offset/span；不同 region_id 范围不应混淆。
dispatch_id 是同一 run 中的实际 launch序号。同dispatch多样本先中位，不能当独立进程。
混合 HARDWARE/SYNTHETIC 文件拒收。每种缓存/指令/工作集独立输出。
缺单元显式 missing；不补矩阵。拟合允许稀疏表，置乱/信号资格要求完整交叉表。
分析器不给物理域名，不自动认定跨地址外推、三进程复验、控制或论文机会。

对应 manifest 还必须保存源码/binary/编译/PTX/SASS哈希、device memory ownership、
初始化seed/hash、链构造、目标/实际 SM、GPU状态、每launch事件时间、异常和安全缩量。
CSV 中偏移不能证明物理连续或物理 home；pointer需要合法API查询。

## renderer session JSON（tools/analyze.py sessions）

输入是有 schema_version=1、source_kind、frozen_primary_baseline 的对象，sessions为列表。
每个 session 必需：split、process_block、scene、trajectory、strategy、
frame_e2e_ms（真实measurement帧时间列表）、one_time_ms。
正式输入还需可追溯的 raw 与manifest链接及输出资格证据；本CPU工具不代替 GPU 资格审计。
策略为 B0–B5、M、C；校准集和测试集均至少完整 B1–B5。
端到端时间已含在线额外成本。one_time_ms 为该策略额外/总一次性成本，
比较时相减；不得重复计入 frame_e2e_ms。不同策略以同一基准定义该列。
每case与process_block所有比较策略均配对，缺配对即报错。
frozen_primary_baseline若给出，必须与校准选择相符；测试数据不参与选择。
CPU生成的合成session验证统计逻辑，不能称真实renderer执行。

## raw 保全

tools/inventory.py --output 使用独占创建，不覆盖已有文件。
tools/analyze.py 输出亦独占创建。新运行用新run_id，源数据不修改。
当前活动 run_id 见 campaign.json；最后由 manifest.json 记录全树文件SHA-256。
每个硬件地图/资产/camera/input更改建立新版本，原raw留存。
