# Nvwa：Rust-first 技术决策与 Codex 原型任务书（v2）

研究日期：2026-10-10
修订依据：Derek 明确要求尽量 Rust 原生、优先单语言维护，并同时面向网页与独立桌面应用。
状态：Rust-first 是用户明确的方向；具体 UI 库和版本组合仍是待原型验证的建议。本文没有宣称已创建仓库、编译、运行或测得性能。

## 本次修订

用 Rust 编写产品核心、运行时、编辑器 UI 与 CLI，移除 React/TypeScript 产品前端的默认选型。建议 Bevy + bevy_egui 作为首个 UI 验证组合；桌面直接使用原生窗口，不以网页套壳作为默认实现。网页和桌面从 M0 共同验收。

保留必要的边界例外：浏览器自动生成的 JavaScript 绑定与最小 HTML 启动页、Blender Python 集成、独立模型推理 worker，以及确有需要的着色器代码。例外必须有理由、窄接口和测试，不能扩展成第二套产品业务逻辑。单语言不等于重写所有第三方库，也不意味着传递依赖和操作系统组件都由 Rust 实现。

本次重新核实 Rust、Bevy、egui、bevy_egui、Feathers 与 WebAssembly 资料。角色来源、AI 模型和 VaM 迁移部分沿用 v1 的研究方案，本次未重新核验其中每一项资料；正式接入前仍需复核能力与许可。

## 1. 产品目标

Nvwa 是以角色为中心、面向人和 AI agent 的 3D 创作与互动沙盒。用户捏出自己喜欢的角色，让角色动起来，修改动作与场景，并把可继续互动的作品发布到网页或通过独立桌面应用使用。

保留用户最初的目标：这是一项兴趣驱动的长期项目；不是只做聊天角色、视频生成器或通用游戏引擎。借鉴 VaM 的可组合内容生态，但不复制其闭源运行时，也不以完整兼容其历史内容作为第一阶段要求。

首个可体验成果：一个有骨骼和真实形变的角色；用户修改外观；通过 UI 或 agent 排出一个 5–10 秒的动作片段；手动修改时间轴；保存、重载；相同作品可在原生应用和静态网页播放并支持少量交互。AI 不在线时仍能播放已保存作品。

## 2. 建议决策

| 项目 | 第一阶段选择 | 边界 |
|---|---|---|
| 产品语言 | Rust-first | 领域数据、命令、运行时、编辑器、CLI 统一 Rust；必要外部集成例外 |
| 3D 运行时 | Bevy，候选固定版本 =0.19.1 | 与 UI 集成库成套验证，不自动追新，不在主线试升级 |
| 编辑器 UI | Rust egui，通过 bevy_egui 集成；候选 =0.42.0 | 桌面与网页共用 UI；Bevy 持有主循环，不再另起 eframe 应用或 React 前端 |
| 平台适配 | Rust native/web 模块 | 隔离文件、任务、剪贴板、浏览器 API 与窗口差异；不在领域代码散布平台条件 |
| 模型交换 | glTF 2.0 / GLB | 起步只支持明确验证过的材质、骨骼、morph、动画子集 |
| Nvwa 数据 | 版本化 JSON + 资源清单 | 不把 Bevy ECS 的内部序列化当作长期作品格式 |
| 离线内容管线 | Blender + Python 导出/校验工具 | 不要求浏览器直接打开 .blend，也不承诺 Blender 节点/约束无损还原 |
| 初始角色 | 原创或已核实许可的基础人形 + 一套服装 | 优先研究 MPFB/MakeHuman 核心 CC0 资产；社区资源逐项核实 |
| AI 接入 | 领域命令 API；CLI 优先，MCP 作为适配层 | 不让 LLM 每帧驱动骨骼；不把 MCP 等同于产品的数据模型 |
| 动作生成 | 可插拔外部 worker；先评估 Kimodo | 模型推理与浏览器实时循环分离；代码、权重和资产许可证分别检查 |
| 发布 | 原生桌面应用 + 静态网页 Studio/Player 与资源包 | 共用作品格式与运行时；第一版不做账号、支付、云端市场、多人协作 |
| VaM | 后续只读分析器与有限迁移 | 不加载或执行 VaM C# 插件，不承诺任意 VAR 可直接游玩 |

