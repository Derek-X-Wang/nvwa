# 角色基础研究：agent 接口、运行时合同与复用边界

检查日期：2026-10-16。仓库观察固定于 `1a91178e894bad13bf51223b33b49cf33ea91a1c`，已包含试演舞台 A。本文只做源码、资产元数据和第一方文本研究；没有角色实现、工具安装、资产下载、新模型推理或界面操作。

## 结论

**建议先复用成熟工具的几何、shape key、蒙皮和动作制作能力，把 Nvwa 的增量放在可发现的语义参数、可复现的配方、明确的 rig 合同和可检查的视觉反馈。** agent 不会天然需要另一套雕刻算法。它需要知道能改什么、改变的含义、哪些组合有效、实际画面发生了什么，以及失败后如何恢复。

这是架构建议，不是已有功能。当前 Nvwa 已有很好的一半：共享 Rust 命令、离线 CLI 能力发现、严格 JSON、原子批量保存、可保存舞台。它仍只是单角色、四个直接 morph 参数与既有动作。不能把已有可编辑参数称为完整人物系统，也不能把新角色的骨骼名称相同当作可复用旧动作映射。[R1–R7；R14]

对于“结合两个动漫角色，再捏细节、创造动作”，应先区分输入：两份**同一参数基础上的配方**可以研究特征混合；两张参考图需要先转成可编辑的目标特征；两份任意拓扑模型需要另外解决对应、rig、服装与材质。当前仓库没有后两条的完整路径。本文不承诺图像→可动画角色，也不把两个任意网格的顶点平均称为角色融合。[R2–R5；格式推论见下文]

## 当前实际已有的支持

| 项目 | 现有支持与证据 | 对下一角色基础的限制 |
| --- | --- | --- |
| 作品与版本 | `SceneDocument` 保存 profile、recipe、timeline、stage；当前写 schema 2，读入旧 schema 1 时补默认舞台。[R1:6–18,25–49] | 文档版本不是角色参数语义、rig 或编译器版本。 |
| 资产身份 | Work 内嵌完整 profile，保留当时参数定义与映射；profile 有字符串 ID、GLB 相对路径、SHA-256、license；recipe 有 profile ID、参数值和整体缩放。[R1:6–10；R2] | 已固定资产字节与所存 profile 内容；还没有独立的 profile 版本/hash、拓扑版本、rig 版本、编译器版本。 |
| 外貌控制 | `jaw_width`、`nose_width`、`smile`、`shoulder_width` 均为 `[0,1]`，直接绑定 morph 0–3。[R3] | 没有参数语义分类、物理/比例单位、适用范围、依赖图或区域锁定。数值归一化不等于跨资产同义。 |
| 当前绑定模型 | `ParameterSpec` 只有 `id/morph_index/min/max/default`；profile 拒绝重复 morph index。运行时逐个把 recipe 值写入每个角色 `MorphWeights` 的该 index，并在动画之后覆盖这些通道。[R2:131–139；R4；R5] | 不能表达 node/mesh 定位、多 morph 宏、一对多绑定、共享目标累加、材质/骨骼绑定或表情合成策略。 |
| 动作 | timeline 引用 profile 中的 clip，设置开始、时长、速度、循环；禁止重叠。现有标准资产有 idle/turn/wave。[R3；R6] | CLI 是选择、编排已存在片段，未提供骨骼关键帧创作、IK、接触编辑或生成 provider。 |
| agent 编辑合同 | `describe-capabilities` 输出实际 ID/revision、生产序列化的命令例子、范围、错误恢复；`apply` 整批成功后保存；schema 2 舞台同样可发现。[R7] | 这部分应扩展复用，无需另造一套 agent 状态。 |
| 文件交换与恢复 | GUI/CLI 共用 core；历史和 command ID 只在会话/单次 apply 内存在。stdout 失败可能发生在成功保存之后；无跨进程 CAS。[R1:68–78；R8] | 批量候选要用不同输出路径，结果带明确 artifact ID/hash；不能依赖跨调用 undo 或永久幂等。 |
| 验证与观测 | core 检查 profile/Work；带 asset root 的 CLI 还检查 GLB hash、容器/基本引用。舞台配置已保存、双端已验收；正式 CLI 不渲染。[R7；R9；R10] | GLB validator 不是完整 glTF、rig、形变或画面质量验收；正式离屏图像、逐帧骨骼采样仍未实现。 |

