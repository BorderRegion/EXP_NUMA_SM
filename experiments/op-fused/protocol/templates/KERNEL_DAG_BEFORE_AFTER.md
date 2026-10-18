# 实际kernel与依赖（执行者填写）

| node_id | 实际符号/来源函数 | 功能 | 输入及其ready范围 | 输出owner | kernel/memset/copy | baseline/candidate | 计时窗口 |
|---|---|---|---|---|---|---|---|

## 新增工作如何承载
每项metadata说明局部还是全局；依赖在何处保证；若仍需要独立阶段，为什么不能合法融合及如何计费。

## 图捕获
capture发生几次，哪些参数每step更新，plan在何时失效；Graph节点总数不等于launch API调用数。

## Ledger证据等级
actual profiler / host API wrapper / source-only。未知项保留UNKNOWN，模板不是证据。
