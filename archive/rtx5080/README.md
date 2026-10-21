# RTX 5080 四轮实验的代码与原始数据

2026-10-21 补传本机 `/home/ws/文档/ChatGPT/EXP_NUMA` 中的 2026-10-13 实验记录。此前仓库只有四份报告与配图；这次补充原始代码、冻结件、日志、派生结果和原始采样/渲染输出。实验结论与统计口径保持不变，没有新增 GPU 实验。

[四轮导读](../../docs/RTX5080_STAGE.md) · [Git 证据目录](../../experiments/rtx5080-20261013/) · [Release](https://github.com/BorderRegion/EXP_NUMA_SM/releases/tag/records-2026-10-13) · [逐文件索引](INDEX.json) · [SHA256SUMS](SHA256SUMS)

## 保存范围

- 五个当时生成的交付原包，保持原始压缩包字节，合计 664,142,323 字节。
- 一个本次生成的补充归档，保存现存项目中未被五个原包覆盖的 457 个文件、5,380,190,139 字节，包括此前只有哈希清单的 R2 渲染输出、早期恢复/失败/重试记录与构建产物。相同内容不重复加入补充归档；历史原包之间的重复保留。
- 合计 **2,111 个归档文件条目**、**7,427,452,550 原始字节**，压缩后 **4,652,125,443 字节**（约 4.33 GiB）。条目数包含历史重复副本，不是独立实验样本量。
- Git 浏览视图保留 **1,862 个证据文件**、121,014,241 字节；原包中的大型 R3 `.bin`/`.npz`、补充包中的大型输出和二进制留在 Release。每个 Git 证据文件均记录与原包/原件一致的 SHA256。

外部依赖没有随本次发布打包：`offline_inbox/` 的 CUDA 工具链、原始 renderer checkout 和 Train/Bonsai 场景资产，以及 `.analysis_libs/` 绘图库。获取来源、版本和环境记录保留在实验的 `recovery/`、`reports/`、`build/` 和配置中。原项目 `.git`、解释器缓存、符号链接及重复的本地交付解压目录也不进入补充包。完整排除项见 [INDEX.json](INDEX.json)；这不是整机环境镜像。

第三方源码保留原始许可证；例如 Graphdeco 核心文件附 `src/core/LICENSE.md`。本次归档没有重新授权第三方内容。

## 下载与验证

在仓库根目录执行：

```bash
python3 tools/download_archives.py --dest /path/to/rtx5080-assets --index archive/rtx5080/INDEX.json
python3 tools/verify_rtx5080_release.py --assets /path/to/rtx5080-assets
```

只验证 Git 里的证据副本：

```bash
python3 tools/verify_rtx5080_release.py --git-only
```

下载脚本会校验每个原包或分片的大小和 SHA256；验证脚本还会读取 ZIP/TAR 中每个普通文件，与 `archive/manifests/rtx5080-*.jsonl` 的哈希和大小比较。校验只读文件，不执行历史脚本。

只取一包时，两条命令均可加 `--only STATIC_AFFINITY_5080_COMPLETED_20261013.zip`。补充包的逻辑名字是 `RTX5080_LOCAL_SUPPLEMENT_20261021.tar.zst`，下载器会取齐四个分片。

## 恢复目录

先校验，再把各个原包解压到**不同的新目录**，保留 R2 早期版本与最终版本之间的差异。ZIP 内自带实验目录；R1 的 TAR 内以 `EXP_NUMA/` 为根。

补充包需要 Python 3.9+、Linux/WSL 与 `zstd`/`tar`。分片顺序如下：

```bash
cat /path/to/rtx5080-assets/RTX5080_LOCAL_SUPPLEMENT_20261021.tar.zst.part00{1,2,3,4} > /path/to/RTX5080_LOCAL_SUPPLEMENT_20261021.tar.zst
mkdir /path/to/new-supplement-directory
zstd -dc /path/to/RTX5080_LOCAL_SUPPLEMENT_20261021.tar.zst | tar -xf - -C /path/to/new-supplement-directory
```

补充包以 `EXP_NUMA/` 为根，只有五个原包未覆盖或内容不同的现存文件，需要与相应原包一起阅读。保留不同版本目录后再按需组合复算副本，不覆盖历史原件。历史分析脚本含本机绝对路径，CPU 复算前需要在副本中调整；重新测 GPU 属于新实验。

## 六个逻辑归档

| 归档 | 文件条目 | 原始字节 | 压缩字节 | 清单 |
|---|---:|---:|---:|---|
| `CAMPAIGN_PACKAGE_affinity_20261013T064931Z_b2cdc88d.tar.gz` | 50 | 4,230,820 | 187,962 | [JSONL](../../archive/manifests/rtx5080-render-opportunity.jsonl) |
| `RTX5080_V2_LOCAL_REPORT_v2_20261013T072225Z.zip` | 59 | 179,774 | 94,514 | [JSONL](../../archive/manifests/rtx5080-render-scheduling-v2.jsonl) |
| `RTX5080_COMPLETED_resumed_20261013T0930Z.zip` | 523 | 14,051,227 | 4,290,772 | [JSONL](../../archive/manifests/rtx5080-render-scheduling.jsonl) |
| `STATIC_AFFINITY_5080_COMPLETED_20261013.zip` | 295 | 1,955,883,539 | 641,988,135 | [JSONL](../../archive/manifests/rtx5080-static-affinity.jsonl) |
| `STATIC_AFFINITY_CAUSAL_COMPLETION_20261013.zip` | 727 | 72,917,051 | 17,580,940 | [JSONL](../../archive/manifests/rtx5080-static-affinity-causal.jsonl) |
| `RTX5080_LOCAL_SUPPLEMENT_20261021.tar.zst` | 457 | 5,380,190,139 | 3,987,983,120 | [JSONL](../../archive/manifests/rtx5080-local-supplement.jsonl) |

补充归档分为四片，每片不超过 1 GiB；五个原包不重新压缩。发布完成后的远端大小、SHA256 和提交对应关系见 `PUBLICATION.json`。
