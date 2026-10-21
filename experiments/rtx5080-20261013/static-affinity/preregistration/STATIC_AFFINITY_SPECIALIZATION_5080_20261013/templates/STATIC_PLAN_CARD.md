# Static plan card

## 允许的信息
设备/分配探测、开发相机、实际布局与工作量估计。逐项列出来源。

## 禁止的信息
测试未来frame的真实列表、测试逐frame最优assignment、未计费新physical mapping。

## 映射与所有权
logical task -> group -> worker rank；task list双射；缺组规则；布局双射；原Gaussian id保持。

## 控制证据
公开resource group或cooperative roster，实际SM覆盖与迁移，仅order control需明确降级。

## 固化粒度
设备／allocation／scene；T与K实际差异；是否有每frame额外工作。

## 有效期
fingerprint、generation、capacity、失效检测、回退；不使用释放指针。

## 参数与算法
score各项、nonzero/rank-changing计数、调参预算、B*公平性。

## 成本
全部必要初始化、每launch与每task残余成本，extra bytes与peak VRAM。
