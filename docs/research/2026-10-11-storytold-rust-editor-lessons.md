# Storytold Rust 编辑器：Nvwa 可借鉴的边界与小实验

调查日期：2026-10-11；API/source 快照开始于 **16:52 UTC / 09:52 PDT**。本报告只读源码、清单、发行元数据及可见 CI 状态。没有编译、安装、下载发行包、运行 UI/GPU、获取模型或大型测试语料。源码链接固定到下表 SHA；组织库存和 Actions 状态是调查时点记录，随后可能变化。

## 结论

**值得借鉴的是“一个命令入口 + 可发现能力 + 可观察 UI + 有限布局组件 + 发行证据门槛”。不应据此替换 Nvwa 的 Bevy/egui，或扩大 M2。** PhotoCraft 的命令注册表、快照编辑、自动化权限边界及真实文件 oracle 都能在源码中找到。它仍自称 early alpha；菜单接线不是行为完成，测试数量也不是日常生产成熟度。[P-registry][P-edit][P-policy][P-oracle][P-status]

Nvwa 已有无 Bevy/egui 的 core、原子命令、单次拖动事务、离线 CLI、双端 Studio/Player 和 Web 文本输入适配器。最直接的差距是**命令说明和可用状态的发现接口**，其次是可观察输入/视口证据与布局恢复。大图像的瓦片 COW 不是当前固定 rig、小 JSON Work 的首要问题。[N-contract][N-cli][N-input][N-roadmap]

以下优先级是研究建议。实现、依赖引入、联网控制、CI/发行改动均未获本报告自动授权。

## 样本与证据身份

| 仓库 | 本次固定源码 SHA | 选它的原因 |
|---|---|---|
| PhotoCraft | `9441484d168a9c40baf97bdd8086f139fdf8b896` | 主样本：图像编辑、命令、布局、native/Web、自动化与格式测试 |
| FilmCraft | `0800a8b0aa4a703ba42172f415b45a61f8d8a5e1` | 最接近时间轴编辑；只抽查项目数据、命令和手势实现 |
| WordCraft | `dba6e66d53733c2c0fd28355249d24eb3698187e` | Office 的文档/布局/命令分层及成熟度边界 |
| GridCraft | `336deb87ded7552f5a2890894ad7d19e9876be91` | Office 的 COW 工作簿、可见区域渲染与重算边界 |
| craft-libs | `af2b0918d2c5e1ec984a1e1e142542a744596d58` | 独立 egui 控件，不携带应用 engine |
| craft-common-actions | `8f081ff5db115de44313c9db09415c359bf2ca01` | 共用发行工作流；只研究，不执行 |
| Nvwa 本地 checkout | `11fc789e898119e0ed2b423f8a909dacb547f772` | 对照当前合同、源码和已有验收文件；没有重跑旧验收 |

