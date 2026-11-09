# CI 分层：候选实现与验收边界

2026-11-09：Derek 批准日常 PR 使用 Linux/core/Web 必需检查和短 Mac
原生编译/真实 CLI 冒烟；完整 Mac 重矩阵对普通 PR 非阻塞但自动报告。
Mac 专属变更及发布仍要求完整 Mac 通过。此决定不删除任何质量 HOLD。

## 工作流契约

建议平台设置将 **`Required CI gate`** 设为必需检查。当前无权限查看或更改
仓库 branch rules；本实现只提供检查，不声称 GitHub 已强制该门禁。
若当前 rules 仍要求全部旧检查或整个 workflow 通过，普通 PR 仍可能等待
后台 Mac，需要仓库所有者核对配置，不能把“代码提供了聚合检查”说成已生效。

聚合检查必须看到 classify、portable、Linux shared、Mac smoke、现有
Linux B1/Web 五项成功。需要完整 Mac 时，还必须看到原
`macOS CPU tests and Wasm compile check` 成功；普通 PR 则必须看到该分支
按分类明确 skipped。失败、取消、缺失、未知分类和意外 skipped 均拒绝。

新 Linux shared 与 Mac smoke 在分类控制通过后即可开始，和 portable 并行。
原完整 Mac 及 B1/Web 的 portable 依赖保留。这样短 Mac 可以尽早进入队列，
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

- portable 与现有 Linux B1/Web 原命令、预算不变。
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
