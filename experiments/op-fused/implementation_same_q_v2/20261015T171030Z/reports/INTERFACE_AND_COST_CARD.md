# 接口、生命周期和成本清单

| 输入/接口 | 生命周期 | 正式每步成本 |
|---|---|---|
| A/B/C 指针、M/N/K、leading dimensions | 每个静态 operator 初始化，GPU 常驻 | grouped kernel 读入；无每步 host 重建 |
| grouped 描述符 | shape 12E + pointers 24E + strides 24E = 60E bytes/operator | 既有 problem 查找；无新外部任务表 |
| q1-minimal | 原生 visitor 继承，仅 ordinal 映射变化 | 不读总 tile/K-budget，不生成 sideband |
| legacy FULLq1 | 旧通用 packet visitor | 每 CTA 的 warp 总 tile 规约仍存在；映射仍与 CACHEq1 相同 |
| 层 up/down 描述符 | 两个 operator 各自初始化，合计 120E bytes | pack/up/activation/down 的必要依赖边界 |
| route token/inverse/gates | 本轮已给定的 post-route 输入，固定三个路由家族 | pack/unpack/gate/reduce 都包含在层时间内 |
| activation fusion | 单独 pointwise consumer，完整 up 之后 | 两个阶段合为一 kernel，保留两次 half 舍入 |
| ring activation | 预先生成 8 槽；权重和描述符共用 | 每请求 CPU 选槽 + 一次 D2D copy，包含在 ready/event 时间内 |
| Graph | 初始化/capture，不在热 phase | 每个算子一 graph replay；完整层每请求一 replay |
| 结果边界 | 正式测量的一部分 | 算子每 batch 一等待；层每请求一输出等待 |
| 数值参考/核对/count_visits | 资格或 phase 之外 | 不计正式性能，但计入 GPU-worker 总预算 |

每步候选新增 scheduler kernel、调度 D2H、sideband 为零。这里“零”只描述候选/用户增加的调度工作；不声称闭源库内部没有任何调度机制。Graph 节点实际计数见 derived/launch_ledger.json。

setup/reference/validation/pilot/Graph/Python 的总剩余墙时在 derived/cost_accounting.json；未分别测量真实部署的冷启动与初始化，不可把余数当成生产 startup cost。resident logical bytes 包含空 expert 权重，不等于实际 DRAM 访存量。编译时间单独保存在 build 日志，仍属于工作墙时。
