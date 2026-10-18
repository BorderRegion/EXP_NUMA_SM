# T10 → 5070 Ti 补充交接

本文件只交接 T10 上已经执行的协议和可复用实现，不访问另一台主机，不合并两卡原始毫秒数。T10 补充实测结论与状态见 `T10_SUPPLEMENT_AND_PAPER_POSITION.md` 和 `T10_SUPPLEMENT.json`。

T10结果摘要：顺序平衡后W1 M/N=1.1033、M/R=1.0012，旧容量结论保持。初始地址相关混入固定CTA顺序；修正后只有2个确认分配，未建立稳定组×区域关系。2MiB顺序访问的A在同执行器内优于I/P，但A/N=1.1316，未产生部署净收益。S4未触发。不能将这些比例或经验表外推到目标设备。

## 可复用内容

- `src/supplement/renderer_runner.cpp`、`sparse_runner.cpp`：同数值体 E_FULL、N_head/尾锚、独立 phase 记录、固定 conditioning。旧 M/R 保持冻结。renderer 的 CUDA 数值体仍来自原锁定版本。
- `address_kernels.cu` 与 `address_common.hpp`：有限依赖链、分段状态延续、同一数据跨位置观测、完整集合吞吐、部署表与独立位置/恰好一次资格。没有 SM 自旋绑定、原子抢任务或新的永久驻留 runtime。
- `address_probe_runner.cpp` / `address_deploy_runner.cpp`：同地址组间交换、组主效应/区域主效应/交互分开、盲表/匹配表/两置乱表、完整 CPU-ready 计时和初始化成本。
- `preregistration/supplement/ADDRESS_PROTOCOL.md`：开发/确认分离、六独立分配、有限规模、条件式渲染验证规则。
- `tools/analyze_*supplement.py`、`analyze_address_probe.py`：以进程块为单位的配对 bootstrap；缺格保留，不将帧或 SM 样本冒充独立器件重复。

## 必须在目标设备重新确定

读取实际 SM/L2、共享内存、compute capability、Green 支持和可创建资源组。现有 runner 明确包含 T10 资格断言，不能原样把断言改成“永远通过”。需要将目标实测设备合同写入新的协议与 build，而不是复制 T10 的常量、SM ID 列表、ownership 表、虚拟区域 home 或延迟数字。目标 CUDA 编译和驱动功能必须以本机可用路线验证；T10 sm_75 cubin 不是目标设备的编译交付。

本轮两个组等大，因此 P0 可直接交换；目标组不等大时应预先设计合法、同配额的匹配控制，不能照搬 T10 图。若目标有 cluster/DSM，属于其独立主任务，不能把 T10 的“不支持”或地址结果当作替代实测。

3% 是 T10 这次有限补充的投入门槛，不是普遍硬件定律、统计显著性阈值或论文标准；目标设备须预注册自己的选择、预算与进入条件。经验相关不等于物理 GPC/显存域识别。

## 不应重犯的解释错误

原 K2 是循环 gather 容量工作，不能作为超 L2 依赖型延迟证据；分配字节与实际消费集合分列。类吞吐可能混入任务组成，必须交叉同一 task/address。N 始终首位会限制因果解释；首尾锚与顺序平衡仍不能保证消除非线性漂移。cuSPARSE 与自写行核的差距不能全算调度效果，保留生产 N 并加同 body/同粒度 E。

不要把 Green 组称物理 NUMA 节点；不要跨 SM 相减 clock；不要把 max(group event)称完整 makespan；不要把 `.cg`、超过 L2 或 scratch 遍历当作已测的 DRAM 命中证据。真正部署价值必须在同信息简单参考和同机制置乱控制之外成立，再考虑适配真实渲染任务。