### 版本核实说明

Bevy 0.20 发布于 2026-10-08。bevy_egui 作者兼容表列出 Bevy 0.19 对应 bevy_egui 0.40–0.42，Bevy 0.20 对应 0.43。固定版本文档显示 bevy_egui 0.42.0 依赖 Bevy ^0.19 和 egui ^0.36；因此候选组合为 Bevy =0.19.1 + bevy_egui =0.42.0，并优先使用后者 re-export 的 egui，避免额外引入不匹配版本。

这只是公开依赖范围兼容，不代表已通过 Nvwa 的原生/Web 实测。先检查 MSRV、锁定满足要求的 stable Rust 工具链和 Cargo.lock，再完成 M0。没有实测依据，不把旧版本宣称为绝对更稳定，也不因刚发布新版就升级。

VRM 不应成为第一版必须使用的插件。v1 记录的 bevy_vrm 兼容信息在真正引入时重新核实，不为了可选 importer 迫使整个运行时升级。

必须使用版本匹配的文档、示例和 Cargo.lock。在线最新 Bevy 示例可能已经使用 0.20 API。不要根据旧训练记忆拼接不同版本代码。

### 放弃 Bevy 的条件

先用同一份真实测试角色验证原生与浏览器加载、skin/morph 同时运行、动画混合、编辑器输入和打包。若性能或关键能力不合格，先区分引擎、UI、资产、浏览器后端和项目集成问题，记录复现与测量。

之后优先比较符合 Rust-first 的替代方案；不得自动改回 TypeScript，也不预先实现第二套 renderer。只有充分证明跨语言方案显著降低总维护成本，才提出有证据的架构例外，由 Derek 决策。

## 3. 架构边界

### 3.1 权威作品数据

Rust `nvwa-core` 管理：

- `SceneDocument`：稳定对象 ID、角色实例、资源引用、空间变换、镜头、时间轴、有限交互。
- `CharacterProfile`：模型版本、骨骼语义映射、形变参数及范围、兼容服装、能力声明。
- `CharacterRecipe`：选用 profile、参数值、材质选择、服装选择。
- `MotionClipRef`：动作文件引用、源 rig、重定向配置、生成来源与可选随机种子。
- 命令、查询、事务、撤销与重做、版本迁移、校验报告。

这些类型不依赖 Bevy Entity ID、GPU 句柄或 egui 的内部 UI 状态。运行时内部 ID 可以变化，文档 ID 不得因此变化。

### 3.2 实时状态

Bevy 管理渲染、资源加载、骨骼/morph 求值、播放时钟、相机与输入。运行时是作品数据的执行结果，不是作品唯一的存储表示。

避免同时实现两套复杂场景图：核心只保存可移植的领域数据，适配器做必要映射即可。第一阶段不设计任意引擎插件 ABI。

### 3.3 资源

GLB、纹理、动作数据与角色 profile 通过清单引用。记录来源、许可、文件哈希与依赖；导入失败返回明确原因。缺少许可证不能自动视为允许分发。

第一版可采用一个目录，加 JSON 和资源文件；作品导出为 ZIP 是后续包装步骤，不先造包管理器。

### 3.4 编辑器 UI 与共享核心

建议以 egui + bevy_egui 做第一个 Studio：提供对象列表、角色参数面板、动作选择、简单时间轴、保存与撤销。使用一个 Bevy 主循环和同一窗口内的 3D 视口；第一版不嵌套第二个 eframe/winit 应用，也不先做可脱离主窗口的复杂 docking 系统。

