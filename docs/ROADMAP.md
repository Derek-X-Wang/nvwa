# Nvwa 路线图

## 当前阶段：M1.2 真人独立验收待完成；M2 有界实验获授权（2026-10-15）

Nvwa 的目标是：捏出角色、编排或生成动作、加入互动，再以桌面应用和网页分享。人和 agent 使用同一份 Work 和同一套 Rust 命令。

M1.1 已按技术范围收束。 [M1.2](https://github.com/Derek-X-Wang/nvwa/milestone/2) 的离线 CLI 创作、双端继续编辑和交接已由 [PR #50](https://github.com/Derek-X-Wang/nvwa/pull/50) 交付，合并 main 为 `9502dd370b262761bf4f4f10f2418163c7574946`。保存反馈 #51 已由 [PR #52](https://github.com/Derek-X-Wang/nvwa/pull/52) 交付，合并 main 为 `f7b15eb166ed8a616dd73965cf23d1b7dcad61f6`。这些技术交付和后续引导式真人观察不等于完整 Alpha 关闭。

新增授权：开展 [M2](https://github.com/Derek-X-Wang/nvwa/milestone/3) 真实生成、结果导入和目标 rig 映射的有界实验，分别跟踪于 [#54 真实短动作生成](https://github.com/Derek-X-Wang/nvwa/issues/54)、[#55 动作导入](https://github.com/Derek-X-Wang/nvwa/issues/55) 和 [#56 rig 映射](https://github.com/Derek-X-Wang/nvwa/issues/56)。隔离实验进行中，具体结果与边界由 #54–#56 分别记录；真实推理未执行、产品 provider 未交付，不包含产品 UI 或依赖整合；模型/编码器下载或额外算力仍需具体批准。#12 的真实输出与生成播放验收条件仍独立开放；先前的 NO-GO 保留为当时的准备度结论，不是实际生成证据。实时 Studio 桥接和公开二进制发行仍属后续范围。

2026-10-14 的开工基线是 `a094baa048e6e50056e3288ecfa85bb4ac62e140`。其 [应用 CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/38521821416) 和 [证据 CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/38521821332) 已成功；113 项独立 Rust 测试、77 项诊断及两个另计采集器对照、原生/Studio Wasm 编译分别记录。这是历史基线，不能代替后续实现 head、合并后 main 或真实 GUI 的验收。

## 阶段与验收门

| 阶段 | 交付与验收 | 状态 |
| --- | --- | --- |
| M0：Rust 双端底座 | 同一核心/运行时；真实 skin/morph 角色、骨骼动画、命令、保存/重载和双端 Work 交换 | 功能闭环已交付；性能、额外平台和发行缺口保留 |
| 薄 M1：可捏、可编排、可互动 | 三段 authored action、5–10 秒编排、播放/暂停/定位、点击触发与恢复、原生/Web Player | #14–#16 已按有界本地验收完成；完整发行目标未完成 |
| M1.1：界面与稳定性 | 窄 UI 组件整合、中文/输入恢复、有界历史/加载、永久 CPU 绘制回归、Web 构建 A/B | 技术范围已关闭；残余 #3/#4 保持开放，不宣称性能或原始 DPR 故障已解决 |
| M1.2：真实 agent 创作 Alpha | 能力发现→实际 CLI 命令→错误回读/纠正→保存→桌面/Web 继续编辑与播放 | #46→#47→#48 技术交付完成；引导式真人检查已补齐，#49 未引导完整 Alpha 门仍开放 |
| M2：真实动作生成 provider | 精确授权模型/编码器、任务失败/取消、规范化结果、目标 rig 映射和实际生成播放 | 隔离实验进行中，具体结果与边界由 #54–#56 分别记录；真实推理未执行、产品 provider 未交付；下载/额外算力另行批准 |
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
