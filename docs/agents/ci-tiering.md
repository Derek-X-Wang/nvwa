# CI 分层：候选实现与验收边界

2026-11-09：Derek 批准日常 PR 使用 Linux/core/Web 必需检查和短 Mac
原生编译/真实 CLI 冒烟；完整 Mac 重矩阵对普通 PR 非阻塞但自动报告。
Mac 专属变更及发布仍要求完整 Mac 通过。此决定不删除任何质量 HOLD。

## 工作流契约

建议平台设置将 **`Required CI gate`** 设为必需检查。当前无权限查看或更改
仓库 branch rules；本实现只提供检查，不声称 GitHub 已强制该门禁。
若当前 rules 仍要求全部旧检查或整个 workflow 通过，普通 PR 仍可能等待
后台 Mac，需要仓库所有者核对配置，不能把“代码提供了聚合检查”说成已生效。

聚合检查必须看到 classify、portable、portable-eye、Linux shared、Mac smoke、
现有 Linux B1/Web 六项成功。需要完整 Mac 时，还必须看到原
`macOS CPU tests and Wasm compile check` 成功；普通 PR 则必须看到该分支
按分类明确 skipped。失败、取消、缺失、未知分类和意外 skipped 均拒绝。

新 Linux shared 与 Mac smoke 在分类控制通过后即可开始，和 portable 并行。
原完整 Mac 及 B1/Web 同时依赖 portable 与 portable-eye。这样短 Mac 可以尽早进入队列，
且普通 portable 失败仍可留下独立的短检查证据；这会增加失败PR的计算成本。

完整 Mac 有两条互斥分支，运行相同的原完整命令和75分钟预算：

- `native-and-wasm`：分类要求完整 Mac 时运行，阻塞聚合检查。
- `mac-full-background`：普通 PR 后台运行，不是聚合检查的依赖。

因此普通 PR 不需等待可选长 Mac，但完整工作流仍可能因后台失败而红色。
`Complete Mac result report` 在完整任务结束后自动写 GitHub job summary；
失败/取消/缺失会保留红色报告与 error annotation，不用 continue-on-error
伪装成功。这不是额外的短信/私信通知服务；个人 GitHub 通知投递仍取决于
用户设置，助手跟进可读取报告。

另外的 `Complete Mac follow-up` 工作流在 Bounded CI 完成后只读查询该次
attempt 的完整分页作业元数据。它没有 checkout、制品下载、缓存或写权限，
不执行 PR 内容，也不写评论。整次运行因并发替换或人工取消时，仍可记录失败／
取消／缺失并标红。此 `workflow_run` 订阅需文件进入默认分支后才生效，草稿
PR 阶段不能声称已现场验证独立回报。保留具体 source run、attempt 与 head 链接。

## 分类

使用完整 checkout 的事件 base/head SHA 和本地 NUL 分隔 Git diff，
不使用会截断的第一页 changed-files API。新增/修改的明确共享路径可普通；
删除、重命名、复制、未知状态/路径、缺失历史、空 diff、不可解析输入均要求
完整 Mac。构建依赖、工具链、CI/脚本、验证政策、vendor、Studio 变更要求
完整 Mac。共享 Rust 文件任一侧有 macOS/Apple/Metal 或 cfg/cfg_attr/Unix 条件代码（精确平台无关的 cfg(test) 除外），也
保守要求完整 Mac，避免删除平台 guard 时漏判。这个保守规则可能多跑，
不追求仅凭文件名猜出绝对最小测试集。符号链接、子模块和未知共享输入类型也要求完整 Mac。

main push、任意 tag push、手动运行、release event 及未知事件一律完整。
发布前必须在拟发布 SHA 手动完成完整门禁或使用对应 tag 检查的通过证据。
`release: published` 事件只是事后审计，不能追回已经发布的制品；本工作流
没有新增 release 发布权限或声称能阻止用户直接发布。

## 各层实际证明

- portable 的完整眼睛／头发组独立并行，其余15组顺序保留；全部原命令和步骤
  预算不变。两个 portable 作业各30分钟，现有 Linux B1/Web 仍60分钟。
- Linux shared 使用独立明确 Linux 入口：完整 workspace tests、实际 CPU
  导出、原独立 probe/appearance bridges、三个 mutation 语义红→恢复绿、
  完整594帧 motion matrix 和实际 source2 garment normal/`-O`控制。
  仅显式启用 Linux 所需现有 `bevy/x11`。原 Darwin/arm64 guard 不删除，
  不伪造平台，不拿小型 viewer 测试替代完整共享覆盖。
