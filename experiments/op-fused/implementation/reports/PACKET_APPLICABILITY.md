# Packet 适用域：实测资源和原规则

所有数字来自实际 adapter 的资源元数据与 GPU 已执行 shape。CPU 重建逐条校验 raw 中 packet 数与长度分布，未改变原 work_budget=128。

| recipe | block tile | threads | CORE/CACHE/FULL registers | shared bytes | 公共 worker 容量 |
|---|---|---:|---|---:|---:|
| 0 | 32×128×32 | 64 | 192/194/198 | 20496 | 168 |
| 1 | 64×128×32 | 128 | 174/176/180 | 24592 | 112 |

实际 worker=min(输出 tiles, 上表容量)，至少 1；无 SM 绑定。q=1 在 Mtiles>1 且 Ntiles>1 时也可改变 native 顺序。32 个原 K=4096 grouped 计划因 Ktiles=128，预算项限制 q<=1；它们是多 tile 复用负控制。

| 开发 case | recipe | tiles | workers | qcap4/w1 的 q | packets | 尾包 | q>1 tiles |
|---|---:|---:|---:|---|---:|---:|---:|
| grouped-042 | 0 | 288 | 168 | [1] | 288 | 0 | 0 |
| grouped-042 | 1 | 256 | 112 | [1] | 256 | 0 | 0 |
| grouped-017 | 0 | 256 | 168 | [1] | 256 | 0 | 0 |
| grouped-017 | 1 | 128 | 112 | [1] | 128 | 0 | 0 |
| grouped-006 | 0 | 288 | 168 | [1] | 288 | 0 | 0 |
| grouped-006 | 1 | 288 | 112 | [1] | 288 | 0 | 0 |
| grouped-053 | 0 | 1024 | 168 | [1] | 1024 | 0 | 0 |
| grouped-053 | 1 | 1024 | 112 | [1] | 1024 | 0 | 0 |
| grouped-045 | 0 | 1024 | 168 | [1] | 1024 | 0 | 0 |
| grouped-045 | 1 | 1024 | 112 | [1] | 1024 | 0 | 0 |
| grouped-010 | 0 | 144 | 144 | [1] | 144 | 0 | 0 |
| grouped-010 | 1 | 128 | 112 | [1] | 128 | 0 | 0 |
| grouped-002 | 0 | 128 | 128 | [1] | 128 | 0 | 0 |
| grouped-002 | 1 | 128 | 112 | [1] | 128 | 0 | 0 |
| grouped-050 | 0 | 576 | 168 | [1, 2] | 352 | 32 | 448 |
| grouped-050 | 1 | 352 | 112 | [1, 2] | 288 | 32 | 128 |
| grouped-009 | 0 | 128 | 128 | [1] | 128 | 0 | 0 |
| grouped-009 | 1 | 128 | 112 | [1] | 128 | 0 | 0 |
| grouped-014 | 0 | 512 | 168 | [1] | 512 | 0 | 0 |
| grouped-014 | 1 | 512 | 112 | [1] | 512 | 0 | 0 |
| grouped-018 | 0 | 288 | 168 | [1] | 288 | 0 | 0 |
| grouped-018 | 1 | 176 | 112 | [1] | 176 | 0 | 0 |
| grouped-022 | 0 | 592 | 168 | [1, 2] | 528 | 0 | 128 |
| grouped-022 | 1 | 528 | 112 | [1, 2] | 512 | 0 | 32 |
| grouped-034 | 0 | 256 | 168 | [1] | 256 | 0 | 0 |
| grouped-034 | 1 | 256 | 112 | [1] | 256 | 0 | 0 |
| grouped-033 | 0 | 256 | 168 | [1] | 256 | 0 | 0 |
| grouped-033 | 1 | 256 | 112 | [1] | 256 | 0 | 0 |
| grouped-005 | 0 | 512 | 168 | [1] | 512 | 0 | 0 |
| grouped-005 | 1 | 512 | 112 | [1] | 512 | 0 | 0 |
| grouped-054 | 0 | 1184 | 168 | [1, 2] | 1056 | 0 | 256 |
| grouped-054 | 1 | 1056 | 112 | [1, 2] | 1024 | 0 | 64 |
| grouped-013 | 0 | 512 | 168 | [1] | 512 | 0 | 0 |
| grouped-013 | 1 | 512 | 112 | [1] | 512 | 0 | 0 |
| grouped-038 | 0 | 576 | 168 | [1] | 576 | 0 | 0 |
| grouped-038 | 1 | 576 | 112 | [1] | 576 | 0 | 0 |
| grouped-041 | 0 | 256 | 168 | [1] | 256 | 0 | 0 |
| grouped-041 | 1 | 256 | 112 | [1] | 256 | 0 | 0 |
| grouped-021 | 0 | 512 | 168 | [1] | 512 | 0 | 0 |
| grouped-021 | 1 | 512 | 112 | [1] | 512 | 0 | 0 |
| grouped-049 | 0 | 512 | 168 | [2] | 256 | 0 | 512 |
| grouped-049 | 1 | 256 | 112 | [1] | 256 | 0 | 0 |
| grouped-037 | 0 | 1024 | 168 | [1] | 1024 | 0 | 0 |
| grouped-037 | 1 | 1024 | 112 | [1] | 1024 | 0 | 0 |
| grouped-001 | 0 | 128 | 128 | [1] | 128 | 0 | 0 |
| grouped-001 | 1 | 128 | 112 | [1] | 128 | 0 | 0 |
| grouped-046 | 0 | 1024 | 168 | [1] | 1024 | 0 | 0 |
| grouped-046 | 1 | 1024 | 112 | [1] | 1024 | 0 | 0 |

正式冻结 recipe=0、qcap=1、waves=2。以下按实际使用的 FULL 包统计，q>1 case-block 计数不会把未选择的开发配方冒充正式效果。

| 阶段/部件 | 记录数 | 有 q>1 记录 | q>1 tile / 全 tiles |
|---|---:|---:|---:|
| implementation_layer_develop / F0S1 / down | 36 | 0 | 0 / 2976 |
| implementation_layer_develop / F0S1 / up | 36 | 0 | 0 / 11904 |
| implementation_layer_develop / F1S1 / down | 36 | 0 | 0 / 2976 |
| implementation_layer_develop / F1S1 / up | 36 | 0 | 0 / 11904 |
| implementation_layer_test / F0S1 / down | 36 | 0 | 0 / 29744 |
| implementation_layer_test / F0S1 / up | 36 | 0 | 0 / 143176 |
| implementation_layer_test / F1S1 / down | 36 | 0 | 0 / 29744 |
| implementation_layer_test / F1S1 / up | 36 | 0 | 0 / 143176 |
| implementation_operator_test / FULL / operator | 252 | 0 | 0 / 399480 |

完整原始分布含每个非空 problem 的 q、packet length、tail packet 数，见 `packet_applicability.json`。这是调度工作分配计数，不是硬件实际尾部时延或 DRAM 流量。
