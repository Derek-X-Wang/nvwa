# #79：三个本地头发素材的有界筛选

2026-10-25。研究基线 `554701a44311c873c0eac45c593b5f89adc0c8d4`。本轮只检查 `ponytail01`、`short01`、`short02`；没有第四个候选，没有候选代码、拟合、构建或新素材获取。

**唯一推荐：`short01`，作为下一次另行授权的上头可见性检查对象。不是准入或画质通过。** 它的上扬前发轮廓比 short02 的宽刘海更适合检查发际，源文件也有明显的预算余量。ponytail01 的露额头线索更强，但按当前素材包构成会超过既有大小上限，因而不作为当前首选。

**未满足的严格条件：尚无一个候选被证明同时露额头、双眼可见。** 三张目录图都只有头发；另找到的 ponytail01 官方上头图是侧面，远侧眼睛不在画面中。short01 可能满足目标只是风格推断。不能把预览筛选写成已达标，也不能因刘海风格而判定一个素材有缺陷。本轮不自动进入实现。

## 对照与决定

| 候选 | 官方像素所见 | 四个简单材质源文件 | 替换后的假设包合计 | 决定 |
| --- | --- | ---: | ---: | --- |
| **short01** | 短发，前部上扬；前侧仍有下垂边缘，无脸可核实眼眉遮挡 | 2,751,498 B | 7,115,895 B；余 1,272,713 B | **唯一待验证首选**；未见静态格式障碍，预算余量较大，双眼可见仍 UNKNOWN |
| ponytail01 | 后梳、长马尾；官方侧面上头图可见额头与近侧眼部，无法看远侧眼睛 | 4,428,551 B | 8,792,948 B；超出 404,340 B | 暂缓；不提高上限，不重编码贴图来挽救这轮筛选 |
| short02 | 宽的前扫刘海，更难直接看发际；实际眼眉遮挡未知 | 3,813,848 B | 8,178,245 B；余 210,363 B | 不优先；诊断可见性较弱、预算余量较小 |

以上包大小是假设四个 hair 文件替换现有 short04、其余 manifest 条目字节不变的静态加法，v1/v2 结果相同。不是构造新包或执行准入。新身份/来源元数据的变化尚未计入。当前上限是单文件 4 MiB、合计 8 MiB；每份候选的单个必要文件均低于 4 MiB。short02 另带未声明使用的 normal PNG；现有简单策略不读取它，也不把忽略它说成复现了旧 shader 的画质。

