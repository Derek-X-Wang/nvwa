# Honey Select 参照：Nvwa 离成熟人物创作产品还差什么

来源检查日期：**2026-10-17**。后台研究者核对公开资料，整合负责人另行核对 Nvwa 当前源码、既有验收文件与 GitHub 状态。本轮不重新运行产品，不下载游戏、模型或插件，不修改实现。本文引用已有运行证据，不把资料研究称为新的实机对比。

## 判断与证据边界

**建议：把目标定为“能反复创作漂亮角色、稳定排演动作的小工作室”，先完成这一条闭环。** 按本轮收到的当前证据，Nvwa 已有可用工程基础，并完成一小块成熟人体数据的接入；离完成这一目标仍有实质产品距离。主要缺口是外观内容和质量、体型变化后的连续动作质量、脸部与姿态控制、可观察且可纠错的人/agent 创作流程。不能用几项参数、一个漂亮静帧或一次保存交换推导完成比例。此段是研究判断，不是开发工期估算。

本报告主要参照 **Honey Select 2 / Studio NEO V2**；不把 HS1、HS2、HS2 DX、Steam 版及社区整合包当作同一版本。可访问的旧页面自署 ILLUSION，但位于第三方 `illusion.rip` 镜像；**原文真实性、完整性和具体适用版本未独立认证**。它们只提供历史能力线索，不能单独证明当前销售版本的完整功能。社区仓库是一手社区项目资料，能证明作者如何定义自己的扩展；没有进行运行验证。

| 证据层 | 本轮实际取得的材料 | 可支持的结论 |
|---|---|---|
| 当前官方入口 | Steam 商店跳转登录/年龄检查；旧 `illusion.jp` 手册请求失败；Steam 发布者新闻仅返回空壳内容 | **无法取得足够当前官方正文**。没有登录、填年龄、接受提示或绕过限制 |
| 历史作者归属页面的第三方镜像 | HS2 Steam 手册、版本说明、Studio NEO V2 介绍、兼容说明 | 历史产品的能力家族和版本边界线索，带上述保留 |
| 社区项目作者仓库 | HF Patch、HSPlugins、KK_Plugins、BepisPlugins、AdvIKPlugin | 社区补丁、工作流与扩展的公开自述；不能算进原版或保证任意组合可用 |

