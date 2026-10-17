# Nvwa 路线图

## 当前阶段：B1 接入正式 Work 进行中；M2 动作质量保持 HOLD（2026-10-16）

人物基础优先复用成熟 MakeHuman/MPFB 的数据设计，先验证相同小样的两条 Rust 路径，再决定正式后端。[53–55 的同样本对照](../experiments/53-character-comparison/RESULTS.md)已完成身体、关节端点和衣物数值检查：A 是编译数据包，B1 是修正小形变过滤后的实际 Humentity。[#73](https://github.com/Derek-X-Wang/nvwa/issues/73) 的 [56–59 完整姿态与双端实验](../experiments/56-b1-pose-reference/RESULTS.md)已通过 40 组数值门、最终原生/Web 六组完整骨架读回、原型状态往返和失败保护；原四权重 GPU 仍 HOLD。保留全部正的最终聚合影响、不受四权重限制的 CPU 桥接成为下一步接入候选，A 保留数值对照。它与 MPFB 的阈值策略不同，不宣称原库完整 GPU 能力。肩/腰穿插、服装折叠和法线角度/性能仍未验收；上述实验阶段未替换产品角色或根依赖，也未解除既有 M2 HOLD。发布审查、PR/main CI 按具体提交在 PR 中记录。

当前 [#74 在同一样本上接入共享命令、CLI 与完整 Work 交换](https://github.com/Derek-X-Wang/nvwa/issues/74)正在实现：明确版本化后端、schema3 及旧 Work 迁移、共享姿态命令、CLI 真实资产校验、按需加载及失败保护。源数据/许可、核心/CLI、桌面/Web 接入分工推进；实际测试、双端启动与文件交换、独立审查、PR 和合并 main CI 分别记录，未完成的门不算通过。之后再扩展身体/脸部参数与组合校验，再做 agent 按描述创作角色和动作。原型 JSON 不是正式 Work；库/资产发布边界和外观质量分别保留准入门。房间导入、接触/物理及 Relais 属于后续独立工作；世界编辑器和多人服务器不进入当前人物工具范围。

用户已授权并行推进 [#69 人物试演室](https://github.com/Derek-X-Wang/nvwa/issues/69)的 [#70 第一阶段](https://github.com/Derek-X-Wang/nvwa/issues/70)：可调灯光、相机、背景/地面和画质，使用共享 Rust 命令与可保存的舞台配置。目标是完成度高、可反复使用的人物展示与动作试演。房间导入和物理分别留在后续阶段；Relais 与多人服务不是舞台交付的前置条件。阶段 A 已完成共享命令、CLI、实际桌面/Web 操作与画面验收，以及原生→Web→原生的完整文件往返；独立复审和最终 CI 通过后合并。编译、实际启动、功能、画面和性能结果分别记录，未完成项不视为通过。

[#68 上臂中立策略对照](https://github.com/Derek-X-Wang/nvwa/issues/68)复用现有角色与真实样本，候选只调整两个上臂通道；数值、表面指标和桌面/Web 同帧效果分别验收。[PR #71](https://github.com/Derek-X-Wang/nvwa/pull/71) 已经在独立审查与 CI 通过后合并，#68 已关闭；精确合并 main `96a58a65` 的 [CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/38889505232) 已通过。它与舞台展示独立，不以灯光改善替代动作质量，生产映射保持原样。

试演舞台 [PR #72](https://github.com/Derek-X-Wang/nvwa/pull/72) 已有 137 项测试、双端构建、实际桌面/Web/CLI 操作及五组原生画面证据。原生保存、自定义舞台在 Web 打开/下载、原生再打开/保存后整份文件逐字节相同。早期锁屏黑图作为失败证据保留。历史来源适配已通过独立复审和两项 CI；最终证据 head 与合并 main 各自核验，结果记录于 PR。#70 在最终门通过后关闭，#69 保留房间/物理后续范围。详细边界见[舞台验收记录](evidence/rehearsal-stage/ACCEPTANCE.md)。

[#59 当前角色标定](https://github.com/Derek-X-Wang/nvwa/issues/59) 已补齐 [47 标定](../experiments/47-fixture-rig-calibration/REPORT.md) 的 [独立来源依据](../experiments/47-fixture-rig-calibration/reference/REPORT.md)：实际眼睛/脸部几何与缓存的固定版本源资料支持 +Y 上、+Z 前、身体左侧 +X。当前 fixture 的 `.L/.R` 名称与身体左右相反，因此保留资产名称，采用恒等坐标基、source Left→target `.R`。静态 T→A 中立对应、投影正面/上方滚转及手脚末端标记是工程约定，不宣称恢复掌面、足底或接触解剖。89 项正向、43 项拒绝和 8 项测量控制通过。47 的 `PROPOSED_NOT_ADMITTED` 是保留的候选快照；两次独立审查后，负责人在 [48 的独立准入记录](../experiments/48-genuine-fixture-work/admission.json)中明确采用这一有界工程策略，再开始后续导出。准入只覆盖当前角色和 44 的原有 90 帧，不是通用骨骼或动作质量认证。[PR #63](https://github.com/Derek-X-Wang/nvwa/pull/63) 已合并；其合并后 main CI 单独核验。

[48 真实 Work 实验](../experiments/48-genuine-fixture-work/README.md)对应 [#64](https://github.com/Derek-X-Wang/nvwa/issues/64)：现有 genuine 样本已实际导出、通过 CLI 校验和保存，分别在桌面/Web 播放、定位，并完成桌面保存→Web 打开/修改/下载→桌面打开/保存。独立序列化检查覆盖全部 90 帧、18 个旋转通道和一次 root 平移；保留旧 GLB 字节及未选中的原动作。完整文件交换证据见 [运行记录](../experiments/48-genuine-fixture-work/runtime/REPORT.md)。该阶段发现手臂与躯干相交并保留质量 HOLD；其当时缺少的运行时数值证据由下一项单独补充。

[#66 的 49 同帧实验](../experiments/49-runtime-pose-parity/README.md)复用相同 Work/GLB，在桌面和 Web 的七个精确关键帧采集实际骨架：24 个 GLB 节点、9 个皮肤实例均完整，局部变换一致，世界矩阵最大分量误差约 `1.76e-7`。离线重建已存在严格表面相交。进一步的[方向归因](../experiments/49-runtime-pose-parity/attribution/README.md)表明，既定 T→A 中立对应约 `45.7°` 的差异可以解释这些帧的上臂内折；这是当前相对中立姿势策略的效果，不是已证明的四元数空间或实现错误。该历史阶段尚未运行替代策略。现在 [#68 的 50 对照](../experiments/50-upper-arm-neutral-ab/REPORT.md)已完成同样本、同角色的固定双上臂候选：全部 90 帧方向门通过，桌面/Web 七帧实际骨架与各自离线预期一致；预先指定的低臂帧相交计数 `397→156`、`416→121`、`454→197`。实际末帧画面中双臂移出躯干，但仍有残余相交。**质量继续 HOLD**：这不等于解剖、接触、语义、插值或一般 rig 验收，生产映射未改。50 的截图属于舞台升级前的明确源码快照；新舞台另行验收。下一步先评估残余肩臂/扭转缺口和候选的独立采用门，再决定是否扩大样本。没有新增模型运行、下载或产品 provider。

[#49 无引导真人试用](m12-unassisted-trial/README.md)已记录一次在创建前求助并暂停的尝试。随后四步有引导操作使用已有九秒作品，参与者报告播放、编辑、保存和 Web 保留修改正常；它不能代替独立创建、Player 和恢复验收。[本次结果](m12-unassisted-trial/RESULTS-2026-10-15.md)与[一页中文说明](m12-unassisted-trial/PARTICIPANT-BRIEF.md)已分开归档；开发者复现命令仍留在技术指南。新说明没有启动新试用，入口单尚待准备，#49 保持开放。#3 保持阻塞，#4 保留原测量缺口。

Nvwa 的目标是：捏出角色、编排或生成动作、加入互动，再以桌面应用和网页分享。桌面、Web 和无需窗口的 CLI 是正式支持的三种入口；人和 agent 使用同一份 Work 和同一套 Rust 命令。当前 CLI 的正式范围是离线文件创作、能力发现和校验，详见 [CLI 支持范围](CLI-SUPPORT.md)。49 的骨架采样是隔离诊断程序；正式 CLI 的逐帧骨骼采样、离屏图像导出、运行中 Studio 控制和并发共享写入仍需单独实现与验收。

以下段落按发生顺序保留此前进展。各旧实验的 HOLD、NOT-RUN 和“未交付”属于当时快照；当前范围以本页开头、阶段表及 48 的运行记录为准。

M1.1 已按技术范围收束。 [M1.2](https://github.com/Derek-X-Wang/nvwa/milestone/2) 的离线 CLI 创作、双端继续编辑和交接已由 [PR #50](https://github.com/Derek-X-Wang/nvwa/pull/50) 交付，合并 main 为 `9502dd370b262761bf4f4f10f2418163c7574946`。保存反馈 #51 已由 [PR #52](https://github.com/Derek-X-Wang/nvwa/pull/52) 交付，合并 main 为 `f7b15eb166ed8a616dd73965cf23d1b7dcad61f6`。这些技术交付和后续引导式真人观察不等于完整 Alpha 关闭。

#53 浏览器标题修复已由 [PR #57](https://github.com/Derek-X-Wang/nvwa/pull/57) 交付，合并 main 为 `c30a250361f1c21ea055fb414c4a2b674702135f`。精确候选 head `7cfe171ea7d0bd2ba8e777b188e68ab9cbd85bf8` 的 [PR CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/38758576949) 已通过；[合并后 main CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/38763622991) 已在同一 `c30a250361f1c21ea055fb414c4a2b674702135f` 通过。#49 的独立真人门保持开放。

新增授权：开展 [M2](https://github.com/Derek-X-Wang/nvwa/milestone/3) 真实生成、结果导入和目标 rig 映射的有界实验，分别跟踪于 [#54 真实短动作生成](https://github.com/Derek-X-Wang/nvwa/issues/54)、[#55 动作导入](https://github.com/Derek-X-Wang/nvwa/issues/55) 和 [#56 rig 映射](https://github.com/Derek-X-Wang/nvwa/issues/56)。[#58](https://github.com/Derek-X-Wang/nvwa/pull/58) 已保留隔离 CPU/importer/authored 映射控制，#55/#56 按有界实验范围完成；其 [PR CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/38764869474) 与 [合并后 main CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/38770232509) 均通过，main 为 `b7122a20366f665f7ca32d48d5dc2f51a874ddbf`。随后，具体批准的三文件下载和一次离线 CPU 试跑已完成：[44 真实原始样本](../experiments/44-approved-cpu-motion-trial/REPORT.md) 保留成功退出、原始字节与数值结构检查。产品 provider、规范化/目标映射及生成播放仍未交付；本次单次授权已用完，新的下载、推理或额外算力仍需另行具体批准。#12 的真实输出与生成播放验收条件仍独立开放；先前的 NO-GO 保留为当时的准备度结论，不是实际生成证据。实时 Studio 桥接和公开二进制发行仍属后续范围。

[41 CPU 后端与 guard](../experiments/41-real-short-motion/REPORT.md) 保留模型外准备时的原始报告；获授权后的真实生成另见 [44](../experiments/44-approved-cpu-motion-trial/REPORT.md)。该一次请求产生 90 帧/30 关节原始数据，11,070 个浮点值均有限，2,700 个四元数非退化；58.545243 秒含 guard/清理，最大采样组 RSS 为 1,234,583,552 字节。这是忙碌 16 GiB Mac、模型刚经 hash 读取后的单次观察，不是冷启动性能测试或硬内存上限。signed axes、rest/root 约定、目标映射、语义质量和真实生成播放仍未验收，M2/#12 保持开放。

[45 真实样本映射数值研究](../experiments/45-genuine-rig-admission/REPORT.md) 对同一个 90 帧样本给出 **HOLD**：直接套用 43 的 authored 规则，目标 pelvis 世界位置约多出 `0.83 m`。旋转和缩放后的 pelvis 偏移重定位能修正声明的 hip-world 数学条件，但 source 左肢为 +X、target `.L` 为 −X，手臂中立姿势/解剖基仍未校准；矩阵自洽不能选择语义方向。该研究不导出规范化动作或 Work，不验收目标播放；CI 检查通过只表示 HOLD 研究/拒绝控制通过。下一步仍属 #12 的明确基准与 root 校准门，#3/#4/#49 不变。

[#59 骨骼校准](https://github.com/Derek-X-Wang/nvwa/issues/59) 的 [46 有界诊断](../experiments/46-soma-reference-calibration/REPORT.md) 复用同一原始样本：独立 up/front/name-side 约束给出条件性的 `48→8→2→1` 候选，保留左右语义冲突；逐关节报告中立几何和扭转可观测性。两个条件基的 pelvis 世界位置在全部 90 帧闭合，最大误差约 `1.735e-18 m`；七种错误 root 规则被实际 oracle 拒绝。[独立 4×4 复算](../experiments/46-soma-reference-calibration/independent/README.md) 不导入 43/45/46 数学实现。源肘部近平直、目标手脚缺少独立扭转参考，因此数值检查通过不改变解剖或可播放 **HOLD**。#59/#12/M2 的后续准入门继续开放；没有新推理、下载或目标导出。CLI 正式支持记录另见 [#61](https://github.com/Derek-X-Wang/nvwa/issues/61) 和 [无窗口实际调用证据](evidence/cli-third-entry/README.md)，与生成动作验收分别记录。

[42 独立导入](../experiments/42-motion-import/REPORT.md) 的 19 项 CLI 边界测试与 [43 authored 映射控制](../experiments/43-rig-mapping/REPORT.md) 通过。父 session 实际验证并在 native/Web 播放原始、naive、calibrated 三份 authored Work；naive 明显折叠，calibrated 呈现声明动作，但端点仍差 `0.277118877976 m`。[历史验收](evidence/m2-authored-controls/ACCEPTANCE.md)中的模型批准待定/真实生成未执行状态及索引属于 #58 的 `b7122a2` 快照；后续 CI 成功与真实样本由本页和 44 分开更新，旧报告、索引和证据字节不重写。authored 控制不能代替真实样本的坐标/rest/目标映射验收，native seek 和独立真人门仍保留。

2026-10-14 的开工基线是 `a094baa048e6e50056e3288ecfa85bb4ac62e140`。其 [应用 CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/38521821416) 和 [证据 CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/38521821332) 已成功；113 项独立 Rust 测试、77 项诊断及两个另计采集器对照、原生/Studio Wasm 编译分别记录。这是历史基线，不能代替后续实现 head、合并后 main 或真实 GUI 的验收。

## 阶段与验收门

| 阶段 | 交付与验收 | 状态 |
| --- | --- | --- |
| M0：Rust 双端底座 | 同一核心/运行时；真实 skin/morph 角色、骨骼动画、命令、保存/重载和双端 Work 交换 | 功能闭环已交付；性能、额外平台和发行缺口保留 |
| 薄 M1：可捏、可编排、可互动 | 三段 authored action、5–10 秒编排、播放/暂停/定位、点击触发与恢复、原生/Web Player | #14–#16 已按有界本地验收完成；完整发行目标未完成 |
| M1.1：界面与稳定性 | 窄 UI 组件整合、中文/输入恢复、有界历史/加载、永久 CPU 绘制回归、Web 构建 A/B | 技术范围已关闭；残余 #3/#4 保持开放，不宣称性能或原始 DPR 故障已解决 |
| M1.2：真实 agent 创作 Alpha | 能力发现→实际 CLI 命令→错误回读/纠正→保存→桌面/Web 继续编辑与播放 | #46→#47→#48 技术交付完成；引导式真人检查已补齐，#49 未引导完整 Alpha 门仍开放 |
| M2：真实动作生成 provider | 精确授权模型/编码器、任务失败/取消、规范化结果、目标 rig 映射和实际生成播放 | 一个真实样本在限定角色上完成工程标定、CLI 校验和双端播放/保存交换；动作质量 HOLD、官方兼容性及产品 provider 未完成，#12 保持开放；单次模型授权已用完 |
| 人物试演室 | A：可调展示舞台；B：静态房间导入；C：按动作需求加入接触与物理 | #70 阶段 A 双端功能/画面/文件往返验收通过，最终审查及 CI 后合并；#69 保留 B/C，独立于多人服务与 Relais，不承诺完整世界编辑器 |
| 内容与沙盒扩展 | Blender 工具、更多角色/服装、指定版本 VRM、IK/接触、只读 VaM 与有限迁移 | 后续逐项定范围，不承诺任意 rig/VAR/插件兼容 |

## M1.2 交付与实验索引

1. [#45 收束 M1.1](https://github.com/Derek-X-Wang/nvwa/issues/45)：核对旧实验 PR，保留原始提交，整理当前索引，将残余验证明确留在开放 backlog。
2. [#46 真实 CLI agent](https://github.com/Derek-X-Wang/nvwa/issues/46)：真实 LLM agent 发现参数/动作和命令合同，制作九秒作品，遇到真实 revision 错误后读取并纠正。原始工具过程与合成重放分开记录。
3. [#47 双端继续编辑](https://github.com/Derek-X-Wang/nvwa/issues/47)：加载 #46 的确切 Work，实际显示角色、播放/定位、UI 修改、保存与整份文档比对。CLI 进程/重载不传递会话历史。
4. [#48 Alpha 交接](https://github.com/Derek-X-Wang/nvwa/issues/48)：提供可执行命令和支持边界，让新的独立操作 session 跟随说明。agent 操作验收与实体真人易用性检查分别记录。
5. [#13 视觉 A/B](https://github.com/Derek-X-Wang/nvwa/issues/13)：已有受控 derivative 在相同 renderer/相机/时间点比较；支持结论限于同拓扑/骨长/语义的 rest-basis 转换。
6. [#12 模型可行性](https://github.com/Derek-X-Wang/nvwa/issues/12)：核查当前本地条件、官方模型/编码器及输出格式；条件不足可按 NO-GO/NOT-RUN 退出。已有 authored action 始终标为手工动作。

Alpha 操作入口：[M1.2 交接与复现](M1.2-ALPHA.md)。实体真人试用单独跟踪 [#49](https://github.com/Derek-X-Wang/nvwa/issues/49)：引导式原生播放、编辑、撤销/重做、保存已通过；后续引导式 Web Player Restart/Pause、胸部点击 wave/恢复及操作清晰度正常；引导式 Web 文件交换、无效 JSON 保留原角色和重新打开有效 Work 恢复九秒播放已通过。记录与评论来源见 [真人试用后续观察](evidence/m12-human-alpha/REPORT.md#follow-on-record-2026-10-15)。保存文字/目的地已获真人确认；最终右下角位置只有技术运行验证，未补做独立真人接受检查。未引导的完整 Alpha 仍未验证，#49 保持开放。

第一版 agent 通过现有 CLI 编辑文件并由 Studio 重载。GUI、CLI 和未来 bridge 共用领域命令；不把离线文件修改描述为控制运行中的窗口。CLI 的 revision 检查针对读入文档，不构成文件系统 CAS；历史和重试记忆属于当前 Editor 会话。

## 持续验证与发行门

| 问题 | 保留的边界与下一决定性条件 |
| --- | --- |
| #3 输入缩放 | OPEN/needs-info；原始 IAB DPR 模拟入口不可用。需要原始受支持控制/轨迹或真实显示尺度迁移；普通 zoom 通过不能关闭原始故障 |
| #4 性能 | OPEN；精确角色首次物理呈现、完全冷状态、原生停顿归因、Web 进程/GPU 总内存和有效 GPU 耗时仍未验证。新条件可得时补测，不将 ready/cadence 当作呈现 |
| #5 Web 截图导出 | 当前顶层成功与 iframe 有界未观察到下载分别保留；历史原因仍 UNKNOWN |
| #9 平台 | macOS/受测浏览器之外按目标逐项验证；编译、实际启动、功能、性能分开记录 |
| #10 发行 | 依赖/字体/资产适用完整条款、第一方许可、签名/公证与干净机器启动仍有缺口。23 个缺少条款文本的历史包/47 个缺口记录未被实验37消除 |
| #11 角色品质 | 手形、权重和形变极值需进一步视觉检查；单一 fixture 不能代表生产级人物系统 |

## 历史证据与实验归档

旧路线图原文保留于 [历史快照](history/ROADMAP-through-m11.md)。其中的“当前”“待合并”和测试数量均属于当时的记录；新状态以本页、各任务及最终 PR 的精确 head/main 验收为准。

[旧实验 PR 清单](history/m11-experiment-pr-inventory.json)逐路径核对完整分页结果。#22/#28/#29 的历史实验并未全部进入 main；关闭它们表示结束实验分支的整合请求，不表示全部证据被采用，也不表示未验证项通过。保留分支和精确提交链接，不删除唯一副本。

- [#22 原始启动/输入证据](https://github.com/Derek-X-Wang/nvwa/tree/11fc789e898119e0ed2b423f8a909dacb547f772)：诊断成果按原边界归档。
- [#28 UI/Web A/B 原型](https://github.com/Derek-X-Wang/nvwa/tree/bb21905879d1fdd6dd3a37ba38400d90801a6b72)：窄 UI 模式已通过 #26/#30 单独整合；较小 Web 配置未采用。
- [#29 Web cadence 跟进](https://github.com/Derek-X-Wang/nvwa/tree/49d116c69cb9e7cfaa6f2c4356749ebd1504dd4e)：保留 DEFER 和无效测量条件，不提升为性能结论。

权威范围：[v2 任务书](specs/Nvwa_Codex_Prototype_Brief_Rust_First_v2.md)、[双轨 kickoff](specs/Nvwa_Codex_Kickoff_Parallel_Spikes.md)、[领域合同](implementation/contract.md)。历史能力/实验/验收入口：[M1](M1-VERIFICATION.md)、[实验](EXPERIMENTS.md)、[性能](PERFORMANCE.md)、[M1.1 最终验收](evidence/m1-1-final/ACCEPTANCE.md)、[源证据37](../experiments/37-pinned-notice-sources/REPORT.md)。
