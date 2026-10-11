# Nvwa 路线图

> 范围依据：[启动任务](specs/Nvwa_Codex_Kickoff_Parallel_Spikes.md)、[Rust-first 原型任务书](specs/Nvwa_Codex_Prototype_Brief_Rust_First_v2.md)、[实验登记](EXPERIMENTS.md)、[M1 验收](M1-VERIFICATION.md)、[问题索引](ISSUES.md)、[交接](HANDOFF.md)及各实验 `REPORT.md`。这是一份状态与证据登记，不授权后续功能实现。

## 里程碑与当前状态

| 里程碑 | 目标 | 已证实状态与边界 |
|---|---|---|
| M0：双端 Rust Studio | 共用核心、桌面/Web 运行时、真实可变形角色、骨骼动画、命令、存档与跨端重载。 | **已交付**。M0 首次发布为 `d74493d`；薄 M1 后续合并后的 main 当前记录为 [`96c00de`](https://github.com/Derek-X-Wang/nvwa/commit/96c00dedf9a4a74038edb7abf20d99d89871ae6b)。真实原生 Metal 与 WebGPU 运行、双向作品交换、33 项 M0 Rust 测试及构建/测量证据已记录。M0 的已知验收缺口仍未全部关闭；功能闭环不等于完整发布就绪。见 [M0 实验](EXPERIMENTS.md)、[性能记录](PERFORMANCE.md)。 |
| M1：可捏、可编排、可分享 | 任务书定义的较完整阶段：有限角色控制、简单时间轴、三段动作、撤销/重做、双端保存/重载、互动、静态 Player、可分发原生构建、CLI/agent 说明。 | **用户批准的薄 M1 已合并**：三段动作与播放/暂停/定位；点击角色触发一次 wave 后恢复作品；原生/Web 静态 Player。#14–#16 按记录的本地验收关闭。PR #17 独立 Standards 审查发现一项 P3 transport 重复代码建议，修复提交 `976331d` 已合并到 main 的 `96c00de`，并通过 targeted rereview；Spec 轴无发现。独立修复验收记录了 57 项测试、strict checks、双端 release 构建与实际运行。该 57 项结果是字体集成前的快照；当前字体分支另有 59 项测试、双端构建及实际中文/Unicode 文件验收；尚待合并。完整 M1 任务书的输入、缩放、性能、发行等验收缺口仍在。见 [PR #17 审查](evidence/pr17-review/REVIEW.md)和[修复验收](evidence/pr17-review/ACCEPTANCE.md)。 |
| M2：真实动作生成 | 一个真实 provider、任务状态/取消/失败、规范化动作、到目标 rig 的映射及质量验证。 | **提议；未开始，也未获准实施。** 现有实验只证明隔离的 authored-preset 导入边界；没有进行模型推理。需先解决授权模型/运行时、输出格式和目标 rig 映射，再决定是否进入 M2。见 [AI 实验报告](../experiments/05-ai-motion/REPORT.md)。 |
| 后续（顺序仍待决） | 简单 Blender 插件 → 额外角色/服装验证 → 指定版本 VRM → 约束/IK/接触 → 只读 VaM 检查器 → 经许可审核的迁移子集。 | **全为提议，未授权实现。** VaM 检查器只读；真实样本与许可不足时，合成包解析不能作为兼容证据。软体物理、头发/布料、VR、多人、市场、任意脚本插件不在前三个里程碑。 |

**当前顺序：**PR #17 独立审查和合并已完成。#1 字体修复在 `fix/cjk-input-acceptance` 通过技术验收并等待合并；#2 的原生错误恢复、两端 Unicode Save/Open、Web 拖动/撤销与按键焦点已验证。原生自动化拖动、剪贴板/Command 组合键和批量中文输入未取得预期结果，不能外推为真人输入故障。用户解锁后，原生点击修改/撤销/重做及整份作品保存比对、文本按键焦点保护和窗口缩放/恢复均通过。原生自动化连续拖动仍未得到有效输入；物理输入及 OS 失焦切换待真人检查。同帧/跨帧 Command+A 的真实依赖库对照已复跑并独立审查；同帧组合键丢失 modifier，但 OS/CUA 实际事件序列仍未知，暂不整合 workaround。见[输入事件实验](../experiments/07-native-input-events/REPORT.md)。见[解锁后验收](evidence/input-fonts/UNLOCKED-ACCEPTANCE.md)。先完成剩余输入验收，再按风险重排 #3/#4/#6/#8/#9/#10 等稳定性和发行缺口；不承诺日期或工期。

## 已验证的风险与限制

| 项目 | 证据支持的结论 | 影响/仍未知 |
|---|---|---|
| 单一角色的能力边界 | 原创 CC0 fixture 有单一连续蒙皮主体、18 骨骼、4 个不同 morph、3 个手工动作；原生与 Web 实际播放已验证。 | 这是风格化固定 rig，不代表任意角色导入。手部粗糙；腋下及极端形变可能夹皱，生产级权重和全组合视觉检查未完成。见 [角色报告](../experiments/01-character/REPORT.md)。 |
| 导出复现性（#7） | 两次独立 Blender 导出的 GLB/Blend **字节不同**；已测拓扑、结构与 morph 数据保持一致，差异原因未定位。 | 不得声称字节可复现。发布时需重写 profile/manifest 以匹配实际文件；跨版本/跨平台未测。 |
| 字体与输入（#1、#2） | 同 cmap static Regular 400 fallback：30,890 映射码点、31,036 glyph；standalone gzip6,303,513bytes，对比 variable11,276,563bytes。59 项测试、strict checks、native/Web release 与实际中英标签、中文文件名、Unicode GUI Save/Open 通过；完整 JSON 等于 baseline。原生 missing-work 经真实 GUI Open 恢复。Web 一次连续拖动提交一个 revision，一次 Undo 恢复全作品；文本 Space 不暂停播放。 | #1 待合并。罕见补充汉字仍缺失；不等于真实 IME 通过。解锁后原生点击修改/撤销/重做和整份作品保存比对、文本焦点与窗口缩放恢复通过。原生 CUA 连续拖动、剪贴板/Command、批量 Unicode entry 未获有效结果；物理输入与 OS 失焦切换仍待真人验证，不将自动化限制视作真人缺陷。见 [验收](evidence/input-fonts/ACCEPTANCE.md)、[字体实验](../experiments/06-cjk-fonts/REPORT.md)。 |
| 浏览器缩放（#3） | IAB 视口/DPR 模拟曾出现显示与输入比例陈旧；普通未模拟视口的输入通过。 | 不把模拟视口结果外推到所有浏览器。Live resize/DPR 恢复仍待验证。 |
| 性能与启动（#4） | M0 连续空闲 release cadence：原生 p95 8.65 ms、Web 11.20 ms。薄 M1 Player 的 600 样本约为原生 8.327/8.924 ms、Web 8.300/9.500 ms（p50/p95）。M1 样本来自 9.5 秒作品已结束并停在末帧之后。压缩文件和为 14,179,929 bytes。 | cadence 不是 GPU 帧完成时间。M1 数字不证明持续动画表现；首次精确呈现、冷启动 Web、浏览器/GPU 内存未测。native 首次截图约 8.52 秒只是可见性的上界。Web 重复 GLB 请求仍可多传约 1,129,081 bytes（#6）。30 fps/30 MB 是任务书初始预算，不是完整性能验收。见 [性能记录](PERFORMANCE.md)。 |
| 命令历史（#8） | 命令事务、撤销/重做和 CLI/GUI 文档结果等价已验证。 | 历史和重试记录只在进程会话内，当前没有内存上限；长时间编辑的内存边界未验证。 |
| 互动命中 | 薄 M1 用原 rig 的胸/头保守目标触发 wave；恢复后的文档与交互前完整相等。 | 不是变形网格精确拾取。所有姿势/morph 极值下的热点包含性未验证；不能外推为任意 rig 支持。 |
| 动作重定向（#13） | 真实动作的 19 个采样点数值 A/B：直接复制旋转的最大顶点误差约 0.868 m；受控 rest-basis 修正约 3.08e-8 m，退化输入检查通过。 | 仅证明骨长/拓扑/语义相同的坐标基变换。目标 GLB 未在渲染器视觉播放；不同骨长、缺骨、任意 rig、root motion、IK/接触均未验证。见 [A/B 报告](../experiments/04-retarget-basis/REPORT.md)。 |
| AI 动作（#12） | 本地有限目录探测未发现可用 Kimodo runtime/授权权重；9 项 Python 测试只导入有明确标记的手工 wave preset。 | 真推理、M2 资源用量和播放兼容均为 NOT-RUN。Kimodo 文档对输出骨数有 30/77 的差异；M2 16 GiB 可行性和准确许可/权重仍需核对。不要把 preset 称作 AI。见 [AI 实验报告](../experiments/05-ai-motion/REPORT.md)。 |
| 平台/发行（#9、#10） | macOS 原生和记录的 IAB WebGPU 环境完成了实际本地运行。 | 其他 OS、其他浏览器/WebGPU、公开托管、签名/公证和发行验证未完成；本地构建不能替代这些证据。 |

## 提议的原型与验证队列

以下都是**候选验证工作，不是实现授权**。PR #17 已合并；当前 #1 字体分支验证已完成，等待合并；先完成 #2 剩余输入验收。M2、一般 rig 支持和 VaM 工作仍需单独明确范围。

| 原型 | 问题与 A/B 候选 | 最小可复现证据 | Go / no-go | 依赖 |
|---|---|---|---|---|
| #1 CJK 字体 | A：完整 variable；B：同 cmap static Regular400。选择 B，standalone gzip 少约4.97MB；共享回退已集成并完成技术验收。 | 实际 native/Web 中文标签/文件名、GUI Unicode Save/Open、59测试、双端构建和完整随包许可。Web 同文件集合 gzip 增加6,314,437bytes，总20,497,855bytes。 | 当前受测字符/两端范围通过，等待合并；保留补充汉字和真实 IME 边界。 | [验收/复现](evidence/input-fonts/ACCEPTANCE.md)、[许可](SOURCES-LICENSES.md)。 |
| #2 输入与失败恢复 | 原生实际键入/Open恢复；Web实际按键、剪贴板、连续拖动/Undo；原生适配器组合键和拖动与物理输入分别验证。 | 已通过：原生 missing-work GUI恢复、两端Unicode Save/Open、Web revision6→7的一次拖动及Undo全量恢复revision8、文本Space焦点保护。尚需实际物理IME/Command/clipboard、原生drag、OSblur/refocus/zoom。 | 已测范围通过；原生适配器操作未得预期结果保持未验证，Mac锁定需人工解锁。只有实际产品缺陷才新建缺陷报告。 | [验收](evidence/input-fonts/ACCEPTANCE.md)、[输入诊断](evidence/input-fonts/INPUT-DIAGNOSIS.md)；公开 baseline 为 `docs/evidence/m1/web-sequence.nvwa.json`。 |
| #13 受控 rig 重定向视觉检查 | A：直接复制关节旋转（数值实验已失败）；B：按 rest basis 转换（数值实验已通过）。 | 用原 fixture 和现有两个 derivative GLB，在同一 runtime、相机和 wave 采样点播放；保留真实画面/播放记录，并复核数值误差及退化输入。 | B 视觉动作可辨且无基姿/末端明显偏移，才把结论扩大到这类受控 rig；否则只保留数值结论，不支持一般重定向。 | [已有受控 A/B 产物](../experiments/04-retarget-basis/REPORT.md)；原 fixture；不得替换成不同拓扑来扩大结论。 |
| #6 GLB 重复传输 | A：当前两个实际 fetch 路径；B：单份已校验字节在加载路径间复用。 | 静态 Player 实际请求跟踪；记录 GLB 请求数、传输字节、SHA-256 校验结果和角色成功加载。 | B 保持完整性校验且只请求一次则通过；否则保留当前正确性并明确重复传输。 | 实际 Web release bundle、静态服务器、网络请求记录。 |
| #4 冷启动与首次呈现测量 | A：已有 warm/steady cadence；B：全新冷 Web 会话并捕捉首次真实像素。 | 固定工作、设备、浏览器和 viewport；区分首次呈现、资产 ready、steady cadence，记录实际画面及可取得的内存/GPU证据。 | 只有真实首帧/冷启动与资源数据足以对照既定预算时才作性能 go/no-go；测不到的量明确 NOT-RUN。 | 单一 renderer、固定 release artifact；不把 cadence 当 GPU timing。 |
| M2 provider 可行性门 | A：Kimodo 精确版本与获准本地权重；B：另一个逐项许可核验的本地 provider；基线为当前 authored-preset 导入，不算生成。 | 先确认本地 runtime、确切权重/代码版本、许可和输出 schema；获准后才做一次真实推理。保存生成元数据、资源/延迟、规范化动作、目标 rig 映射、失败/取消行为及真实播放质量。 | 只有实际生成、许可可接受、输出可映射并由 Nvwa 播放，才建议启动 M2；条件缺失即 no-go/继续 NOT-RUN，不下载权重或改称 preset。 | 单独授权的 M2 范围；本地可用算力/权重；模型、编码器与动作资产各自许可；与 #13 映射验证衔接。 |
| 额外角色 / SOMA-X 离线导出 | A：继续使用原创固定 rig；B：选一个可核实许可的额外参数角色，离线导出到同一窄 profile。 | 固定单位、轴向、rest pose、skin/morph/服装语义；真实双端加载和形变极值检查；代码/资产/权重许可分别记录。 | 只有测试过的角色/参数进入支持清单；不得因能显示模型就承诺任意捏人。 | 在 M1 稳定后另定范围；SOMA-X 是候选研究，不移植其完整计算栈。 |
| Blender Validate / Export / Send | A：当前脚本校验与离线导出；B：最小按钮调用同一约定及 CLI。 | 同源导出、校验报告、失败不覆盖发布资产；调查字节漂移并记录语义稳定性。 | 可重复运行且错误清楚才采用；不得用“Send”绕过已有校验。 | #7 与固定 GLB/profile 合同；无需双向完整同步。 |
| VRM 指定版本适配 | A：当前普通 GLB；B：一个获准真实 VRM0.x 或1.0样本。 | 检查 humanoid、表情、视线、材质、spring bone 等扩展，逐项实际渲染并报告不支持。 | 单一版本、测试样本的能力通过才扩大；普通 glTF 显示不等于完整 VRM。 | 额外角色合同；两版本分别声明，不一起默认为支持。 |
| 两骨骼 IK / 接触 | A：重定向后的未修正动作；B：一个两骨骼手目标或脚接触修正。 | 同一动作/目标，测末端误差、脚滑、不可达/共线等退化情况，并真实播放。 | 明确改善且稳定才集成；否则保留实验，不引入完整物理。 | 先有实际动作映射播放；与 M2 质量关衔接。 |
| 后续 VaM 只读检查器 | A：获准真实样本 / B：标明为合成的最小容器 fixture。 | 只读检查容器、元数据、依赖和未知类型；验证路径穿越、文件数/解压大小上限；不执行脚本。 | 合成样本只能通过解析边界；声称真实格式能力需授权真实样本验证。许可字段不等于法律授权。 | P0/M0 不受拖慢；授权样本；单独批准后续实验。 |

**原型退出规则：**每项先写问题、假设、对照、验收与退出条件；实验放 `experiments/`，留下 `REPORT.md` 和复现命令。正式测量仅一个 Nvwa 渲染器，暂停竞争重任务；默认最多两个重编译任务。不租用 GPU、不调用付费 API、不扩大 CI。结果可以 adopt/reject/inconclusive/blocked，失败实验不阻塞主线。

## 证据索引

- 里程碑原文：[v2 brief](specs/Nvwa_Codex_Prototype_Brief_Rust_First_v2.md)；双轨边界与 throwaway 规则：[kickoff](specs/Nvwa_Codex_Kickoff_Parallel_Spikes.md)。
- 当前整合与开放工作：[M1 验收](M1-VERIFICATION.md)、[问题索引](ISSUES.md)、[交接](HANDOFF.md)。
- 已做实验与决策：[实验汇总](EXPERIMENTS.md)、[角色](../experiments/01-character/REPORT.md)、[命令](../experiments/02-command-transactions/REPORT.md)、[运行时/UI](../experiments/03-runtime-ui/REPORT.md)、[重定向 A/B](../experiments/04-retarget-basis/REPORT.md)、[AI motion](../experiments/05-ai-motion/REPORT.md)。
