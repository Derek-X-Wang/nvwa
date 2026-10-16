# 开源参数化人体基础：MakeHuman / MPFB 与替代路线

核查日期：2026-10-16。范围：公开一手资料、官方许可证、仓库元数据与少量官方脚本示例。未下载模型、贴图包或二进制，未安装、运行 Blender 或角色生成器，未修改产品代码。

## 建议

优先把 **MPFB + MakeHuman 核心 CC0 数据**作为人体资产制作与参考计算管线。先在 Blender 外部工具环境中产出一个可核对的角色，再选择性地把已核准的数据和必要计算放进 Nvwa 的 Rust 核心。官方明确允许以基底网格、targets、系统资产包另建角色生成器；不必为了复用人体数据而把 MakeHuman/MPFB 的 Python 实现整体带入产品。[官方许可重用 FAQ](https://static.makehumancommunity.org/mpfb/faq/build_other_chargen.html)

这是研究建议，不是已验证的集成结论。Nvwa 的 Rust、Bevy、Web、CLI 共同运行边界来自本次任务约束；本文不重新验证现有 fixture。现有 fixture 的 CC0 声明不能替代未来导入资产的来源与许可清单。

核心取舍：这条路线可复用成熟的人体形变、关节定位与服装对应数据；Nvwa 负责跨平台参数执行、数据打包、极端形变质量与运行时验证，优先复用现成实现。先做资产制作管线最容易控制风险；把 Blender/Python 作为所有客户端的必需运行环境会引入另一套执行与交付边界。MPFB 本身定位为 Blender 生成器，服务 API 的对象也是 `bpy.types.Object`。[官方仓库](https://github.com/makehumancommunity/mpfb2)、[HumanService 文档](https://github.com/makehumancommunity/mpfb2/blob/3af0cd5a2ffba072e93a34e5f6f494fdc4813ddf/docs/services/humanservice.md)

## 候选比较

| 路线 | 当前维护证据 | 人体/风格能力 | 资产与导出许可 | 对 Nvwa 的判断 |
|---|---|---|---|---|
| MakeHuman 1.x | 官方说旧 GUI 已基本不改动，不应期待一般修复；新 GUI 重写尚不能替代它 | 成熟共用人体数据；独立 GUI；与 MPFB 共用 hm08 | 程序 AGPL-3.0-or-later；随附图形数据 CC0；第三方资产另查 | 用作数据来源和参考；不建议把旧 GUI/引擎作为新产品基础 |
| **MPFB 2** | 2.0.18 于 2026-10-10 发布；仓库仍更新 | Blender 原生人体建模，宏参数、细节、多个骨架、衣服拟合、代理拓扑；有可选 cartoon/anime targets | 代码 GPL-3.0-or-later；随附图形数据 CC0；可选包逐项核对 | 首选资产制作和参考实现；能否形成 Rust 数据管线需小样证明 |
| CharMorph | 仓库未归档；默认分支提交快照为 2024-10-10；不能从未归档推断持续维护强度 | 重写 MB-Lab 功能，实时衣服拟合、Rigify 面部 rig、替代拓扑；MB 人物配置含 Anime/Elf/Dwarf | 代码 GPL-3.0-or-later；角色库混合 CC-BY 与 AGPL，导出跟随所选基底 | 技术备选；只在选定角色数据许可明确后继续 |
| MB-Lab（animate1978） | 2024-07-21 归档；README 称 1.8.1 为最终版，开发转向 CharMorph | Blender 4.0 系列；含 Anime 模型与 CEL shader；不能据此证明当前 Blender 版本兼容 | Python 代码 GPL-3.0-or-later；数据库 AGPL-3.0-or-later，3D 导出明确默认 AGPL | 适合历史设计参考，不宜成为新的默认资产基础 |

一手依据：[MakeHuman 状态](https://static.makehumancommunity.org/makehuman/faq/current_status.html)、[MPFB 2.0.18](https://static.makehumancommunity.org/mpfb/releases/release_2018.html)、[CharMorph README](https://github.com/Upliner/CharMorph/blob/ec5e13dcd5a7330b35fa7474b3abd2f406d77bd2/README.md)、[CharMorph 许可](https://github.com/Upliner/CharMorph/blob/ec5e13dcd5a7330b35fa7474b3abd2f406d77bd2/license.txt)、[MB-Lab 仓库与归档提示](https://github.com/animate1978/MB-Lab)、[MB-Lab README](https://github.com/animate1978/MB-Lab/blob/063bff04e60f3e7c651fda628c30f5d83f3f3078/README.md)。两条替代路线是有参数化人体基础的候选；不把只有静态基础网格的资源算作等价生成器。

## 许可必须分层

### MakeHuman 与 MPFB

| 层 | 已核实范围 | 限制或未决项 |
|---|---|---|
| 程序代码 | MakeHuman 程序逻辑、脚本、shader、UI 图像等属于 AGPL-3.0-or-later；MPFB Python、shell、程序配置属于 GPL-3.0-or-later | 不能因图形数据 CC0 就把其实现代码也归为 CC0 |
| 基底网格 / proxies | 两项目随附图形资产定义包含 base mesh 与 proxies，采用 CC0 1.0 | 固定上游版本与具体文件；外部 proxy 不能直接继承该结论 |
| morph / targets 数据 | 随附 targets、modifiers 在图形资产定义中，采用 CC0 1.0 | MPFB 同时把程序 configuration files 列入代码，把 mesh JSON 列入资产。若要原样分发 `macro.json` 或其他混合配置，需确认具体文件属于哪一层；不能只凭扩展名推断 |
| 骨架 / weights / 姿势 | MPFB 明列 rigs、poses、expressions 与 mesh-info JSON 为 CC0 图形数据 | 自建/社区骨架及其他插件的数据需各查；完整 Rigify 实现不是可据此宣称 CC0 的资产 |
| 随附皮肤、贴图、衣服 | 图形资产定义包含 textures 与 MHCLO 资产；官方 `makehuman_system_assets` 表逐项列为 CC0 | 本轮仅核实官方表与声明，未打开 ZIP 内的每个文件头 |
| 可选包、社区衣服/头发/皮肤 | 官方包 FAQ 说明多数由第三方作者提供，使用 CC0 或 CC-BY 等逐项声明；包只是资产合集 | 官方提供下载不代表全包/全生态 CC0；作者、具体版本、署名、材质依赖必须留存 |
| 生成的 3D 导出 | 两项目声明其输出是资产与用户输入的组合，不包含程序逻辑；对基于其 CC0 核心资产的模型、脚本生成图形、渲染等不主张限制 | 加入第三方素材后仍受那些素材许可约束；“导出后属于我”不能清除其条件 |

许可证原文：[MakeHuman LICENSE](https://github.com/makehumancommunity/makehuman/blob/a8bc2d54ff0ac92e78ff71431b1023eda42bf482/LICENSE.md)、[MPFB LICENSE](https://github.com/makehumancommunity/mpfb2/blob/3af0cd5a2ffba072e93a34e5f6f494fdc4813ddf/LICENSE.md)、[MPFB CC0 正文](https://github.com/makehumancommunity/mpfb2/blob/3af0cd5a2ffba072e93a34e5f6f494fdc4813ddf/LICENSE.ASSETS.md)。额外范围依据：[系统资产包逐项列表](https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html)、[资产包 FAQ](https://static.makehumancommunity.org/assets/assetpacks/faq.html)。后者还说明“checked”只是打开与粗检，并不保证所有体型都合适。

这次找到的可选风格数据是官方 `cartoon01` 页面：列出 cartoon、anime、chibi 形变，并将列出的每项标为 CC0。该页属旧文档结构；原作者链接本轮有超时，ZIP 未下载。它是值得做小样的具体候选，不足以证明已拥有高质量动漫角色系统。[cartoon01 清单](https://static.makehumancommunity.org/assets/assetpacks/cartoon01.html)

### CharMorph / MB-Lab：不是统一 CC0

- CharMorph 的程序许可为 GPL-3.0-or-later。其许可文件明确区分角色自己的许可，并说明 MB-Lab 派生角色数据库为 AGPL，生成 3D 模型也必须按 AGPL 分发；普通场景的二维渲染另有例外。这一渲染例外不能用于论证可自由分发 3D 角色。[CharMorph 许可原文](https://github.com/Upliner/CharMorph/blob/ec5e13dcd5a7330b35fa7474b3abd2f406d77bd2/license.txt)
- Antonia 的 `config.yaml` 标为 CC-BY 3.0；其独立许可文件明确 CC BY 3.0 Unported，并提醒外部分发的相关内容未必同许可。应对基底、morph、贴图、默认衣服和附加头发分别留存来源，不能把该角色标题扩展为整个 CharMorph 库的许可。[Antonia 配置](https://github.com/Upliner/CharMorph-db/blob/a8512ac299c0cb1724c7b5417267c94bef024d64/characters/antonia/config.yaml)、[Antonia 许可](https://github.com/Upliner/CharMorph-db/blob/a8512ac299c0cb1724c7b5417267c94bef024d64/characters/antonia/license.txt)
- Reom 的配置写 `CC-BY`，列出 mesh 作者 ComplexAce 与 morph/texture 作者 Hope，但没有写版本；本轮未核实额外许可正文。可作为进一步查证对象，不能替它补成 CC BY 4.0 或 CC0。[Reom 配置](https://github.com/Upliner/CharMorph-db/blob/a8512ac299c0cb1724c7b5417267c94bef024d64/characters/reom/config.yaml)
- `mb_male` 明标 AGPL3，配置虽包含 Anime 等类型，也仍是同一许可边界。[MB male 配置](https://github.com/Upliner/CharMorph-db/blob/a8512ac299c0cb1724c7b5417267c94bef024d64/characters/mb_male/config.yaml)
- MB-Lab 的 `license.txt` 将 Python 代码列为 GPL-3.0-or-later，把网格、图像与 JSON 数据列为 AGPL-3.0-or-later，生成的 3D 模型默认 AGPL。其旧 issue 中作者讨论过原版 1.6.1 的双重许可，但不能将旧版本例外套用到当前 fork 的所有数据。[当前许可原文](https://github.com/animate1978/MB-Lab/blob/063bff04e60f3e7c651fda628c30f5d83f3f3078/license.txt)、[作者讨论 #215](https://github.com/animate1978/MB-Lab/issues/215)

## MPFB 数据与变形机制

### 固定拓扑与宏参数

hm08 是 MakeHuman 与 MPFB 共用的基底。人体比例改变时顶点位置改变，基底的顶点数和面数不变；隐藏 helper 几何包含关节立方体及服装拟合辅助面。**推论**：它适合建立稳定的顶点索引与 morph 数据契约；删除 helper、套 proxy、subdivision 或烘焙遮罩后的导出不能再假定保持原始索引。[基底与 helpers](https://static.makehumancommunity.org/mpfb/docs/assets/concept_basemesh_and_helpers.html)

target 是顶点索引和 XYZ 位移组成的 shape key。宏参数不是给单个 morph 换标签：官方 `TargetService` 文档将年龄、体重、肌肉、比例、身高等参数经 `macro.json` 对底层形变组合插值；细节 targets 可单独加载。Rust 若只复制当前 glTF 的少数 shape keys，不能据此宣称复刻整个参数系统。[targets 概念](https://static.makehumancommunity.org/mpfb/docs/assets/concept_targets.html)、[TargetService 文档](https://github.com/makehumancommunity/mpfb2/blob/3af0cd5a2ffba072e93a34e5f6f494fdc4813ddf/docs/services/targetservice.md)

### 骨架、权重与修正

官方骨架数据把骨头 head/tail 写为相对基底的计算策略：`CUBE` 取关节组中心，`VERTEX` 取指定顶点，`MEAN` 取多个顶点均值，`XYZ` 取三个顶点的各轴分量，也可带 offset。权重文件按骨头列出顶点索引与权重。它解决“体型变化后关节放哪里”和“顶点跟哪根骨头”的不同问题。[rig/weights 开发文档](https://static.makehumancommunity.org/mpfb/developer/rigging_and_posing.html)

`HumanService.refit()` 文档说明会重拟合衣服、proxy、主骨架及 sub-rig；生成后的 Rigify 缺少 meta rig 时会停止相应拟合并报告问题。可选 rig 包括默认、GameEngine、CMU、Mixamo、Rigify；外部运行时应优先核对一个简单 deform 骨架，再考虑 Blender 的控制骨、约束与程序驱动。[HumanService refit](https://github.com/makehumancommunity/mpfb2/blob/3af0cd5a2ffba072e93a34e5f6f494fdc4813ddf/docs/services/humanservice.md)、[rig 选择](https://static.makehumancommunity.org/mpfb/docs/characters/rig.html)

未找到足以证明“所有体型和所有姿势已有完整自动修正形变”的一手依据。旧官方 corrective-shape-key 教程展示手工塑形与骨头旋转 driver，并提醒跨角色转移需同拓扑，可能还要角色专属调整。因此不能把 morph 数量、Rigify、或已有 weights 当作肩、肘、膝、髋极端动作质量保证。[旧 corrective 教程](https://static.makehumancommunity.org/oldsite/documentation/corrective_shape_keys.html)

### 衣服、头发、部件与 proxy

MHCLO 不只指衣服；头发、眼、牙、舌也是“附着网格 + 对应规则”。改基底后要显式 refit，或打开自动 refit；密集衣服实时拟合有成本。`add_mhclo_asset()` 提供基底权重插值、可选自定义权重与 sub-rig。此处是形状/骨架适配能力，不是已证明的布料物理或保证无穿插。[MHCLO 概念](https://static.makehumancommunity.org/mpfb/docs/assets/concept_clothes_hair_bodyparts.html)、[refit FAQ](https://static.makehumancommunity.org/mpfb/faq/clothes_do_not_fit.html)、[HumanService 资产 API](https://github.com/makehumancommunity/mpfb2/blob/3af0cd5a2ffba072e93a34e5f6f494fdc4813ddf/docs/services/humanservice.md)

proxy 可替换显示表面，保留基底结构与 rig 关系；系统 proxy 可用系统皮肤，第三方 proxy 可能需自己的皮肤。低面数是可能的制作选择，尚未测得 Nvwa 的帧率、显存、包大小或 Web 加载成本。[proxy 文档](https://static.makehumancommunity.org/mpfb/docs/assets/concept_proxymeshes.html)

## 自动化与导出边界

**有一手 headless 路径，但不是独立 Rust/通用 Python 库。** 官方测试 README 明确支持不打开 Blender GUI 的测试方式，启动脚本用 `BLENDER_EXE -b ... -P ...`。官方脚本目录还覆盖建人、设置 target、添加 rig、装配皮肤与衣服、导出 FBX。由此可合理选择 Blender 后台进程作制作工具；本轮没有运行该流程，也没有证明安装、打包或 glTF 结果。[headless 说明](https://github.com/makehumancommunity/mpfb2/blob/3af0cd5a2ffba072e93a34e5f6f494fdc4813ddf/test/README.md)、[headless 启动脚本](https://github.com/makehumancommunity/mpfb2/blob/3af0cd5a2ffba072e93a34e5f6f494fdc4813ddf/test/execute_tests_headless.bash)、[脚本样例目录](https://github.com/makehumancommunity/mpfb2/blob/3af0cd5a2ffba072e93a34e5f6f494fdc4813ddf/script_samples/index.md)

MPFB 的 Export Copy 可以烘焙建模 shape keys、遮罩与 subdivision、删除 helpers，也能在关闭建模烘焙时保留形变；面部 visemes 与 ARKit-style faceunits 需另外资产包。**风险**：以“可观看/动画的导出”为目标的默认清理，会丢掉继续参数化所需的基底或辅助信息。需分别保存制作源数据与运行时资产，明确顶点重映射及 sidecar 数据。[Export Copy 官方说明](https://static.makehumancommunity.org/mpfb/docs/exporting/export_copy.html)

官方完整导出样例选 `GAMEENGINE` 材质和 `game_engine` rig，并提醒 FBX shader 转换只是 best effort。它证明有可参考脚本，不证明 Blender 的复杂皮肤节点会自动变成 Bevy/Web 相同材质。glTF 保留 morph、skin、纹理与所需元数据的结果要在下一阶段实测。[完整 FBX 样例](https://github.com/makehumancommunity/mpfb2/blob/3af0cd5a2ffba072e93a34e5f6f494fdc4813ddf/script_samples/10_complete_character_export_fbx.py)

CharMorph 的实时拟合、替代拓扑和完整面部 Rigify 值得参考，但其 README 说 rig 到 finalization 才添加；未证明它提供与 MPFB 同等成熟的无 GUI 生成接口。MB-Lab 也未在本轮核实 headless 产品接口。两者依赖 Blender，不能因此推断可直接在 Nvwa Web/WASM 中运行。[CharMorph README](https://github.com/Upliner/CharMorph/blob/ec5e13dcd5a7330b35fa7474b3abd2f406d77bd2/README.md)

## 写实与动漫的结论

MPFB/MakeHuman 提供成熟的参数化人体出发点。它有明确可查的 cartoon/anime 目标资产，不能说它完全不支持动漫；但也不能从一套 targets 推断已解决动漫的大眼眶、眼球/眼睑、脸部表情、发片、轮廓、服装与 shader 的整体设计。[cartoon01](https://static.makehumancommunity.org/assets/assetpacks/cartoon01.html)

CharMorph 的 MB 基底含 Anime 类型，MB-Lab 有 Anime CEL shader，但相关 MB 数据的 AGPL 边界仍存在。若 Nvwa 第一阶段目标是高辨识度动漫审美，建议先用一个已核准的 stylized target 做头部与身体比例评审；未通过再决定独立风格化网格，而不是先承诺换掉整个人体系统。[CharMorph MB 配置](https://github.com/Upliner/CharMorph-db/blob/a8512ac299c0cb1724c7b5417267c94bef024d64/characters/mb_male/config.yaml)、[MB-Lab README](https://github.com/animate1978/MB-Lab/blob/063bff04e60f3e7c651fda628c30f5d83f3f3078/README.md)

## 最小下一步验证（本轮未执行）

统一下一阶段以本目录整合报告 `README.md` 为准：使用共同的 MPFB 样例，以 Blender/MPFB 为共同参考，比较离线编译人物包与读取源数据的两条 Rust 执行路径。以下只定义样例输入、参考输出与验收要求，不构成另一份实施路线图。

1. **锁定来源**：选一个 MPFB 版本、hm08、2–3 个基础参数、一个面部细节 target、一个衣服和一种 GameEngine rig；建立逐文件清单：URL、提交或包版本、哈希、作者、许可、依赖。第一轮只用明确 CC0 的核心数据。`macro.json` 等混合配置未分类前不整包纳入产品。
2. **离线生成小样**：在单独的 Blender 制作环境中，生成中性、矮瘦、高壮三个体型；同一衣服分别 refit。另加一个可选动漫形变作审美门槛。保存源 `.blend`、原始 target/rig 数据清单与导出结果。
3. **证明编辑契约**：比较体型间原始拓扑哈希、target 稀疏位移、关节位置、骨权重和服装对应。再导出 GLB，检查 retained morph 数量、joint/inverse-bind、遮罩删除与顶点重映射。导出可用不等于重新编辑可用。
4. **先验证现有 Rust 候选**：用同一项体型/细节 target 与关节定位要求，先评估整合报告选出的现有 Rust 候选；以 Blender/MPFB 输出为参考，在端点与中间值比较顶点、关节及衣服误差。只有记录并证明候选缺少必要能力后，才实现补足该缺口的最小部分。若不能取得明确许可的数据定义，先停在资产生成管线。
5. **三端同源证据**：同一 GLB 和参数样例在 Nvwa desktop、Web、headless CLI 分别检查；加肩抬高、屈肘、深屈膝动作和衣服穿插评审。记录数值误差、耗时、内存、文件体积；本报告不提供尚未测量的性能数字。

通过这些门槛后，才决定“导出少量预制可编辑角色”还是“运行时加载更完整的参数数据”。骨架拟合、衣服拟合、corrective、动画及 PBR 材质应分别验收。

## 版本快照、矛盾与未知

2026-10-16 读取仓库 API 的默认分支快照如下；`pushed_at` 可能由其他分支变化更新，不能当作默认分支最后提交日期。

| 官方仓库 | 默认分支提交 | 提交日期（UTC） | 归档状态 |
|---|---|---|---|
| [makehumancommunity/mpfb2](https://api.github.com/repos/makehumancommunity/mpfb2/commits/master) | `3af0cd5a2ffba072e93a34e5f6f494fdc4813ddf` | 2026-10-13 | 未归档 |
| [makehumancommunity/makehuman](https://api.github.com/repos/makehumancommunity/makehuman/commits/master) | `a8bc2d54ff0ac92e78ff71431b1023eda42bf482` | 2024-06-26 | 未归档 |
| [Upliner/CharMorph](https://api.github.com/repos/Upliner/CharMorph/commits/master) | `ec5e13dcd5a7330b35fa7474b3abd2f406d77bd2` | 2024-10-10 | 未归档 |
| [Upliner/CharMorph-db](https://api.github.com/repos/Upliner/CharMorph-db/commits/master) | `a8512ac299c0cb1724c7b5417267c94bef024d64` | 2023-12-11 | 未归档 |
| [animate1978/MB-Lab](https://api.github.com/repos/animate1978/MB-Lab/commits/master) | `063bff04e60f3e7c651fda628c30f5d83f3f3078` | 2024-06-08 | 已归档 |

- 搜索仍会出现旧 MakeHuman fork 的“仅官方未修改软件导出才有 CC0 例外”文字。当前官方仓库将随附资产本身置于 CC0，官方 FAQ 还明确允许另建生成器；应固定当前官方来源，不混用旧 fork 的规则。[当前官方 LICENSE](https://github.com/makehumancommunity/makehuman/blob/a8bc2d54ff0ac92e78ff71431b1023eda42bf482/LICENSE.md)
- `makehumancommunity/makehuman-assets` 在本轮 API 查询为 404；不要把搜索得到的同名个人 fork 当作当前权威资产仓库。系统包应从官方清单定位。未下载包，所以包内逐文件声明、哈希与缺失文件尚未验证。
- Antonia 与 Reom 的角色级标识不能保证任意附加内容同许可；Reom 的 CC-BY 版本缺失仍是具体未知项。
- MPFB 服务文档、官方脚本及 headless 测试入口是源码/文档证据；本轮未运行测试、批量生成、GLB 导出、native/Web/CLI 或性能检查。

**PARTIAL — 已核对一手许可、维护状态、机制文档和官方 headless 入口；资产包逐文件审计、形变质量、GLB 保真和 Nvwa 三端运行均 NOT-RUN。**