UI 可以持有选中项、滚动位置、折叠状态、拖动预览等临时状态，但不得直接修改唯一作品数据来绕过领域命令。UI 与 CLI 同进程调用使用强类型 Rust API；只有外部 agent、存档和 IPC 边界才序列化为 JSON。不得为了共用协议让 Rust 内部每次操作都绕一圈 JSON。

egui 是即时模式 UI；界面绘制与副作用提交分开。拖动期间产生预览，结束后合并提交一个撤销事务；耗时导入、生成动作和网络请求放入任务队列，不能每次绘制面板都重复启动。输入焦点由集成层协调，拖动 UI 不应同时旋转相机，编辑文本不应触发场景快捷键。

Bevy UI / Feathers 是备选，不是排除项。0.20 的官方资料已列出更多编辑器控件；选择 egui 是为了先验证现成控件与明确的双端集成，不是宣称 Bevy 自带 UI 无法做编辑器。M0 默认一套主编辑器 UI；除非出现明确缺口，不同时维护两套面板系统，也不预先承诺未来全部重写。

这里的“原生”指 Rust 应用直接运行和绘制，不代表按钮采用 macOS/Windows 系统原生控件外观。

### 3.5 平台边界

原生与 Web 共用文档、角色算法、时间轴、运行时和大部分 UI。仅平台模块处理文件导入/导出、持久化、剪贴板、任务执行与外部连接。

Web 不能照搬原生文件系统、任意进程和线程假设。以异步操作与能力声明设计边界；浏览器不支持的操作明确返回 Unsupported，而不是静默成功。M0 优先实现文件选择/下载式保存，不先承诺所有浏览器的目录写入能力。

网页产物可以包含自动生成的 JavaScript 绑定和最小 HTML/启动代码；不手工修改生成文件，不在启动层加入角色或时间轴业务逻辑，不默认引入 Node/npm 产品构建依赖。优先使用 Rust 工具组织打包；确有收益的测试或发布工具可以例外，但要记录必要性。

## 4. Agent 接口

GUI、CLI 和后续 MCP 适配器调用同一套领域命令。核心类型在 Rust 中定义一次，外部协议从这些类型派生或校验；JSON 是交换格式，不是核心内部唯一类型系统。

外部 agent 不能直接调用本地 UI 或文件系统特权。实时桥接在需要时单独实现授权、会话边界和错误报告；不为了方便测试默认暴露无鉴权的网络控制端点。M0 的程序化命令测试不等于已经支持任意远程 agent。

建议先实现的查询和操作：

```text
scene.inspect
character.describe_capabilities
character.set_parameters
animation.list_clips
animation.add_clip
timeline.patch
scene.validate
scene.save
history.undo
history.redo
```

后续再添加 `animation.generate`、`animation.set_constraint` 与视觉预览工具。

命令需要：目标稳定 ID、明确的单位和合法范围、结构化错误、文档 revision、事务边界。接受 `expected_revision`，避免 agent 覆盖用户刚刚修改的作品。具有副作用的重试通过 command ID 或等价机制避免重复应用。

GUI 拖动滑块应更新实时预览，但一次拖动在撤销历史中归为一个事务。高频预览和提交可以分开，但不能分成两套互不一致的业务逻辑。

成功结果应包括 revision、变更摘要和可验证状态，而不只是“成功”。规划中的多步编辑可以先放在草稿上，预览后提交；不要默认所有 agent 修改都立即覆盖当前作品。

AI 原生的验收不是存在一个聊天框，而是：外部 agent 能发现角色能力、完成结构化修改、读取结果、得到失败原因并纠正；人能继续用同一界面编辑和撤销这些改动。

## 5. 角色系统

区分三类导入物：

1. **Nvwa 可捏角色**：有经过验证的参数、形变、rig、材质和服装适配，可完整使用对应能力。
2. **已绑定骨骼的外部角色**：映射 rig 后可能能使用通用动作，但没有形变数据时不得宣称可任意捏脸/捏身体。
3. **静态模型**：作为道具显示；自动绑定不是第一版隐含能力。

