# Nvwa 路线图

更新：2026-11-03。目标：让 AI 成为主要创作者，创建和修改人物、编排动作并查看试演结果；人主要审核作品、提出反馈。桌面、Web 与 CLI 共用可继续编辑、跨入口交换的作品（Work）。

八秒编排阶段的编译与实际验收锁定 [`30aa99e`](https://github.com/Derek-X-Wang/nvwa/commit/30aa99e5bba3fef82ba4d533ce8a6ee01586a17b)，与后续文档提交分开。用户可在已编辑人物上创建／恢复八秒预制动作，修改行、撤销／重做、播放并保存交换；见[阶段证据](evidence/b1-motion-authoring/README.md)与 [#124 发布回执](https://github.com/Derek-X-Wang/nvwa/issues/124)。

该八秒阶段已随 PR #125 合并，main 验证通过。后续 [#126 多段编排](https://github.com/Derek-X-Wang/nvwa/issues/126) 与 [#127 agent CLI 实例](https://github.com/Derek-X-Wang/nvwa/issues/127) 已随 PR #128 合并；预算修正 PR #129 后，main `b8bf864` 的[正常 CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/41367991273)通过。已交付当前人物上添加／复制现有动作、三段以上10–30秒编排及真实 Web／CLI 交换；见[阶段记录](evidence/b1-multisegment/README.md)与[CLI 实例](examples/b1-agent-authoring/README.md)。

[#130 独立 AI 创作试用](https://github.com/Derek-X-Wang/nvwa/issues/130)已完成：新上下文 agent 从自然语言目标创建20秒作品，按反馈及澄清另存连续19秒版本；独立 CLI 重放和实际 Web 播放／保存交换通过。结实上身的表达仍受八参数限制；试用不代表 AI 生成动作或完整 Alpha 关闭。

[#131 AI 视觉反馈创作闭环](https://github.com/Derek-X-Wang/nvwa/issues/131)已随 PR #132 合并，main `96cda1b` 的[正常 CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/41593771147)通过。已补清时序编辑语义，复用 Web 取得指定 Work、保存相机和时间点的真实预览。新上下文 agent 实际看图并只修改相机，另存近景；两版实际图片、独立逐字节重放、普通保存交换和原生251项检查通过。第二轮浏览器打开需要整合会话接力，人物质量 HOLD 保留。见[当时的候选验收记录](evidence/agent-visual-feedback/README.md)与 [#131 最终发布回执](https://github.com/Derek-X-Wang/nvwa/issues/131#issuecomment-6598741363)。

上一轮 [#133 AI 目标驱动捏人与局部修订](https://github.com/Derek-X-Wang/nvwa/issues/133) 在固定正面与侧前方视角下，根据真实画面修改人物本身。首例完成六张真实图和唯一一次修订，身份与字段审计通过，但独立图像评审仍为 **HOLD**：主要是末端下巴变尖，未建立清楚的下半脸收窄与侧前方鼻部变宽。已停止该案例的后续调参；新一轮 #134 不改写这个结论。本轮结果尚未计为产品交付。

当前主线是 [#134 人物轮廓控制闭环](https://github.com/Derek-X-Wang/nvwa/issues/134)，设计依据见[下颌／脸颊调查](research/jaw-cheek-control/README.md)。六个获准的 MPFB 源 target 已核查；`chin-bones` 尚不支持直接命名为下颌宽度。双侧脸颊饱满度的[独立源参考](evidence/b1-contour-reference/README.md)已通过盲评，原始过曝失败及一次统一曝光修正保留。候选已接入显式新版本的 `cheek_fullness`，保留旧八参数人物；独立 AI 从能力发现开始创作，初稿视觉收益不足，依据画面修订一次后，匹配正面／35度近景通过独立局部视觉审查。普通 Web 编辑、撤销重做、有限八秒播放、真实 CLI 文件交换和命令逐字节重放已有实际证据，见[创作实例](evidence/b1-contour-agent/README.md)。

当前仍未发布，等待正式 PR／main CI。新增精确比较最初失败，单次受控探针及独立复审支持只修正新增测试的准备顺序；修正后完整93项 runtime 测试、82项 Studio 测试、实际原生／Wasm 构建和16组 portable 已通过。条件等价不承诺任意独立重开的逐位重复，全部精确断言和旧失败记录保留。额外全目标 Clippy 仍因未改动旧代码的诊断失败，既有 core／CLI lint 门禁不变。近景判断不证明完整人体、所有体型或嘴鼻独立性，#133 和所有质量 HOLD 保留。

[PR #120](https://github.com/Derek-X-Wang/nvwa/pull/120) 候选 head `51cff65c34966a76511e317e76ba8bd4d75bafba` 仍保持 **HOLD**；数值候选不计为 main 产品交付，不继续其 CI 诊断或重试。

## 七个阶段：能力与边界

| 阶段 | 用户已能做什么／下一结果 | 状态与限制 |
| --- | --- | --- |
| M0：共享 Rust 底座 | 桌面、Web、CLI 共用 Work 与命令；编辑、撤销／重做、保存／重载及文件交换 | 核心闭环已交付。CLI 离线编辑文件，不控制运行中的窗口；性能和发行缺口保留。 |
| 薄 M1：编排与游玩 | 原始 GLB 人物的三段预制动作、5–10 秒编排、播放／暂停／定位、点击触发与恢复、Studio／Player | 有界功能已交付。预制动作不是 AI 生成；不承诺任意角色兼容。 |
| M1.1：界面与稳定性 | 窄 UI、中文与输入恢复、有界历史／加载、CPU 绘制回归 | 技术范围已收束。#3 原始缩放复现仍阻塞；#4 性能测量仍有缺口。 |
| M1.2：agent 创作 Alpha | 能力发现→CLI 创作与纠错→保存→桌面／Web 继续编辑播放；独立离线 CLI 资产包 | 技术交付及引导式真人观察已有证据。[#49 未引导完整试用](m12-unassisted-trial/README.md)仍开放，不能宣告完整 Alpha 关闭。 |
| 正式 B1 人物 | 八个体型／面部参数、short04／short01 外观，以及添加／复制现有动作的多段编排 | 八秒阶段回执见 #124；多段编排已随 PR #128 合并，后续 main 验证通过；发布结果见 #126／#127。旧 Work／默认 short04 保留，完整外观与衣物质量仍 HOLD。 |
| M2／M2-A：真实动作 | 既有真实 90 帧样本已在旧 GLB 人物完成工程标定、播放与保存交换；下一步接入正式 B1 | M2 质量 HOLD，产品生成服务未交付。[#118](https://github.com/Derek-X-Wang/nvwa/issues/118) 的正式 B1 导入、播放、CLI／Web 保存闭环尚未交付；数值候选不等于产品完成。 |
| 人物试演室 | 阶段 A：可保存的灯光、背景／地面、相机和画质设置，随 Work 交换 | 阶段 A 已有桌面／Web／CLI 证据。房间导入与物理保留为后续 B／C；世界编辑器、多人及 Relais 不进入当前范围。 |

## 当前用力点

| 优先级 | 可交付结果 | 完成或恢复条件 |
| --- | --- | --- |
| 当前主线：[人物轮廓控制 #134](https://github.com/Derek-X-Wang/nvwa/issues/134) | 一个有明确语义和真实视觉收益的新控制，AI 自行发现／使用并看图修订，保留非目标设置和可编辑 Work | 版本化候选、真实 AI 看图修订、局部视觉审查和实际 Web/CLI 功能已验证；测试准备修正经过独立复审，完整 runtime／Studio 测试、构建和 portable 通过。下一步正式 PR CI、合并和 main 验证。额外 lint 失败及原始数值失败保留，不改变既有门禁，不解除其他 HOLD。 |
| 上一轮视觉 HOLD：[AI 目标驱动捏人 #133](https://github.com/Derek-X-Wang/nvwa/issues/133) | agent 根据自然语言外观目标修改人物，固定视角看图并作最多一次局部修订，保留其他设置和可继续编辑的作品 | 首例的命令／捕获／身份通过，但预定视觉收益未通过；唯一修订已用完，不启动第二／第三例，不继续调参、扩参数／素材／运行时或验证框架。保留原始作品与独立判断，等待新的范围决定。 |
| 已交付：[AI 视觉反馈 #131](https://github.com/Derek-X-Wang/nvwa/issues/131) | 指定 Work／保存相机／时间的真实 Web 预览，独立 agent 看图、修改相机、另存与再次查看 | PR #132 合并且 main CI 通过；两版 Work／PNG、命令、身份回执与普通 Web／CLI 交换证据保留。第二轮需要整合会话打开同一预览 URL，不代表任意 agent 浏览器路由均可自助。 |
| 已交付：[现有 main 可直接体验的捏人／试演入口 #121](https://github.com/Derek-X-Wang/nvwa/issues/121) | 静态 Web 入口可选择八参数 short04／short01 人物或原始九秒作品，一步进入编辑或 Player | PR #122 已合并，main CI 已通过；复用现有 Work 与路由。保留该轮实际进入、编辑／播放及保存交换证据。 |
| 已交付：[B1 多段编排 #126](https://github.com/Derek-X-Wang/nvwa/issues/126) | 给当前人物添加／复制现有动作，组合三段以上、10–30 秒作品，并复用排序、删除、时长、历史和播放控件 | 已实际制作五段20.5秒作品，CLI 将末段改短后，Web 正常打开、播放至20秒结束并保存；revision34 读回与 CLI 文件逐字节一致。本地81项 Studio 测试、源码控制、Wasm 构建和完整16组 portable 通过。PR #128 已合并，PR #129 后 main CI 通过；[阶段记录](evidence/b1-multisegment/README.md)。 |
| 已交付：[agent CLI 创作实例 #127](https://github.com/Derek-X-Wang/nvwa/issues/127) | agent 无需打开窗口，通过现有 CLI 发现能力、捏人、设置舞台和发型、编排约20秒动作，再修改并保存 | 脚本、真实 Work、命令及中文说明已有重复执行和独立审查证据；复用现有预制动作，不代表 AI 动作生成。已合并并完成 main 验证；[运行方式](examples/b1-agent-authoring/README.md)。 |
| 已交付：B1 八秒编排／#124 | 当前人物的有限八秒编排、行编辑、撤销／重做、播放／暂停／定位／结束及 Web→CLI→Web 交换 | PR #125 已合并且 main 通过。原阶段240项 workspace 测试、编译、完整16组 portable 及 revision29 逐字节交换证据保留于 [#124](https://github.com/Derek-X-Wang/nvwa/issues/124)。普通桌面画面按策略记 NOT-RUN；不等同于真实动作导入或质量解禁。 |
| 上一阶段：GUI 发型选择 | 在已编辑的八参数人物上切换现有 short04／short01，保留体型、动作、舞台和历史 | 保留[该阶段快照](evidence/hair79-selector/RESULTS.md)与 [#79](https://github.com/Derek-X-Wang/nvwa/issues/79) 的发布记录；本轮不改写旧上下文、断言或质量结论。 |
| 停放：M2-A／#118 | 正式 B1 播放既有真实短动作，完成 CLI→Web→CLI 文件闭环 | 依赖 #120 的旋转基础与来源准入。解除该依赖后，先完成实际标定和默认体型，再逐步验收播放／交换；不把数值候选当作完成。 |
| 停放：#120、CI／缓存优化 | 保留原候选与失败记录，停止继续诊断和重试 | 仅在新的明确授权与有界验收方案具备后恢复。当前自然 main CI 预留一次，不挪用。 |
| 停放：#79／#80 质量研究 | 保留已交付 short01 及既有 REJECT／HOLD 结果 | 出现能解释已知缺陷的新证据或明确资产方案，并先定一轮判定与停止条件，再恢复；不循环采集旧候选。 |

主线之外最多保留一条副线。每次交付后，或连续两次尝试没有实际能力、画面或可用性收益时，重新排序并暂停原循环。本次入口交付只做一轮有界产品整合；完成后优先复盘实际人物创作与动作能力。每周做一次只读组合复盘，请 Astra 审视用户收益、依赖、证据与成本，提出下一主线＋副线建议；评分只作排序参考，已授权且前提满足的日常推进继续自主执行。

## 不被阶段收束消除的缺口

[#79](https://github.com/Derek-X-Wang/nvwa/issues/79) 的完整发际／眼睑／接触质量、[#80](https://github.com/Derek-X-Wang/nvwa/issues/80) 衣物和 M2 动作质量继续 **HOLD**；[#112](https://github.com/Derek-X-Wang/nvwa/issues/112) 原始失败、[#3](https://github.com/Derek-X-Wang/nvwa/issues/3) 阻塞、[#4](https://github.com/Derek-X-Wang/nvwa/issues/4) 测量缺口保留。#86 呈现稳定性、其他平台及公开发行仍需各自证据。

日常按[验收策略](agents/verification.md)运行相关 Web／CLI 验收；桌面专项和既有自动测试、原生／Wasm 编译、CI 门禁保留。普通桌面画面按大版本策略延后并记 `NOT-RUN`。旧实验通过不能替代当前提交的实际验收；不新增云端发布、下载或模型推理授权。

证据入口：[脸颊 AI 创作候选](evidence/b1-contour-agent/README.md) · [B1 动作编排](evidence/b1-motion-authoring/README.md) · [人物基础阶段总结](closeout/character-foundation-20261020.md) · [八参数人物](evidence/b1-character-quality/RESULTS.md) · [short01](evidence/hair79-short01/README.md) · [外观保存交换](evidence/b1-appearance-work/RESULTS.md) · [试演舞台 A](evidence/rehearsal-stage/ACCEPTANCE.md) · [CLI 支持](CLI-SUPPORT.md)。各报告的历史状态只属于其原提交与验收范围。

完整历史沿革保留于固定 main 提交的[原路线图（916215a）](https://github.com/Derek-X-Wang/nvwa/blob/916215a116cbc4ee4d55f57d53fe6e892f7b1303/docs/ROADMAP.md)，包括更早的快照与实验索引；原报告、失败、哈希和素材不改写。
