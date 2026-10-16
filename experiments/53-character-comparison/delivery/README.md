# 已批准人物样本：实际交付

原下载清单与许可证快照保持不变。人已批准固定清单，并随后改为由集成代理通过 Homebrew 升级、保留系统 Blender。因此本交付**没有下载 Blender 4.2.23 DMG**。Homebrew 与 Blender 的运行结果由集成代理单独记录。

其余获准文件已全部取得，共 **327,316,919 字节**。其中 1,741 字节 Humentity 许可证复用了此前公开审阅文本，新增资产、代码和 crate 文件内容为 **327,315,178 字节**。这不是网络流量计数；HTTP/TLS 开销和中止请求时尚未写盘的字节未测量。[总收据](download-receipt.json)与[冻结文件清单](artifact-inventory.json)记录实际文件、大小和 SHA256。

| 原文件 | 实际字节 | SHA256 |
|---|---:|---|
| MPFB 2.0.18 ZIP | 45,956,992 | `c075b3e9b94b8e5556a5f03f4653602d02ea306de08126e8f55ed6dee28a2dad` |
| 官方系统资产 ZIP | 280,737,770 | `b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107` |
| Humentity 固定提交的 45 个文件 | 561,909 | 各文件 SHA256 与固定提交 Git blob SHA1 均在[源码收据](humentity-source-download.json)，全部通过。 |
| bevy_obj 0.19.0 crate | 44,610 | `894c100f4b3f147d67fab910e176e8c5453593abdfb894a94eb0c93661996dfa` |
| wobj 0.3.0 crate | 15,638 | `28b34b5fbb60f0273c065bfadca18e2decf9e1cac4da09e0ce61b799c05ee631` |

系统资产摘要是本地取得文件后计算的冻结值，不是假称上游公布的摘要。下载前和各 range 响应的长度、ETag、Last-Modified 均匹配已批准快照。慢速完整 GET 已保留 91,226,112 字节，随后在集成代理授权下用同一 URL 的四段互不重叠 range 取得剩余 189,511,658 字节；每段必须先通过 206、Content-Range 和文件身份检查。没有重新发起完整 GET。[系统 ZIP 收据](system-assets-download.json)保留逐请求/逐段字节账本。

## 可用的本地输入

均位于工作树的 `.work/character-approved-20261016/`：

- 原始 ZIP：`downloads/`；原始 crate：`crates/`。
- 已审计并安全解包的 MPFB：`mpfb-addon/`，2,422 个文件，共 76,173,015 字节。
- Humentity 原源码：`upstream/Humentity/`，固定提交 `286d33124648501535655a0de811cef55152b9fd` 的 45 个明确文件，无 Git checkout、LFS 或额外资产。
- crate 解包：`crates/extracted/bevy_obj-0.19.0/`、`crates/extracted/wobj-0.3.0/`，分别 172,609 与 60,245 字节；两包都实际包含完整 MIT 和 Apache-2.0 许可证文本。
- 选定衣服：`system-assets/clothes/female_sportsuit01/`，只有 `female_sportsuit01.mhclo`、`.obj`、`.mhmat`、`_diffuse.png`、`_normal.png`、`_ao.png` 六个依赖文件，共 3,607,692 字节。没有提取其他人物资产或缩略图。

MPFB 和系统 ZIP 全部目录项都通过路径穿越、符号链接和大小写路径冲突检查。选定文件解压时通过 ZIP CRC，随后计算 SHA256；没有声称检查系统 ZIP 内所有未选文件的 CRC。系统 ZIP 完全展开的文件内容总量为 298,739,872 字节，本任务实际只展开其中选定衣服的六个文件。

