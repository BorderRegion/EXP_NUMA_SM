# 离线实验准备工具

只依赖 Python 标准库，不安装依赖，不联网；没有 GPU benchmark 或 renderer 实现。

`inventory.py` 只读主机和常规项目/工具目录，不申请显存、不启动kernel；
沙箱内可能看不到设备，不能把 CUDA_ERROR_NO_DEVICE 当主机没有GPU。
`--output` 文件必须不存在，raw不覆盖。正式操作若需沙箱外设备权限需按会话授权执行。

`analyze.py affinity INPUT.csv --output OUTPUT.json` 按地图身份分析同分配留出。
校验checksum/地址边界，按dispatch聚合，比较additive与经验交互，做固定置乱。
它不自动宣布物理NUMA，也不完成新地址、三进程复验、合法控制和E2门。

`analyze.py sessions INPUT.json --output OUTPUT.json` 在校准上选择最强基线，
每session采用全部measurement帧的算术均值，以process block做配对bootstrap，完整输出各基线及实测范围内生命周期。
统计汇总前仍需人工/实验runner检查输出资格、实际SM分配、计量范围和完整manifest。

`self_check.py --raw-dir DIR --derived-dir DIR` 生成完整SYNTHETIC样本并运行10项科学逻辑检查。
自检验证分析工具，对本机GPU和渲染收益没有证据效力。
直接命令示例（运行时替换RUN_ID，输出目录须新建）：

```bash
python3 tools/inventory.py --output results/raw/RUN_ID/environment.json
python3 tools/self_check.py --raw-dir results/raw/RUN_ID/cpu_sanity --derived-dir results/derived/RUN_ID/cpu_sanity
python3 tools/analyze.py affinity results/raw/RUN_ID/affinity.csv --output results/derived/RUN_ID/affinity_analysis.json
python3 tools/analyze.py sessions results/raw/RUN_ID/sessions.json --output results/derived/RUN_ID/sessions_analysis.json
```

先阅读 preregistration/PROTOCOL.md 与 RAW_SCHEMA.md。编译器和资产补齐前停止GPU分支。
CPU合成fixtures使用虚构SM编号和数值，仅为检验稀疏ID、无交互/有交互/地图失效等情况。