受限入口：[Steam 商店](https://store.steampowered.com/app/1631080/HoneySelect2Libido_DX/)、[旧官方手册地址](https://hs2steam.illusion.jp/manual/readme_en.html)、[尝试的旧 Studio 手册地址](https://www.illusion.jp/preview/honey2/manual/studio.html)、[Steam 发布者公告](https://steamcommunity.com/games/1631080/announcements/detail/3660916710569411748)。本轮取得的错误不能证明这些入口对所有用户永久不可用。

## 距离应按三个目标判断

| 目标 | 当前判断 | 下一个可见的验收结果 |
|---|---|---|
| 一个能编辑、保存、播放的人物技术原型 | 已有有界运行证据；新旧人物后端的能力仍不相同 | 在同一个 B1 人物上同时成立：可见的外形变化、连续动作、衣物跟随、保存重开 |
| 接近成熟人物编辑器/Studio 的实用小工作室 | 还有几个核心系统与内容管线的差距，尤其外观、多样体型和动作组合质量 | 捏出几种明显不同且愿意保留的角色，在少量好用动作与试演环境中反复创作；人和 agent 都能看见结果并修正 |
| 完整商业游戏及社区内容规模 | 属于更大的产品目标；现有资料不足以给出完成百分比或工期 | 先定义玩法、互动反馈、内容覆盖和发布目标；世界编辑与多人服务器不自动加入 Nvwa 范围 |

这是基于当前证据的产品判断。代码、模型/素材制作、动作调校、工具体验和兼容测试应分别估算；不能把“有人物、能动、有房间”三项功能的存在当作商业完成度。

## Nvwa 当前状态的核验依据

本轮核对 GitHub `main ea02b0a05e7be96ba481fdf4898dc20e59af69bd`；[#74](https://github.com/Derek-X-Wang/nvwa/issues/74) 已完成，[PR #76](https://github.com/Derek-X-Wang/nvwa/pull/76) 已合并，其 [精确 main CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/39017885725) 已通过。`docs/ROADMAP.md` 的 2026-10-16 段落仍是此前快照，不能据其“接入中”文字否认此后交付。

- [原 GLB 配置](../../assets/character.profile.json)：四个形变参数、三个预制动作；[当前 README](../../README.md) 区分该路径与 B1。
- [B1 合同](../../crates/nvwa-core/src/b1.rs)：固定人体/运动服、两个参数与五个诊断姿态；[原生和双端往返验收](../evidence/b1-work/NATIVE-VALIDATION.md) 记录实际运行及边界。
- [舞台验收](../evidence/rehearsal-stage/ACCEPTANCE.md) 与 [#69](https://github.com/Derek-X-Wang/nvwa/issues/69)：A 阶段可调舞台已交付，B 房间导入与 C 接触/物理仍未交付。
- [CLI 正式范围](../CLI-SUPPORT.md)：离线文件命令、发现和校验；正式离屏渲染、运行中 Studio 控制与外部引擎接收尚未验收。已有诊断实验或文件往返不扩大此正式范围。

## 参照产品应怎样拆开

1. **角色编辑器**：历史 HS2 Steam 手册列出脸、身体、头发、服装、配饰；形状滑杆与类型/颜色选择并存。人物卡、服装卡、部分加载和两个人物的合并也是明确的创作流程。这里的深度包含资产选择和配方管理，不只是 morph 数量。手册还描述独立于编辑器的房间、分组、对话、状态、事件、奖励及进度保存流程。[S1：历史手册镜像](https://hs2steam.illusion.rip/manual/readme_en.html)
2. **Studio 场景创作**：历史 NEO V2 页面将其定义为摆放人物、地图和物件，进行拍摄及观赏的场景工具；列出物件移动/旋转/缩放、人物姿态与表情、灯光。社区 HF Patch 作者也明确说明 Studio 是独立可执行程序，由免费更新提供。两种来源相互支持“本篇与 Studio 分开”，但不能补出某一具体原版发行包的完整清单。[S2：历史 Studio 介绍镜像](https://old.illusion.rip/preview/studioneo2/index.php)、[S5：HF Patch 作者说明](https://github.com/ManlyMarco/HS2-HF_Patch)
3. **版本与内容包**：历史兼容页明确排除 HS1 的人物卡/场景直接用于 HS2，并将 Studio 场景与本篇分开；Steam 介绍页也警告 Steam 版和 DVD/DL 更新、付费 DLC 可能不兼容。故不能用“HS 系列都能”代替版本核查。[S3：历史兼容页镜像](https://illusion.rip/preview/honey2/compatible.php)、[S4：历史 Steam 版介绍镜像](https://hs2steam.illusion.rip/index_en.php)
4. **社区工作室**：HSPlugins 当前仓库明确含 HS2 的 PoseEditor、Timeline、NodesConstraints、VideoExport 项目；HF Patch 的插件说明也把 Timeline 与录像作为扩展列出。看到复杂社区作品，不能将其所有能力归给原版。这里没有把 Studio 推导成开放世界、在线多人或网络服务器。[S6：HSPlugins](https://github.com/IllusionMods/HSPlugins)、[S10：HF Patch 插件清单](https://github.com/ManlyMarco/HS2-HF_Patch/blob/master/Plugin%20Readme.md)

## 对 Nvwa 最有用的差距清单

以下“当前证据”由主审查者在 `main ea02b0a` 上确认。**旧 GLB 与新 B1 是不同路径，不能把两者能力相加后称为新人体已可跳舞。** 本表的目标/优先顺序是建议，不是已承诺范围。

| 责任 | HS2/社区给出的参照 | Nvwa 当前证据与建议验收 |
|---|---|---|
| 外观深度与审美 | 历史编辑器同时组织形状、头发、衣物、配饰及配方；这是内容库与编辑流程的组合。[S1](https://hs2steam.illusion.rip/manual/readme_en.html) | 旧 GLB 有 4 morph；新 B1 只有 torso_length/jaw_drop 两参数与一套 body+sportsuit。应先形成少量风格明确、真的愿意使用的完整角色，再扩大参数和资产数量；当前证据不证明皮肤/头发/妆容/衣物品类已完成 |
| 材质、头发、服装资产链 | 社区 MaterialEditor 能改贴图、材质、shader 并随卡/场景保存；HairAccessoryCustomizer 要求作者正确配置部件、网格和骨骼。资产必须按规范制作，并非随便导入就自然可编辑。[S7](https://github.com/IllusionMods/KK_Plugins/blob/master/README.md) | B1 静态衣物适配是小范围准入。下一步应验证外观包的合法来源、材质/UV/rig 兼容、体型端点、动作中的穿插和退化结果。没有资料证明 HS2 的内部衣物拟合算法，不能照名猜实现 |
| 连续动作与体型适配 | 社区 AdvIK 提供肩部控制、呼吸和换不同身高角色时的目标调整；作者同时说明自动中心可能选错，需要按脚、坐姿等条件选择。这是任务相关校正，不是任意动作自动正确。[S8](https://github.com/OrangeSpork/AdvIKPlugin) | 旧 GLB 有 idle/turn/wave、9 秒序列和 Player；90 帧 AI 样本曾在旧 GLB 播放，但质量仍 HOLD。新 B1 只准入 5 静态姿势，没有连续 clips。优先用同一 B1 的连续动作验证脚底接地、关节、衣物穿插和体型端点 |
| 姿态、脸部和驱动关系 | 历史 Studio 提供姿态/表情；社区 FKIK 在反向运动学（拖目标求关节）与正向运动学（直接转关节）间补充组合控制。它是社区扩展，不是原版“任意 IK/FK 一起都稳”。[S2](https://old.illusion.rip/preview/studioneo2/index.php)、[S7](https://github.com/IllusionMods/KK_Plugins/blob/master/README.md) | 需要明确动作、手动 pose、脸部参数和未来 IK 谁控制最终结果；能编辑 smile 不等于完成眼神、眨眼、嘴型及表情动作系统。先建立一组表达与摆姿任务的可见验收 |
| 可用的排练室 | Studio 的核心是局部构图；更复杂时间线与导出可来自社区。[S2](https://old.illusion.rip/preview/studioneo2/index.php)、[S6](https://github.com/IllusionMods/HSPlugins) | Room A 已有相机、key/fill/ambient、背景、地板、阴影、质量档位及保存交换。Room B、接触/物理 C 尚未验证。当前目标可先完成一个能看清人物、比较动作、保留取景的排练室；无需先做通用世界编辑器 |
| 人/agent 共创与反馈 | 社区卡/场景能携带扩展数据和依赖信息；但这不等于 agent 的语义编辑、截图判断或自动纠错。[S9](https://github.com/IllusionMods/BepisPlugins) | 当前 CLI 是文件式 typed commands/capabilities/validation，没有正式离屏画帧、渲染、MCP 或实时 Studio 桥。需要“查能力→改配方→取得可信画面→诊断→修正→保存/重开”的产品闭环；全流程文本/参考图到漂亮人物到好动作尚未产品化 |
| 成品包装与内容循环 | 历史本篇还有教程、事件、对话、状态、奖励、进度等使用循环；它们与 Studio 创作循环是不同产品层。[S1](https://hs2steam.illusion.rip/manual/readme_en.html) | Nvwa 现阶段可先完成角色+动作工具的循环：选角色、改外观、选/做动作、排练、纠正、保存、交换、再次打开继续。若以后要完整可玩游戏，还需单独定义剧情/互动/内容循环；不把它们混入当前里程碑 |

**外部世界工作流另设出口门。** 当前 Desktop↔Web 的 Work 交换证明同一格式与同一执行体系间互通；它不等于已将编辑后的 mesh、rig、morph 和材质导出并准入第三方游戏引擎。若目标是把人物送进别的游戏/世界，应另选一个具体接收端，验证外观、动作、材质、单位/坐标、许可与重开结果。这是人物工具的出口能力；不要求 Nvwa 同时开发通用世界或网络服务器。此现状由主审查者提供，出口门是建议。

## 最值得学与复用的边界

**优先学结构，内容另找合法来源。** 角色卡、服装卡、场景状态及插件数据分开，有利于替换角色、复用动作、定位依赖。BepisPlugins 的 ExtensibleSaveFormat 把扩展数据附在人物/服装/场景卡上；Sideloader 使用压缩包并解决项目 ID 冲突。它也明确：非模组环境可能丢失扩展数据。因此 Nvwa 的 Work 应继续显式记录资产身份、版本、依赖、兼容性和无法恢复的字段；不要默默降级为“加载成功”。[S9：BepisPlugins](https://github.com/IllusionMods/BepisPlugins)

**把社区能力当成需求证据，不当成可直接移植的 Rust 人体内核。** HSPlugins 自述依赖 BepInEx/BepisPlugins，按游戏分别构建；这是围绕现有游戏的扩展。可学习姿态、时间线、约束、输出的模块边界，但本轮没有核验任意代码迁移的成本或全部许可证，更没有证明商业人物/衣物/动作可重分发。[S6：HSPlugins](https://github.com/IllusionMods/HSPlugins)

**先补角色在运动中成立的证据，再扩房间和滑杆。** 最有价值的下一片是：同一可分发 B1 角色，有限外观/体型，至少一个连续动作；固定镜头比较、停帧纠正、保存重开。手/脚接触、表情、物理可分片加入。社区高级 IK 的中心选择要求说明：人的身高变化、姿势意图和接触点必须显式处理，不能期待一套通用缩放自动解决。[S8：AdvIKPlugin](https://github.com/OrangeSpork/AdvIKPlugin)

**漂亮画面不自动要求完整物理模拟。** 本轮没有足够一手证据确定 HS2 原版布料、头发或软体的精确技术范围。预制动画、IK、附属骨骼运动、碰撞和通用物理模拟应分别验收。Nvwa 可以先用合法的预制内容与受限修正完成好看的排练；没有依据要求先建设 VaM 规模的物理系统。此段是针对未知技术范围的设计判断。

## 明确未知项

- **原版细节未知**：本轮未独立认证当前原版的精确 morph/发型/衣物/动作数量、Steam 版 Studio 准确交付范围、现代硬件性能或插件组合稳定性。没有给出这些数量或完成百分比。
- **内部技术未知**：没有原厂人体/服装求值算法、关节修正、碰撞体更新、物理约束、动画重定向的充分公开源码证据。可观察的 UI 不证明底层通用性。
- **内容可复用性未知**：本轮未做商业资产或完整插件依赖的许可审计，没有推荐复制 HS 卡、网格、贴图、声音或动作。
- **质量仍需实测**：文档说明功能存在，不说明任意体型、长发、衣物、表情和多人动作都达到目标品质。Nvwa 也需分别取得静态形变、连续动作、画面审美、保存交换和性能证据。

**PARTIAL —** 完成 10 个公开文档/项目页面的有界研究及版本/原版/社区区分；当前官方正文有访问限制，历史镜像真实性未独立认证。所有产品运行、资产质量、内部算法和迁移验证均 **NOT-RUN**。