首个原型必须使用真实的 skinned mesh，而不是用方块旋转代替角色系统。允许视觉风格简洁，但必须有连续表面形变、骨骼和可观察的动画。

建议首批控制：4–6 个经过作者验证的脸部形变、整体缩放、少量材质参数。一旦扩大到身体比例，必须检查 rest pose、骨骼位置、蒙皮、服装与接触点；不能只改 mesh 顶点后宣称完成任意体型适配。非均匀骨骼缩放和自动服装适配不在默认范围。

绑定一套服装；禁止为“先看得到结果”偷偷省略受许可约束的资产来源记录。

MPFB/MakeHuman 的核心资产与软件代码是不同许可：核心资产 CC0，MPFB 代码 GPL，MakeHuman 代码 AGPL；社区内容单独核实。离线导出资产不是直接把其源码复制进 Rust 项目。

SOMA-X 是可选的独立研究分支：评估 native SOMA 资产的参数化能力和离线导出，检查 Apache-2.0 与第三方 backend 的不同许可。不要把 SMPL/MANO 等可选模型的权限当作由 SOMA-X 自动授予，也不在 P0 移植 PyTorch/Warp 实现。

## 6. 动画与沙盒

### 6.1 P0/P1

准备至少 idle、wave 和一个独立动作片段，确保可合法分发。第一阶段重点验证开始时间、时长/速度、过渡、停止和重播；不要先实现完整 DCC 时间轴。

在沙盒里，播放逻辑与编辑工具共用同一文档。至少提供一个点击角色触发挥手或镜头切换的交互，使发布产物不只是导出视频。若 walk clip 被引入，应显式标注 in-place 还是 root motion，禁止双重位移。

可以暂不引入完整物理引擎；用固定地面与明确的角色变换即可验证闭环。脚接触修正、IK、碰撞、ragdoll 和软体物理按独立里程碑增加。

### 6.2 实际 AI 动作生成

路线：文本意图 → 场景约束与起止条件 → 现有动作检索/组合或模型生成 → rig 重定向 → 接触/IK 修正 → 标准动作文件 → 可编辑时间轴。

Kimodo 值得作为第一个受约束动作生成试验：官方提供代码、时间轴界面以及关键帧、稀疏关节、路径等条件。研究时 SOMA-RP-v1.1 模型输出 30 关节骨骼动作，有长度等限制，且官方明确其不了解场景物体、可能脚滑、一次针对单个角色。因此“知道场景中的杯子在哪里、手是否碰到杯柄”仍由 Nvwa 负责。

Kimodo 仓库代码是 Apache-2.0；模型权重使用 NVIDIA Open Model License，不能混写为整个工具链 Apache-2.0。不要假定已有官方托管推理 API。先用本地或受控 GPU worker 的文件/任务接口；没有 GPU 或权重时报告阻塞，先完成动作文件导入与重定向，不虚构推理结果。

缓存生成的动作结果、模型版本与参数。已经发布的作品不依赖再次调用模型。生成失败不应污染当前文档。

对照测试建议：站立挥手、按指定起止姿势转身、沿简单路径行走。测试骨长/关节映射、起止姿态、脚滑和路径误差。跨平台浮点或物理结果可采用容差，不承诺逐比特一致。

## 7. Blender 与格式

第一步是固定导出约定和校验器，而不是大型双向同步插件：

- Blender 源工程留在作者工作区，导出受支持的 GLB。
- 明确单位、轴向、rest pose、节点/骨骼与 morph 命名。
- 不假定 Rigify 控制器、约束、几何节点和任意 shader 能以原语义在浏览器中运行；按场景烘焙或拒绝，并给报告。
- Nvwa 角色含 `character.profile.json`，补上 GLB 不提供的“哪一个滑块代表什么”“合法范围”“哪些衣服兼容”等语义。
- 第一个工具只需要 Validate / Export。之后才加 Send to Nvwa。

