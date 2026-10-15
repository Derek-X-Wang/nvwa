# Experiment conclusions

## 2026-10-15：CLI 第三入口与同一样本的有界校准

CLI 已明确为与桌面、Web 并列的正式入口，支持范围是现有离线文件操作；[实际六次调用](evidence/cli-third-entry/README.md) 保留能力发现、命令、真实资产校验和完整保存回读。数据编辑不要求窗口、GPU 或本地动作权重。逐帧姿态、离屏图像导出、运行中桥接与并发共享写入未交付，详见 [CLI 支持范围](CLI-SUPPORT.md)。

| 实验 | 决定 | 实际证据与限制 |
| --- | --- | --- |
| [46 签名参考与骨骼校准](../experiments/46-soma-reference-calibration/REPORT.md) | 接受条件 root 数学与诊断；解剖/可播放准入 HOLD | 复用 44 原始 90 帧；独立 signed anchors 条件约束 `48→8→2→1`，不自动采用反射或左右标签政策。逐关节几何/扭转缺口明确。两个条件基的 pelvis 世界误差最大约 `1.735e-18 m`，七个 root 错误策略被拒绝；27 个正向与 48 个拒绝检查在 Python 3.9/3.12/3.14 普通及优化模式通过。无规范化/生成 Work/目标播放。 |
| [46 独立仿射 oracle](../experiments/46-soma-reference-calibration/independent/README.md) | 保留独立实现与反例 | 不导入 43/45/46 数学；独立冻结后复算 90 帧、q/−q、近共线敏感性和扭转不可观测性。绝对 hip 与中立相对位置是分别声明的条件规则；数学闭合不选择解剖政策或实际落地高度。 |

173 项既有产品、资产与 41–45 输入路径保持冻结；无根依赖、锁文件、模型或渲染器改变。新增 CI 只在原 portable job 增加离线标准库检查。候选与合并后 main CI 仍需分别验证；#3 保持阻塞，#4/#49 未验证项保留，#59/#12/M2 的后续准入门开放。此前 [#60](https://github.com/Derek-X-Wang/nvwa/pull/60) 已合并为 `8dfc8a8c05ac2f5794498a76b36e8c747e27054c`，其 [独立 main CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/38790750484) 通过，#54 按单次原始试跑范围关闭。下方旧记录保留当时状态。

## 2026-10-15：一个获授权的真实原始 CPU 动作样本

| 实验 | 决定 | 实际证据与限制 |
| --- | --- | --- |
| [44 获授权 CPU 原始动作试跑](../experiments/44-approved-cpu-motion-trial/REPORT.md) | 接受一个 genuine raw 样本及数值结构；M2/#12 保持开放 | 精确三文件 6,198,789,742 字节已获批准并验证；一次离线 CPU 请求 exit 0，90 帧/30 关节，两份 F32 大小/hash 与 11,070 个有限值、2,700 个非退化四元数检查通过。58.545243 秒包含 guard/清理，1,234,583,552 字节为采样组 RSS；忙碌 16 GiB Mac、hash 后缓存状态，不是硬峰值/冷启动基准。坐标、rest/root、规范化、目标映射、语义和生成播放仍未验收；单次授权已用完，无重试。 |
| [45 真实样本映射数值研究](../experiments/45-genuine-rig-admission/REPORT.md) | HOLD 可播放准入；保留 root 与解剖基问题的数值证据 | 只使用 44 的同一 90 帧样本。原 43 规则产生约 `0.83 m` pelvis 世界位置偏差；旋转/缩放偏移重定位只修正声明的 hip-world 条件，左右方向与手臂中立姿势仍未校准。无规范化/导出/Work/播放；离线 CI 通过表示 HOLD 研究与拒绝控制通过，不表示生成播放获准。 |

44 保留原始 acquisition/controller/process/profile/resource/cleanup 记录、两个小原始数组和独立前/后审查；可仅用 Python 标准库离线核验，不运行模型。41 的预跑报告保持原字节，授权后的真实证据在 44 单独记录。#54 仅在本轮审查与发布合并后可按有界实验范围关闭；#3/#4/#12/#49 不变。

