# Packet 适用域：实际数学主体尚不可用

当前不能填写实际 tile、worker、q 或尾包数据。`packet_applicability.json` 保留全部 24 个原 grouped 开发点，每点均标记 `NA_NO_QUALIFIED_BODY`；没有把假设的 BM32/64、W56/112 冒充本机实际配置。

旧 work-budget 规则不变，没有 amendment，也没有候选调参或候选计时。此前 BK32、budget128 的设计计算说明 K4096 时 q≤1，仍只能作为旧假设的结构性结论。

原计划的 24 个 grouped 开发点只含 K1024 和 K2048，各 12 个；全部 32 个 K4096 点属于 test。脚本不会为了补充开发域而把这些已阅测试点重新标作开发。后续开发 q1 负控制须来自原开发域中实际可达的容量/包长约束，不能声称已在开发点验证 K4096。

新 CPU 接口支持从实际 backend 配置解码 packet，明确区分 FULL、普通固定 q CACHE 与 q1 消融。CORE/BAL 必须来自真实后端，因此未伪造 native 顺序。515 个有限逻辑样例中有 170 个出现多 tile 包；这是合成 CPU 测试覆盖，**不是正式开发点在 GPU 上实现了 q>1**。

q=1 顺序仍可能不同。例如一个 2×2 tile 网格，本接口按 `(m,n)=(0,0),(1,0),(0,1),(1,1)` 遍历。必须拿实际 native visitor 对比，才能判定 identity；不能仅由 q=1 得出结论。

资源到位且主体合格后，保存 backend evidence JSON：`tile_m/tile_n/tile_k/active_workers/backend_commit/worker_evidence_path/mma_evidence_path/numerical_qualification_path`。证据路径指向真实资格产物。然后运行：

```bash
python3 op-fused/recovery_20261015/tools/packet_applicability.py \
  --backend-evidence /absolute/path/to/qualified_backend.json \
  --out /absolute/path/to/new_packet_applicability.json
```

脚本只读取原 24 个开发点，以非空 problem 的 K-tile 第 75 百分位上取整再乘 2 得到原预算；对 qcap1/2/4、waves1/2 共 6 设置生成总 tile、各专家 q、packet 数和短尾包数。第二种真实 tile 配方若使用，总设置仍不超过 12。证据文件存在是输入检查，不等于脚本独立认证其内容。

未预建任何用于动态生产请求的 O(tile) 任务表。CPU 枚举仅作测试 oracle；实际 GPU 代的 metadata 就绪、stream 依赖、合法 producer 和 native warp search 仍待主体接入后实现。
