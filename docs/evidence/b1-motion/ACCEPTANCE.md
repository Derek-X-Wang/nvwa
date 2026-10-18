# 同一 B1 人物的连续动作与体型验收

跟踪：[#78](https://github.com/Derek-X-Wang/nvwa/issues/78)。本页是2026-10-17的本地证据快照；最终原生补验与精确PR/main CI以该issue及关联PR为准。旧[B1静态验收](../b1-work/NATIVE-VALIDATION.md)和56–59实验保持原样。

## 范围与合同

同一套十三个原始文件、人体/运动服、53骨骼和完整正聚合影响CPU蒙皮，新增两个明确为Nvwa预制的四秒动作：手臂活动和单腿屈膝。它们不是AI生成，也不修复M2真实样本的动作质量。Work schema3不变；version2/profile `nvwa-mpfb-b1-motion-v1`与静态version1明确分开。旧作品不自动升级，CLI `new-b1`仍创建静态作品。[完整合同](../../implementation/b1-motion-contract.md)列出曲线、优先级、播放与采样语义。

体型为torso_length的−1/0/+1三个设置；jaw_drop的−1/0/+1是脸部设置，九种配方不代表九种全身体型。固定拟合后的中立位置，不逐帧抬高人物、不做地面夹紧、IK或接触求解。屈膝包含明确的预制脚部反向旋转。脚部低点补丁按脚/脚趾权重和中立最低面选取，不是解剖足底标定。

## 当前执行结果

| 验证层 | 状态 | 实际证据 |
|---|---|---|
| 工作区测试 | VERIFIED | 171项：adapter1、core33、CLI18、runtime59、Studio60；含实际上传网格33时刻×3躯干脚部回归，无忽略项 |
| 完整生产运行时CPU矩阵 | VERIFIED | 594个唯一k/8网格帧＋16定位＋2暂停全部通过；另有结束标记，30个深度关键帧通过；[结果](matrix-summary.json) |
| 独立几何预期 | VERIFIED | 真实拟合骨架、原始signed MHCLO/完整正聚合权重、实际上传网格分别对照；不是替代查看器或预存答案 |
| 原生与Web构建 | VERIFIED | 产品应用/实际Wasm、Studio加性探针双端均构建；[193源与125产物哈希](build-closure.json)与当前文件一致 |
| 实际Studio数值读回 | VERIFIED | 桌面14/14、Web14/14分别通过独立FK/LBS/脚部及表面描述检查，之后14组双端数值对照通过；[结果](platform-summary.json) |
| 当前Web普通界面 | VERIFIED | 实际播放/暂停、7秒定位、jaw编辑/Undo/Redo且时刻保留、真实保存下载、坏文件保留人物、有效文件重开恢复 |
| 当前原生画面/普通界面 | VERIFIED bounded | 解锁后用当前r4实际运行Studio及Player；三torso×两动作峰值可见，普通编辑/Undo/Redo、Save、坏文件保留、有效重开及播放完成均实测；[新补验](native-resume-20261017/README.md) |
| CLI与文件交换 | VERIFIED bounded | 当前Web rev7→当前原生普通GUI编辑/Save rev10→正常Web picker Open，并由当前原生重开同一新Save文件。新增文件实际validate/inspect成功；此前21命令仅复用字节相同的证据，无本轮Web新下载声明 |
| 真实生产故障控制 | VERIFIED | 去掉手臂动作、漏传衣物网格、关闭脚部反向旋转均触发精确运行时断言；恢复原字节后同测试通过；[三组红/恢复绿](mutations.json) |
| 比较器/捕获/输入拒绝控制 | VERIFIED | 16/9/20项各自正常及Python `-O`通过；比较器控制与实际生产故障分开计数 |
| 独立审查与PR/main CI | PARTIAL | 既有修正源码/数值证据审查CLEAR；c655217精确PR的四项CI已成功。新增原生补验[独立复核CLEAR](native-resume-20261017/independent-review.md)，原生P1解除；本次证据提交后的最终head及合并后main CI另行确认 |

CPU矩阵安装完整生产`NvwaRuntimePlugin`及真实加载器、拟合、骨骼传播和网格上传，但没有窗口/渲染器/GPU。两端Studio探针调用正常`nvwa_studio::build_app()`，只添加命令/采样控制器；读到实际CPU上传缓冲，不是GPU顶点回读。普通界面另行操作。数字、画面、保存和性能互不替代。

[紧凑结果](RESULTS.json)与[采样身份/哈希](captured-samples.json)保留当前来源。完整原始网格快照保留于任务输出；仓库不提交数百MB的JSON。永久CI从相同真实源重跑矩阵，而非只校验旧答案。

## 原候选否决与修正

[r2失败记录](BASELINE-FAILURE.json)保留145项实际脚部失败及原始哈希：594帧中450通过、144失败，额外定位另有1次失败；30份深度原始数据中只有24份完成检查。发出结束标记/退出0不等于比较器通过。

实际0.125/0.25/0.375秒帧，脚部低点约−1.064/−4.541/−9.686毫米。离线重建的周期最深下扫约19.914毫米，区别于保留的实际帧。旧原生/Web0.25秒点位差不超过2.39e−7米。修正按已准入骨架中立坐标保留小腿+65度，加入脚部−65度反向旋转，不放宽1毫米接地/20毫米抬脚要求。

当前矩阵的对应低点约+0.423/+1.937/+5.223毫米。额外重测同一Web失败配方/0.25秒，实际低点从−4.541变为+1.937毫米，与当前CPU矩阵低点差1.19e−7米，并通过独立FK/全权重LBS/脚部检查。比较[旧Web帧](web-rejected-knee025.jpg)与[修正同帧](web-corrected-knee025.jpg)时，毫米结论来自几何数据，不来自截图目测。

关闭反向旋转的真实Rust故障重现`min_y=-0.0010642409`并失败，恢复后通过。新版动作在准入前修正，仍是同一未发布候选；旧静态v1不变。修正峰值含额外脚部旋转，不宣称与旧静态knee全网格相同；今后修改已准入动作需新profile身份。

早期r1因测试时钟加速而超时；测试改为零步进并新增31秒真实停滞拒绝控制，产品超时未删除。r3拒绝脚本同时匹配正/负65度，在编译前停止；精确匹配正向小腿字段后20项控制通过。失败日志均保留，失败轮次不计成功。

## 画面、失败尝试与质量限制

Web固定镜头包含[短躯干手臂](web-short-arm.jpg)、[中立躯干手臂](web-neutral-arm.jpg)、[长躯干手臂](web-long-arm.jpg)，及对应[短躯干屈膝](web-short-knee.jpg)、[中立躯干屈膝](web-neutral-knee.jpg)、[长躯干屈膝](web-long-knee.jpg)。人物/衣物随真实骨骼变化，支撑/摆动脚分开检查。正面全身图不建立任意视角的碰撞或解剖质量结论。

肩腰穿插、服装折叠及极端法线质量继续HOLD，由[#80](https://github.com/Derek-X-Wang/nvwa/issues/80)单独跟踪。面积/边长比、最近三角形局部有符号投影及相邻面翻折只是描述；开放表面符号不证明全局内外或真实穿透深度。通用相交/自相交分类、布料物理、IK、任意体型/骨架/衣物、动作审美及M2真实生成质量均未准入。#3保持阻塞，#4保留首次物理呈现、完全冷启动与GPU/内存缺口。

此前原生[自截图](native-locked.png)为黑图，[退出0/Ready/回调记录](native-capture-rejected.json)继续保留为被拒绝的失败尝试。解锁后用当前同字节r4完成[新的实际原生补验](native-resume-20261017/README.md)，不借用旧r2画面。新增14帧完整骨骼/网格与既有独立检查的现行r4帧精确对应；没有声称重跑完整数值检查器。回调时间/主循环频率不作为性能结果。

原生探针首个命令早于Work加载被拒绝；加入就绪读回、新请求ID后继续。一次大JSON捕获超过私有脚本60秒等待，文件随后完成；保留该超时，将诊断捕获等待上限设180秒后取得14帧。产品超时、正确性阈值和CI界限未改，不据此归因产品性能。Web标签/正则选择器适配失败也保留，改用已观察到的控件ID和精确回执后采样；计算器/结果未改。

普通Web数字输入的一次批量工具操作未确认生效，分开观察焦点后单字符输入成功；不声称新的实体输入故障或修复。实体拖动、输入法与缩放本轮没有重做。

## 复现

仓库根使用现有依赖/工具执行`bash scripts/check-b1-work.sh`。完整矩阵、双端14帧、真实源故障和捕获服务的命令与边界见[实验60](../../../experiments/60-b1-continuous-motion/README.md)。输出目录必须是新的；长检查按本地agent约定通过wefty运行，不共享target。源故障脚本只在专用可丢弃checkout运行。

[桌面rev4](native-edited.nvwa.json)与[Web rev7](web-edited.nvwa.json)均含完整八秒两段编排；后者为torso0.75/jaw1。实时光标不写进Work，重开从0开始。先构建`nvwa-studio`，复制文件后启动以保留证据原件：

```sh
nvwa_demo_dir="$(mktemp -d)"
cp docs/evidence/b1-motion/web-edited.nvwa.json "$nvwa_demo_dir/demo.nvwa.json"
target/debug/nvwa-studio --work "$nvwa_demo_dir/demo.nvwa.json"
```

**PARTIAL — 完整数值、构建、三项真实故障、双端14帧、当前原生画面/普通GUI/Player及文件交换通过；新增证据独立复核通过，最终PR/main CI待完成。衣物/M2质量HOLD保留。**
