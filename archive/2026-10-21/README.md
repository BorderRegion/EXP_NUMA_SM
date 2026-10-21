# 2026-10-21增量归档：T10第26–28阶段与最终诊断

[新发布页](https://github.com/BorderRegion/EXP_NUMA_SM/releases/tag/records-2026-10-21) · [文件清单](INDEX.json) · [SHA256](SHA256SUMS) · [本地完整性校验](LOCAL_ASSETS_QA.json)

01–25阶段仍由[2026-10-18旧发布](https://github.com/BorderRegion/EXP_NUMA_SM/releases/tag/records-2026-10-18)保存，其49个资产和原始Git历史不覆盖。这里新增三阶段和一次CPU诊断；诊断没有新增GPU测量，不计第29阶段。RTX5080前史独立保留，只含报告和图。

|资产|内容|边界|
|---|---|---|
|T10_GPC_CONTENTION_GQA_REVIEW_20261019.zip|第26阶段完整本轮raw、源码、freeze、派生值、报告和关键二进制|历史第15阶段大raw仍在旧发布|
|T10_QUOTA_TAIL_CLOSURE_REVIEW_20261019.zip|第27阶段完整本轮raw及失败记录、源码、冻结规则、报告和关键二进制|不包含外部CUDA/PyTorch环境|
|T10_RESEARCH_FINAL_REVIEW_SMALL_20261021.zip|28阶段汇总、探索图、复核级别、结论与反例；第28阶段raw和CPU复算|23.4MiB，不含GPU二进制|
|T10_RESEARCH_FINAL_REPRODUCE_FULL_20261021.zip|小包内容加第28阶段及N19关键二进制|33.9MiB，历史大raw仍为引用，不是全历史离线独立复现包|

所有四个ZIP保持原交付字节，不重新命名旧结果。第28阶段的分享副本脱敏记录在包内index/SHARING_REDACTIONS.json；原实验文件未静默改写。Git中只复制适合浏览的原证据；每项是否随Git及hash见[GIT_EVIDENCE_EXPORT](GIT_EVIDENCE_EXPORT.json)。本轮新增的CPU诊断在[DIAGNOSIS.json](DIAGNOSIS.json)和[诊断说明](../../docs/T10_FINAL_DIAGNOSIS_20261021.md)。

## 下载与校验

```bash
gh release download records-2026-10-21 -R BorderRegion/EXP_NUMA_SM --dir /path/to/new-assets
python3 tools/verify_20261021.py --assets /path/to/new-assets
```

没有gh时也可在发布页手动下载。校验工具只验证资产大小、SHA256、ZIP CRC和逐文件manifest，不解压、不执行包内代码；文件匹配不等于物理解释成立。

解压相应ZIP到新目录后，各轮CPU入口为：

```bash
# 第26阶段，在该包根目录
python3 gpc-contention-gqa-t10/src/recompute.py gpc-contention-gqa-t10/runs/20261019T041515Z
# 第27阶段，在该包根目录
python3 quota-tail-closure-t10/src/recompute.py quota-tail-closure-t10/runs/20261019T064852Z
# 第28阶段，在包含T10_RESEARCH_FINAL的解压目录
python3 T10_RESEARCH_FINAL/last_run/final-gpc-capacity-t10/src/recompute_final.py
```

需要Python和NumPy，不启动CUDA。第28阶段小包已经在全新解压目录复算通过；旧阶段复核级别详见stage_catalog，不能把本轮CPU复算说成所有历史GPU重跑。GPU重测需要另建兼容环境、新run与资格确认，绝不能覆盖旧raw。

## 本轮收束与口径

三次管理锁频实际执行，状态资格未通过，按CONTROL_LIMITED完成48容量条件、四GQA锚六策略两块；完整固定状态、留出、增长和长程均NA。CAP对N19配对完整ready约慢2.0%–19.6%，GPU跨度也慢，未建立拓扑/地址调度的净增量。最初全N19窗口合并得到的9.8%–19.8%保留为辅助汇总，最终主值使用各自相邻ABBA/BAAB窗口。不得挑选两种口径中更好看的数值。

默认保留N19快核。100W和风扇/过温保护保留，动态时钟已恢复；GPU工作已结束。发布回执在上传核验后追加为PUBLICATION.json。
