# 04 必要信息整理：交接后能找得到、读得懂、复算得了

本轮无论性能正负都必须交付本节。不要再复制一堆不同名字的“最终版”；历史原件只读，新增一个总入口。不要按旧ordinal猜阶段：使用稳定的stage_uid（原目录+run_id），原01–25等编号作为显示字段，后续轮次继续纳入。

## 输出目录

```text
T10_RESEARCH_FINAL/
  README.md                          # 先读这一份：结论、默认入口、状态、怎么检索
  FINAL_RESEARCH_REPORT.md            # 最终机制/部署/论文判断，历史与新结果分开
  MENTOR_UPDATE.md                    # 约400–700汉字，不夸大、不掩盖反例
  index/
    stage_catalog.jsonl              # 每阶段一行
    claims_and_evidence.jsonl         # 每项结论一行，精确来源与证据层级
    artifact_manifest.jsonl           # 本地可访问位置、哈希、大小、是否随包
    baseline_lineage.json             # N19/E56/CAP等源与二进制的继承链
    unresolved_questions.md           # 已答/仍未知/没做，避免下一位再走25轮
  reusable/
    FAST_GQA.md                      # 真正可调用入口、环境、数值/布局/并发合同
    TOPOLOGY_READER.md                # 只读、driver ABI、快照有效期
    MEASUREMENT.md                    # 协议、clock权限、计时范围、原值口径
    deprecated_paths.md              # 旧搜索/选择器不再默认启用
    source_snapshot/                 # 只装实际需要的自有源、patch、构建/资格命令
  last_run/                          # 本轮全部freeze/derived/reports及必要raw
  sources/                           # 阶段报告与来源索引，不塞重复模型/vendor
  archive_checks.json
```

## 每阶段必须整理的字段

stage_uid、原编号、日期与时区、run_id、目的/假设、执行状态、硬件/driver/state、工作负载真实性、实现入口、数学体/launcher hash、基线、主要指标定义、原始路径、可复算范围、结论、反例、未完成项、下一阶段如何使用了它。

特别增加`verification_level`：`REPORT_ONLY`/`AGGREGATES_RECOMPUTED`/`RAW_RECOMPUTED`/`GPU_RERUN`。哈希通过不是数值和物理解释通过。旧小包缺tensor/raw时不写“全部已验证”。

claim记录：claim_id、statement、status（支持/限制/未知/被更强基线解释）、scope、source_file与段落/行、raw_run、metric_definition、comparison、absolute_values、uncertainty、counterevidence、not_implied。

以下五项必须有单独claim：
1. 当前实读非均匀GPC配置；
2. 特定地址构造下GPC相关偏好；
3. 16B GQA工程加速与专用decode基线缺口；
4. Softmax/当前静态共置的收束边界；
5. 固定状态和本轮容量/CAP是否带来新证据。

不得把同一批数据的主报告、审计和汇报草稿当作三项独立证据。旧正数与新强基线下消失的正数都保留；`同参数alias`、`强制split`、合成输入、确认后接口默认选择等限制也要可检索。

## 资产整理的具体工作

- 选出唯一推荐的快GQA调用入口；保留N19/E56基线。未获稳健净增量不把CAP设成默认。
- 固定源码、编译命令、include/lib路径说明、编译器版本、当前可执行文件hash；绝不只给`.so`不留source。
- 并发workspace、私有末页/COW、alignment、page capacity、length更新、capture支持、错误/unsupported shape行为写清。
- 把历史风险路由、阈值搜索、NUMA命名与默认生产入口拆开；旧模块只读留存，不批量删源码/数据。
- 只对关键报告、freeze、使用过的源码/二进制和新raw做完整hash；旧大raw可复用旧manifest并抽验，记录INHERITED而非声称重验。
- 不压缩模型权重、不重复复制整个CUDA/CUTLASS，不下载缺失的15GB归档。旧文件确实找不到就标missing。
- 私密信息、token、账号路径里不必要个人信息与凭证不得打入共享包；原本地原件不做静默修改。机器UUID可按报告需求保留或在分享副本脱敏并记录。

## 两个交付包

1. **REVIEW_SMALL.zip**：全部报告、stage/claim索引、所有主比较逐块绝对值、全部条件NA/alias、冻结计划、实际修改source、CPU复算入口、代表请求、环境恢复证明。目标≤100MiB；超限先去图重复和非必要sample，不删主比较原值。
2. **REPRODUCE_FULL**：本轮raw/代码/关键二进制及历史raw引用清单。本地可做分卷；原有历史档案不再复制多份。若只提供引用，要明确它不是可离线独立复现包，不能把绝对路径当成已打包文件。

仅本地归档；不自动推送GitHub/Drive或上传云盘。恢复/复制/压缩前检查磁盘；不删除唯一原始文件，临时重复件只在核验可恢复后处理。ZIP最后做CRC与manifest存在性检查。

## 最终报告必须直接回答

这次修正了哪些原设计错误？有效容量是否真的与SM数不成比例？实际kernel是否利用它？若未加速，瓶颈/表示粒度/launch成本/原生动态均衡/状态限制分别有哪些证据？哪些事情尚未测，不能靠推理补全？

论文状态只能是：已有工程资产；单设备机制表征；有限的同体增量；已过强基线的部署增量；或条件不足。按事实选择，不承诺录用，不把“最后一轮”变成“最后必须有正数”。