- Mac smoke：真实 `cargo check -p nvwa-studio`，构建无可选特性的 CLI，
  实际创建 waist Work、验证正式素材、拒绝缺失素材、保存并重新读取。
  不证明 Metal、窗口/输入、UI 画面或 CPU 渲染。CPU 渲染由 Linux 完整实际
  检查及适用完整 Mac 检查覆盖。

新任务预算：Mac smoke30分钟、Linux shared75分钟，mutation12分钟和
matrix20分钟边界保留；原完整 Mac75、portable30、B1/Web60及其他既有预算
不变。冷编译开销仍存在，首次 hosted 运行前不承诺固定完成时间或提速比例。

## 缓存与来源

完整 Mac 的既有 main-push-only 缓存原样保留；普通 PR 仍冷编译。
短 Mac 和 Linux 新层不生产旧完整 native seed，新拓扑、分类器与所有 workflow 都纳入兼容身份；只允许完整 native-and-wasm producer 选择 main seed，不修饰指纹或mtime，
不把短冒烟当作完成完整门禁。完整 workflow/source 旧字节保留为历史 fixture；
四个独立历史消费者分别验证新作业及入口的精确合同，只反向删除已验证的新增
拓扑，然后继续原整文件、命令顺序、预算、失败与 normal/`-O` 断言。保留
9031ce7 的48个 run bodies 和16组 portable catalog。原 mutation 脚本恢复原字节；
Linux 专用副本逐字验证只有平台参数及目录定位差异，不刷新72/73旧 source maps。

## 本地验收

```sh
python3 -B scripts/ci-tiering/test_policy.py
python3 -B -O scripts/ci-tiering/test_policy.py
bash -n scripts/ci-tiering/linux-shared.sh
```

上述为策略与命令合同测试，不是 Mac/编译/运行性能验收。
实际 Linux共享、Mac短冒烟、完整Mac与全门禁另在PR执行记录中记录结果；任何未运行项
标 NOT-RUN，不因策略单元测试通过而改写。


## 当前验证记录

- 原 main Bounded run42585301578 的 portable 在约30分钟取消，current19未完成，
  frozen-upper-arm与Mac/Linux B1未运行。CLI run42585301571通过。没有重启它们。
- 新策略/真实Git/报告/命令合同18项，四个历史消费者21/18/15/28项，均在normal与
  `-O`通过。包括缓存完整producer限定、所有workflow与分类器身份敏感性。
- 本地Linux复用已有共享target、单Cargo worker：workspace检查／测试与真实CPU导出
  合计618.59秒（293项workspace测试、4项CPU导出）；六个appearance桥接85项，147.54秒；
  三个真实production mutation的语义红／恢复绿，531.44秒。没有修改既有预算。
- 全部594帧、衣物normal/`-O`以及hosted Mac结果见PR执行记录。本文件不将待执行
  项标绿，也不把本地复用target时间换算成hosted冷编译或队列提速。
- 分类有意保守：Studio、脚本、CI、来源策略及未知路径仍要求完整Mac，收益仅适用于
  明确共享且无平台条件的代码／素材／文档变更；不承诺每个小功能都会走普通分支。
- 不存在自动发布制品的workflow；发布前目标SHA的完整检查仍需发布者核对。
  默认分支上的独立完成报告和普通PR后台分支的现场行为需上线后继续验收。


## 首次 hosted 结果与衣物数值诊断

