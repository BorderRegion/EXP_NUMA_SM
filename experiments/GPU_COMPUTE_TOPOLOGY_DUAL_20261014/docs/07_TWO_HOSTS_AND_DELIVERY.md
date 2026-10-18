# 两台机器的独立执行与最终合并

## A. 同一个包，两份平台档案

- T10 与 RTX 5070 Ti 各自拥有独立的 `build`、`environment`、`plan` 和 `runs` 目录。
- 两边使用相同的协议修订版本（protocol revision）和相同的方法源码。
- T10 不支持的功能，**不**用模拟层补齐，直接记为 `NA`。
- `platform=t10` 与 `platform=rtx5070ti` 只是计划标签。如果实际 GPU 查询结果与标签不符，要在 CPU 报告中写明，**不能冒充硬件**。
- 先在本机填写 LOCAL_PATHS（由模板 `config/LOCAL_PATHS.template.json` 复制并填写）。**不要复制另一台机器的绝对路径。**
- 已有的资产和工具由用户离线搬运。Codex 不使用 SSH、SCP，也不发起网络请求。
- 两台机器可以同时开工，互不依赖对方在线。

## B. 每个平台的机器可读摘要

`platform_summary.json` 至少包含以下字段：

`platform`、`device identity`、`protocol_hash`、`method_source_hash`、`inputs_manifest_hash`、`build recipe`、`available_paths`、`missing_cells`、`primary comparisons`、`scope`、`worker_seconds`、`actual_cost`、`cost_unit`。

- 每一个比较（comparison）都保留本机的配对过程。GPU 型号之间的差异，不能被一个总的几何平均数掩盖。
- 两张卡的 native 输出不要求逐位相同。正确性只在每张卡内部检查，即同一 body 下的基线与候选之间。
- 架构或编译配方的差异，不能作为 floorsweeping 的唯一因果解释。
- 如果同型号 GPU 只有一张，明确写 `n_device=1`。
- T10 与 RTX 5070 Ti **不是**“只有屏蔽单元不同”的随机实验。
- RTX 5080 的历史结果只在背景段引用，不能与新输入、新驱动下的结果直接比较。

## C. 合并工具

把两个 `platform_summary.json` 放到同一台 CPU 主机后，运行：

```
python tools/merge_platforms.py --inputs t10_summary.json rtx5070ti_summary.json --out combined_review.json
```

工具会检查 profile、协议 hash 和方法源码 hash，只组合摘要，并列出兼容性检查结果。

- 不会自动平均不同设备的原始耗时。
- “兼容”只表示字段核对通过，**不表示输入相同**。
- 缺少任一输入的 hash 时，结果为 `UNKNOWN`，**不能**默认为 True。

## D. 主报告开头必须回答的十二个问题

1. 两张卡的真实资源是什么？哪些来自规格，哪些来自实测？
2. RTX 5070 Ti 有哪些计算与 cluster 方面的不均衡？T10 上哪些部分可以直接比较？
3. 现有的原生调度，是否已经处理了这些不均衡？
4. 在 SM 数相同、逻辑任务相同的条件下，实际可控组之间的差异有多大？
5. 候选方法是否胜过了 Native 与单速率强基线？
6. 如果它只胜过人工等分，这是机制结果，还是可部署的收益？
7. 不同的 kernel 类型与并发度，是否会改变有效容量？
8. 静态计划的稳态成本、启动回本与生命周期成本分别是多少？
9. 两个场景，还是两个独立程序？哪些真实范围没有做？
10. 相对原论文的静态调度与普通加权均衡，本方法新增了什么能力？
11. 哪些是弱的正效应，哪些是可靠的，哪些只因样本不足？
12. 是否值得写完整论文？需要补的是方法、真实程序，还是第二块器件实例？

## E. 验收，而不是无限继续

- 只把最终平台报告和双平台汇总返回给用户。普通的中间检查由本机自动处理，不逐项请示。
- 科学上的负结果，只要完成了报告，也是有效交付。
  - 不能仅因为效应低于约 3–5% 的参考值，就把全部结果判为负。
  - 也不能因为出现一个显著的 p 值，就认定可以发表。
- 不要自动追加第三张卡、新算法、新的驱动版本，或更换研究题目。
