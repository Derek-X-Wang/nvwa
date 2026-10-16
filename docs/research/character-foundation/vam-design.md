# VaM 角色系统：可借鉴的边界与不可搬运的依赖

来源检查日期：2026-10-16。范围：VaM **1.x** 公开官方文档、官方补丁说明、公开授权文本。未把 VaM2 计划当作 VaM1 的现有能力。未登录、运行 VaM、下载资产、安装插件、反编译或读取非公开资料。没有实现代码。

证据标记：**VERIFIED-DOC** 表示公开文档明确记载，未作运行验证；**建议/推断** 表示面向 Nvwa 的设计判断；**UNKNOWN** 表示本轮未找到足够的一手证据。官方 Wiki 由 VaMDeV 发布，页面同时说明具备权限者可编辑；这是一手产品文档，不是源码或形式化契约。[官方目录](https://hub.virtamate.com/forums/wiki.54/)

## 结论

Nvwa 应借鉴 VaM 的三个成熟边界：角色实例与舞台分开；外观、姿态和动作分开；资源引用与分发许可分开。不要以 VaM 文件或插件兼容为目标。当前 4 morph / 18 bones fixture 和已固定资产的保存格式，仍只说明已有的小规模通路；不能据此声称具备成熟人体、体型适配或通用动作兼容性。这些 Nvwa 现状来自本次研究 dispatch，未在本文件重新审计。

最重要的反面证据也来自官方文档：体型 morph 可以影响骨骼；多个动画驱动通道会争夺控制；资源能加载不代表可重分发。下一步应先用一套来源清楚的角色资产证明“改体型后仍能摆姿、播放动作、保存并离线复现”，再扩充参数数量。此段是研究建议。

## 1. Person / Atom：角色是有身份的场景实体

**VERIFIED-DOC**：Person 是场景中的 Atom。Root Control 移动整个角色控制架。官方明确区分用户操作的 **Control Rig** 与实际驱动网格的 **Mesh Rig**；弹簧和力参数影响两者关系，On / Comply 提供不同操控方式。官方同时明确 VaM1 男女人体基于 **DAZ Genesis 2**，选择男/女 skin 会切换对应人体类型。[Person Atom Basics](https://hub.virtamate.com/threads/09-person-atom-basics.55033/)

**建议/推断**：Nvwa 可使用独立角色实例身份、资产引用、外观状态、当前姿态和动作播放状态。舞台只持有角色实例及灯光、相机、地面等局部对象。应借鉴“作者意图与最终骨骼结果分开”；当前不需要复制 VaM 的双物理 rig、成人物理细节或完整 Atom 宇宙。Rust 核心要能回答哪个系统控制某根骨骼，以及最终姿态由何种输入产生。桌面、Web、CLI 应读同一结果。

**建议/推断**：不要复刻 skin 选择与人体类型切换的隐式耦合。Nvwa 应让 mesh / rig compatibility 与材质替换有明确独立身份，避免 agent 换肤时意外换了骨架或身体结构。

## 2. Morph：不是一组没有语义的浮点数

**VERIFIED-DOC**：Morph UI 有名称和类别过滤、来源过滤、active / favorite 过滤；区分普通 morph、pose 和驱动其他目标的 formula morph。参数有 min / max / default / zero；范围可扩展，但官方警告极值可能失真甚至崩溃。带骨骼变化的 morph 有专门提示，突变动画可能造成物理爆炸。来源可区分 built-in、package、local 与旧式 transient，并可复制完整 UID。[Morphs](https://hub.virtamate.com/wiki/person_female_morphs/)

**建议/推断**：下一代 Nvwa 参数目录至少应有稳定 ID、显示名、身体区域、默认值、有效范围、单位或归一化语义、资产来源、是否影响骨骼，以及是否适合连续动画。UI 的中文标签和搜索不应成为保存键。不要假定全部参数都是 `[0,1]`，也不要把“0”当作所有参数的默认值。高层参数若驱动多个目标，应能列出驱动关系，检测环，并规定父项和子项同时写入时的冲突规则。这是新契约建议，不是声称 VaM 使用某种特定依赖图算法。

对 agent 的重要区别：人工可以凭视觉试滑杆；agent 需要先枚举能力，再按 ID 写值，得到合法范围、实际接受值和结构化错误。批量命令应原子验证，避免半数参数成功后留下难复现的身体。

## 3. 改体型后的骨骼、关节与皮肤适配

**VERIFIED-DOC**：VaM 提供 Physics Explosion Recovery，恢复过程涉及重置姿态与物理对象。它的 OBJ 导出分别提供基准 T-pose 和当前 skinned pose；导出不包含头发、服装、贴图、动画或场景物件。[Control & Physics 1](https://hub.virtamate.com/wiki/person_control_physics1/)

**VERIFIED-DOC**：皮肤贴图必须匹配角色的 UV 布局；Genesis 2 的多个 UV 集存在差异，选错会出现接缝、错位或拉伸。VaM 分开处理 diffuse、specular、gloss、decal、normal 等贴图。[Skin Textures](https://hub.virtamate.com/wiki/person_skin_textures/)

**UNKNOWN**：本轮没有公开官方源码或充分技术说明，证明 VaM 如何计算 morph 后的关节中心、bind matrix、骨长、蒙皮权重、碰撞体重建、joint limits、衣物适配或 corrective shape。不能从“有 bone morph”推出它能自动可靠修正任意体型，也不能从 UI 滑杆顺滑推出所有组合都有效。

**建议/推断**：Nvwa 应把身体变形、静息骨架变化、皮肤变形和动作适配作为独立可测责任。先挑一个会改变骨长或肩宽的参数，检查 neutral / 两端值 / 两个参数组合下的手肘和膝盖弯曲、足底接地及动作结果。若下一片暂不含物理，则显式用确定性动画验证，不能用“无物理爆炸”代替变形质量。皮肤材质需携带 UV / mesh compatibility；“可加载图片”不等于“可用皮肤”。

## 4. 外观、姿态、动作与命令

**VERIFIED-DOC**：VaM 的 `.vap` preset 是 JSON 文本，按 appearance、morph、pose、skin、hair、clothing、plugin 等用途区分；scene / subscene 使用 `.json`。官方提醒 legacy preset 可能造成场景问题，建议不用。[File Types and Presets](https://hub.virtamate.com/threads/08-file-types-and-presets.55029/)

**VERIFIED-DOC**：Person 的录制场景动画、built-in 动画和 plugin 动画有不同开关；关闭场景 Playback 并不会关闭其他通道。Built-in 动画可覆盖 plugin 对控制节点的驱动，并与 mocap 冲突。动作可组成 sequence，具有速度、循环、逐片 crossfade、暂停和重置等行为；官方列出其内置动作来自 Mixamo。[Person Animation](https://hub.virtamate.com/wiki/person_animation/)

**VERIFIED-DOC**：Trigger 采用 `Receiver Atom > Receiver > Receiver Target` 结构，以同一种寻址方式对 Atom 内部属性或动作发命令。[Triggers](https://hub.virtamate.com/threads/10-triggers.65436/)

**建议/推断**：Nvwa 应给 appearance load 定义明确写集，不修改 stage transform、当前动作或播放时钟；pose 是时刻姿态，clip 是随时间变化的数据，rehearsal 是角色与动作的绑定及播放状态。统一命令可借鉴分层寻址，但用稳定类型和 ID，避免显示名、字符串路径和 UI 状态成为隐含协议。应规定每个关节和参数的驱动优先级；Pause / Reset / Stop 的影响范围应在 GUI 和 CLI 完全相同。

**UNKNOWN**：官方 preset 概览没有在本轮提供完整字段级写集、迁移规范和 schema。不能仅凭文件名认定 VaM Appearance 一定包含或排除某个物理或 plugin 状态。本轮没有验证 `.vap` 的任意字段兼容，也不建议实现它。

## 5. Plugin：学能力边界，不学二进制或脚本兼容

**VERIFIED-DOC**：官方发布说明确认可动态载入 C# / managed DLL 的 plugin 系统，并记载 `FileManagerSecure`、preset 加载、保存回调等扩展点。但它同时持续记录安全修补和 API 兼容修复。[VaM Patch Notes](https://cdn.virtamate.com/Release/VaM_PatchNotes.html)

**VERIFIED-DOC**：插件、网络、内置浏览器、远程图片/音频及 Hub 访问有分开的安全选项；第三方插件需要许可，网络能力也可独立关闭。官方文档说明场景可触发网络导航或下载。[Security Tab](https://hub.virtamate.com/wiki/user_preferences_security/)

**建议/推断**：Nvwa 第一阶段优先提供核心类型化命令和可查询能力。未来扩展也应按文件读取、文件写入、网络、模型服务等能力声明权限，并可在无网络、无插件状态下离线打开基础角色与动作。不要把 scene load 等同于执行任意代码，不要让存档依赖某个插件的私有全局状态。插件缺失应给诊断，而非静默替换。

**UNKNOWN**：公开 `apidoc.virtamate.com` 的 MVRScript / DAZMorph / JSONStorable 页面在本轮工具访问失败；没有核对完整 API。未检查或复制第三方插件代码，也未确认任何插件许可。此文没有任何可直接复用的 VaM 插件实现结论。

## 6. VAR、依赖与离线可复现

**VERIFIED-DOC**：`.var` 是放在 `AddonPackages` 的内容包，包根的 `meta.json` 用于 VaM / Hub 元数据；morph 文件形式包括 `.vmi`、`.vmb`、`.dsf`。Unity assetbundle 另有特定 Unity 版本要求。这说明文件可读并不意味着运行时通用。[File Types and Presets](https://hub.virtamate.com/threads/08-file-types-and-presets.55029/)

**VERIFIED-DOC**：Package Manager 展示作者、内容、许可和外部引用；能区分缺失依赖与安装了其他版本的情况，并可扫描 Hub。插件信任是每包偏好。文档还提供隐藏缺失依赖列表错误的选项；隐藏显示不是修复依赖。[Package Manager](https://hub.virtamate.com/wiki/package_manager/)

**VERIFIED-DOC**：官方补丁说明记载 exact / latest / minimum 版本选择，以及 package finalize 的引用检查和错误标记。[VaM Patch Notes](https://cdn.virtamate.com/Release/VaM_PatchNotes.html)

**建议/推断**：Nvwa 的固定资产保存格式应继续沿用“显式资产身份”的方向。以后增加包时，需加 manifest、内容 hash、精确解析结果、直接/传递依赖、作者/许可/来源和兼容版本。编辑时允许建议更新，保存/重放使用锁定解析结果；`latest` 不应改变既有离线作品。可做一个纯本地检查命令：列缺失文件、错误 hash、不兼容 rig、未确认许可和必需扩展。不得悄悄访问 Hub 或补下载；将可选贴图缺失与使角色不可重放的必需资产缺失分开报告。

## 7. 授权与来源：VaM 能用，不代表 Nvwa 能带走

| 对象 | VERIFIED-DOC | 对 Nvwa 的边界建议 |
| --- | --- | --- |
| VaM 程序及随附文件 | 公开 VaM+vamX EULA 是专有许可；限制转让、提取/修改文件和衍生作品。反编译例外仅针对给该产品制作插件。[公开 EULA](https://store.steampowered.com/eula/2149830_eula_0) | 不导入 VaM binaries、随附素材或反编译产物；公开文档只作为设计研究。该 EULA 对应 Steam 捆绑版，不声称已验证所有发行渠道的相同条款。 |
| DAZ / Genesis | VaM 官方确认 Genesis 2 来源。DAZ 官方区分渲染成品与交互式 3D 资产使用；是否有 Interactive License 是逐商品决定。[DAZ Interactive License](https://www.daz3d.com/interactive-license-info) | 购买 VaM、拿到免费 Genesis 或成功导出 OBJ，都不能当作可重分发许可证。 |
| DAZ 再分发与 agent 使用 | 当前 EULA 保留资产所有权，要求保护交互式应用中的资产免于原生格式提取；另有商品额外条款和 AI 输入限制。[DAZ EULA §1.0 / §3.0](https://www.daz3d.com/eula) | 可自由导出、由 agent 操控/生成角色的工具，不能仅凭“买了 interactive license”判定适配。此产品形态必须逐项确认授权。研究建议优先使用明确允许编辑和再分发的自有/开放资产。 |
| Hub VAR / 插件 / morph / 皮肤 | 官方区分 CC 条款、FC、PC、PC EA 和缺失/可疑许可；免费、依赖引用、改包并非统一权利，且 NC / ND / SA / BY 各有条件。[VAR Licenses](https://hub.virtamate.com/wiki/license_help/) | 每个资源核对权利与上游来源；外层包许可不洗白底层 DAZ 或他人作品。没有明确许可就不纳入可分发 fixture。 |
| VaM 内置动作 | 官方只证明其来自 Mixamo。[Person Animation](https://hub.virtamate.com/wiki/person_animation/) | 本轮没有独立核对 Adobe / Mixamo 授权；不复制这些 clips，不作动作再分发许可结论。 |

**UNKNOWN**：MeshedVR 与 DAZ 之间具体商业许可、VaM 各内置文件的逐项来源及授权、任意 Hub 资源作者是否拥有其声称的权利、插件能否跨运行时复用，都未被本轮证明。对法律文本的上述内容是来源摘要和产品边界判断，不是特定资产的法律批准。DAZ 的 AI 条款也不能被直接扩大解释为“任何 agent 调一个本地参数都被禁止”；具体场景仍需确认。

## 8. 给下一片的可验收研究建议

以下均为建议，未实现、未运行。范围保持 Rust + Desktop + Web + CLI 的单角色创作和排练，不扩到 world server。

1. **先选合法底座**：一套明确允许产品分发、角色修改及保存/导出的 mesh、rig、皮肤和短动作。资产与代码许可分开记录；没有确定来源的资源不得用来证明可发布。
2. **再证明体型与动作共存**：一个骨长相关参数、一个局部面部参数、中立值与端点值、一个组合，播放同一段动作；检查关节、轮廓、足底和可见皮肤。证据应包括已知极端失败，而不只看正常身材。
3. **证明状态边界**：外观替换保留场景位置和动作时钟；pose 替换和 clip 播放有明确优先级；CLI 与可视端得出相同核心姿态。保存、重启、离线重放保留精确资产与参数。
4. **排练舞台保留可观察性**：角色脚下地面、稳定灯光、相机预设、动作列表、时间轴、播放/暂停/重置和当前驱动提示。先让人看清“身体是否工作”，再增加物理和插件。
5. **保留失败信息**：缺失资产、错误版本、未知参数、越界值、动画驱动冲突和不兼容 rig 都应返回结构化诊断；不得静默忽略并显示成功。

## 验证范围

**VERIFIED —** 公开官方 Wiki、官方补丁说明、VaM+vamX 公开 EULA、DAZ 官方许可页面和当前 EULA 已在 2026-10-16 读取；关键结论附直接链接。

**NOT-RUN —** VaM 运行、体型与骨骼适配、存档 round-trip、插件 API 实测、VAR 实包解析、Nvwa 三端测试与视觉验证均未进行。没有下载或复用任何受许可约束的 mesh、贴图、动作或插件代码。
