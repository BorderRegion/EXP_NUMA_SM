# 实现层级与kernel融合合同（本轮最高优先级）

## 1. 先画真实生产DAG，而不是先写一串小kernel
每个实际入口生成 `KERNEL_DAG_BEFORE_AFTER.md`：每节点实际kernel符号/作用、读写buffer、数据就绪范围、前后依赖、是否可Graph capture。
必须包含真实baseline已有的count/scan/packing/reset/activation/merge，不能只列两个大GEMM。

MoE参考形态（不是规定所有backend都必须如此）：
```
router / top-k
 -> count / prefix / token pack
 -> grouped gate+up GEMM
 -> SwiGLU (可能已经在epilogue)
 -> grouped down GEMM
 -> weighted unpermute / combine / residual
```
Attention参考形态：
```
QKV / RoPE / KV append 或已有输入
 -> 已有plan/segment元数据更新
 -> attention work + 必要partial merge
 -> 输出交付/后续投影
```
主方法不得把上述节点再拆细，也不得为每个专家、head、tile额外launch。

## 2. 允许的落点与前提
| 新工作 | 优先落点 | 必须满足 |
|---|---|---|
| tile/problem选择 | 已有GEMM/attention visitor | 当前descriptor可用，完整tile恰好一次 |
| per-expert tile数、局部类别 | 已有count/scan/pack尾部 | 此字段依赖的计数在本阶段确已完成 |
| 全局packet前缀 | 已有全局prefix阶段或native device-only visitor | 不从未完成的其他CTA读取计数 |
| 已有bias/激活/局部门控 | GEMM epilogue | 当前CTA/warp拥有所需全部元素，执行次数正确 |
| QKV局部布局/位置变换 | 已有投影epilogue/KV append | 不改变kv生命周期、索引与下游可见性 |
| 简单输出索引/写回 | 现有最终store/combine | 无跨token无序竞争，gating累加顺序保持 |

**不能把全局工作当局部epilogue。** 例如两路gate/up列在不同CTA，不能读取另一CTA尚未写出的部分；需采用原本支持的配对输出tile布局或保留已有SwiGLU核。整行router top-k/归一化若不在一个CTA拥有的范围内，不能生搬到GEMM epilogue。
两个GEMM之间若存在全局或跨CTA依赖，保留合法边界，不用自旋等待全设备、最后CTA计数协议或长寿命megakernel强行融合。本轮不是全图megakernel研究。

## 3. 主生产路径的零新增调度launch
定义 `delta_scheduler_launches` 相对**同算法、同数学主体、同已有融合**的基线计算，不能只对比一个故意碎片化版本。
主候选要求：
- 新增独立调度kernel = 0；
- 新增调度D2H = 0；
- 每个expert独立CPU发射 = 0（真正grouped后端内核）；
- 新增每算子host完成等待 = 0；
- 每步JIT = 0（只允许首次specialization缓存）。
已有的必要数学/算法节点可以不为零。一个Graph含5个kernel仍然是5个kernel，不可写成“一次kernel”。

开发期独立planner允许短期调试，但只作 `UNFUSED_DIAGNOSTIC`，不进入主性能结论。E2结束前：
A. 移入合法producer/native visitor；或
B. 改为无物化的device-only映射；或
C. 坦诚 `FUSION_INTEGRATION_INCOMPLETE`，只交原型界限，不用它的负收益裁决思想。
不要为了0 launch把O(experts×tiles)计算塞进每个CTA，或在producer重复全局scan。新增指令和读取同样要计费。

## 4. Counter与reset：最常见的隐藏小kernel
现有动态scheduler若需要counter清零，必须遵守原实现。
- 可将本方法新增counter reset并入原本需要的producer/init节点，且consumer之前有kernel依赖。
- 不能在consumer中由block0先清零、其他block同时atomicAdd；没有合法全grid顺序保证。
- standalone kernel测试没有真实producer时，优先native静态visitor；使用异步memset则明确计入总调用/重放成本，不能移出测量后冒充部署路径。
- Graph中的memset node、device metadata update和replay更新也记在账本，不能只计kernel node。

## 5. 允许与不允许的融合差异
F0 = 本地最佳可用后端已支持的融合；F1 = F0 + 本轮新增的一个合法sideband/epilogue改动。
若F0已做同样工作，F1此项标IDENTICAL，不重复算新贡献。
本轮最多2处融合：
1. 动态任务metadata的合法生产点（优先）；
2. 一处局部activation/写回（确实未已有时）。
不因收益不够继续融合整个Transformer，不改attention算法、不变路由。

## 6. 同融合、同Graph强对照
生产主模式为预先可支持的CUDA Graph replay；不能只有candidate用Graph。
不支持Graph的组合，所有方法用同一异步提交配方，并标出来。主模型动态输入不能依赖每请求capture。
另做小型 eager/Graph 2×2诊断以分离CPU launch收益与内核效果，不把Graph收益当scheduler贡献。

Graph静态元数据只能用于真实不变的shape；动态route/seq_len变化必须更新设备输入/metadata，update/plan/copy计入完整窗口。记录plan generation与哪一步变化导致失效，不拿预录未来计划当动态部署。
共享Graph内存池按本机官方使用前提：输出活跃期、回放顺序、非并发条件；不要因为同一stream就默认任意图顺序安全。

## 7. 四级计时终点
1. `OP_RESIDENT`：输入/descriptor已经就绪的纯算子。单列，不作为完整层。
2. `PRODUCER_CONSUMER`：从生成当前动态descriptor的必要producer之前，到consumer输出就绪。
3. `LAYER_POST_ROUTE`或`LAYER_WITH_ROUTER`：显式写明入口。包含layout/pack/scan、GEMM、activation、merge和结果写回。
4. `MODEL_REQUEST`：包含模型实际请求路径的必要host/GPU工作，不含离线profile与论文hash；报是否tokenization、网络/排队纳入。

M在OP_RESIDENT快而PRODUCER_CONSUMER慢，结论是未部署回本；反之fusion更快但same-fusion下M无增量，结论是融合工程收益。

## 8. 简洁验收，不新建大型监控框架
优先使用现成 Nsight Systems / CUPTI / 后端profile的代表性trace核对符号与节点。工具不可用就使用统一host launch wrapper记录，标为HOST/API证据而非硬件动态计数。
每个版本只保存一份DAG、12个代表case以内的trace、简短节点账本。正式计时不要逐launch同步或落盘。`tools/reference.py`中的台账函数只是加减已输入统计，不能代替实际采集。
