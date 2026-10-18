# 01 A/A 起始瞬态：固定因子，不猜原因

## 1. 首先把“同一Graph”说准确

SLOT0控制只重放同一个已初始化Graph、相同指针和同一输入槽。RING4测量轮换四个预建Graph，四图的数学参数与库算法相同，输入槽不同；A与B重放的是**相同的四图序列**，不能把它描述为单图单地址控制。

固定异常输入`R_G017=(32,8192,4096)`，较弱历史BEGIN对照`R_G002=(1,1024,16384)`。这两者是先验固定的机制输入，后者不保证绝对稳定。所有A/A的A/B标签不影响实际Job选择。

## 2. 2×2×2 主因子

|因子|水平0|水平1|
|---|---|---|
|conditioning提交方式|BURST64：连续提交64次、只在组尾等一次|READY：每个请求都等待结果，再读事件|
|conditioning输入|SLOT0：永远用第0槽|RING4：逐请求0/1/2/3循环|
|实验夹具|NATIVE_ONLY：只建LIB所需资源|ALL_ACTIONS_RESIDENT：按旧流程建九动作/资源，但计时只运行LIB|

共2输入×8组合×3重复=48个transition episode。每种fixture/输入/重复使用独立进程，避免先创建全部Green再声称能退回“没创建”的native环境。该进程内四种conditioning使用计划中给定的顺序，不按曲线调顺序；3次重复不是完整四阶carryover平衡，报告前一profile，不宣称消除全部历史。

每次conditioning固定30秒，全部策略相同；最后一个有限64请求包完成后才切换测量，记录实际时长。30秒不能保证所有状态收敛，也不是正式请求的一部分。数学输出必须被真实产生，不能空kernel预热。

### BURST64/RING4的正确实现

```
for each finite batch:
    for j in 0..63:
        enqueue original body_graph[global_request_index % 4]
        ++global_request_index
    wait once on the common parent stream
```

不是`job[batch_index%4].batch(64)`：后者每64次才换槽。不得使用同一组逐请求计时event在64个未完成重放间反复覆盖后，宣称拿到了64个独立时长。conditioning只需要已确认提交数、槽位直方图、有限包总完成时间；不需要为每次异步提交再插GPU事件。

READY/RING4则每次运行原`Job::run`的完整ready语义；condition阶段保留头64与末128请求的预分配环形缓冲即可，不必记录几十万conditioning请求。

## 3. 接着测什么？

conditioning一结束，立即运行12个窗口。每窗依次：n次同路径warmup、n次测量。n取本轮每输入一次LIB-only pilot的`clamp(ceil(20000/cpu_ready_us),8,128)`，在任何因子结果前冻结；同输入各组合、各重复相同。保存**所有窗口warmup及测量请求**，不要丢掉“还没稳定”的前缀。

A/B标签按四窗组交替ABBA/BAAB；两者执行完全相同。RING4槽位按窗口内请求号%4，与旧路径一致。每条记录同时保存全episode请求号与窗口请求号，以免重置计数后误判槽位效应。

同时报告按请求数、按切换后的真实毫秒两种坐标。不同计算速度下第128次并不代表相同运行时长。

增加6个SLOT0控制：2输入×3新重复，仅NATIVE_ONLY、READY/SLOT0 conditioning，正式也固定slot0。它区分四图/四输入工作集与单图控制，不把两者的差异全称cache影响。

## 4. 事件作用域与小型独立计量

D1检查：每个Job的event归属context/stream是否正确；外部计时节点是否覆盖最终ready；每个请求完成后再读event；没有前一次record覆盖、未完成就读、多个Job误共享正在使用的event。所有CUDA返回码保留。GPU事件跨度不是纯kernel活跃时间。[O1]

仅在R_G017原LIB上做4个episode（2新进程×2timer模式）：
- ORIGINAL_EVENT：保留原wrapped Graph计量；
- BODY_CPU_ONLY：重放相同body节点、相同ready等待，去掉外围计时节点，记录CPU时间；GPU时长NA，仅在另行CUPTI中获得活动时长。

这是测量观察效应，不是候选优化。两模式分别qualify数学输出与body DAG，不能一边改变库选择，一边说只是去事件。主体CUDA源码/cubin保持不变。

CUPTI最多6个短捕获，优先AA的两种提交节奏和F4两条链。只使用已有工具。保存kernel活动区间、CUDA API提交/等待（若实际被工具导出）、context/stream、correlation id；没记录的字段写未知，不能用源码调用次数冒充独立trace。

## 5. D4独立复验

D2结束后，冻结采用`READY_RING4`作为语义对齐协议，与`BURST_SLOT0`旧协议比较；只在NATIVE_ONLY做2输入×2协议×4新进程块=16个episode。不是挑最小方差的任意方案。若D1找到明确计时bug，修复原因与patch在D4之前冻结，旧模式仍保留记录。

报告每episode全12窗、第一/第二/第三quartet、warmup曲线、共同时间区间和请求级极值。原始全数据与预设位置分层并列，不通过只留末窗宣布问题解决。

能够说“某因素对当前异常有作用”的依据：同数学/输入合同的因子对照及新块复验，且能够解释时间跃迁的位置。只有温度/时钟相关而没有干预，就只能说关联；没有复现就写未复现。无论结果如何都不启动新选择器训练。
