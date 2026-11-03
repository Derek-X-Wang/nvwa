# AI 看图修订脸颊：候选验收记录

2026-11-03，[#134](https://github.com/Derek-X-Wang/nvwa/issues/134)。
本页记录实际发生的创作与验证。本地功能、修正后的完整 runtime 测试、Studio 测试和构建已通过；候选尚未发布，正式 CI、合并及 main 验证待完成。额外扩大的 Clippy 检查失败另列，不冒称全部检查通过。

## AI 实际做了什么

新上下文 agent 使用独立 CLI 包查询能力，显式创建九参数人物。目标是让同一个人的双侧脸颊明显更饱满，同时保持自然、克制，保留其他参数、short01 外观、舞台和八秒编排。

作者先通过 CLI 制作基线和暂定值为 `0.5` 的初稿。收到实际图片后，先查看基线，再比较初稿。独立图像审查认为初稿变化偏弱，结论为 `HOLD_INSUFFICIENT`。作者据此用共享命令将该值改为 `0.85`，并重新查看两张实际渲染图。独立审查确认两个视角都有可识别的温和脸颊饱满变化，未见新增明显局部面部缺陷；这不证明嘴鼻完全独立。

| 版本 | 可继续编辑的 Work | 正面 | 35度侧前方 |
| --- | --- | --- | --- |
| 基线，`0` | [baseline](baseline.nvwa.json) | [图片](baseline-front.png) | [图片](baseline-angle35.png) |
| 初稿，`0.5`，视觉收益不足 | [draft](draft.nvwa.json) | [图片](draft-front.png) | [图片](draft-angle35.png) |
| 看图修订，`0.85` | [revision1](revision1.nvwa.json) | [图片](final-front.png) | [图片](final-angle35.png) |

原始作品只改变 `cheek_fullness` 和 revision，其他字段相同。近景来自共同的审阅相机副本：方位0／35度、仰角0、距离1.05、目标高度1.5、视场32度，时间固定为0。原始作品保留全身相机16／8度、距离3.8、目标高度0.95、视场36度。每个相机副本也在本目录中保留；没有按候选调整灯光或视角来制造改善。

## agent 可复用的创作方式

先阅读[CLI 创作说明](../../agents/cli-authoring.md)和[实际预览入口](../../agents/visual-preview.md)。使用包含本候选素材的 CLI 包；下面从包根目录执行，`evidence` 指向本页所在目录的绝对路径。

```sh
bin/nvwa-cli new-character-contour assets constructor.nvwa.json
bin/nvwa-cli describe-capabilities constructor.nvwa.json
bin/nvwa-cli apply constructor.nvwa.json "$evidence/baseline-commands.json" baseline.nvwa.json
bin/nvwa-cli apply baseline.nvwa.json "$evidence/draft-commands.json" draft.nvwa.json
bin/nvwa-cli validate draft.nvwa.json assets
```

此时请求并实际查看匹配视角的基线／初稿预览。根据画面决定是否修订。此案例的唯一看图修订是：

```sh
bin/nvwa-cli apply draft.nvwa.json "$evidence/revision1-commands.json" revision1.nvwa.json
bin/nvwa-cli validate revision1.nvwa.json assets
```

这些命令 JSON 是该案例实际使用的原件，带有 `expected_revision`。作者从新目录实际执行八条 CLI 命令，重建 constructor 和三份 Work；四份文件均与原件逐字节相同，三份 Work 的实际素材校验也通过。把命令用于另一份作品时，先查询该作品的能力、人物 ID 和 revision，再生成适用命令；不要照抄旧 revision 或假设所有人物都支持此控制。

`cheek_fullness` 是双侧饱满度，范围 `[-1,1]`，默认0。它不是纯下颌宽度，也不承诺嘴鼻保持。普通 `new-character` 和旧八参数作品保持原版本，必须显式选择新人物才能使用它。八秒举臂／抬膝是既有预制动作，不是 AI 新生成的动作。

## 实际 Web 与动作观察

普通 Studio 用真实文件选择器打开最终 `revision1`，Save 下载的3896字节与作者文件完全相同，SHA256 为 `16e1887c91e2b298f567ae130b91f9631c80a63dba2e4faa1ab87e5669836fb4`。实际 Play 后时间推进，Pause 保持，定位进入抬膝段，8秒结束显示 Replay／complete；播放后 Save 仍与原文件相同。

另一个功能验收作品完成真实 Web Save→新 CLI 校验并修改→普通文件选择器 Web Open→Save；最终3898字节与 CLI 文件一致。该交换属于单独的功能作品，不能冒称最终脸颊案例的参数修订记录。坏 Work、缺失及损坏 V3 素材的实际失败保留了旧八参数人物、最后正常画面和可用历史。

| 固定时刻，原全身相机 | 基线 | 最终人物 |
| --- | --- | --- |
| 2秒举臂 | [图片](baseline-arm-2s.png) | [图片](final-arm-2s.png) |
| 6秒抬膝 | [图片](baseline-knee-6s.png) | [图片](final-knee-6s.png) |

整合者独立查看上述四张原图：姿态和全身轮廓一致，未见新增明显全身、肢体或衣物破损。既有腰部衣物缺口仍可见。此结论仅限这两对同帧图片，不能代替完整动作、全体型或衣物质量验收。

## 身份与判断边界

图片是实际 Rust/Wasm WebGPU 画布 PNG。原始回执确认 Work、revision、相机、时间及真实截图回调；见[预览回执](preview-receipts.json)、[结果摘要](RESULTS.json)和[文件身份](SHA256SUMS.json)。公开回执只保留所需字段并替换本地路径，原始私有回执不改写。指纹确认实际编译源与后续源码仅有一份 `cfg(test)` 文件不同，其他351个输入相同；正式 CI 仍须验证最终源码。

初稿审查的符号链接暴露了基线／初稿标签，因此不称完全盲评。修订审查改用普通匿名图片副本，在固定观察结论后才揭示映射；同一审查者仍有先前案例经验。最终结论是匹配近景的局部收益，不是所有面部区域的独立性证明。

新增精确比较最初失败，同版本旧八参数人物的混合体型重复打开也出现微小浮点差异。后续单次受控探针独立核对真实输入，只统一构建前的 target 遍历顺序，再让真实管线重新生成结果：六对完整缓冲精确相同，统一前记录到四个混合体型差异见证，非零新控制和被改坏的读回也正确拒绝。独立审查允许据此修正本轮新增测试的准备方式；修正后的完整93项 runtime 测试已通过，零失败／忽略，用时223.54秒。精确断言、比较字段、原有案例和负向见证保留，生产计算未改。该证据证明相同输入和顺序下的条件等价，不能证明任意独立重开都逐位重复；所有旧失败记录保留。

## 本地自动检查与构建

| 检查 | 实际结果 | 范围 |
| --- | --- | --- |
| core／CLI 测试与原有 Clippy 门禁 | 81项测试及 Clippy 通过 | CLI 构建输入重新核对，相关代码未因测试准备修正改变 |
| runtime 完整 lib 测试 | 93项通过，零失败／忽略 | 包括修正后的精确比较、原始端点、附件、失败恢复和负向见证 |
| Studio 完整 lib 测试 | 82项通过，零失败／忽略／过滤 | 捕获于测试准备修正前，生产代码不变；不代表原生 GUI 实际操作 |
| 完整 portable | 16组通过，944.51秒 | 捕获于测试准备修正前，原有组、顺序和门槛保留；不是 hosted CI 时间保证 |
| CLI 独立分发 | 普通／`-O` 各13项通过 | 实际搬移解包后执行，包内包含新版本素材和可编辑示例 |
| 实际 Wasm 构建 | Studio 和预览均通过 | 实际图片来自这份构建；后续变化仅为未参与 Wasm 生产构建的测试文件 |
| 原生构建与真实打包 | Mach-O arm64 构建及未签名 `.app` 通过 | 143文件、172,060,661字节；三份底模 manifest／65个 payload、两个新外观绑定／通知、许可证和五个示例核对通过，真实 CLI 从打包素材创建并校验九参数作品 |
| 额外 runtime／Studio 全目标 Clippy | **FAIL**，退出101 | 超出既有 core／CLI lint 门禁；最终源码报告十处未改动旧代码的诊断，独立复审逐处与基线核对。首次旧测试快照另有一处新 `map_identity`，已修正且最终执行不再报告。Studio 全目标 lint 完成未建立 |

额外 lint 的失败日志保留，没有抑制诊断、删除测试或修改现有门禁。原生 GUI、打包内嵌外观的实际原生加载、签名和公证未验证；Web 外观已有独立实际证据。

新控制不解除 #133、#120、M2、#80、完整 #79 的 HOLD，#112 原失败、#3 阻塞、#4 缺口和 #49 边界保持。普通桌面 GUI 按大版本策略记 NOT-RUN。

VERIFIED — 实际 AI 能力发现、人物修改、看图修订、局部独立审查、普通 Web 打开保存及有限八秒播放。
PARTIAL — 正式 PR CI、合并及 main 验证待完成；额外 lint 的失败与原生 GUI 等边界保留。