草稿 [#148](https://github.com/Derek-X-Wang/nvwa/pull/148) 的首个
[Bounded CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/42595411772)
对应 head `9092e900c22a7ad1caed94bcb7e2de65447d0454`。实际 macOS 15 arm64
短作业通过，用时9分11秒；Studio check 与普通 CLI build 合计8分36秒，
真实 Work／素材／拒绝／保存冒烟约2秒。这是一次 hosted 测量，不是完整 Mac
验收或普遍提速保证。Linux shared 用时57分49秒，workspace／真实CPU导出
39分34秒、appearance 2分4秒、三类mutation红／恢复绿7分3秒均通过；
matrix／衣物阶段8分36秒，594帧及30个深度关键帧完整，随后原衣物normal
仍为16通过／2失败，实际比值与本地完全一致。`-O`因normal失败未执行。
聚合检查正确失败；这次运行保留为failure，不重写成全绿。

portable 在 `test_timing_order.py` 的嵌套集成检查失败：原13项缓存控制及新增
2项分层控制均通过，但外层仍要求两次“Ran 13 tests”。修复逐项验证原13个
方法名及新增2个方法在normal／`-O`各成功一次，仍要求两份15项摘要，并增加
缺失、失败、改名、重复、错误类和缺少模式的负向控制。原四组真实 catalog
执行、源码身份、失败传播与生成文件断言保留。完整 native-cache-contract
本地normal／`-O`各17项通过；旧 hosted 失败不改写为通过。

本地实际 Linux source2 衣物帧仍有2/18项失败（normal与`-O`相同）：三角形200
的 posed/fitted-rest 面积比为 `22.005667838827247`，历史期望为
`22.0056357384`，原断言精度为6位。其余16项控制通过。raw及fitted-rest坐标
完全相同；三个上传顶点最大差异为 `1.1920928955078125e-7`，面积差约
`6.05e-10` 平方米，经很小的 fitted-rest 面积相除，放大为约 `3.21e-5`
的比值差异。所有1797个衣物源顶点仍通过原重建边界；这不豁免失败的固定值。

仓库外的独立公式重建使用相同已准入输入：默认glam 0.32.1 x86 SSE2路径
逐位匹配实际记录的全部53个骨骼矩阵及三个最终顶点；scalar-math路径逐位
匹配历史三个顶点，得到 `22.005635738420796`。最早差异是pelvis四元数
归一化：SSE2除以长度，scalar／NEON源码乘长度倒数，w分量相差1个f32 ULP。
仅替换该归一化还不足以匹配最终历史值；后续矩阵计算也与运算后端有关。
强制libm未改变Linux结果。没有进行新的Darwin／NEON完整重建运行，不能把
scalar重建称为当前Mac验收。历史来源c655217的adapter、vendor、B1素材和
experiment60 source／lock与当前对应树完全相同。

原Mac衣物测试、容差、生产数学代码与素材均未修改。仓库外另有仅替换两处
固定值并添加真实Linux x86_64主机检查的候选，全部18项normal／`-O`控制通过；
它仅用于评估平台数值合同，**未采用**，不属于正式门禁通过证据。采用任何新
数值合同前仍需审查；hosted现已佐证Linux数值，但未执行该仓库外候选。
不能仅切换scalar-math来获得绿色。
完整Mac和发布HOLD继续保留。


对照运行 [#146 / 42589213875](https://github.com/Derek-X-Wang/nvwa/actions/runs/42589213875)
在10:27 UTC完整通过，Mac作业71分45秒，594帧／30个深度关键帧完整，原衣物
normal／`-O`各18项通过（3.092／3.302秒）。这是
`c1a4a613be913cd7e0cbc040a0a4e00988970cc6` 的实际Mac对照，不能替代本PR
精确SHA的完整Mac验证，也不是新增NEON公式探针的执行证据。


同一初始候选加计时集成修复，在隔离checkout运行完整
`python3 -B scripts/check-portable.py all`，全部16组按原顺序通过，exit 0；
最后的normal／`-O`与真实catalog集成均执行。此结果早于整合#146，不能称为
新main组合树的完整portable结果。#146随后于10:31 UTC合并为
`e21322c95b3b9ca40334206de135a19b1ad6cb0f`，已无冲突整合到CI分支；
新组合树的合同、来源上下文及Core／CLI验证单独记录在PR中。


新main组合验证已通过：分层／历史合同204次（含完整嵌套catalog normal／`-O`），
72／73的CPU-export、reference-motion及waist精确上下文40次，Core／CLI 100项，
以及普通CLI实际创建、完整素材校验、拒绝和保存／重读语义。该CLI语义运行主机
为Linux，不重复标成Darwin。正式新head CI另行采集；衣物数值合同仍未采用，
不能仅凭这些局部成功解除Linux必需门禁或发布HOLD。


## Linux x86_64 数值合同候选（后续修复）

在首次失败、独立源公式重建、hosted Linux完全一致的复现及#146实际Mac对照
之后，本PR新增独立 `scripts/ci-tiering/linux_garment_controls.py`。它要求真实
Linux x86_64，在该平台使用固定值 `22.005667838827247`；原Mac文件继续使用
`22.0056357384`。两端仍为 `places=6`，不是扩大容差，也不根据待测数据选择
期望值。未知主机、Linux arm64及Mac均不能误用这个Linux入口。工具链、glam
feature或运算后端变化若不再匹配固定值，应失败并重新审查，不能自动选择另一值。

新文件逐字保留原18项控制，只有主机／导入定位和两处期望常量不同。三角形、
全部正权重、源系数、FK／时刻／形状绑定、上传顶点扰动、top4截断、清单损坏、
非有限／重复JSON、旧帧及bridge68拒绝用例均保留；独立analyzer及其边界不变。
原Mac测试SHA256仍为
`8cd854388f6f5d4411355217e21d97f38303693db2289cf6782e23e8040c728a`，
两条完整Mac分支继续调用该原文件的normal／`-O`，不调用Linux入口。

四个历史消费者没有刷新原v1输入哈希。它们先验证当前v2脚本及控制的精确
SHA256，再反向还原两条Linux命令和已验证的新增策略控制块，继续原v1输入
哈希、9031ce7整份workflow和所有旧拒绝断言。额外负向控制拒绝改变精度、
常量、主机guard、模式或来源等价断言。缓存身份原本已纳入全部scripts，因此
新合同会产生新身份，短作业仍不能生产完整native seed。

这项修复定义平台对应的历史缺陷观测值，并不修复衣物几何缺陷或解除服装质量
HOLD。正式采用仍以当前PR完整Linux／Mac实测和审查为依据。先前失败记录、
仓库外未采用试验与当时的验证缺口保留；后续候选结果单独记录。


后续候选的本地验证：四个历史消费者及分层控制在normal／`-O`通过，共208次；
在当前main代码上重新构建并执行完整594帧／30个深度关键帧后，Linux入口
normal／`-O`各18项通过。同一新帧上，未修改的原Mac测试仍在两种模式中
恰好失败于原两条固定值断言，其余16项通过；这组反向对照按失败保存，不是
Mac主机验收。新帧SHA256为
`3f966d6ec29c2b3039530b8c4a798371c0b06f349a21bfa82043930e26949d50`。

同时，[8d09b1d的真实CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/42604442597)
portable再次触及30分钟总上限。GitHub明确标注超过30m0s；normal嵌套集成
17项已通过（156.468秒），优化模式进入真实catalog集成后未完成。后续
main-cache、shoulder、current19及frozen-upper-arm未执行，完整Mac与B1/Web
跳过。Mac smoke8分13秒通过不能替代这些缺口。该预算失败与release HOLD
保留；本数值修复不增加预算、删用例、优化测试成本或重跑旧identity。
新的实质性数值合同仍须其精确head的正常CI。若要改进portable测试成本或
另调预算，按verification.md中的portable30停止规则单独决定。


## Portable 分组候选（明确授权后的成本设计）

[a7773e9 的运行](https://github.com/Derek-X-Wang/nvwa/actions/runs/42611367912)
保留为 cancelled：eye/hair 用时17分10秒，native-cache normal 的17项已通过，
optimized 集成尚未完成时触及 portable30；其余组、完整 Mac、B1/Web 未运行。
同次 Linux shared 完整通过但用了73分36秒，仅剩84秒预算；Mac smoke8分29秒。
这些结果不能证明完整 CI 通过，也不是普遍提速证据。

本次只把独立的 `eye-hair-parameters` 整组移到并行作业。它读取仓库正式素材和
精确来源上下文，运行 Python／Node 控制，不依赖前面 source-cli 的编译输出。
catalog 和运行器不改；原 portable 保留其余15组顺序，完整 Mac 与 B1/Web 等待
两项均成功。最终 gate 对任一组失败／取消／skipped／缺失继续返回非零。

新增分组控制验证16组恰好各一次、依赖关系、真实 gate 进程的失败出口、独立组
缺失 Node 的真实失败。四个历史消费者精确认证新作业／输入和依赖，再还原完整
旧 workflow，所有历史哈希和断言继续执行。缓存身份原本已包含所有 scripts 与
workflow，因此新拓扑进入新身份；短检查仍不产生完整 native seed。

验收：本地独立完整眼睛／头发组与剩余15组、各历史合同 normal／`-O`、正式新
head CI 的结果随 PR 记录。此处不把未完成项标为通过。并行会增加 runner 启动
成本，缩短关键路径的幅度以实测为准；未改变各步骤上限或总计算量的承诺。


## 完整 Mac 独立作业候选（2026-11-09 新授权）

Derek 在 [36e9136 的自然运行](https://github.com/Derek-X-Wang/nvwa/actions/runs/42653697946)
完整 Mac 达到原75分钟上限之后，明确同意保留全部 Mac 测试与失败信号，将
完整 Mac 拆为独立作业并分别实测；不以单纯加时或删除检查换绿色。
本节覆盖上文对完整 Mac 单作业拓扑的描述，旧结果仍保留。

必需分支和普通 PR 后台分支各有三个互斥的 macOS 15 作业：
workspace/实际CPU导出、appearance/三类生产 mutation、594帧矩阵/原衣物
normal及 `-O`。这三段从完整旧作业按步骤原字节复制，normal/`-O`、
Darwin/arm64 native guard、mutation12分钟、matrix20分钟、单Cargo worker
及每个作业75分钟上限保留。每段都在新runner冷编译；appearance和matrix作业先对各自独立graph执行精确
locked Cargo fetch，随后运行原有offline命令。分别耗时与总计算成本必须
通过hosted数据记录，不能从并行推断节省。

原 `native-and-wasm` 和 `mac-full-background` 作业仅保留作历史合同基线，
条件为false，不执行旧整任务。此前仅完整 producer 可使用的main-only
native seed和optional warm trial因此不产出或复用；任何只完成部分检查的
新作业都没有cache save/restore步骤，也不能声称生成完整种子。四个独立
历史消费者验证六个新作业的精确身份、投影回旧整工作流，然后继续原有
整文件、命令、预算、失败和negative controls。旧48个run bodies与16组
portable catalog仍为历史基线，不改写旧失败。

完整必需场景中，`Required CI gate`直读三个Mac作业并要求全部success；
普通PR要求必需分支三个明确skipped，不等待后台三项。
`Complete Mac result report`和默认分支独立只读报告要求同一分支三个success、
另一分支三个skipped；任一失败、取消、缺失、混合或未知均为红色。
普通PR后台失败仍为真实失败和后续跟进；相关Mac工作和发布需要目标SHA的
完整三项成功，不能只看短Mac。分支保护的实际required status设置未变更，
默认分支独立报告和普通PR后台分支仍需上线现场验收。


## Mac 矩阵主机范围调整（#148 后续候选）

[ba772184 的完整重跑](https://github.com/Derek-X-Wang/nvwa/actions/runs/42672359165/attempts/2)
在19:25 UTC开始，最终failure：Linux shared完整594帧／30关键帧和衣物
normal／`-O`通过；Mac workspace/CPU、appearance/mutation、短冒烟和
portable、B1/Web通过。独立Mac matrix作业在20分钟步骤上限时仍编译Bevy，
没有执行完整矩阵或原Mac衣物控制；运行内报告和Required gate均失败。
此记录不视作Mac矩阵通过。随后#149腿部形态已合入main `d5bc346`，候选
已在本地整合该基线，正式CI需对新组合SHA重新验证。

用户明确质疑慢速Mac runner重复完整矩阵的必要性。实验60的matrix二进制
只使用生产runtime CPU快照，无窗口／GPU，源中只有native／Wasm条件分支，
没有Mac专属矩阵代码。现将完整594帧矩阵仅作为Linux shared的必需检查；
此作业仍运行原矩阵checker、source2真实帧、Linux固定数值衣物18项的normal
和`-O`，不变更步骤20分钟上限。Linux失败使所有PR、main和发布门禁失败。

原Mac衣物数值有独立于Linux的固定值，因此不能用Linux结果声称Mac平台
精度已验收。Mac workspace的必需／后台两个分支在原native workspace与CPU
检查后，用同一生产probe的`--garment-witness-only`模式只生成精确
torso+1/jaw0/arm2/source2帧；严格拒绝缺帧、重复、错绑定及非Darwin arm64，
再用未修改的原Mac衣物文件运行18项normal和`-O`。Mac不再逐帧检查其余593帧、
第二动作及seek/pause；这些完整语义由Linux必需矩阵承担，不能描述为Mac平台
逐帧通过。本地实际Linux probe
生成一帧及完成标记用时3.392秒，**不是Mac编译或运行耗时**。该Mac步骤沿用
20分钟限额，整个作业75分钟，仍可能因额外冷编译失败；需hosted实测。

完整Mac现在为workspace/CPU/单帧数值见证与appearance/三类mutation两个
互斥分支作业；必需场景两个都成功才通过，普通PR两个后台作业自动报告，
失败／取消／缺失不转绿。历史六作业完整工作流保留为精确snapshot，四个
历史消费者先投影当前两作业拓扑，再继续先前v4/v3/原9031ce7完整哈希、
命令顺序、预算和负向控制。旧单体Mac作业仍停用，部分新作业不能产生完整
main-only缓存种子。完整Mac报告的默认分支触发、普通PR后台现场行为与实际
required-status规则仍待上线验收。发布和Mac相关工作仍需目标SHA全部适用
检查通过；衣物质量、动作画面与性能HOLD不因主机调整解除。

## Linux 完整动作矩阵独立必需作业（2026-11-10）

[#156 的精确 head 运行](https://github.com/Derek-X-Wang/nvwa/actions/runs/42811101279)
在完整 Linux shared 作业约75分钟上限取消，发生于594帧矩阵步骤；此前
workspace／CPU、appearance 与三类生产 mutation 通过不能推断矩阵及衣物完成。
Required CI gate 正确失败，完整Mac两项通过。旧取消与发布HOLD保留。

首次独立冷runner候选 [51c5a67 / 42824045098](https://github.com/Derek-X-Wang/nvwa/actions/runs/42824045098)
被新合同测试的历史字符串误用挡在分类作业，未测矩阵；修正后
[68902a0 / 42824494336](https://github.com/Derek-X-Wang/nvwa/actions/runs/42824494336)
的独立矩阵步骤确实在20分钟上限失败：Cargo冷编译19分56秒才完成，
594帧和衣物控制都未开始。这两条失败不改写为通过，也不靠加时掩盖。

后续候选让 Linux shared 在原 workspace／CPU、appearance、生产 mutation
之后，使用同一已预热target、原Linux guard和锁定离线依赖编译完整矩阵二进制。
同次运行的不可变 artifact 只传递该二进制；必需 matrix 作业必须等待 shared
成功，校验来自其输出的 SHA256 后才运行原完整594帧／30关键帧、真实source2
衣物normal／`-O`，不接受未知或缺失二进制。artifact 按run attempt命名，
下载失败或摘要不符保持红色。原矩阵本地入口保留；新runner只执行由它拆出的
原运行与断言命令。源码、素材和探针均来自同次精确checkout，不使用跨运行
cache或部分native seed，不增加GitHub token权限。

两个Linux作业、独立workspace check以及原有portable／Mac等仍被Required
CI gate直接要求success。mutation12分钟、矩阵执行步骤20分钟及各作业75分钟
上限不变；没有`continue-on-error`。共享作业增加已预热编译及artifact
上传，可能挤压它自己的75分钟余量；新runner和串行交接也增加总耗时／成本。
必须以新精确head正式CI验证，不能将静态合同或先前局部成功当成验收。
历史消费者先认证交接拓扑与原命令，再还原旧整工作流及原哈希。


## Mac 生产 mutation 分组（2026-11-10）

[#158 合并后 main 自然运行 42842699353](https://github.com/Derek-X-Wang/nvwa/actions/runs/42842699353)
的完整 Mac appearance 作业先通过六个原有桥接图，随后三类生产源码
mutation 在原 12 分钟步骤上限取消。日志显示 Cargo/rustc 尚在执行，
没有完整的红测／恢复绿测摘要；timing report 因命令记录不完整也正确失败。
Required gate、Mac 结果报告和后续发布证据保持红色。此前同一步骤在
[#158 PR 运行 42829525866](https://github.com/Derek-X-Wang/nvwa/actions/runs/42829525866)
耗时 10 分 25 秒通过，故仅靠偶然快一次不足以保证稳定。

候选把原三类红绿见证分为两组：arm-pose 加 garment-upload，以及
foot-counterrotation。两组在独立 macOS 15 runner 并行运行；脚本未指定组时
仍执行原全部三类。每组保留原源码 seam、预期失败断言、原字节恢复、
真实恢复绿测和日志；Cargo workspace lib locked/offline 命令不变。
每个 mutation 步骤仍限 12 分钟，独立作业仍限 75 分钟，关闭矩阵提前
取消以让一组失败时另一组继续记录结果。appearance 桥接在对应 mutation 矩阵成功后运行，workspace／CPU／
单帧 Mac 衣物见证仍独立运行。桥接作业保留原显示名称并明确依赖 mutation，
因此旧的默认分支完成报告也不会在 mutation 失败时误报成功；运行内报告会
逐项列出新分组。必需场景的矩阵总结果必须成功，
普通 PR 的后台矩阵必须自动报告真实结果；缺失、失败、取消与混合分支均
不得转绿。此分组增加 runner 及冷编译成本，关键路径缩短与实际余量仍须
精确 head 的 hosted CI 实测。历史合同先认证新增分组并还原原工作流，再
核对原命令、预算与负向控制；不修改安全设置或原失败记录。