官方原始预览：[short01](https://static.makehumancommunity.org/assets/assetpacks/short01.png)、[ponytail01](https://static.makehumancommunity.org/assets/assetpacks/ponytail01.png)、[short02](https://static.makehumancommunity.org/assets/assetpacks/short02.png)。均为 256×256、单角度、无脸的发型图。[Rigging Mesh Assets 教程](https://static.makehumancommunity.org/mpfb/docs/rigging_mesh_assets.html)明确点名加载 ponytail01；其[上头截图](https://static.makehumancommunity.org/mpfb/docs/add_ponytail.png)支持露额头的侧面观察，不证明该精确资产版本、双眼可见、Nvwa 接触或运动质量。没有找更有利角度来给候选判通过。

## 来源与许可

本地保留的 system-assets ZIP 为 280,737,770 B，SHA256 `b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107`。本轮重新计算匹配，只在内存读取这三个候选及包元数据；没有把新模型或贴图解包到磁盘。哈希匹配证明本地归档一致性；本轮未与上游签名或发布哈希核对，亦未独立验证历史分发链。

[官方 system-assets 目录](https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html)逐项把三个候选标为 `makehuman_system`、`hair`、`CC0`。本地包条目和各自 OBJ/MHCLO/MHMAT 的 September 2020 发布头一致声明 CC0。PNG 由条目的 diffuseTexture 指向，不声称 PNG 自带独立嵌入的许可声明。ZIP 没有单独 CC0 文本成员；现有仓库已保留[完整 CC0 文本](../../assets/appearances/mpfb-b1-cc0-v2/licenses/CC0-1.0.txt)。将来提取/重分发应保留这些来源、原始头和逐文件哈希。

[官方许可页](https://static.makehumancommunity.org/about/license.html)区分核心素材 CC0 和工具代码许可证；[官方复用 FAQ](https://static.makehumancommunity.org/mpfb/faq/build_other_chargen.html)明确讨论在其他角色生成器使用 system assets。该来源依据不扩大为对整个社区素材库、未知第三方依赖或新代码的许可结论。

## 静态兼容性

| 候选 | hm08 UUID | 源点 / 渲染角点 / 三角面 | 映射中的负系数 |
| --- | --- | ---: | ---: |
| short01 | 766436e9-63ed-4f6a-afa9-99f3acff70a8 | 2,984 / 3,177 / 3,678 | 549，分布在 501 行 |
| ponytail01 | 44e0340e-c7a6-4d22-814c-0632968d2dde | 3,718 / 4,049 / 5,352 | 386，分布在 343 行 |
| short02 | c104cd4a-1edc-43f9-8b94-f63345a44638 | 1,755 / 2,061 / 3,344 | 153，分布在 144 行 |

- 三者 OBJ 都是已支持的 v/vt/f 四边形和正绝对索引；映射行数匹配、helper 在现有 19,158 点域内，没有观察到静态语法障碍。**未执行 Rust parser**；源数据检查不是实际导入通过。
- 参考 helper 有现有 53 骨架的正源权重支持。必须保留 signed 映射、最终正聚合归一化和全部影响；没有计算任何候选的最终权重、拟合、法线或蒙皮，不声称绑定正确。旧四槽 GLB 路线不能替代 B1 的完整影响合同。
- 三份 diffuse 都是 2048² RGBA8；ZIP CRC、PNG chunk CRC 和解压扫描线长度核对通过。尚未验证 Bevy 解码、alpha 覆盖、GPU 表现或材质审美。
- 三者的原材质都使用 litsphere，并带有当前路径不复现的 SSS/alpha-to-coverage 设置。仅可按现有 `simple-srgb-mask-v1`（sRGB、Mask(0.5)、roughness 0.7、双面无剔除）做未来比较。**官方图不能保证该策略下的效果。** 不新增 shader、发丝物理或下载旧 litsphere 来补画质。
- 正式产品仍固定认证 short04；实验89仍固定 short03/short04。这三个文件都不能直接冒充现有身份或绕过其哈希检查。未来候选需要独立身份及限定准入，本轮没有实施。

源码依据：[大小上限与身份合同](../../crates/nvwa-core/src/appearance.rs)、[固定来源与解码](../../crates/nvwa-runtime/src/appearance/assets.rs)、[映射/拟合/完整影响](../../crates/nvwa-runtime/src/appearance/geometry.rs)、[材质发布](../../crates/nvwa-runtime/src/appearance/mod.rs)。检查结果明确属于静态来源与格式推断。

## 唯一推荐的文件清单

全部已存在于保留的 ZIP 内，无需重新下载；本轮没有提取这些文件。四个模型/材质文件共 2,751,498 B，另有已保留的完整包元数据 39,220 B。

| short01 的 ZIP 成员 | 字节 | SHA256 |
| --- | ---: | --- |
| hair/short01/short01.mhclo | 201588 | ae1ffaa98da5753b803b3a173bede4895d2215e6bb94763f3765a71f0e984f35 |
| hair/short01/short01.obj | 194450 | d998d8416f9b5d5591f1d756f4d292288d000a6951bc0f4d2e8e72727bbc44fa |
| hair/short01/short01.mhmat | 1314 | 01e2e12ce3f3d3c859225456660acadcdd27d4f4b4d888bcbd6f11998cadd975 |
| hair/short01/short01_diffuse.png | 2354146 | f34a0957184e3d1e911ed59245f874f8d4843f61ee44ff49f43edb4be0196949 |
| packs/makehuman_system_assets.json | 39220 | e86f1572432cfd062f372adddba4eb7c2e2e31280e96c29291a970320e0a5df0 |

下一步若另行授权，只应先回答 short01 上头后是否露额头、双眼可见、发际是否比 A 更自然。该问题未通过就停止，不扩成新材质、参数搜索或完整动作矩阵。新增获取始终先确认。正式 A/short04、M2/#80 HOLD、旧失败记录保持不变。

## 证据与完成边界

本地研究回执根为 `~/.codex/work-products/nvwa/2026-10-25-hair79-screen90/`：`compat/static-evidence.json` 保存逐文件身份、静态语法/PNG 检查、预算及源码锚点；`preview/evidence-manifest.json` 保存四张未修改浏览器 JPEG 原图的 URL、大小和哈希；`review/notes.md` 保存独立审查。它们不作为已公开像素或 clean-checkout 可复跑的承诺。

**PARTIAL —** 三个候选的本地来源、许可声明、静态格式/预算与官方预览已核对；唯一待验证首选 short01。严格露额头且双眼可见条件尚未证实，实际拟合/导入/权重/渲染未运行，#79 未准入。没有候选代码、门禁改动、拟合、测试、构建、CI、模型运行、素材下载或新资产解包。浏览器临时标签已关闭；研究回执保留。