VRM 是后续标准适配层，不是万能的捏人格式。VRM 的 humanoid、表情、视线、材质和 spring bone 需要识别相应扩展；普通 glTF loader 不能被假定完整支持它们。VRM 0.x 与 1.0 单独声明兼容能力。

## 8. 原生桌面与浏览器都是第一天的约束

M0 必须产出同一份源代码构建的原生应用和可静态托管的浏览器 build，二者互不能代替验收。先在有条件的原生 OS 与明确版本的桌面浏览器跑通闭环，Windows/macOS/Linux 分别记录“已构建”“已运行”“未测”；不把交叉编译成功写成真机通过。

桌面使用原生可执行程序，不默认采用 Electron/Tauri 网页套壳。正式发行时，资源打包、各 OS 所需系统依赖、安装包、签名/公证与更新机制另做发行验收；cargo build 不是完成所有平台发行的证据。

Studio 和轻量 Player 共用运行时。Studio 带编辑器；Player 可通过明确的 Cargo feature/入口省去编辑器依赖与面板。M0 先完成 Studio 双端，M1 再验证轻量发布目标，不因此复制角色/动画代码。

默认先验证支持 WebGPU 的桌面浏览器；用功能检测选择支持状态，不仅匹配浏览器名字。加载界面和失败原因必须可读。WebGL2 降级作为独立后续选项，不能未经测试承诺同等画质、功能或自动回退。

UI 直接调用 Rust 类型化命令队列与只读视图，不再维护 React/Wasm 业务状态桥。每帧姿态在 Rust/Bevy 内部计算；为外部 agent 提供的快照和预览按需生成，不每帧复制完整世界。

重点测试中文输入法、文本选择与剪贴板、键盘焦点、快捷键冲突、HiDPI/缩放、文件拖放/选择和基本无障碍。egui/eframe 的某个功能存在不代表 bevy_egui 在全部平台上已同样验证；以选定集成和具体设备实测为准。

3D 播放性能之外，还要记录暂停、空闲和后台时的资源消耗；避免编辑器无必要的高频刷新。

记录：压缩后的 Wasm/JS/初始资产体积、冷启动/首帧、帧时间和内存；注明硬件、浏览器、构建模式与分辨率。Linux CI 的软件渲染结果不代表用户真实 GPU 表现。

以下只是原型预算建议，不是现有性能结论：单角色、简单环境、纹理不超过 2K、固定 1280×720 基准渲染、在记录的实际测试设备上稳定达到至少 30fps；压缩后的首屏总下载以 30MB 为初步预算。超预算先出测量和取舍报告，不通过偷偷删掉形变、动画或换成视频达标。

不做浏览器内的大模型推理，不把 API 密钥嵌入静态网页。需要上传用户资产进行云端推理时必须有明确授权和隐私说明。

## 9. VaM 迁移策略

先做只读 inspector：识别 VAR 容器、meta.json、依赖、许可声明、缺失资源和未知类型。容器可解包不代表能复现运行时。

未来仅对有明确使用/转换权限、且有经过验证的格式定义的子集做 importer。输出迁移报告：成功保留、近似转换、缺失、不支持、许可待核实。

不在第一阶段执行 C# 插件、解析全部 Unity AssetBundle、模拟 VaM 物理或兼容其渲染器。不要把 VaM 控制点数值直接假设为新骨骼旋转，也不要把基于不同拓扑的 morph 值硬套到新角色。

Timeline 项目为 GPL-3.0。参考其功能不意味着可把代码复制进任意许可的项目；使用源码应遵守许可。独立实现导入器也要以可合法使用的格式资料和测试资产为依据。

Daz 的使用/互动授权不等同于可自由提取、重新导出并分发给另一创作平台的权利；其条款还涉及 AI 使用限制。不得把“用户自己有文件”写成自动合法的豁免。面向公开迁移/分发前需核对具体资产权利和必要授权。

## 10. 推荐最小仓库