各 GitHub SHA 来自对应仓库 default branch commit API；本地 SHA 来自 `git rev-parse HEAD`。`sheetcraft` API 路由重定向为 **GridCraft**，本报告使用正式名称。[组织仓库 API](https://api.github.com/orgs/storytold/repos?per_page=100)

## 组织范围：不能概括成“所有项目纯 Rust”

组织 API 本次返回 **57 个公开仓库，9 个 fork，28 个 Rust 主语言仓库**。这 28 个 Rust 主语言条目都不是 fork；GitHub 的主语言分类不证明每个源文件、打包脚本或 Web 外壳都是 Rust。原创仓库中还包括 Python 的 `realtime-voice-conversion`、C++ 的 `HyperJail`、TypeScript 的 `placeholder-artcraft`、JavaScript 的 `hanashi-graphics-demo`；fork 包括 `spark`、`RuntimeAudioImporter`、`LiveScan3D`。此处只做库存分类，没有浅扫全部实现。[组织仓库 API](https://api.github.com/orgs/storytold/repos?per_page=100)

实际 Adobe 风格例子有 **PhotoCraft/Photoshop、FilmCraft/Premiere、VectorCraft/Illustrator、LightCraft/Lightroom、PDFCraft/Acrobat**；Office 风格例子有 **WordCraft/Word、GridCraft/Excel、DeckCraft/PowerPoint**。这些对应关系由仓库自己的描述提供，不是已获得原产品兼容认证。[组织仓库 API](https://api.github.com/orgs/storytold/repos?per_page=100)

相邻老项目仅作背景：`bevy-mocap` 的 Cargo 清单仍为 Bevy 0.12，README 描述 ARKit CSV、morph 顺序及骨路径/轴/offset/scale 映射；该快照根目录未见 LICENSE，GitHub license 元数据为空，复制许可未建立。`storyteller-bevy` 的 README 有 Node/npm、Nx 与 Rust/Wasm 前端流程，再次说明主语言不能等同于全栈仅 Rust。[B-mocap][B-mocap-cargo][B-bevy]

## PhotoCraft：源码支持哪些工程模式

### 1. 分层是真实结构，但“24 crates”已不是精确库存

固定树中有 **25 个 `crates/*/Cargo.toml`、3 个 app 清单和 xtask**；README 仍写 24。核心路径是 `doc → ops/paint/algo/text/vector → compose/gpu/format → io → engine → ui-egui/automation → apps`。`engine/Cargo.toml` 没有 egui/eframe 依赖；`xtask layers` 明确列出层次并禁止 L6 以下依赖 UI/windowing 库，且有 standalone 与同层例外规则。这比单靠文件夹命名更能防止边界漂移。[P-tree][P-cargo][P-engine-deps][P-layers][P-readme-underhood]

UI 使用 egui/eframe 0.36；GPU crate 使用 wgpu 30，并说明与 eframe 共享设备版本。Web app 运行同一个 `PhotocraftApp`，文件打开异步送 inbox，保存触发下载，浏览器没有 native TCP listener。其源码说明 WebGPU/WebGL2 两条后端；本次没有验证浏览器实际行为。对 Nvwa 的启发是平台外壳留窄，不能推导为换掉现有 Bevy 3D runtime。[P-ui-deps][P-gpu-deps][P-web]

### 2. 命令入口最值得学；描述目前仍是 JSON-ish 文本

`CommandSpec` 包含稳定 id、标签、菜单路径、快捷键、参数说明、enabled 函数、run 函数和 journal 标志。`command_specs/find` 提供目录和查找；`Session::execute` 进入共同 dispatch；disabled reason 同时考虑前置条件及后台 job。UI、CLI、control、MCP 共用命令的设计在 engine 入口注释及 control 文档中有明确对应。README 的“500+”仅作为上游宣称，本次没有运行注册表计数。[P-registry][P-entry][P-edit][P-command-protocol]

参数 `params` 是人/agent 可读的字符串，**不是机器验证的 JSON Schema**。注册表重复 id 取首次匹配，不能直接把它当 Nvwa 必须复制的质量约束。Nvwa 可以保留 typed `Command`，增加元数据/正式参数 schema/禁用理由，避免第二套修改逻辑。[P-registry][P-lookup][N-contract]

```text
菜单 / 快捷键 / 命令搜索 / CLI / 可选控制通道
                    ↓
             命令说明 + 同一入口
                    ↓
           校验 → 编辑 → 历史 → 观察状态
```

### 3. 控制通道有可用 seam，也有必须保留的不确定性

源码监听 **127.0.0.1**，先认证每条连接，再经 channel 排入 UI；调用 `request_repaint`，等待 UI 回复。文档说明 token 可由文件或进程生成，文件新建在 Unix 为 0600。读写根是启动时授予的独立 capability；`cap-std` 目录句柄限制文件访问，未授权失败关闭，ambient filesystem 命令和间接授予路径的偏好更新被拒绝。[P-server][P-auth][P-policy][P-policy-deny]

这不是“所有菜单无条件远程可执行”。例如自动化拒绝普通 `file.open/save`，要求 root-scoped 文档接口；桌面还拒绝可能加载 ambient 色彩 profile 的 mode 命令。MCP 桥接到 native control；Web 不监听 TCP。[P-policy-deny][P-command-protocol][P-web]

边界如下：[P-transport][P-timeout]

- TCP 请求上限 1 MiB、回复 8 MiB、最多 16 个连接、socket 读写 30 秒；batch 最多 256 步。
- UI 回复 deadline 为 60 秒；到期仍在队列的请求拒绝，**已经开始的操作继续运行**。隐藏/休眠窗口可能无法 drain UI 请求。
- 回复过大可能发生在编辑完成后；错误不证明操作没有执行。batch 前面完成的步骤不回滚。
- MCP stdio 输入由 SDK 读取，没有同样的请求字节上限；文档明确尚无统一 JSON 深度、全会话内存、scratch、执行时长/取消预算。有限输出不等于有限成本。

**推论：** Nvwa 的 `command_id + expected_revision` 是优势，未来 live control 应保留它；超时先 inspect 再决定重试，不复制“error 就盲重试”。第一个小实验宜在进程内或受限本地适配器中证明 UI/CLI parity；MCP 作为最后一层壳，不先造通用网络脚本系统。[N-contract]

### 4. COW 与 Undo：学事务语义，暂不搬图像瓦片

`Session::edit` 先保存 `Arc<Document>`，克隆候选，closure 成功后发布新 doc、记录历史、增 revision。相同 coalesce key 的连续修改可合并成一步。raster 的 `Surface` 用 `BTreeMap<TileCoord, Arc<Tile>>`，写时 `Arc::make_mut` 或 fallible clone；快照复制指针，而非整张像素数据。[P-edit][P-raster]

History 默认 50 步、`max_bytes=0`；开启像素预算后统计 current 和历史不共享 tile 的像素 bytes。但 trim **始终保留最近至少一步**，故不能宣称严格总进程内存上限。layers、索引、GPU/caches、临时分配亦不等于该数字。[P-history][P-history-budget]

Nvwa 已限制 combined undo/redo 为 128 个快照/16 MiB 紧凑 JSON，以及 retry 为 1024 条/8 MiB；已有长会话验收。其计数也不等于 allocator/RSS。先测真实 Work 编辑的 RSS、临时 clone 与动画 asset/cache；将来数据量证明需要时再考虑 `Arc`/结构共享。256² raster tile 不能直接解决 3D rig、动画或小 JSON 的成本。[N-retention][N-history]

### 5. 持久化与 oracle：把“格式不坏”和“行为正确”分开

`.pcraft` 使用版本化 manifest、按 blake3 寻址的 zstd tiles/blobs、可选 thumbnail/composite，支持 ZIP 和目录；writer 增量写新增内容，并验证/修复目录对象。这服务大量图像数据，Nvwa 当前便携 JSON+asset hash 不需立即引入 blob store。[P-format][N-contract]

最可迁移的是验收的分层：PSD parser corpus 逐文件做 parse/write **字节相等**；经过文档 model 的 IO corpus 则比较导入渲染与原文件 merged image oracle，再比较 export/reimport 的像素误差，并保留已知坏样本、缺 oracle skip、pass floors 和严格模式。README 的 307/309、169/170 是作者报告，没有在本次独立运行；源码中的 floor/容差测试也不是所有文件全兼容。[P-psd-corpus][P-oracle][P-readme-psd]

对应 Nvwa：分别保留 schema/资产/完整 JSON exchange、命令后结果、AnimationPlayer/pose、实际屏幕输入、打包/HTTP 五层证据。不要用命令目录完整率代替姿势正确、Web IME 候选框或最终帧呈现。[N-m1][N-tests]

### 6. 编辑器布局、输入和 HiDPI

PhotoCraft 有序列化 dock 的顺序、高度、collapsed/visible tabs、workspace 保存与恢复；另有 `craft_ui::docking` 事务布局、校验、floating groups。应用仍持有 panel ids 与显示语义，库不持有 engine。[P-dock][P-docking][L-ui-source]

快捷键 dispatch 区分 Text、Widget、DeletingWidget 与无焦点，避免 Space/箭头/Delete 和文本撤销被全局命令抢走。type tool 显式处理 IME preedit/commit 并把 caret rect 写入 OS IMEOutput。UI inspect 回报 logical window 尺寸及 pixelsPerPoint。以上是源码证据，不能当本机 IME/混合 DPI 实测通过。[P-focus][P-ime][P-ime-caret][P-ui-inspect]

Nvwa 当前是固定 top/left/right/bottom 面板；Web textarea 代理已经实现，真人基础输入结果记录在路线图。适合先试 split/tab、锁定/重置 workspace、尺寸和输入坐标诊断，再决定是否值得完整 docking。不要让布局改变保存 Work 或 undo history。[N-layout][N-input][N-roadmap]

## 三个对照应用与共用支持：只提炼不同点

| 样本 | 确认的模式 | Nvwa 可迁移部分与限制 |
|---|---|---|
| FilmCraft | Timeline 源码有 drag 状态和单独 preview geometry；注释与实现组织把一次手势收束到一个 engine command；Project 的 TrackItem 用 Tick 表示 start/duration/source_in，支持 speed。 | 借鉴 preview/commit/cancel、可见区裁剪和 seek/边界验收；Nvwa 是固定 authored-action timeline，不因此引入视频轨/codec/音频或 Premiere 的时间基。 [F-timeline][F-preview][F-project] |
| WordCraft | `CommandSpec` 有 id/location/shortcut/params/mutates/enabled；独立 layout/display-list/render 与 IO/engine/UI 的分层在架构记录中明确。 | 命令发现及内容/布局分离有价值；文字排版/分页不是 Nvwa 3D 渲染替代品。其 alpha 宣称和约800测试仍需按作者报告理解。 [W-command][W-architecture][W-status] |
| GridCraft | `Session::execute` lookup/precondition/snapshot/run/journal/history；panic guard 恢复 workbook 与 selection。架构记录 COW 64-row bands、dependency-graph recalc、visible grid。 | 更贴近“只复制改变的数据”和只显示可见内容。不要泛化为所有 command Err 都自动原子恢复；此段明确恢复的是 panic。模型缺失的 XLSX parts 不保留、calc 单线程等局限有记录。 [G-execute][G-architecture] |
| craft-libs | `craft-ui` 提供 tabs、split/resize、图标按钮、docking/theme；接受样式，返回 egui Response，命令和 engine 留给 app。Rust1.95、egui0.36。 | 可以窄试一个 tab/split 控件，保留 Bevy 单 loop。版本范围相容只表明候选可能性，未编译证明。PhotoCraft 使用 **5c874d51…** pin，不能用本次库 HEAD 假称已在 PhotoCraft 集成。 [L-cargo][L-ui-source][L-ui-readme][P-cargo] |
| craft-common-actions | 共用 macOS/windows/linux/web 发行与 packaging lint；PhotoCraft caller 当前引用 `@main`，源码明说为组织内传播改进。 | 借鉴打包/签名验证和 checksum gate；Nvwa 应按自身预算选择平台，并优先 pin 可复现输入。不要直接继承 moving `@main` 或未知授权 YAML。 [A-readme][A-release][P-release] |

## 成熟度：源码、发行资产与 CI 的证据分别算

PhotoCraft 自称 early alpha；FilmCraft/WordCraft/GridCraft 也自称 alpha。FilmCraft 的约86%覆盖/56%实际替代、WordCraft 的88% ribbon/60%整体替代、GridCraft 的89% ribbon/50%实际准备度都是**作者的不同指标/估计**，不是独立用户研究或本次 benchmark。FilmCraft 还说明 `.prproj` 不可打开、无 plugin，真实相机/手机素材覆盖及 Windows/Linux 测试较弱；Office 两者仍有实际文件 fidelity、分页/大型 workbook 等缺口。[P-status][F-status][W-status][G-status]

本次 GitHub release API 确认以下 **资产记录实际存在**，并非 README-only；没有下载、校验 checksum、检查签名/公证、解包或安装运行：[PhotoCraft v0.7.0](https://github.com/storytold/photocraft/releases/tag/v0.7.0)、[FilmCraft v0.6.0](https://github.com/storytold/filmcraft/releases/tag/v0.6.0)、[WordCraft v0.5.0](https://github.com/storytold/wordcraft/releases/tag/v0.5.0)、[GridCraft v0.5.0](https://github.com/storytold/gridcraft/releases/tag/v0.5.0)。

| release（UTC 发布时间） | 资产数 | macOS DMG / Web ZIP bytes（压缩包大小，不是 app 内存或 raw Wasm） |
|---|---:|---:|
| PhotoCraft 0.7.0（10-11 02:12:31） | 24 | 84,113,310 / 11,044,166 |
| FilmCraft 0.6.0（10-11 00:28:54） | 24 | 71,290,924 / 15,611,674 |
| WordCraft 0.5.0（10-11 00:36:07） | 24 | 96,574,549 / 15,279,373 |
| GridCraft 0.5.0（10-10 23:50:05） | 24 | 21,811,006 / 6,255,103 |

PhotoCraft 0.7.0 release 指向 `79261615956ab21334e49ca1d384390272e647da`，**不同于本次源码 SHA**。有发布包不证明今天 main 的改变经过同样发行验证。[发行 API](https://api.github.com/repos/storytold/photocraft/releases/tags/v0.7.0)

PhotoCraft CI 源码有 Linux/Windows workspace test、optional font/HEIF、fmt/clippy、layers、corpus fetch+hash 验证、wasm check 和 Web release size gate；macOS 只在发行流程中覆盖。可见本次 SHA 的 [main push CI 38157186354](https://github.com/storytold/photocraft/actions/runs/38157186354) 为 **completed/cancelled**，jobs API 返回空列表，没有完整当前 SHA pass 证据。FilmCraft 本次 SHA 的 [Windows ARM64 run 38153123248](https://github.com/storytold/filmcraft/actions/runs/38153123248) 为 **failure**，cross-package job 失败、ARM install/run skipped；同 SHA packaging lint success 仅证明 lint。WordCraft 本次 SHA 的相关 OS jobs 尚 queued/cancelled；没有依据宣称全矩阵绿。[P-ci][FilmCraft packaging lint](https://github.com/storytold/filmcraft/actions/runs/38153123214)

## 大小/性能：复制 gate 思路，不复制不同的预算

PhotoCraft 将 Web profile 独立：fat LTO、codegen1、通常 opt-level s、UI z，而像素处理保留3；package 脚本检查相对 URL 和 **raw Wasm≤24 MiB**。这是项目选择的托管单文件限制，应与 gzip 传输、整个 bundle、运行内存分别测量。Web hosting docs 的19.68MB raw /8.18MB gzip 样本明确来自 **0.2.x**，不能给0.7.0冠名；当前 Web ZIP11.04MB也不能代替 raw Wasm/gzip 或启动性能。[P-cargo][P-web-package][P-web-sizes]

Nvwa 的原型任务书预算是**压缩首屏总下载30MB**，与 raw24MiB不同。当前已有单次GLB HTTP A/B、93测试整合版、native/Web连续idle cadence 证据；已知仍未建立精确GPU帧完成、完整workload、冷启动Web、浏览器内存和更广平台结论。用新profile测量生成报告，再判断优化是否值得，不删除 morph/animation 以达标。[N-budget][N-single-transfer][N-performance]

## 建议的五个小实验（按顺序；尚未实现）

| 顺序 | 小实验与范围 | 可衡量 pass/fail |
|---|---|---|
| 1 | **布局与输入原型**：仅现有inspector/timeline一个split/tab，锁定/重置与版本化session layout；可选试craft-ui一个组件，无新renderer。 | native/Web1280×720和1024×768及可实现的真实DPR/zoom下，关键控件可见、pointer对齐；中文preedit/候选框、Space/Undo/clipboard焦点守卫通过；cancel/reset后Work和history完整相等；布局坏数据可恢复。不要把未可操作的DPR项写pass。 |
| 2 | **内存与Web profile A/B**：固定同一Work、rig、渲染尺寸、连续播放及长编辑；控制并发负载，分别记录raw/gzip总量、网络body、startup边界、p95 cadence、RSS/可获得的Web内存。 | retention仍满足128/16MiB、1024/8MiB；新profile相对baseline显著减小bundle且没有预先约定的性能回退（可提议gzip至少降10%、p95不增>10%）；首屏30MB预算保留；不可测浏览器/GPU内存写NOT-RUN。达不到目标就拒绝profile，不引入瓦片结构。 |
| 3 | **命令说明目录**：给现有5种 typed core command 提供稳定id、正式参数schema、前置条件/禁用理由、是否修改Work及Undo策略；接现有CLI并在Studio加窄命令搜索。 | 五种都能发现；有效GUI/CLI输入产生相同完整Work；坏字段/范围/过期revision拒绝且Work/history不变；现有profile输出和值保持兼容。若目录与typed commands漂移或产生第二套修改逻辑则fail。 |
| 4 | **受限观察/控制 seam**：先只读inspect（revision、selection、transport、asset-ready、viewport logical/physical/DPR、错误）；再让一个现有edit经同一Editor入口。网络/文件/MCP放后续独立决定。 | inspect不改Work/revision/history；一次真实拖动一条事务；重复ID不产生二次编辑；stale revision、过期队列、超时后inspect恢复验证。若加native listener，必须另验loopback/auth/字节与队列上限，默认无file能力。 |
| 5 | **发行与小fixture corpus gate**：保持固定rig范围，用既有合法/损坏Work、缺asset/hash错/超时、时间轴边界样本，关联源码和产物hash；跑目标macOS及实际Web环境。 | 每个声明能回指exact source/artifact；完整JSON交换、pose/time边界、错误恢复、native迁移目录、Web子路径与实际响应压缩通过；签名/公证/新OS未跑就不标完成；不把all-target check替代实际运行。 |

上述阈值属于提议，需实现前固定baseline/设备/测试入口；不构成实测结果。M2 provider、任意角色/rig、IK、通用脚本、codec/Office格式不进入这些实验。[N-m1-contract][N-roadmap]

## 许可：代码与素材逐项处理

PhotoCraft、FilmCraft、WordCraft、GridCraft 的根 Cargo/license 文件为 **MIT OR Apache-2.0**；craft-libs 同样双许可。选MIT复制代码时保留copyright和permission notice；选Apache时满足其license副本、修改说明、相关attribution/NOTICE条件。记录源SHA/文件/选择的许可即可形成reviewable来源清单；这不是法律认证。[P-cargo][F-cargo][W-cargo][G-cargo][L-cargo][P-mit][P-apache]

PhotoCraft NOTICE 明确 **ArtCraft品牌名/wordmark/logo不在代码许可内**；字体OFL、Lucide图标ISC/部分MIT、SCOWL词表等有单独许可。ATTRIBUTION 是文件级清单，不能从GitHub Apache徽章推导“整库所有素材随便复制”。craft-ui没有bundled icons/fonts/engine，更适合小范围代码/控件评估，但仍要保留声明。[P-notice][P-attribution][L-ui-readme]

本次 craft-common-actions 根树未见 LICENSE，API license为空；只学习 gate 和拆分方式，暂不复制其workflow实现。相邻 bevy-mocap同样未建立复制许可。架构灵感与从源码/资产复制是不同工作，应在未来复制前逐文件核对。[A-tree][B-mocap-tree]

**PARTIAL — 已查固定SHA源码、组织库存、真实发行资产元数据和可见CI状态；所有本次build/runtime/UI/GPU/性能/发行包签名验证均NOT-RUN。Nvwa既有93测试和真人验收沿用仓库证据，不是本次重跑。**

## 固定源码引用

[P-tree]: https://github.com/storytold/photocraft/tree/9441484d168a9c40baf97bdd8086f139fdf8b896/crates
[P-cargo]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/Cargo.toml#L1-L114
[P-engine-deps]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/engine/Cargo.toml#L14-L39
[P-layers]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/xtask/src/layers.rs#L33-L104
[P-readme-underhood]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/README.md#L244-L251
[P-ui-deps]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/ui-egui/Cargo.toml#L10-L49
[P-gpu-deps]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/gpu/Cargo.toml#L10-L26
[P-web]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/apps/photocraft-web/src/main.rs#L1-L30
[P-registry]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/engine/src/commands.rs#L11-L27
[P-entry]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/engine/src/lib.rs#L1-L8
[P-edit]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/engine/src/lib.rs#L509-L639
[P-command-protocol]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/docs/control-protocol.md#L78-L88
[P-server]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/apps/photocraft/src/control_server.rs#L18-L109
[P-auth]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/docs/control-protocol.md#L10-L41
[P-policy]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/automation/src/workspace.rs#L16-L90
[P-policy-deny]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/automation/src/workspace.rs#L214-L275
[P-transport]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/docs/control-protocol.md#L333-L374
[P-timeout]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/ui-egui/src/control.rs#L46-L64
[P-raster]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/raster/src/lib.rs#L85-L191
[P-history]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/ops/src/lib.rs#L1-L94
[P-history-budget]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/ops/src/lib.rs#L201-L247
[P-format]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/format/src/lib.rs#L1-L21
[P-psd-corpus]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/psd/tests/corpus.rs#L22-L69
[P-oracle]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/io/tests/corpus.rs#L1-L44
[P-readme-psd]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/README.md#L213-L219
[P-dock]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/ui-egui/src/dock.rs#L1-L13
[P-docking]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/ui-egui/src/panel_docking.rs#L1-L59
[P-focus]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/ui-egui/src/shortcut_dispatch.rs#L119-L145
[P-ime]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/ui-egui/src/type_tool.rs#L563-L572
[P-ui-inspect]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/ui-egui/src/control.rs#L1161-L1170
[P-status]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/README.md#L300-L301
[P-ci]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/.github/workflows/ci.yml#L33-L242
[P-release]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/.github/workflows/release.yml#L23-L37
[P-web-package]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/packaging/web/package.sh#L19-L42
[P-web-sizes]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/packaging/web/README.md#L75-L109
[P-mit]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/LICENSE-MIT#L3-L13
[P-apache]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/LICENSE-APACHE#L90-L122
[P-notice]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/NOTICE#L1-L18
[P-attribution]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/ATTRIBUTION.md#L28-L61
[F-timeline]: https://github.com/storytold/filmcraft/blob/0800a8b0aa4a703ba42172f415b45a61f8d8a5e1/crates/ui-egui/src/panels/timeline.rs#L1-L10
[F-preview]: https://github.com/storytold/filmcraft/blob/0800a8b0aa4a703ba42172f415b45a61f8d8a5e1/crates/ui-egui/src/panels/timeline.rs#L404-L411
[F-project]: https://github.com/storytold/filmcraft/blob/0800a8b0aa4a703ba42172f415b45a61f8d8a5e1/crates/project/src/lib.rs#L511-L540
[F-status]: https://github.com/storytold/filmcraft/blob/0800a8b0aa4a703ba42172f415b45a61f8d8a5e1/README.md#L281-L297
[F-cargo]: https://github.com/storytold/filmcraft/blob/0800a8b0aa4a703ba42172f415b45a61f8d8a5e1/Cargo.toml#L1-L12
[W-command]: https://github.com/storytold/wordcraft/blob/dba6e66d53733c2c0fd28355249d24eb3698187e/crates/engine/src/lib.rs#L52-L117
[W-architecture]: https://github.com/storytold/wordcraft/blob/dba6e66d53733c2c0fd28355249d24eb3698187e/docs/architecture.md#L15-L49
[W-status]: https://github.com/storytold/wordcraft/blob/dba6e66d53733c2c0fd28355249d24eb3698187e/README.md#L196-L206
[W-cargo]: https://github.com/storytold/wordcraft/blob/dba6e66d53733c2c0fd28355249d24eb3698187e/Cargo.toml#L1-L12
[G-execute]: https://github.com/storytold/gridcraft/blob/336deb87ded7552f5a2890894ad7d19e9876be91/crates/engine/src/lib.rs#L272-L316
[G-architecture]: https://github.com/storytold/gridcraft/blob/336deb87ded7552f5a2890894ad7d19e9876be91/docs/architecture.md#L15-L65
[G-status]: https://github.com/storytold/gridcraft/blob/336deb87ded7552f5a2890894ad7d19e9876be91/README.md#L198-L204
[G-cargo]: https://github.com/storytold/gridcraft/blob/336deb87ded7552f5a2890894ad7d19e9876be91/Cargo.toml#L1-L12
[L-cargo]: https://github.com/storytold/craft-libs/blob/af2b0918d2c5e1ec984a1e1e142542a744596d58/Cargo.toml#L5-L15
[L-ui-source]: https://github.com/storytold/craft-libs/blob/af2b0918d2c5e1ec984a1e1e142542a744596d58/crates/ui/src/lib.rs#L1-L13
[L-ui-readme]: https://github.com/storytold/craft-libs/blob/af2b0918d2c5e1ec984a1e1e142542a744596d58/crates/ui/README.md#L1-L9
[A-readme]: https://github.com/storytold/craft-common-actions/blob/8f081ff5db115de44313c9db09415c359bf2ca01/README.md#L1-L61
[A-release]: https://github.com/storytold/craft-common-actions/blob/8f081ff5db115de44313c9db09415c359bf2ca01/.github/workflows/release.yml#L93-L199
[A-tree]: https://github.com/storytold/craft-common-actions/tree/8f081ff5db115de44313c9db09415c359bf2ca01/
[N-contract]: ../../docs/implementation/contract.md
[N-m1-contract]: ../../docs/implementation/m1-contract.md
[N-cli]: ../../crates/nvwa-cli/src/main.rs
[N-input]: ../../crates/nvwa-studio/src/web_input.rs
[N-roadmap]: ../../docs/ROADMAP.md
[N-retention]: ../../crates/nvwa-core/src/lib.rs
[N-history]: ../../docs/evidence/bounded-history/ACCEPTANCE.md
[N-m1]: ../../docs/M1-VERIFICATION.md
[N-tests]: ../../docs/evidence/single-transfer/ACCEPTANCE.md
[N-layout]: ../../crates/nvwa-studio/src/lib.rs
[N-budget]: ../../docs/specs/Nvwa_Codex_Prototype_Brief_Rust_First_v2.md
[N-single-transfer]: ../../docs/evidence/single-transfer/ACCEPTANCE.md
[N-performance]: ../../docs/PERFORMANCE.md
[B-mocap]: https://github.com/storytold/bevy-mocap/blob/1de4500cbae9f81ce37c304a22360c8a6990a0e4/README.md
[B-mocap-cargo]: https://github.com/storytold/bevy-mocap/blob/1de4500cbae9f81ce37c304a22360c8a6990a0e4/Cargo.toml
[B-mocap-tree]: https://github.com/storytold/bevy-mocap/tree/1de4500cbae9f81ce37c304a22360c8a6990a0e4
[B-bevy]: https://github.com/storytold/storyteller-bevy/blob/4ce8b72c4cf3263ef9df99761f93832009026a89/README.md
[P-lookup]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/engine/src/commands.rs#L124-L151
[P-ime-caret]: https://github.com/storytold/photocraft/blob/9441484d168a9c40baf97bdd8086f139fdf8b896/crates/ui-egui/src/type_tool.rs#L732-L739
