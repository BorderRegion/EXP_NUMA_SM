# T10 / RTX 5070 Ti 双平台 GPU 计算拓扑实验

版本：2026-10-14 v1.0
状态：**设计与 CPU 辅助工具已交付；GPU 实验尚未执行。**

## 1. 研究要回答什么
研究终点是一条完整的证据链：

真实可用资源 → 按 kernel 类型区分的有效执行容量 → 可控的静态配置与任务分配 → 相对原生和强简单基线的净收益 → 跨程序与跨平台的适用边界。

主线是计算侧的 floorsweeping、cluster 与资源分区。内存 NUMA 只是独立支线，不是继续计算实验的前提。

## 2. 怎么使用这个包
- 把同一个完整包分别放到 T10 主机和 RTX 5070 Ti 主机。
- 两台机器上的 Codex 互不连接：不 SSH、不主动联网、不等待对方完成。
- 每台机器各自生成带平台和设备标识的结果包，由用户搬运到任意 CPU 主机合并。

## 3. 阅读顺序
1. `CODEX_MASTER_TASK.md`：任务书，说明要做什么、怎样算完成。
2. `docs/00_GLOSSARY.md`：术语、代码、固定数字。遇到不熟悉的词先查这里。
3. `docs/01_PLATFORMS_AND_SOURCES.md` 与 `docs/02_TOPOLOGY_AND_CAPACITY.md`：平台事实与拓扑测量方法。
4. `docs/03` 方法与基线；`docs/04` 工作负载与正确性；`docs/05` 实验矩阵与统计；`docs/06` 记录与恢复；`docs/07` 双机与交付；`docs/08` 设计约束。
5. 复制 `config/LOCAL_PATHS.template.json` 为本机副本并填写。本包不会自动下载任何东西。

## 4. CPU 部分的命令（任何机器都可运行，不执行 GPU）
- `python -m unittest discover -s tests -v`：验证本包的 CPU 工具，应为 48 个测试全部通过。
- `python tools/validate_plan.py`：检查计划矩阵与 `campaign.json` 是否一致。
- `python tools/plan.py --platform rtx5070ti --out <本机目录>/planned_sessions.json`，或 `--platform t10`：只生成计划，不执行。

## 5. GPU 部分
包内没有完整的调度器或 runner。Codex 需要在本机构建或复用 CUDA runner，然后按 E0–E6 顺序执行。
最终交付 `DUAL_TOPOLOGY_PAPER_REPORT_<platform>.md`，结构见 `templates/PLATFORM_REPORT.md`。

## 6. 五个必须记住的区别
1. RTX 5070 Ti 的公开总量规格支持“裁剪”这个研究动机。但它不提供实卡的 SM→GPC 图，也不保证有收益。
2. T10 是 Turing 平台，不是“无裁剪、无 NUMA”的已知负对照。
3. 相同的 SM 数量可以有不同的 cluster 合法性；相同的 GPC 数量也不代表吞吐相同。
4. 只有超过全卡原生执行的增量，才能支持部署收益。人工切分后再修复，只能算机制结果。
5. 不做逐帧 CPU 打包，不为题目硬加 block cluster，不强制一个 SM 对应一个 block。

## 7. 包含与不包含
- 包含：任务书、完整实验与证据协议、两份平台说明、日志模板、CPU 计划/统计/任务分配工具、只读 CUDA 盘点与 cluster 拓扑探针源码。
- 不包含：驱动、SDK、模型或场景数据、外部论文全文、完整 GPU 实现、任何性能数据。
- CUDA starter 没有在本交付环境中编译或运行，见 `starter_cuda/README.md`。

## 8. 当前状态
- 已完成：设计文档、CPU 工具与 48 个单元测试、计划校验（`validation/plan_check.json`）。
- 未完成：全部 GPU 实验。本包不含任何 GPU 结果。
- 已核对项与未验证项见 `validation/DESIGN_REVIEW.md`。
