# Nvwa 路线图

更新：2026-10-29。目标：让用户捏好一个人物，为它编排动作，在试演舞台播放，并保存为可继续编辑、跨入口交换的作品（Work）。

本轮 B1 动作编排的编译与实际验收锁定 [`30aa99e`](https://github.com/Derek-X-Wang/nvwa/commit/30aa99e5bba3fef82ba4d533ce8a6ee01586a17b)，与后续文档提交分开。实现及实际 Web／CLI 验收已完成；发布回执由 [#124](https://github.com/Derek-X-Wang/nvwa/issues/124) 记录，此页不预判 PR／main CI。用户可在已编辑人物上创建／恢复八秒预制动作，修改行、撤销／重做、播放并保存交换；见[阶段证据](evidence/b1-motion-authoring/README.md)。

[PR #120](https://github.com/Derek-X-Wang/nvwa/pull/120) 候选 head `51cff65c34966a76511e317e76ba8bd4d75bafba` 仍保持 **HOLD**；数值候选不计为 main 产品交付，不继续其 CI 诊断或重试。

## 七个阶段：能力与边界

| 阶段 | 用户已能做什么／下一结果 | 状态与限制 |
| --- | --- | --- |
| M0：共享 Rust 底座 | 桌面、Web、CLI 共用 Work 与命令；编辑、撤销／重做、保存／重载及文件交换 | 核心闭环已交付。CLI 离线编辑文件，不控制运行中的窗口；性能和发行缺口保留。 |
| 薄 M1：编排与游玩 | 原始 GLB 人物的三段预制动作、5–10 秒编排、播放／暂停／定位、点击触发与恢复、Studio／Player | 有界功能已交付。预制动作不是 AI 生成；不承诺任意角色兼容。 |
| M1.1：界面与稳定性 | 窄 UI、中文与输入恢复、有界历史／加载、CPU 绘制回归 | 技术范围已收束。#3 原始缩放复现仍阻塞；#4 性能测量仍有缺口。 |
| M1.2：agent 创作 Alpha | 能力发现→CLI 创作与纠错→保存→桌面／Web 继续编辑播放；独立离线 CLI 资产包 | 技术交付及引导式真人观察已有证据。[#49 未引导完整试用](m12-unassisted-trial/README.md)仍开放，不能宣告完整 Alpha 关闭。 |
| 正式 B1 人物 | 八个体型／面部参数、short04／short01 外观；在当前 Work 创建／恢复 arm4s→knee4s，编辑动作／时长／顺序并保存交换 | 动作编排实现及实际 Web／CLI 验收已完成，发布回执见 #124；[证据与原文件](evidence/b1-motion-authoring/README.md)。旧 Work／默认 short04 保留，完整外观与衣物质量仍 HOLD。 |
| M2／M2-A：真实动作 | 既有真实 90 帧样本已在旧 GLB 人物完成工程标定、播放与保存交换；下一步接入正式 B1 | M2 质量 HOLD，产品生成服务未交付。[#118](https://github.com/Derek-X-Wang/nvwa/issues/118) 的正式 B1 导入、播放、CLI／Web 保存闭环尚未交付；数值候选不等于产品完成。 |
| 人物试演室 | 阶段 A：可保存的灯光、背景／地面、相机和画质设置，随 Work 交换 | 阶段 A 已有桌面／Web／CLI 证据。房间导入与物理保留为后续 B／C；世界编辑器、多人及 Relais 不进入当前范围。 |

## 当前用力点

| 优先级 | 可交付结果 | 完成或恢复条件 |
| --- | --- | --- |
| 已交付：[现有 main 可直接体验的捏人／试演入口 #121](https://github.com/Derek-X-Wang/nvwa/issues/121) | 静态 Web 入口可选择八参数 short04／short01 人物或原始九秒作品，一步进入编辑或 Player | PR #122 已合并，main CI 已通过；复用现有 Work 与路由。保留该轮实际进入、编辑／播放及保存交换证据。 |
| 当前主线：B1 动作编排／#124 | 当前人物的有限八秒编排、行编辑、撤销／重做、播放／暂停／定位／结束及 Web→CLI→Web 交换 | 实现及实际验收已完成；240 项 workspace 测试、原生／Wasm 编译、Web 导出与完整16组 portable 通过。实际交换的 revision29 文件逐字节一致；发布回执由 [#124](https://github.com/Derek-X-Wang/nvwa/issues/124) 记录。普通桌面画面按策略记 NOT-RUN；不等同于真实动作导入或质量解禁。 |
| 上一阶段：GUI 发型选择 | 在已编辑的八参数人物上切换现有 short04／short01，保留体型、动作、舞台和历史 | 保留[该阶段快照](evidence/hair79-selector/RESULTS.md)与 [#79](https://github.com/Derek-X-Wang/nvwa/issues/79) 的发布记录；本轮不改写旧上下文、断言或质量结论。 |
| 停放：M2-A／#118 | 正式 B1 播放既有真实短动作，完成 CLI→Web→CLI 文件闭环 | 依赖 #120 的旋转基础与来源准入。解除该依赖后，先完成实际标定和默认体型，再逐步验收播放／交换；不把数值候选当作完成。 |
| 停放：#120、CI／缓存优化 | 保留原候选与失败记录，停止继续诊断和重试 | 仅在新的明确授权与有界验收方案具备后恢复。当前自然 main CI 预留一次，不挪用。 |
| 停放：#79／#80 质量研究 | 保留已交付 short01 及既有 REJECT／HOLD 结果 | 出现能解释已知缺陷的新证据或明确资产方案，并先定一轮判定与停止条件，再恢复；不循环采集旧候选。 |

主线之外最多保留一条副线。每次交付后，或连续两次尝试没有实际能力、画面或可用性收益时，重新排序并暂停原循环。本次入口交付只做一轮有界产品整合；完成后优先复盘实际人物创作与动作能力。每周做一次只读组合复盘，请 Astra 审视用户收益、依赖、证据与成本，提出下一主线＋副线建议；评分只作排序参考，已授权且前提满足的日常推进继续自主执行。

## 不被阶段收束消除的缺口

[#79](https://github.com/Derek-X-Wang/nvwa/issues/79) 的完整发际／眼睑／接触质量、[#80](https://github.com/Derek-X-Wang/nvwa/issues/80) 衣物和 M2 动作质量继续 **HOLD**；[#112](https://github.com/Derek-X-Wang/nvwa/issues/112) 原始失败、[#3](https://github.com/Derek-X-Wang/nvwa/issues/3) 阻塞、[#4](https://github.com/Derek-X-Wang/nvwa/issues/4) 测量缺口保留。#86 呈现稳定性、其他平台及公开发行仍需各自证据。

日常按[验收策略](agents/verification.md)运行相关 Web／CLI 验收；桌面专项和既有自动测试、原生／Wasm 编译、CI 门禁保留。普通桌面画面按大版本策略延后并记 `NOT-RUN`。旧实验通过不能替代当前提交的实际验收；不新增云端发布、下载或模型推理授权。

证据入口：[B1 动作编排](evidence/b1-motion-authoring/README.md) · [人物基础阶段总结](closeout/character-foundation-20261020.md) · [八参数人物](evidence/b1-character-quality/RESULTS.md) · [short01](evidence/hair79-short01/README.md) · [外观保存交换](evidence/b1-appearance-work/RESULTS.md) · [试演舞台 A](evidence/rehearsal-stage/ACCEPTANCE.md) · [CLI 支持](CLI-SUPPORT.md)。各报告的历史状态只属于其原提交与验收范围。

完整历史沿革保留于固定 main 提交的[原路线图（916215a）](https://github.com/Derek-X-Wang/nvwa/blob/916215a116cbc4ee4d55f57d53fe6e892f7b1303/docs/ROADMAP.md)，包括更早的快照与实验索引；原报告、失败、哈希和素材不改写。