[#58](https://github.com/Derek-X-Wang/nvwa/pull/58) 的 [PR CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/38764869474) 和 `b7122a20366f665f7ca32d48d5dc2f51a874ddbf` 的 [main CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/38770232509) 已通过。下方 41–43 与历史验收/索引保留各自当时状态，旧整合清单中的根文档 hash 属于该历史快照；当前文档的状态更新不改写旧清单，也不宣称全部历史路径仍与当前文档逐字节相同。

## 2026-10-15：M2 隔离控制与双端 authored 播放

| 实验 | 决定 | 实际证据与限制 |
| --- | --- | --- |
| [41 真实短动作 CPU 准备](../experiments/41-real-short-motion/REPORT.md) | 保留私有构建/guard 证据；真实生成待批准 | CPU 后端构建/help、原生 float 前提及失败/清理控制通过；后续 ps 误判导致 HOLD，修复后定向 R2 通过，旧结论与失败证据分开保留。模型/编码器下载和一次有界 CPU 推理仍需明确批准，未执行真实推理或证明输出坐标约定。 |
| [42 动作导入](../experiments/42-motion-import/REPORT.md) | 保留独立 importer 与回归控制；不整合产品 | 离线锁定构建及 19 项真实 CLI 边界测试通过；authored GLB/Work 已由父 session 用产品 CLI 验证并双端播放。伪造生成凭证仍被拒绝，归一化输入/输出 hash 分开记录。 |
| [43 rig 映射](../experiments/43-rig-mapping/REPORT.md) | 接受 authored 控制的旋转规则；拒绝一般位置保持 | 30/77 数值 A/B、负例及父 session 导入/双端播放通过；naive 四肢明显折叠，calibrated 呈现声明的非对称动作。源手/脚端点仍差 `0.277118877976 m`，真实 provider rest/handedness、接触/IK 与一般 rig 未验证。 |

[父 session 验收与复现](evidence/m2-authored-controls/ACCEPTANCE.md)分开记录本地 model-free 检查、CLI、native/Web 实际观察和历史报告边界。当前 70 项冻结文件与源 cohort 一致；仅 41 经明确授权按原 worker 的修复版本精确刷新，初始 64 项索引及失败历史保留。新增 CI 只在现有 portable job 显式准备锁定 Rust 源依赖，再离线运行 importer/mapping 与实际 CPU 清理控制，不调用 provider 或模型。36 份独立 authored 参考文件支持跨 Python 的严格结构/来源与有限浮点误差比较；3.9/3.12/当前版本检查通过。尚待本轮 hosted CI 和定向独立整合复审。全部动作均为 `authored_control`、`ai_generated:false`，没有新真人或性能结论；#3/#4/#12/#49 门保持开放。以下记录保留各自历史状态。

## 2026-10-13：下载观察与发行许可候选

| 实验 | 决定 | 实际证据与限制 |
| --- | --- | --- |
| [35 Web下载观察复查](../experiments/35-web-export-followup/REPORT.md) | 保留有界证据；不采用产品补丁 | 两个真实Web加载、三个触发取得原有按钮和当前页面自动导出的真实角色PNG。跨导航监听30秒未观察到事件；监听生命周期、日志与启动时序有混杂，原因仍未知。未来日志工具的CPU修复与原始实际运行副本分别保存。 |
| [36 发行许可候选](../experiments/36-distribution-notices/REPORT.md) | 保留隔离清单；不安装到打包产物 | 正常/构建目标闭包307原生、278Web，联合323个候选、1040个索引文件；不是最终链接成员。23项无实质性条款候选、三个第一方许可未知、47个缺口。签名、发行、清洁机器及法律批准NOT-RUN。 |

[本轮验收与独立复审](evidence/export-notices-20261013/ACCEPTANCE.md)分别记录实际运行、CPU控制、修复及复审。没有新产品/根依赖/锁文件/CI/角色资产变化。PR42已合并main7851c2e，原性能实验33/34及190项归档保持原字节；#3阻塞、#4未验证项保留。下方记录保留历史状态。

## 2026-10-13：首帧、GPU 与内存补测

| 实验 | 决定 | 实际证据与限制 |
| --- | --- | --- |
| [33 原生 Metal 呈现与内存](../experiments/33-native-present-metrics/RESULTS.md) | 保留隔离诊断；不整合观察器 | 已编译独立 release 诊断，原有基线加两次诊断共三个进程实际显示角色并退出0。记录有效呈现时间、GPU 命令完成、PID/birth 核对内存和真实像素。首个回调零值、首个截图空白均保留。诊断会干扰启动，完全冷态和停顿原因未验证。 |
| [34 Web 冷态边界与 GPU 时间戳](../experiments/34-web-cold-metrics/RESULTS.md) | 采用可复核测量边界；GPU 对照不接受 | 三个实际加载完整 no-store HTTP/CPU 记录通过，30个 JS heap 子集样本/加载。GPU 查询实际尝试，但零值与倒序错误使结果保持 NOT-RUN；不修改源代码或追加加载来隐藏失败。完全冷态、精确屏幕首帧和进程/GPU 总内存不可取得。 |

[原始测量与验收](evidence/bounded-perf-20261013/ACCEPTANCE.md)。同一 Work、真实角色、1280×720/DPR1；一个渲染器、没有竞争重编译，用户应用及系统缓存未控制。只增加 `experiments/` 与证据，不改变根依赖/锁文件或主线角色资产。#4 开放，#3 保持阻塞。

Current M1.1 continuation (2026-10-13): the accepted base is045d8abc after PR36/38/35. Experiment28's CPU painter check becomes six permanent tests in candidate#39; the original paint-only red/state-green control is preserved. [Experiment29](../experiments/29-stalled-loads/README.md) verifies the four-root/latest-pending policy with real stalled HTTP production-system controls and actual one-app Web recovery. [Experiment30](../experiments/30-startup-profile/REPORT.md) retains two all-black native captures and profiler results; its separate [baseline Web control](../experiments/30-startup-profile/WEB-REPORT.md) has real character pixels and exact eight-request reconciliation. [Experiment31](../experiments/31-ui-pixels/REPORT.md) compiled; its native-window pixel cases remain NOT-RUN. [Experiment32](../experiments/32-tab-pixels-headless/REPORT.md) separately proves actual headless Metal/Image rendering: unchanged literal checker accepts two normal images and rejects a paint-only mutant with state held, exits0/0/1. One adapter/two interior regions do not establish full UI coverage or permanent GPU CI. Its compile guard also repairs an inherited I/O cleanup gap with ten real controls; historical30 bytes remain intact. These measurement results do not establish first physical presentation, fully cold startup, GPU memory or a cause for native blank content. Integrated113 tests, both release builds and source-cohort hosted run38392776461 pass. A later actual native continuation separately verifies real tabs, missing-asset same/different-path recovery, whole-Work Save/Open and paused click-action restoration; [native archive](evidence/m1-1-final/native/README.md). Final archive-head/post-merge CI remain separate gates. [Current acceptance](evidence/m1-1-final/ACCEPTANCE.md). Earlier conclusions below retain their original dates and scopes.

Latest independent continuation (2026-10-12): PR #34 is merged at `de4ddef`. #3 stays blocked. [Experiment26](../experiments/26-export-drift/REPORT.md) compares two actual same-version Blender exports: varying eye triangle ordering/storage and 485 normal components; positions, skin data, morph POSITION deltas and animation samples match exactly. Frozen assets remain unchanged. Complete `.blend` equivalence and shading impact are NOT-RUN. [PR #35](https://github.com/Derek-X-Wang/nvwa/pull/35) contains separate ArtCraft testing research and bounded CI: meaningful command/corruption checks first; independent UI references/mutation controls remain a proposal. Its local CPU/compile results and hosted trial do not imply native/Web rendering or physical-input validation. Earlier tables retain their original snapshot and scope.

Latest bounded update (2026-10-12 PDT): PR33 is merged at `6b5cf80`. #3 remains blocked by missing original IAB DPR emulation. [Experiment24](../experiments/24-http-cold-startup/REPORT.md) verifies two actual HTTP-cache startup boundaries; [experiment25](../experiments/25-screenshot-export/REPORT.md) records successful top-level PNGs and unresolved iframe export failures. Anchor-attachment/revocation candidates are not adopted. [Current evidence](evidence/bounded-startup-capture/ACCEPTANCE.md). Production code/dependencies unchanged; earlier tables retain their acceptance date and scope.

Final snapshot: 2026-10-10 PDT / 2026-10-11 UTC. Source compilation, CPU checks, native/browser execution, UI exchange and isolated cadence measurements have separate evidence. Four implementation workflows ran within the four-agent limit; reviews and optional experiments followed as slots became available. Experiment code stays outside mainline dependencies.

| Experiment | Decision and actual evidence | Limit / effect on architecture |
|---|---|---|
| [01 — Original character](../experiments/01-character/REPORT.md) | **Adopt.** Continuous 22,572-vertex primary body, normalized skin weights, 18 joints, 4 distinct nonzero morphs, 3 authored clips. Binary validation, Blender inspection and native/Web rendering passed. | One original fixed rig with CC0 fixture provenance. Two exports match measured structure/morph hashes but differ in file bytes. Production hands/weighting remain future work. |
| [02 — Command transactions](../experiments/02-command-transactions/REPORT.md) | **Adopt.** 13 core tests plus actual CLI equality with GUI-produced revisions 7 and 10. Real Web drag commits once; history restores geometry. | One pure Rust authoritative document and atomic typed API serve CLI/runtime/UI. Initial retry/undo history was unbounded; experiment10 now supplies bounded session retention. |
| [03 — Runtime/UI](../experiments/03-runtime-ui/REPORT.md) | **Adopt.** Same Bevy/egui Rust app runs native Metal/WebGPU. Actual four morphs, skeletal clips, save/reload/error recovery, bidirectional exchange and final 33 tests passed. 1280×720 steady cadence p95 native 8.65 ms, Web 11.20 ms. | Keep one runtime/editor. Real import revealed and fixed replacement-player initialization. CJK/IME/native drag/clipboard and browser scaling/input coverage remain limited. Cadence is not GPU timing. |
| [04 — Rest-basis retargeting A/B](../experiments/04-retarget-basis/REPORT.md) | **Adopt correction / reject naive copying for this controlled case.** 19 real-wave samples, 18 joints, 24,736 vertices in exported/reloaded GLBs. Max vertex error corrected 3.08e-8 m, naive 0.868 m. Identity/rest and invalid-input controls pass. | Narrow future basis conversion rule. Derivatives retain anatomy/topology/proportions; visual retarget playback, arbitrary rigs, IK/root-motion policy NOT-RUN. Nothing added to M0 runtime. |
| [05 — Optional AI motion](../experiments/05-ai-motion/REPORT.md) | **Inconclusive for genuine inference; adopt only isolated import seam.** Official Kimodo/component licenses checked. Runtime/authorized weights absent in checked locations; 9 Python tests use an authored preset with ai_generated=false. | No model packages/weights/paid calls/inference in Studio. 16 GiB M2 feasibility, output schema/mapping, performance and genuine generated playback unverified. M0 proceeds independently. |
| [06 — CJK fonts A/B](../experiments/06-cjk-fonts/REPORT.md) | **Choose the static Regular derivative for acceptance.** Actual source and derivative retain the same 30,890 mapped codepoints and glyph order. Standalone gzip-9 is 11,276,563 bytes for the variable source and 6,303,513 for static weight 400. Source, deterministic derivation and OFL notice are recorded. | One shared egui fallback for native/Web; no extra dependency or font download at runtime. Most supplementary Han is absent. Final build/render/input evidence is recorded separately in [font/input acceptance](evidence/input-fonts/ACCEPTANCE.md); IME requires its own verification. |
| [07 — Native input event batches](../experiments/07-native-input-events/REPORT.md) | **Keep isolated diagnosis; no production integration.** Actual pinned library systems and TextEdit: a complete one-frame Command+A chord loses Command and inserts `a`; held across frames selects all. Plain A control passes. Three assertions, root rerun and independent cross-model R1 source review passed. | Only supplied library messages. Full EguiPlugin/Winit, OS/CUA event delivery, physical keys/clipboard/IME and pointer delivery remain unverified. No root dependency or lock change. Native clicks/Undo/Redo and zoom have separate GUI evidence. |
| [08 — Desktop Web IME](../experiments/08-web-ime/REPORT.md) | **Adopt committed-only desktop input boundary; reject inline-preview rollback.** The desktop upstream helper lacks its DOM composition/activation route. Final Rust/wasm proxy retains OS preedit and sends confirmed text to egui. 67 workspace tests, strict checks, both release builds/runs, 12 real-library probe assertions and actual browser commit/cancel/selection/clipboard checks passed. Derek's repaired physical Web retest reports “全部正常”. | Preserved rejected source reproduces selection-cancel loss. An unsupported diagnostic InputEvent type was normalized to empty; corrected supported-type callbacks insert once on unchanged production code. Native and command schema stay unchanged. Other engines, zoom/DPR and new performance remain unverified. See [Web input evidence](evidence/web-input/ACCEPTANCE.md). |


| [09 — Single GLB retrieval](../experiments/09-single-transfer/REPORT.md) | **Adopt within the supported fixed-GLB explicit-open contract.** Reader delegation preserves the complete asset tree; same-path publication fencing repairs a reproduced late-subasset race.93 integrated tests and both release builds pass. Actual Web A/B is2→1 GLB GETs, saving1,129,081 compressed body bytes; missing/hash errors and same-path recovery pass. | Independent R2 repaired P1/P2 and accepted the final source. Hung same-path readers remain fenced; retained pending roots have no RAM/GPU cap. Native Ready passes but current screenshots are black while the Mac is locked; unlocked visual acceptance remains NOT-RUN. [Integrated evidence](evidence/single-transfer/ACCEPTANCE.md). |
| [10 — Bounded session history](../experiments/10-bounded-history/REPORT.md) | **Adopt.**128 snapshots/16MiB and1024 successful retries/8MiB compact payload limits;79 integrated tests, long-session workload, dual release builds, actual native/Web whole-document Undo/Redo/Save/Open/exchange pass. | Content budgets are not exact heap/RSS. Failed commands stay atomic; oversized adjacent states form history barriers. Independent real CLI probe found and repaired f32 widening. Published in [PR20](https://github.com/Derek-X-Wang/nvwa/pull/20), pending merge. |
| [11 — Live viewport input](../experiments/11-viewport-input/REPORT.md) | **Keep bounded evidence; no production scaling workaround.**1600×900 and1024×768 at DPR1 pass text/caret and actual slider/whole-document Undo. | Original simulated DPR failure remains unreproduced. True zoom/DPR and browser-tab transitions remain unverified; current adapter lacks a DPR override. |

Publication: [character.profile.json](../assets/character.profile.json), [provenance/hash manifest](../assets/fixtures/provenance-manifest.json), [sources and licenses](SOURCES-LICENSES.md). Asset/code/model licenses are distinct. Retarget derivatives and AI-boundary presets do not replace the frozen main fixture or enter normal builds.

A/B compared two motion mappings on the same real fixture and sampling conditions. It establishes a high-risk basis-conversion result without a second product renderer. No Bevy UI/Feathers comparison, full IK, VaM inspector or real AI inference ran. Each retained experiment has reproduction steps and an explicit conclusion; unavailable paths were not relabelled as successes.

Final evidence: [GUI session](evidence/GUI-SESSION.md), [exchange equality](evidence/exchange-result.json), [CLI/GUI replay](evidence/cli-gui-parity.json), [test matrix](TEST-MATRIX.md) and [performance](PERFORMANCE.md). Decisions are in [ADRs](adr/).

PARTIAL — M0 and eleven isolated experiment reports retain actual evidence or explicit unavailability; genuine AI inference is NOT-RUN, retargeting is numerical-only for controlled derivatives. The bounded desktop Web input repair has actual callback and user-performed physical acceptance.


Later acceptance update: Derek manually unlocked the Mac. The same current native binary (`3be9380f…`) now exits0 with a visually inspected real character playing wave, revision9 and18 joints/4 morphs/3 timeline entries. [Unlocked native evidence](evidence/single-transfer/native-unlocked.png) supersedes only the earlier blocked visual result; both black captures remain retained failures. This is a functional smoke, not a current performance benchmark. PR18 is merged at `07858fe6b5d6062200d28df654c5ce53ad89007b`, with #1/#19 closed; #2/#3 remain open. PR20 remains pending merge; PR21 completes local acceptance and is pending review/merge.

## 2026-10-11：输入恢复与缩放边界

| 实验 | 决定 | 已运行证据与边界 |
| --- | --- | --- |
| [19 输入恢复](../experiments/19-input-focus-recovery/REPORT.md) | 采用被动诊断工具；无产品修复 | 实际 Chrome 标签离开/返回后自然继续输入，完整作品不变；Derek 的125%中文/Space、Command+A/V与切换恢复通过。来源不明的 untrusted compositionend 保留 PARTIAL。 |
| [20 缩放边界](../experiments/20-scale-boundary/README.md) | 正常 Chrome zoom 通过；原始 IAB 问题保留 | 实际 DPR2→2.2→2.5→2；点击/光标、jaw修改/Undo、完整作品检查通过。独立审查修复证据检查器误判，15测试通过；旧脚本13断言失败与1schema错误保留。CSS也改变，固定CSS DPR隔离和原始IAB入口 NOT-RUN。 |
| [21 完整作品检查](../experiments/21-input-scale-evidence-checks/README.md) | 保留独立离线核验 | 实际 tab-return 全文含revision相等；jaw修改/Undo全文核验通过。该检查器只要求revision递增；单次提交断言由实验20承担。数值几何一致不等于输入命中。 |

复现、运行环境、精确原始JSON/截图、真人归因和清理记录统一见[验收](evidence/input-scale/ACCEPTANCE.md)。无新增 Cargo 依赖、重编译或性能测试；当前正式 Rust/资产输入31项与已验收构建保持相同。

## 2026-10-11：固定画布与输入法来源对照

| 实验 | 决定 | 实际证据与边界 |
| --- | --- | --- |
| [22 固定 CSS / DPR](../experiments/22-fixed-css-dpr/REPORT.md) | 保留通过的缩放对照；不整合产品 workaround | 实际 Chrome100%→125%→100%，固定父容器/画布1100×640，DPR2→2.5→2，buffer2200×1280→2750×1600→2200×1280；点击、整份作品修改/一次Undo通过。普通与固定画布合计六个点击区间通过。工具拖动没有连续事件，实物显示迁移与原始IAB模拟故障 NOT-RUN。 |
| [23 IME 来源](../experiments/23-ime-event-provenance/REPORT.md) | 一次真实对照后按 UNKNOWN 退出；无产品修复 | 实际 Chrome 合成自检有15行、三次精确匹配的事件/dispatch/callstack。真人普通文本框52行/Nvwa42行、搜狗（用户报告），均有相同来源未明的长度2结束事件；两份检查均保持PARTIAL/exit2。20项检查器测试、3项准备变异控制通过。旧710仍UNKNOWN；本次候选框位置/Space选字NOT-RUN，不重复实机输入。 |

独立审查发现并修复观测器把后代焦点变化误记为窗口焦点，以及两个检查器误判路径；保留失败原始文件和 red/green 证据。26项缩放控制通过。原生2x实际角色、窗口放大后的点击/一次撤销通过；不是显示迁移或性能测量。统一见[验收](evidence/bounded-scale-ime/ACCEPTANCE.md)、[独立审查](evidence/bounded-scale-ime/REVIEW.md)。
