# 论文贡献卡（运行时填写，不预设正结论）

## 1. 一句话问题
用明确任务、硬件条件和瓶颈表达；不能只写“5080优化”。

## 2. 当前最强简单基线
B0是哪一个实现？B*如何只用校准选出？缺了哪些现代baseline？

## 3. 新增约束和算法
为什么现有空间/工作量/共享分组不能处理？M在哪一个可具体检查的决策上不同？如果等价于B5，直接写ENGINEERING_ONLY。

## 4. 物理与程序证据
实际硬件域与软件组如何区别？独立位置亲和是否成立？资源工作集和alpha顺序哪些是exact，哪些是proxy？

## 5. 主结果
M相对B0、B*的完整帧与绝对ms、区间、负例；不可填只对置乱baseline的最大数。

## 6. 全部成本
setup、metadata、排序、分组、队列、额外copy、内存和CPU处理是否计入？

## 7. 因果与局限
拓扑置乱／摘要置乱／容量消融解释什么？counter有无？未独立定位哪些因素？

## 8. 泛化
开发、留出、1440p、第二renderer/第二GPU哪些真正运行？没有就写PENDING，不复制标签凑数。

## 9. 与相关工作
逐项对P1–P6；更换GPU/应用不是独立新颖性。哪些来源只有摘要、哪些全文已核对？

## 10. 投入决定
AFFINITY_AND_CACHE_OPPORTUNITY / CACHE_LOAD_OPPORTUNITY_ONLY / ENGINEERING_GAIN_ONLY /
NO_INCREMENTAL_OPPORTUNITY_ON_5080 / BLOCKED_LOCAL_RESOURCE / INCONCLUSIVE_WITHIN_BUDGET。

只判断下一轮是否值得投入；不保证论文、级别或录用。给导师一段150–300字汇报，数据与判断分开。
