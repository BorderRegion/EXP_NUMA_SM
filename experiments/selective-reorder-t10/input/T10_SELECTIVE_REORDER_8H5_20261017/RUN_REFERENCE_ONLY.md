# CPU参考工具

本目录工具不是GPU runner，不会运行T10实验。

```bash
python tools/validate_package.py
python -m unittest discover -s tests -v
python reference/train_rules.py /path/to/development_rows.jsonl /path/to/fitted_cpu_model
```

训练行必须来自本轮开发数据，字段：
`cohort="development"`, `case_id`, `action`, `cpu_ready_us`, `shape_features`, `resource_features`。
`shape_features`为文档规定的11个字段，`resource_features`为4项冻结卡特征。资源卡在同一签名的重复数据间必须相同；不能将当次正式计时反过来塞入feature。

脚本按整个shape做LOSO，不将同shape不同seed当新shape；基础动作在SHAPE和RESOURCE模型中完全共享。输出CPP只是宿主直线预测函数，不含GPU调度/物理绑定，不是完整的部署选择器。

部署需先调用 `choose_base` 并计基础实现准备成本，再调用 `choose_plan(frozen_base_action=...)`；最终把动作绑定到已验证的本地Plan接口。`choose_plan`未指定base时的argmin仅供离线数学分析，不是免初始化成本的生产默认。

`binding_skeleton.hpp`只演示原生直达的所有权分流；需要接入本地backend并验证真实Graph节点、资源和调用成本。测试中的mock成功不证明GPU编译/内核/驱动正确。
