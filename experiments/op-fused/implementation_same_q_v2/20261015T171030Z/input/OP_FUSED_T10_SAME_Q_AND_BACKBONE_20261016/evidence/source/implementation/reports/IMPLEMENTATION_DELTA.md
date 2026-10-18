# T10 算子内实现变化

本文件记录新实现的机制，性能结论以同目录最终报告及 `derived/implementation_v1/summary.json` 为准。原 baseline 报告和 raw 保留；旧报告中的“候选未实现”是当时状态。

## 来源和数学主体

完整 CUTLASS v3.5.1 checkout 在 `op-fused/vendor/cutlass`，commit `f7b19de32c5d1f3cedfc735c2849f12b537522ee`。本轮用户已授权联网下载源码及必要依赖。无需修改驱动或安装整套系统 CUDA。新代码在 `op-fused/src`；upstream checkout 不打实验补丁。

`grouped_backend.cu::Math` 实例化 SM75 `DefaultGemmGrouped`：FP16 输入与输出、FP32 累加，row-major，K/N 与行跨度按 8 元素对齐。两种预先固定的 block tile 为 32×128×32 和 64×128×32，warp tile 均为 32×64×32，instruction tile 16×8×8，两级 pipeline。没有新增 split-K、改变路由或降低精度。M 尾块及 K/N 非 tile 整倍数在资格阶段验证。

`op_fused_gemm_grouped.h` 从上游 `gemm_grouped.h` 复制，只增加 visitor 模板参数和类名；`operator()` 源码逐字节一致。MMA、共享内存迭代器、pipeline reset/barrier、epilogue 均保持。最终二进制 `09bd2afd400e7cb32bfcad004617260ad40dc571f09469f364a62cedc7b954ed` 有六个数学 kernel，各有 64 条静态 HMMA 指令；这证明生成了 Tensor Core 代码，不等于运行时效率已追平 cuBLAS。

## CORE、BAL、CACHE、FULL、ABL

| 名称 | 实际实现 | 新信息或限制 |
|---|---|---|
| CORE | CUTLASS 原始 device-only grouped visitor | 原生按输出 tile 的 round-robin |
| BAL | 相同原 visitor；异质 K 时静态描述符按 K 降序 | 同 K 时与 CORE 完全同一次测量，明确 alias |
| CACHE | `OpPacketVisitor<Full=false>`，全局固定 q=1/2/4 | 固定相邻 M tile 包，按 N panel 遍历；开发集选择一个 q |
| FULL | `OpPacketVisitor<Full=true>` | 在相同 packet 机制上，根据总 tile / worker / waves 和 K 工作预算限制 q |
| ABL | 同 FULL 机制但 qcap=1 | 仍支付 FULL 的信息读取及判断成本；若 FULL 也 qcap=1 则 alias 去重 |

FULL 规则保持原版本：`q = pow2floor(min(qcap, Mtiles, max(1,total_tiles/(workers*waves)), max(1,128/ceil(K/32))))`。qcap=1/2/4、waves=1/2，两种数学配方共 12 个 FULL 组合，没有测试后修改预算。worker 数按该配方 CORE/CACHE/FULL 的最小实测 occupancy × 56 SM，限制不超过实际输出 tile 数。它是共同 launch 配置，不绑定 SM。

`packet_visitor.h::{q_for,packet_count,next_tile,threadblock_idx,advance}` 是唯一新调度主体。保留原 warp prefix/search；改变 work unit 计数、packet 内推进和输出 tile ordinal。一个 packet 处理完后再按 gridDim.x 前进。没有外部任务列表、全局队列或第二个 planner。

q=1 也可把原 M-major 顺序变为 N-panel-major，不能称为 native identity。q>1 是同 CTA 连续处理相邻 M tile；每个 tile 仍执行原 MMA mainloop，未显式跨 tile 保留 B fragment 或共享内存。潜在缓存复用不是已测 L2/DRAM 命中率证据。没有物理 SM 亲和、裁剪信息或 NUMA 拓扑输入。

## 合法融合四格

全层执行有用的 token gather pack → gate/up grouped GEMM → SiLU → multiply → down grouped GEMM → unpack → gate multiply → reduce。所有 expert 权重驻留。

F0/F1 都使用同一个向量化 `pack_rows` gather。F1 额外由 CTA0 的第一 warp 读取已就绪的 GPU up/down problem shapes，写两个 int32 总 tile 数；后续 GEMM 通过同 stream 的依赖读取。它不读其他 pack CTA 的输出，也不做跨 CTA 同步。F0 FULL 在各 CTA 内读取 problem shapes 并做 warp reduction；F1 FULL 用 sideband 替代。F1S0 同样包含 sideband 的成本，即便 simple 不使用它。

S0 是开发集冻结的同体 CORE/CACHE 强简单策略，S1 是冻结的 FULL。四格 F0S0/F0S1/F1S0/F1S1 使用同一数学配方与精度。生产 LIB 保留原 Torch index_select pack 和实际所需的全部库内节点；不人为拆开 LIB，也不删掉库自己的 split-K/merge。

sideband 来自本步已准备的 GPU 描述符，但正式输入是固定 post-route replay：CPU 预建 route/count、problem shapes、指针/stride 数组、Graph 都在热计时外。没有动态 router/count/scan 或每请求变形数据；不能声称动态元数据免费。Graph 对所有策略开放，Graph 本身不是 fusion。

## 验证、执行与限制

数值使用原 FP64 参考合同，逐元素 `abs_error <= .005 + .005*abs(ref)`，relative Frobenius <= .002；同体要求全输出 bitwise。资格覆盖空 expert、尾块、多 tile 包、65 experts 跨 warp-prefix 边界、同 Graph 改输入/清 NaN 输出。诊断 `count_visits` 只在资格阶段调用，未进入正式 Graph。

生产热路径为一次 grouped GEMM kernel，或全层必要算子序列，无新调度 kernel、动态 scheduler D2H、按 expert CPU 发射及算子内部全设备等待。宿主依然调用 Graph replay；层请求在真实结果边界同步一次。资格、初始化和验证有 D2H/synchronize，明确在计时外。

worker 获锁后复制只读源码及实际二进制，执行快照入口；继承同一个 GPU 锁和原 16 小时累计账本。正式源和参数不在测试中修改。新 sanitizer 为 NVIDIA CUDA 12.8.93 用户目录解包版，有限 memcheck 通过；旧工具的两个启动失败全部留存。

100 W 固定上限由本轮用户批准；保留风扇、过温、低转速和 watchdog 保护。固定功耗不等于锁频。首尾漂移块保留，不按温度回归修正或重跑取最快值。

未单独测每一项初始化耗时或 kernel 内部 scheduler/mainloop 时间；现有残差只能记为设置、验证、pilot、Graph 和 Python 总开销。没有硬件计数器，不用逻辑字节充当实际 DRAM 流量。attention 内部 visitor 与真实模型 adapter 未成熟，原库结果保留，不能改名为本方法结果。
