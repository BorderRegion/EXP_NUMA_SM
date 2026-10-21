# 历史原件可用性

继承36份旧manifest；逐条检查132039项本地引用存在，471项外部交接路径未擅自重定位。存在性计数可含不同manifest重复引用，不是独立实验数。

1项缺失为 `numa_gpu/vendor/thrust/cub`（旧vendor引用）；没有下载或伪造补齐。逐条状态在historical_raw_availability.jsonl的exists字段。60个确定性抽验文件hash全部匹配；并非132039项全部重新hash或数值复核。关键旧报告/源码/二进制另见artifact_manifest的HASHED_NOW记录。

旧阶段19的原CPU复算得到三份完全一致的派生JSON；22重算RM映射；26重算派生CSV的GPC块均值。其余本轮仅复核报告/引用，不写成GPU重跑。