```text
Cargo.toml             # workspace 与统一依赖配置
Cargo.lock
rust-toolchain.toml     # 固定满足依赖要求的 stable 工具链
crates/
  nvwa-core/           # 文档、强类型命令、查询、校验、撤销；不依赖 Bevy/egui
  nvwa-runtime/        # Bevy/GLB/动画/世界映射
  nvwa-studio/         # Rust egui 编辑器；native/web 入口和平台模块
  nvwa-cli/            # inspect/validate/apply，便于外部 agent 与测试
web/
  index.html           # 最小启动页；生成的 JS/Wasm 进入构建产物
assets/
  fixtures/            # 获准分发的最小真实角色与动画
examples/
  scenes/              # 版本化演示文档
tools/
  blender/             # 必要的 Python 集成，不含第二套产品核心
docs/
  adr/
  schemas/
```

无理由不要拆出十几个 crate。首先以小型 workspace 和清晰模块边界完成真实闭环。平台模块一开始可放在 nvwa-studio 内；Player 可以先是独立入口/feature，确有共享需求后再抽 crate。构建任务可以逐步收拢到 Rust xtask，但不为目录完整而先造工具框架。

## 11. 里程碑与验收

### M0：Rust 双端 + 真实角色 + 编辑器命令

交付：锁定依赖的 Cargo workspace、共用 Rust egui UI 的原生/Web Studio、一个真实 skinned/morph 角色、动画播放、一个 Rust 命令改变形变、保存/重载最小文档、双端 smoke test、实际能力/性能报告。M0 不实现完整时间轴编辑器。

必须验证：

- 显示的不是静态截图或视频；角色能在原生窗口和浏览器实时形变并播放骨骼动画。
- 不存在 UI 数值变化而模型未变的伪实现。
- GLB 加载完成与节点映射过程可靠，错误有报告。
- 同一强类型命令可以来自 GUI 和程序化接口，得到等价文档。
- 原生保存的作品能在 Web 加载，Web 导出的作品能在原生加载，参数与动作不丢失。
- UI 选择、滑块、文本输入和 3D 镜头输入无明显冲突；中文输入至少记录实际结果。
- 没有悄悄引入第二套 TypeScript UI、网页套壳或重复的作品状态。
- Windows/macOS 真机性能未测到时如实标明，不能用 CI 通过冒充已验证。

停止条件：得到对 Bevy/egui/Native/Web/真实角色管线的证据和明确 go/no-go；不自动开工完整 AI 系统。

### M1：可捏、可编排、可分享

交付：有限角色控制、Rust 简单时间轴、三段获准分发的动作、撤销/重做、双端保存/重载、一个互动触发器、静态 Player 发布包、可分发原生构建、CLI 命令与外部 agent 使用说明。

验收：GUI 和 agent 对相同初始文档应用相同命令得到等价文档；重载不丢角色参数和动作时序；暂停/拖动时间轴可工作；发布作品不调用 AI 也能播放。

没有真实 LLM/agent 连接时，只能宣称“接口已准备好”，不能把写死的字符串规则称作自然语言 agent。

### M2：一个真实动作生成 provider

交付：Kimodo 或经许可核验的等价 provider adapter、任务状态/取消/失败处理、规范化动作结果、一个到目标 rig 的映射、明确的质量测试。

必须呈现生成结果与已知问题；预设动画不得伪装成模型生成。不可把模型输出存成只可在某厂商 UI 中打开、Nvwa 本身不能播放的专有结果。

### 后续按风险排序

Blender 简单插件 → 额外角色/服装验证 → VRM 指定版本适配 → 约束/IK/接触系统 → 只读 VaM inspector → 经许可审核的迁移子集。完整软体物理、头发/布料、VR、多人、市场、任意脚本插件不进入前三个里程碑。

## 12. 并行 Codex 工作方式

先合并一份最小文档 schema 和命令合同，再并行：

