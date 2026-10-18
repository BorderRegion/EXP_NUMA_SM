# 本次归档的构建过程

这里是创建这次快照、内容扫描与校验汇总的原脚本，保留当时主机路径，便于审阅保存规则。它们不是跨机器一键安装器，也不运行GPU实验。恢复现有档案请使用仓库根目录tools/download_archives.py和tools/verify_archive.py。

步骤：只读清点与SHA256 → 分目录tar.zst → 完整成员验证 → 有日志的分片及拼接哈希验证 → 原Git bundle独立克隆/fsck → 全部发布资产再次哈希 → 文档/源码副本QA → BorderRegion提交与发布。原项目、暂存区和旧ZIP未被覆盖。