`asset.json` 不是本次基线中的实际文件名：已搜索文件清单，未找到该文件。实际资产合同入口是 `assets/character.profile.json`、`assets/fixtures/provenance-manifest.json` 和 GLB 内部 JSON 的 `asset` 对象。[R3；R11] 本次只读解析 GLB，得到 `asset.version=2.0`、generator=`Khronos glTF Blender I/O v3.3.32`，5 个 mesh，1 个 18-joint skin，3 个名为 idle/turn/wave 的 animation，无 `extensionsUsed`；一个 mesh 的 5 个 primitive 均有 4 个 morph，其余 mesh 无 morph。实际 GLB hash 与 profile 一致。这是元数据读取，不是加载或画面验证。[R3；R11–R12]

ADR 0003 明确把当前角色定位为工程 fixture，且仍缺组合 morph、生产级手和抬臂权重。它还明确区分结构再现与字节再现：两次源生成的结构和 morph delta 相同，但 GLB/`.blend` 字节不相同。因此应先保证相同已发布资产与配方的语义结果可复现，不能先承诺整个 Blender 构建管线跨平台逐字节一致。[R13]

## 成熟格式能承担什么

### glTF 2.0：交付形变结果，不是人物生成规则

glTF 的 morph 是基准属性加权增量；目标 accessor 对应同一 primitive 的顶点，且形变先于蒙皮变换。skin 保存 joint 节点、逆绑定矩阵和顶点 joint/weight 数据。它足够交付已制作的网格、shape key 与骨骼动画。[glTF 2.0 §3.7.2.2–3.7.3](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#morph-targets)

**设计推论：** glTF 中的 morph index 不是“眼睛大小”这样的跨角色语义；不同拓扑的形变增量不能直接互换。导出几何也不会自动携带 Nvwa 所需的宏参数依赖、关节重定位规则或任意 Blender driver 求值器。可选择在制作端编译这些规则，或在 Nvwa 明确实现受限、可版本化的求值器。格式能装入某项数据，不等于当前 Bevy/Nvwa 支持它。

当前 `validate_asset_bytes` 的 morph 检查取所有 primitive 的最大 target 数，再比对全局 index；它并未证明每个指定 node/mesh 绑定有效，也没有检查完整 skin accessor、权重和 rest 语义。因此下一角色不能仅用该检查获得“动作兼容”准入。[R9:42–91]

### VRM 1.0：有用的人形与表情语义，但不是通用捏人系统

VRM 1.0 humanoid 定义身体骨骼槽位、必需/可选骨骼和层级规则；这能减少名称猜测。它不能单凭骨骼槽位保证同一个动作在不同体型上保持接触和穿插质量。[VRM 1.0 humanoid](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/humanoid.md)

VRM expression 可把一个表达值绑定到指定 node 的 morph、材质颜色或纹理变换，并定义 blink/mouth/lookAt 覆盖策略；预设表情并未规定具体脸部形变。这个“语义→多绑定”结构值得借鉴，但 expression 本身不提供身份体型宏、骨长适配或从参考图造人的规则。[VRM 1.0 expressions](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/expressions.md)

VRM 的官方、明确标为非规范性说明也指出：不同 T-pose rest rotation 和可选骨骼会让同一姿势的局部数值不同，需要转换。[VRM Animation pose compatibility](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm_animation-1.0/how_to_transform_human_pose.md) 因而“采用 VRM1”与“通用动作重定向完成”必须分别验收。当前 fixture 的 `.L/.R` 与身体左右相反；已采用映射只限该角色和同一个 90 帧样本，残余相交与质量 HOLD 仍在。[R10:11–15]

### Blender 与 Bevy：继续复用，但固定实际工具版本

Blender 已有 relative shape keys、骨架/蒙皮和 driver。官方示例直接用 pose 驱动 corrective shape key 改善关节形变。无需为了 agent 重新实现这套制作能力。[Blender shape keys](https://docs.blender.org/manual/en/4.4/animation/shape_keys/shape_keys_panel.html)、[Blender corrective driver 示例](https://docs.staging.blender.org/manual/en/latest/animation/drivers/workflow_examples.html)

Blender CLI 有后台执行、Python 和逐帧输出；glTF exporter 有 shape key、骨骼/动画导出选项。因此可以研究“固定源资产＋受控脚本＋结构化输入＋批量渲染”，让 agent 通过语义命令使用成熟工具。[Blender CLI](https://docs.blender.org/manual/en/3.6/advanced/command_line/arguments.html)、[Blender glTF exporter](https://docs.blender.org/manual/en/4.0/addons/import_export/scene_gltf2.html) 这是可行接口方向，不是本次运行证明。当前 fixture 制作记录是 Blender 3.3.1；上面的不同版本文档只证明已有机制，不能证明该旧安装支持所有新参数。[R11:5–8]

Bevy 0.19 官方迁移说明区分 `MorphWeights` 与 `MeshMorphWeights::Reference`，可共享 morph 权重。Nvwa 应继续把引擎组件当成 profile 编译结果的镜像，而非持久配方；node/primitive 的绑定与动画写入顺序需要 Nvwa 自己明确。[Bevy 0.18→0.19 morph weights](https://bevy.org/learn/migration-guides/0-18-to-0-19/#morphweights-and-meshmorphweights-have-been-restructured)、[R5；R8]

资料边界：本次部分 Blender 全文 `open` 返回 402；相关机制使用官方搜索结果提供的段落，未把失败读取当全文审阅。`docs.rs/bevy/latest` 当前指向 0.20，未将它当仓库 0.19.1 的精确 API 依据。未读取第三方深层库源码，也未启动 Blender/Bevy。

## 为 agent 增加的最小合同（全部为提案）

### 1. 一个语义参数可以编译成多个实际变化

保留稳定参数 ID、范围、默认值，补充中文/英文描述、类别、受影响区域、正负方向、单位或比例定义、适用 profile 与示例预览。`eye_size=0.7` 必须说明它与默认值的关系；`[0,1]` 只是本 profile 的输入域，不保证跨角色视觉一致。

把 `morph_index` 从唯一绑定升级为**定位到 node/mesh/target 的绑定表**。一个语义参数可编译为多个 morph、材质变化和受控骨骼适配。先支持有限规则，再逐项扩大；不能直接执行资产携带的任意脚本。

宏参数采用无环依赖图，写明顺序、范围、互斥项与冲突处理。分开保存“用户输入”与“求值后的实际权重”，后者可检查但不成为另一套编辑权威。例如体型宏同时影响躯干宽度、上臂起点和衣物；不能只移动身体表面而假定骨骼与服装自动适配。

### 2. 身份、表情、动作修正分层

身份参数描述持续外貌；表情是当前表演状态；corrective 是身份组合或姿势触发的补偿。`smile` 目前与 `jaw_width` 在一个 map，且同一 runtime 覆盖阶段写入，不能据此认为已有表情轨或混合策略。[R3；R5]

提案求值合同：身份配方 → 体型/关节适配 → 采样动作 → 姿势/组合 corrective → 表情与其覆盖策略 → 最终 morph 权重/骨骼状态；具体实现可在源工具编译或 runtime 求值。**这是逻辑阶段图，不是断言所有 morph 应在蒙皮之后应用。** 实际 glTF morph 仍须遵从格式的蒙皮前增量约定。每阶段写哪些通道、累加/替换/钳制由 profile 明确指定。

若小范围外貌 morph 保持原 rig，也必须在极值和动作中验证。若参数改变肢体长度、肩/髋位置或 rest pose，则要明确关节重定位、逆绑定矩阵、权重/服装适配与动作转换策略。最小版本可以声明“固定 rig、禁止骨长参数”；不应为了参数数量而引入未经验证的骨架变化。

### 3. 把 rig 合同当作动作前置条件

每个准入角色记录：单位、up/front/身体左右、root 与 pelvis 语义、rest pose、骨骼槽位/层级与局部基、skin joint 列表、inverse bind、权重限制、可选骨骼、可用表情与材料特性。保存 topology/rig/profile 的独立身份和版本。

动作导入记录 source 格式/版本、坐标和 rest 约定、root policy、转换器/映射版本与目标 rig hash。原始动作、目标动作和质量报告分别保存。更换角色或改骨长后必须重新准入；旧 fixture 校准只提供测试思路，不能自动授权或证明新角色映射。

### 4. 配方有可复现边界

Work 继续拥有用户选择。当前 Work 已经内嵌完整 profile，因而会保留当时的参数定义与映射；并非只存一个会漂移的 profile 指针。[R1:6–10] 引入编译器或更多资产后，再按需要固定 profile schema/version/content hash、编译规则版本、源模板版本及依赖摘要、rig/topology ID，并继续保留 asset SHA；有随机过程时记录 seed 和实际工具版本。保存必要的 source/export options 与 license/provenance。最小固定 rig/直接 morph 试验无需先实现全部元数据层。

把两种承诺分开：相同已发布资产＋相同配方→相同求值状态；相同源与工具环境→等价导出结构。字节一致性单独测试，尤其不能覆盖 ADR 0003 已记录的非确定导出。修改参数含义必须升级或明确迁移，不能静默让旧配方变脸。

### 5. agent 的最小闭环是发现→编辑→观察→评价→纠正

沿用当前 discovery、严格命令、revision 和结构化错误。增补只读发现：可编辑的语义组、固定约束、依赖、绑定、支持的导出目标、测量项、已知失败组合。扩展编辑仍走共享 core，而不是写 GPU/entity。

候选命令形状可以是 `evaluate-recipe`、`preview-batch`、`measure`、`validate-character`；这些名称只是研究草案，当前 CLI 不支持。每个输出带输入 Work/profile/asset hash、实际 recipe、camera/stage hash、姿势采样时间、renderer/tool version、运行状态及 artifact 路径。未渲染、超时和测量缺失必须独立返回，不能只输出 `valid=true`。

“无窗口”分两类：CPU 结构/蒙皮/骨骼求值可用于快速检查；真实离屏图像通常仍要渲染设备和确定的读回流程。Blender 源图不能代替 Bevy native/Web 的最终形变、材质或阴影验收。已有保存舞台适合固定曝光、相机与背景，但需要另做正式批量/离屏入口。[R1:25–49；R10:19]

目标函数先用可解释约束：脸宽/头高、肩宽/身高、眼间距等测量、左右对称误差、ground/contact 误差、关节活动范围和预定义穿插检测。明确测量坐标系、单位、采样姿势和容差。数值只能帮助搜索；“像角色 A 的脸＋角色 B 的体型”、美术质量和动作语义须有明确参考与人类评价。未经验证的评分不能冒充角色相似度真值。

## 复用优先的路线选择

| 路线 | 实际增加的东西 | 主要取舍 |
| --- | --- | --- |
| 成熟参数基础＋Nvwa adapter（优先验证） | 复用可分发角色模板与参数体系；以同样本对照决定离线编译或数据驱动求值；Nvwa 管配方/命令/预览/动作准入 | 参数覆盖、美术风格、再分发与修改权由具体基础限制，需要单独选型。 |
| Blender authoring＋受控批处理（最稳的保底） | 艺术家/脚本制作 basis、morph、权重与 correctives；薄接口接收结构化配方、导出/测量/渲染 | 复用范围大，能满足定制；每个模板的参数化与导出合同仍需制作，不能声称 Blender 自动捏好所有人物。 |
| Nvwa 自建全套雕刻/自动 rig 内核 | 网格编辑、拓扑、变形、权重、工具交互、导出、运行时兼容全部自管 | 当前没有证据证明必要；先证实现成工具存在不可接受的产品瓶颈，再考虑。 |

**直接下一阶段以[总报告的同样本基础 A/B 对照](README.md#下一轮的有界对照)为准。** 固定同一 MH/MPFB 基础、简单 deform rig、合法衣物和少量参数，至少一个体型参数、一个脸部参数；比较“离线编译小人物包”与“Humentity 等读取成熟人体数据的 Rust 路径”。该阶段必须检查体型改变后的骨架/衣物拟合及动作结果，不能先把 rig 固定不变来回避比例适配问题，也不预先宣布编译路径获胜。动漫 target 是该基础对照中的独立风格候选。具体共同样本、验收和资源门以总报告为权威。

人物基础与运行路径选定，且对应 rig、比例变化和衣物处理通过准入后，才考虑下面的配方组合实验。其固定 rig 是一个独立、有界的 agent 合同测试范围，不替代前面的基础选择或骨架适配验收。任意雕刻、任意模型融合和新动作生成仍分别定义；图片拟合语义参数仍是未验证假设。

## 后续条件实验：基础选定后的 agent 配方组合（未执行）

问题：**不重写雕刻内核，用可发现参数＋固定视觉/测量反馈，agent 能否稳定把同一动漫基础的两个配方组合成第三个，并保留动作可用性？**

启动条件：先完成总报告的同样本基础 A/B 对照、选定人物基础及运行路径，并完成该基础的 rig/比例/衣物准入；否则本实验不启动。输入限定为该已准入、可修改/分发基础的两份同 profile 配方；不用任意图片、任意拓扑或新模型。不能拿当前四参数 fixture 充当动漫人物完成度。

在上述条件满足后，验收采用一个连续闭环；6–10 参数与固定 rig 只属于这一后续阶段，不是直接下一轮基础 A/B 的前置工作：

1. 固定 asset/profile/rig/compiler 身份；6–10 个有实际可见形变的身份参数，至少两类脸部与一类身体特征。表情独立；第一版不改骨长。选定一个有界双参数组合，若需要补偿，在 Blender 制作并编译一个 corrective；不临时扩大范围。
2. agent 只读发现输出，接收“用 A 的脸宽/眼距、B 的肩宽，保留中性表情”的结构化意图；创建第三份 Work，不覆盖 A/B。必须展示实际参数、命令和最终 recipe。不得把数值平均默认为特征保留。
3. 固定舞台/相机输出前、侧、3/4 三视图，以及 idle、抬臂、屈肘三个已制作测试姿势。身份极值与选定双参数组合都要检查；输出测量、异常与实际图像。先验定义脸部/比例的容差及网格穿插检查范围，报告基线是否本来有缺陷。
4. 独立复算身份测量，检查目标特征落入预定容差；故意用错 profile hash、target 定位、越界值和 revision，必须拒绝且保留原作品。故意移除 corrective 时，预先选定的组合质量检查应转红，否则该质量检查不足以证明修正有效。
5. 同资产/配方重复求值，比较数值状态；单独比较导出结构，记录允许的浮点容差。不要用重复渲染像素逐字节一致作为所有 GPU 的默认承诺。
6. 最终 Work 在实际 native/Web 加载、播放、保存往返；把 headless 数值、离屏图像、双端实际图像和人类美术接受分别记录。若尚无正式离屏入口，先在隔离实验实现/验证，再提出产品接入；不声称当前 CLI 已支持。

通过只证明该基础、参数域、组合和姿势的接口闭环。扩大体型、服装、头发、骨长、更复杂 corrective 或动作来源都要加新准入门。若 agent 仍需大量猜测 vertex/target 或盲试，优先改善描述和反馈；这不是立即重写雕刻算法的证据。

## 风险、现有证据与未验证项

- **现有**：共享文件/命令、Work 内嵌 profile、固定资产 SHA 与四 morph、schema 2 舞台已从当前源码核对。Roadmap 中的 native/Web、真实动作样本与质量 HOLD 是已有报告状态，本次没有重跑。
- **提案**：语义编译器、node-specific 多绑定、身份/表情分层、宏依赖、rig manifest、批量预览、测量与候选搜索接口，均未实现。
- **假设**：某个成熟动漫参数基础可在可接受许可、风格和性能下满足目标；参数＋视觉反馈足以让 agent 得到满意混合角色。需最小实验验证，本文不替具体 provider 选型作结论。
- **NOT-RUN**：新角色导入/导出、骨骼适配、corrective、任意模型融合、图像拟合、模型推理、离屏渲染、native/Web 角色质量、新 head 的 CI/性能。没有下载/安装/执行第三方工具、运行模型或修改 root dependencies/lockfile/产品源码。

PARTIAL — 当前源码与 GLB 元数据已核对，官方格式/工具文档已研究；新角色与 agent 视觉闭环尚未运行。

## 仓库引用（均为上述固定提交）

行号以仓库内当前文本为准；路径为 repo-relative，便于在工作树或该提交中重查。

- R1: [`docs/implementation/contract.md`](../../implementation/contract.md):3–22,25–49,52–80。
- R2: [`crates/nvwa-core/src/lib.rs`](../../../crates/nvwa-core/src/lib.rs):120–156。
- R3: [`assets/character.profile.json`](../../../assets/character.profile.json):1–53。
- R4: [`crates/nvwa-core/src/lib.rs`](../../../crates/nvwa-core/src/lib.rs):359–387。
- R5: [`crates/nvwa-runtime/src/lib.rs`](../../../crates/nvwa-runtime/src/lib.rs):350–364,1157–1178。
- R6: [`crates/nvwa-core/src/lib.rs`](../../../crates/nvwa-core/src/lib.rs):158–197,477–515。
- R7: [`crates/nvwa-cli/src/main.rs`](../../../crates/nvwa-cli/src/main.rs):86–219,237–311；[`docs/CLI-SUPPORT.md`](../../CLI-SUPPORT.md):7–26,38–48。
- R8: [`docs/adr/0005-portable-document-and-commands.md`](../../adr/0005-portable-document-and-commands.md):3–9；[`docs/agents/cli-authoring.md`](../../agents/cli-authoring.md):19–62。
- R9: [`crates/nvwa-core/src/asset.rs`](../../../crates/nvwa-core/src/asset.rs):5–91,109–151。
- R10: [`docs/ROADMAP.md`](../../ROADMAP.md):3–19。
- R11: [`assets/fixtures/provenance-manifest.json`](../../../assets/fixtures/provenance-manifest.json):2–28。
- R12: [`assets/fixtures/source-structure.json`](../../../assets/fixtures/source-structure.json):7–40；实际 GLB JSON 与 SHA 由本次内置 Python `struct/json/hashlib` 只读解析，未保存新资产。
- R13: [`docs/adr/0003-original-character-fixture.md`](../../adr/0003-original-character-fixture.md):7–47。
- R14: [`GLOSSARY.md`](../../../GLOSSARY.md):7–37。
