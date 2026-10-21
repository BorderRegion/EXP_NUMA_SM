# RTX 5080 静态亲和特化：执行入口

这是新的研究授权，不是已完成的实现。主目标：**初始化／场景加载时标定实际访存亲和性并生成静态任务—数据—kernel 映射；稳态不做每帧 CPU 规划或全局任务打包。**

## 阅读顺序
1. `CODEX_MASTER_TASK.md`：范围、连续执行、自动分支、收尾。
2. `MEASUREMENT_AND_CONTROL.md`：如何获得真实的位置×数据矩阵，以及如何安全控制执行。
3. `STATIC_SPECIALIZATION_DESIGN.md`：静态计划、数据生命周期、四类主对照与应用接入。
4. `EXPERIMENTS_AND_STATISTICS.md`：完整矩阵、预算、正确性和统计。
5. `SOURCES_AND_NOVELTY.md`、`campaign.json`、`templates/`。

## 使用已有环境
复用已恢复的 Ubuntu / RTX 5080 / 本地 CUDA 与 Graphdeco headless adapter、Train/Bonsai/Truck 资产、日志工具。实际运行时只做增量核对，不回到缺 nvcc 的历史阶段。不调用远程 Git、不下载、不 SSH、不改驱动。不需要断开 Codex 客户端自身连接。

## CPU 辅助工具
在任务包根目录运行：
```sh
python tools/plancheck.py campaign.json
python -m unittest discover -s tests -v
```
这些命令只验证计划和有限辅助函数。它们不识别 GPU NUMA、不生成 CUDA kernel、不证明硬件安全或性能。不要把单元测试 PASS 当成 GPU 实验完成。

## 终点
连续完成所有有条件可执行阶段，最后一次性交付 `STATIC_AFFINITY_SPECIALIZATION_REPORT.md`。缺少亲和信号／控制时，按预先定义的缩减分支收尾，不改成另一种缓存研究、不反复询问是否“再试一次”。
