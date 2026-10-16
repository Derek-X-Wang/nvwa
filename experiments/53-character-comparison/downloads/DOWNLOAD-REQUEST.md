# 共同人物样本：待批准下载清单

核查：2026-10-16。状态：**尚未批准，尚未下载任何二进制、插件、人体资产、库源码或 crate 包。** 本目录只有公开的 JSON/HEAD 元数据、许可证文本和本请求。机器可读明细见 [manifest.json](manifest.json)，原始尺寸与来源证据见 [source-metadata.json](source-metadata.json)。

建议采用下面的完整小样来源。共同参考环境与资产共 **634,934,102 字节（605.520 MiB）**。另列 B 路径固定源码和两个已知缺失 crate 后，完整文件预算为 **635,556,259 字节（606.114 MiB）**；其中源码许可证的 1,741 字节已作为公开审阅文本取得，复用它时实际新增文件内容为 **635,554,518 字节**。数字是文件内容字节，不含 HTTP/TLS 开销。解压后的磁盘占用仍未知，不能把这些数字当成解压大小。

此清单让两条 Rust 路径使用同一人体数据、同一衣服和同一 Blender/MPFB 参考。批准这些文件不等于批准任意后续依赖下载，也不等于产品采用或运行验证通过。

| 顺序 | 固定文件或来源 | 文件内容字节 | 用途与许可 |
|---|---|---:|---|
| 1 | [Blender 4.2.23 macOS arm64 DMG](https://download.blender.org/release/Blender4.2/blender-4.2.23-macos-arm64.dmg) | 308,239,340 | 离线参考工具；Blender GPL 与随包组件许可证。任务目录单独解包，不覆盖现有 Blender。 |
| 2 | [MPFB 2.0.18 扩展 ZIP](https://extensions.blender.org/download/sha256:c075b3e9b94b8e5556a5f03f4653602d02ea306de08126e8f55ed6dee28a2dad/add-on-mpfb-v2.0.18.zip) | 45,956,992 | 生成器代码 GPL-3.0-or-later；随附图形数据 CC0 1.0。已包含人体网格、targets、rig 和 weights，不重复下载 MakeHuman。 |
| 3 | [官方系统资产包 ZIP](https://files2.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip) | 280,737,770 | 只选 `female_sportsuit01` 一件衣服进入共同样本；[官方清单](https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html)将它及其他表项标为 CC0，作者 `makehuman_system`。包内逐文件审计仍待执行。 |
| B1 | [Humentity 固定提交](https://github.com/emberlightstudios/Humentity/tree/286d33124648501535655a0de811cef55152b9fd) 的 `Cargo.toml`、`LICENSE`、`README.md`、`src/**`，共 45 个独立 raw 文件 | 561,909 | B 路径候选代码；MIT 或 Apache-2.0。此范围不包含仓库资产、示例、旧锁文件与开发依赖。完整 URL、逐文件大小与 Git blob SHA1 已列入 manifest。 |
| B2 | [bevy_obj 0.19.0 crate](https://static.crates.io/crates/bevy_obj/bevy_obj-0.19.0.crate) | 44,610 | B 路径已知缺失依赖；注册表标为 MIT 或 Apache-2.0。 |
| B3 | [wobj 0.3.0 crate](https://static.crates.io/crates/wobj/wobj-0.3.0.crate) | 15,638 | `bevy_obj` 的已知缺失依赖；注册表标为 MIT 或 Apache-2.0。 |

尺寸依据：Blender [官方发布目录](https://download.blender.org/release/Blender4.2/)与 HEAD `Content-Length` 一致；MPFB [官方扩展 API](https://extensions.blender.org/api/v1/extensions/)的 `archive_size` 与 HEAD 一致；系统包 HEAD 返回确切长度；Humentity [固定提交 Git tree](https://api.github.com/repos/emberlightstudios/Humentity/git/trees/286d33124648501535655a0de811cef55152b9fd?recursive=1) 未截断，以所选 45 个 blob 大小求和；crate 大小来自 [bevy_obj 版本元数据](https://crates.io/api/v1/crates/bevy_obj/0.19.0)与 [wobj 版本元数据](https://crates.io/api/v1/crates/wobj/0.3.0)。

## 为什么需要新 Blender 和整个系统包

MPFB 2.0.18 的[固定版本 manifest](https://github.com/makehumancommunity/mpfb2/blob/d0a32e57a7f915cb2f2b95410e2117648c7bbb7e/src/mpfb/blender_manifest.toml)要求 Blender 至少 4.2.0。集成代理已确认本机 `/opt/homebrew/bin/blender` 实际为 3.3.1，因此它不能作为本次 MPFB 参考工具。4.2.23 位于符合要求的 4.2 系列；这属于文档兼容条件，实际启动与插件执行尚未验证。任务只使用单独解包的应用与隔离配置，不改机器上的 Blender 或全局插件设置。

系统包是本次清单中有意识的额外传输。公开官方表给出了具体衣服及 CC0 声明，但其 `asset repo` 链接只指向通用首页；未找到可以核对完整文件、依赖与固定来源的单衣服下载入口。不能凭猜测列一组 OBJ/MHCLO/贴图 URL。故选一个确切大小的官方包，而不是增加多个可选包。下载后只提取 `female_sportsuit01` 及它实际引用的网格、材质、贴图、可选权重或 rig；若缺文件或许可不符，停止使用。包内准确文件名与解压大小目前未知。

数值比较可先用中性表面材质检查身体、关节和衣服。皮肤、眼球、牙齿、头发与动漫包不是这个几何小样的新增必需下载；最终外观与面部完整性仍须独立验收，不能从本小样宣称完成。

## 样本数据和许可边界

MPFB 固定版本为 `v2.0.18`，源提交为 `d0a32e57a7f915cb2f2b95410e2117648c7bbb7e`。扩展平台发布 ZIP 用 SHA256 锁定；尚未检查 ZIP 内容与该提交逐文件相等。manifest 中的内部文件名目前是**固定源码树证据**，下载后必须验证，不能冒充已打开 ZIP 的结果。

建议的最小参数输入来自同一扩展已有的数据：

| 数据 | 固定源码路径（`src/mpfb/data/` 下） | blob 字节 |
|---|---|---:|
| hm08 原始网格 | `3dobjs/base.obj` | 1,749,303 |
| 关节定位顶点组 | `mesh_metadata/basemesh_vertex_groups.json` | 81,984 |
| 网格配置 | `mesh_metadata/hm08_config.json` | 3,600 |
| 简单 GameEngine 骨架 | `rigs/standard/rig.game_engine.json` | 40,936 |
| 相应蒙皮权重 | `rigs/standard/weights.game_engine.json` | 3,026,778 |
| 对应 T pose 数据 | `poses/game_engine_fk/t-pose.json` | 1,258 |
| 身体比例候选 target 对 | `targets/torso/torso-scale-vert-decr.target.gz`、`...-incr.target.gz` | 39,045 + 36,386 |
| 局部脸部候选 target 对 | `targets/chin/chin-jaw-drop-decr.target.gz`、`...-incr.target.gz` | 374 + 288 |

这些是扩展已含的数据，**额外传输为零**。上游[许可定义](https://github.com/makehumancommunity/mpfb2/blob/d0a32e57a7f915cb2f2b95410e2117648c7bbb7e/LICENSE.md)把 base mesh、targets、rigs、poses、mesh-info JSON 明列为 CC0 资产。文件名并不能证明参数的数值范围、默认值、坐标含义或生成质量；参数契约须在获准取得原文件后确定。这个 target 对方案也不等于复刻整套宏参数系统。

`targets/macrodetails/macro.json` 为 4,356 字节，位于同一个扩展。上游同时把 configuration files 纳入 GPL 代码，把 targets/modifiers 和 mesh-info JSON 纳入 CC0 图形资产。这个具体文件的分类仍未解决。本次可把它保留在原 GPL 工具环境中核查，**不能因此把它复制进产品并标为 CC0**。初始成对 target 比较不以原样分发它为前提。

公开许可证文本已保存在 [licenses/](licenses/)，其原始 URL、大小和 SHA256 见 manifest。它们是研究材料，不是资产下载许可。Humentity `LICENSE` 含完整 MIT 文本，Apache 部分为声明与链接；若选择 Apache 路径，仍须保存其完整法律文本。各 crate 的实际随包许可证尚待下载后检查。

## 校验与仍未完成的事项

已公布的文件 SHA256：

| 文件 | SHA256 |
|---|---|
| Blender DMG | `8b6bc5fafd4773e94bb863ca19ba1c9a54d096eecbbc4375eae7dbc3b49fab40` |
| MPFB ZIP | `c075b3e9b94b8e5556a5f03f4653602d02ea306de08126e8f55ed6dee28a2dad` |
| bevy_obj crate | `894c100f4b3f147d67fab910e176e8c5453593abdfb894a94eb0c93661996dfa` |
| wobj crate | `28b34b5fbb60f0273c065bfadca18e2decf9e1cac4da09e0ce61b799c05ee631` |

Blender 摘要来自[官方 SHA256 文件](https://download.blender.org/release/Blender4.2/blender-4.2.23.sha256)；MPFB 与 crate 摘要来自前述官方 API。它们是发布者给出的值，还没有下载本体并本地验证。

系统资产包没有找到公开 SHA256。其 HEAD 快照为 `Last-Modified: Sun, 14 Apr 2024 13:28:46 GMT`、`ETag: "10bbb7ea-6160e7c0d7996"`。这个标签不是密码学摘要。下载前重查三个字段（长度、时间、ETag），任一变化则先更新清单；下载后计算 SHA256、保留原 ZIP，再冻结共同样本逐文件摘要。Humentity raw 文件以固定提交和 Git blob SHA1 校验，下载后补 SHA256；不得编造尚未知的摘要。

B 还有明确构建障碍：原 `Cargo.toml` 的可选 `bevy_jolt` 继承了缺失的 workspace 定义，原锁文件与当前 Bevy 版本不一致。已知直接缺失 crate 不等于依赖闭包完整。需在独立目录做最小 manifest 和离线解析，之后才知道是否还缺其他确切版本。**其余传递依赖大小未知，本请求不批准自动 Cargo 网络下载**，也不包括可选物理、开发资源或示例资产。

获得批准后才按顺序执行：校验并保存原文件；审计归档路径、许可与依赖；在任务目录隔离解包工具；冻结共同样本清单与参数；最后运行参考生成与 A/B 比较。运行时、导出质量、衣服穿插、动画、Nvwa 桌面/Web/CLI 接入均未执行。

供集成代理使用的一次确认范围：**是否批准上述共同工具与资产，以及另列的固定 B 源码、`bevy_obj 0.19.0`、`wobj 0.3.0` 文件预算 635,556,259 字节？未知的后续依赖不包含在内。**

**PARTIAL — 已核对固定版本、公开许可、逐文件源码大小、发布者摘要和 HEAD 长度；资产本体、包内许可与依赖审计、解压体积、参考生成及 A/B 执行均 NOT-RUN。**