- 核心/测试：负责 nvwa-core 与 CLI，不修改 renderer。
- 运行时：负责 Bevy、加载、动画与世界映射，使用约定命令合同。
- 编辑器：负责 Rust egui Studio、输入和时间轴，不另写一套场景业务规则。
- 资产/管线：负责角色、导出、合法来源、fixtures。

一个集成负责人处理共享类型、Cargo.lock 与主线冲突。可以并行做 Kimodo/SOMA-X 小型研究，但不能让其阻塞 M0，也不让研究分支的大型 Python/GPU 依赖进入 Studio 的原生或 Web 构建。

所有 agent 使用自己的分支/工作目录；不能通过关闭测试、放松校验或移除特性来实现表面通过。先有可运行切片，再增加抽象。

### 12.1 发挥编译器价值，而不是只统一文件扩展名

核心领域使用明确的 ID 类型、命令 enum、参数单位/范围与 Result 错误；重要数据结构尽量采用使非法组合无法构造的设计。外部动态参数仍需运行时校验，不假装编译器能识别任意用户资产。

自有核心代码默认禁止 unsafe；必要平台边界出现 unsafe 时需要独立审查与不变量说明。不要用全局可变状态、大量无解释的 unwrap、吞错或无边界的 Arc<Mutex<_>> 绕过所有权设计，也不要机械禁止合理共享状态。第三方依赖内部的 unsafe/FFI 不因产品 Rust-first 就消失。

日常采用固定工具链、cargo fmt、clippy、核心单元/属性测试、双目标构建和真实运行 smoke test；具体命令以实际 features 为准。核心测试不依赖 GPU，避免每次领域修改都完整重编渲染器。记录增量编译成本，合理缓存依赖，开发构建和发行构建分开优化；不为追求编译速度默认转 nightly 或永久 fork 引擎。

依赖升级单独成批进行，并运行作品兼容与双端回归。Rust 语言的稳定性不能等同于 Bevy/egui API 永不变化；类型正确也不能代替动画、保存、撤销、导入边界与性能测试。

## 13. 安全与最低测试

必须校验 JSON schema 版本、未知字段策略、参数范围、非有限数值、缺失对象与资源。导入文件限制大小与解压上限，拒绝路径穿越；不执行导入项目自带的脚本或命令。

模型、场景描述和 README 都是用户数据，不应被 agent 当作高优先级指令。云端凭证不进入静态 bundle；第一版不开放任意上传脚本。

基础测试包括文档 round-trip、命令合法/非法输入、事务/撤销、revision 冲突、缺失骨骼/morph、资源许可证清单、Native/Wasm 构建、双端加载和控制 smoke test，以及跨端作品重载。Rust 编译通过不等于产品验收通过。

## 14. 可交给 Codex 的第一条任务

> 阅读本文件，只实施 M0。Nvwa 是 Rust-first 的原生桌面与 Web 3D 沙盒，产品核心、运行时、编辑器 UI 和 CLI 使用 Rust；不得因开发者熟悉 TypeScript 引入 React/TypeScript 前端，也不默认用网页套壳实现桌面。先核对并锁定 Bevy =0.19.1 + bevy_egui =0.42.0 候选依赖和满足 MSRV 的 stable 工具链，不能混用不同版本示例。用一个可合法分发的真实角色验证同一 Rust Studio 在原生窗口和浏览器运行：skin/morph、动画播放、egui 滑块、类型化命令、保存/重载及跨端作品兼容。Bevy 管主循环，UI 不再启动第二个 eframe 应用，也不直接绕过领域命令修改作品。平台差异隔离到少量模块，网页仅保留必要 HTML/生成的 JS 绑定。按闭环实现最小字段，不先造完整编辑器或通用跨引擎抽象。提交可重复构建步骤、两类产物、实际运行证据、输入/性能观察、未测 OS/浏览器和 go/no-go 建议。不得实施账号、市场、多人、VaM 插件兼容或浏览器内大模型推理。权限、GPU、下载或设备不足时完成不受阻工作并准确记录阻塞，不虚构运行结果。

## 15. 一手资料

