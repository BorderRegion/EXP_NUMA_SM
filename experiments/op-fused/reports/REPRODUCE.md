# 复核与复算

当前项目原始数据保留在本机 `op-fused/runs/`。本包带标量raw、源快照、有限trace、固定输入seed、协议和分析源码；不带实际tensor/库/权重。

在本机项目目录执行（解压包可将`op-fused/tools/`替换为包内`tools/`）：

```bash
python3 op-fused/tools/analyze_native.py
python3 op-fused/tools/analyze_strong.py
python3 op-fused/tools/audit_memory.py
python3 op-fused/tools/analyze_sensitivity.py
python3 op-fused/tools/derive_costs.py
python3 op-fused/tools/plot_native.py
python3 op-fused/tools/plot_thermal.py
python3 op-fused/tools/write_report.py
```

默认analyze_native使用已保存 thermal_controller_events.json，离线包可以直接复算；只有原机明确加 --refresh-controller-journal 才读取服务journal。不能用别的机器journal替换。包内phase_means.csv已带重建功耗标签，case_results.json已有功耗分层。

原始进程、顺序、重复数、输入seed、库选择、协议hash见manifest/phase记录。测量源变更只涉及记录、资源异常分类及正式前动态KV ring/重复数冻结；具体版本快照保留。未运行候选，不能用分析脚本生成候选效应。

再次做GPU实验须创建新的campaign/run命名；现有成功或失败块不可覆盖。没有下载/安装步骤。旧实验数据没有迁移进新矩阵。
