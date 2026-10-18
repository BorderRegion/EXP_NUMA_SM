# 真实核低成本采样实验复现

先读 `reports/REPORT.md`、`reports/REVIEW_QUESTIONS.md` 与冻结 `freeze/PROTOCOL.json`。BASE54为用户指定的新基线，两个输入条件均采用上轮热输入约+0.68%的固定配置；FROZEN另保留上轮逐次重写输入的更强配置56。

完整包支持无GPU纯CPU复算，需要Python3、NumPy、pandas。Matplotlib只用于绘图，不是复算依赖。

```bash
cd topology-real-t10
OPENBLAS_NUM_THREADS=2 python3 src/recompute.py
```

复算会核验文件SHA256、冻结的原二进制与源码、STATIC开发选择、目标与影子校准的确定性决策、Graph顺序、数值检查记录、原始计时、遥测和全部派生统计；重算后比对并恢复原始字节和mtime，最后再次检查包内哈希。不导入Torch或启动GPU，不重选确认参数。小包不含原始数据和二进制，不能执行独立复算。

绘图入口 `python3 src/figures.py`；报告生成器 `src/report.py`。PDF/PNG渲染可能随绘图库版本变化，不作为原始性能证据。

GPU复现须另建目录和新run，保留本包只读。`src/campaign.py`是历史入口，会写freeze并要求worker目录不存在，不应直接在已完成run重跑。参考 `build/BUILD.json` 构建主机端C++采样器；没有新增GPU kernel，原 `softmax_const.so` 逐字节继承，源码在 `support/`。需要本地CUDA兼容驱动、CUDA12.x头文件、PyTorch CUDA以及适配本机的Python/工具路径；`common.py`中的绝对路径来自原环境，CPU复算不执行这些路径。

温控条件为100W、82°C停止阈值，保留风扇与过温保护。memcheck/synccheck是资格路径，racecheck仅定点1次原paired核launch，不代表整个长测逐次检查。正式长测计入每块更新、预热、同步、计时返回及候选实测准备；共同构图、输入分配、首次上下文/编译和研究文件I/O排除。固定输入重复调用不是完整LLM推理。

首次最终汇总在GPU全部完成后遇到NumPy布尔JSON序列化问题；原分析文件保持冻结，`src/analyze_repaired.py`只转换输出标量类型。复算入口自动使用该适配器，原失败日志与修复说明均保留。