以下为研究时查阅的官方文档、作者仓库或模型卡；链接用于重新核实，不代表本文已运行这些项目。

1. Bevy 0.20 发布： https://bevy.org/news/bevy-0-20/
2. Bevy 0.19.1 固定版本 API： https://docs.rs/bevy/0.19.1/bevy/
3. Bevy morph 示例： https://bevy.org/examples/animation/morph-targets/
4. Bevy 动画混合示例： https://bevy.org/examples/animation/animation-graph/
5. wgpu： https://wgpu.rs/
6. Fyrox 作者仓库： https://github.com/FyroxEngine/Fyrox
7. Babylon.js WebGPU（v1 背景资料，不再作为默认回退）： https://doc.babylonjs.com/setup/support/webGPU
8. bevy_vrm 版本/依赖： https://docs.rs/crate/bevy_vrm/0.4.0
9. bevy_vrm 支持范围： https://github.com/unavi-xyz/bevy_vrm
10. VRM 规范： https://vrm.dev/en/vrm/vrm_features/
11. VRM Animation： https://vrm.dev/en/vrma/
12. Khronos/Blender glTF 插件： https://github.com/KhronosGroup/glTF-Blender-IO
13. Blender glTF 文档： https://docs.blender.org/manual/en/latest/addons/scene_gltf2.html
14. MakeHuman/MPFB 许可： https://static.makehumancommunity.org/about/license.html
15. SOMA-X 代码： https://github.com/NVlabs/SOMA-X
16. SOMA-X 原生资产模型卡： https://huggingface.co/nvidia/SOMA-X
17. Kimodo 项目： https://research.nvidia.com/labs/sil/projects/kimodo/
18. Kimodo 代码： https://github.com/nv-tlabs/kimodo
19. Kimodo SOMA-RP-v1.1 模型卡： https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.1
20. 腾讯 HY-Motion-1.0（备选研究）： https://github.com/Tencent-Hunyuan/HY-Motion-1.0
21. WebGPU 浏览器说明： https://developer.mozilla.org/en-US/docs/Web/API/WebGPU_API
22. VaM VAR/许可帮助： https://hub.virtamate.com/wiki/license_help/
23. VaM Timeline： https://github.com/acidbubbles/vam-timeline
24. Daz EULA： https://www.daz3d.com/eula
25. MCP 架构： https://modelcontextprotocol.io/docs/learn/architecture

### v2 新增核实资料

26. egui 作者文档（跨平台、控件、非系统原生外观、升级破坏性变化）： https://github.com/emilk/egui
27. bevy_egui 作者文档与版本兼容表： https://github.com/vladbat00/bevy_egui
28. bevy_egui 0.42.0 固定版本依赖与示例： https://docs.rs/crate/bevy_egui/0.42.0
29. Bevy Feathers 官方说明： https://docs.rs/bevy_feathers/0.20.0/bevy_feathers/
30. Rust 所有权： https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html
31. Rust 并发类型检查： https://doc.rust-lang.org/book/ch16-00-concurrency.html
32. wasm32-unknown-unknown 平台限制： https://doc.rust-lang.org/rustc/platform-support/wasm32-unknown-unknown.html
33. wasm-bindgen 无 bundler 示例： https://wasm-bindgen.github.io/wasm-bindgen/examples/without-a-bundler.html
34. wasm-bindgen 发布方式： https://wasm-bindgen.github.io/wasm-bindgen/reference/deployment.html
35. Bevy 编译和发行配置说明： https://bevy.org/learn/quick-start/getting-started/setup/

### 研究与执行的区别

已完成：v1 研究方案，以及 v2 的 Rust-first / 双端 / UI / 维护与验收修订和相关资料核对。
尚未完成：Bevy/egui/GLB/Native/Wasm 实际整合、VRM 兼容测试、Kimodo 推理与重定向、SOMA-X 资产导出、真机性能和任何 VaM 迁移。所有技术验收必须由实现阶段补上证据。