MPFB 发布 ZIP 与固定 tag 的所有图形数据逐文件一致。只有 `__init__.py` 的三个构建标记由 `FROM_SOURCE` 改为 `20261010`，合计减少九字节；其他 2,421 个文件均一致。[完整差异](mpfb-init-release-diff.patch)与[比较收据](mpfb-archive-source-equivalence.json)已保留。ZIP 本身不带根许可证文本，原清单保留的固定源码许可证用于记录代码 GPL-3.0-or-later 与图形资产 CC0 1.0 的边界。

## 衣服许可与依赖结论

衣服的 MHCLO、OBJ 和 MHMAT 三个文本文件都明确写明：2020 年 9 月以 CC0 发布，原权利人包括 Data Collection AB、Joel Palmius、Jonas Hauquier。三张 PNG 正是该 CC0 材质直接命名的依赖；官方系统包表也将整项 `female_sportsuit01` 标为 CC0。没有声称 PNG 内各自含独立许可证头。[衣服收据](system-garment-extraction-receipt.json)保留声明、文件摘要和依赖边。

MHCLO 仅引用本文件夹的 OBJ 与 MHMAT，没有额外自定义权重或 rig 文件；OBJ 没有 `mtllib` 外部引用。MHMAT 的 diffuse、normal 和 AO 三张贴图均存在。但它还保留 MakeHuman 旧 GLSL shader `data/shaders/glsl/litsphere` 和 `data/litspheres/lit_matte.png` 两个引用；这两项不在系统包中。MPFB 的 `MhMaterial` 源码也把旧 shader/litsphere 处理标为 TODO。因此本交付只确认几何与三个贴图依赖，**不确认旧 MakeHuman 材质外观一致**。集成代理已指定用中性材质执行几何对照；未为旧 shader 增加下载。

`macro.json` 的产品分发许可分类依旧未解决。本交付不把它标为可直接放进产品的 CC0 配置，也不把 Humentity 候选代码或未知传递依赖宣布为已采用。没有额外资产、crate 或自动依赖下载。

## 执行边界

下载代理只执行了下载、哈希、文本与归档审计、安全解包脚本；没有执行 Blender、MPFB 或 Humentity 代码。参考生成、导出、Rust A/B 与桌面/Web/CLI 结果由其他负责代理分别提供，不能从本交付推断成功。

长时间 range 传输尝试使用已就绪的本机 wefty。它在创建 run 前因共享工作树同时变化而报 `checkout changed during capture; retry exec`，未返回 run ID。按明确调度许可改为直接本地执行，成功结果与失败原因都已追加到 `~/.codex/work-products/wefty-daily-use/exec-log.md`。没有用 wefty 绕过权限拒绝，也没有改机器配置或调用管理命令。

**VERIFIED — 获准的非 Blender 文件全部到位；发布者哈希、源码 Git blob SHA1、实际 SHA256、归档安全及六个衣服文件许可/依赖审计通过。旧 GLSL 外观一致性与产品采用未证明；本代理没有执行上游代码。**

## 后续执行与清理

系统 Blender 已实际升级并执行 MPFB 参考，详见[准确安装收据](blender-homebrew-upgrade.json)和[参考说明](../reference/README.md)。此结果属于集成负责人的实际执行，不回写为下载代理曾运行过上游代码。

完整系统 ZIP 重新校验后，集成负责人删除了已合并的四段 range 与旧前缀，共回收 **280,737,770 字节**。删除前逐块证明它们与完整包相应区间相同；原始完整 ZIP、原始插件、候选源码、两份 crate 与共同样本均保留。[清理收据](fragment-cleanup.json)保留分段摘要与对应区间。

独立审查发现 `fetch()` 在复用完整文件时可能错误提升旧 `.part`。修复后仅提升本次独占创建且验证通过的临时文件，复用时保留完整文件和旧 `.part`。两个原始反例先失败，11 项真实函数离线控制在普通 Python 和 `-O` 下通过，独立复审也重现修复效果。已交付的 55 个文件随后全部重算哈希不变。控制使用内存传输替身测试下载接缝，不是候选人体系统的运行替身。
