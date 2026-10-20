# 人物基础与质量排查阶段冻结 — 2026-10-20

本地收口验证已完成：#87 版本错误文案已纠正，基线中已有的 #86 就绪／等待反馈已核验，并完成一次有界普通 Web／CLI 回归。最终独立审查、精确 PR CI、合并及自然触发 main CI 由 [#87 关联 PR 的完成账本](https://github.com/Derek-X-Wang/nvwa/issues/87)记录；发布门通过后，本阶段才记为有界冻结、可进入复盘。基础设施重构、新肩部资产和新发际候选均未开始。

**阶段冻结不是 M2 完成，不是人物质量准入，也不是产品发布批准。** 历史失败、实验结论、哈希与原有门禁保持原样。后续是否继续质量研究或整理基础设施，由复盘后另定范围。

## 已交付能力与证据

这里列出已有证据支持的能力。证据只覆盖各报告写明的构建、输入和操作，不能合并成当前版本的全量重验。

| 能力 | 已有实际证据 | 边界 |
| --- | --- | --- |
| 共享 Rust Work 与命令 | Web／桌面共用文档、命令、运行时与编辑界面；CLI 用同一命令核心离线创作、校验和保存。见 [CLI 支持](../CLI-SUPPORT.md)与[创作合同](../agents/cli-authoring.md)。 | CLI 编辑文件，不控制已打开的窗口，也不证明画面已呈现。 |
| Web、桌面与独立 CLI | 普通 Studio／Player、文件交换及完整独立 CLI 资产包已有实际记录。见 [CLI 包](../evidence/cli-standalone/README.md)。 | 本地源构建支持不等于公开安装器、签名、干净机器或其他系统认证；发行边界仍由 #10 跟踪。 |
| B1 八参数人物 | 躯干长度、张嘴、头宽、鼻宽、嘴宽、下巴宽、颈宽和臀宽；编辑、撤销／重做、双端各 69 组暂停 CPU 门与各 18 步短播放检查已有记录。见[人物记录](../evidence/b1-character-quality/RESULTS.md)。 | 旧 Work 保留原 profile，不自动增加参数；暂停读回与短时播放不证明长时连续呈现或任意时刻 GPU 形变。 |
| 连续预制动作 | 同一 B1 的四秒手臂活动、四秒单腿屈膝及共享播放／暂停／定位已有[连续动作验收](../evidence/b1-motion/ACCEPTANCE.md)。 | 这些是 Nvwa authored actions，不是 AI 生成；衣物与 M2 真实动作质量仍 HOLD。 |
| 外观保存与交换 | 皮肤、眼睛、短发独立选择，写入 Work，走共享命令／撤销与 CLI；实际原生→Web→原生往返见[外观记录](../evidence/b1-appearance-work/RESULTS.md)。 | 固定 CC0 来源与材质合同；保存和 CPU 绑定通过不等于发际、眼睑或整体审美通过。 |
| 可调试演舞台 | 灯光、背景／地面、相机和画质保存并交换；实际 Web／原生／CLI 证据见[舞台验收](../evidence/rehearsal-stage/ACCEPTANCE.md)。 | 房间导入、物理、多人及质量成本测量未由该阶段交付。 |

## 冻结的质量决定

- **肩部 #80：REJECT，保持 HOLD。** [实验 81](../../experiments/81-shoulder-patch-corrective/README.md)只评估一版七点连接范围的姿态修正，19 组固定输入完成。默认抬臂峰值分析性采样 44→0，但六组中段输入各新增两组严格横穿；独立算法确认，九组零激活控制精确不变。离线拒绝后没有构建或上传候选运行时，不能声称实际 Web 改善。静止肩部面板重拟合只是候选后续比较，没有制作新资产，也没有证明源网格就是病因。
- **发际 #79：保留 A，不扩大当前 B 采集。** [实验 82](../../experiments/82-hairline-aba/RESULTS.md)的同场景实际 Web A→B→A 有三份完整记录和合格截图；来源／CPU、原组间控制、A 恢复及实际 Work 的 CLI 逐字节往返通过。当前 B 是既有 `BLocalAlpha` 临时局部 alpha 候选，source0 只见细微边界变化，实际改善不足，结论为 **INCONCLUSIVE / NO-ADOPT**。它与早期遮挡额头／眼睛的 fringe-B、实验 69 的 mip 候选各自独立。当前 source0 未见新增额头／眼睛遮挡，不能据此推断完整 cohort。完整体型／动作、眼睑、GPU 读回和性能仍未验收。

## 保留的开放边界

下列状态来自 2026-10-20 的议题读回及上述固定报告。冻结阶段不会关闭这些要求。

| 项目 | 冻结状态与下一证据 |
| --- | --- |
| [#3](https://github.com/Derek-X-Wang/nvwa/issues/3) | 仍阻塞。需要原始 DPR 仿真条件／轨迹或实际显示缩放迁移；普通浏览器回归不能替代原始复现。 |
| [#4](https://github.com/Derek-X-Wang/nvwa/issues/4) | 保留首次实际呈现、完全冷启动、GPU／浏览器内存与原生启动归因缺口。Ready、截图回调和主循环频率均不能替代它。 |
| [#49](https://github.com/Derek-X-Wang/nvwa/issues/49) | 未引导的完整真人 Alpha 仍开放；已引导成功与 agent 执行不同。见[试用包状态](../m12-unassisted-trial/README.md)。此次不开始新试用。 |
| [#79](https://github.com/Derek-X-Wang/nvwa/issues/79)、[#80](https://github.com/Derek-X-Wang/nvwa/issues/80)、M2 | 完整发际／眼睑、衣物与真实动作质量仍 HOLD。阶段冻结与 CI 通过均不能解除。 |
| [#86](https://github.com/Derek-X-Wang/nvwa/issues/86) | 保持开放。收口基线已包含反馈修正，当前说明为 CPU body + requested appearance bound · presentation unconfirmed；本轮核验该行为，并给现有生命周期测试增加调度后反馈断言；未改变渲染行为。该反馈只区分等待、CPU 当前状态和未确认的画面，不修复或证明消失根因，不建立无闪断／最坏恢复时间保证。[既有普通 Web 回归](../evidence/web-edit-regression-20261018/README.md)的首次无效输入及未知原因保留。 |
| [#84](https://github.com/Derek-X-Wang/nvwa/issues/84) | 九项既有严格全工作区 Clippy 告警仍开放。它是可独立安排的有界维护候选；更广的基础设施重构尚未批准或开始。 |
| [#87](https://github.com/Derek-X-Wang/nvwa/issues/87) | 本地修正与实际 UI 拒绝通过；发布完成／关闭以关联 PR 账本为准。只去掉错误的“expected 1”，不接受新版本、不升级 Work、不改变拒绝代码或原子保护。 |
| 日常桌面回归 | 依[验收策略](../agents/verification.md)集中到较大版本节点，标记 `NOT-RUN（按策略延后）`。桌面专属变化仍须专项验证。 |

## 本次收口核验记录

完整[实际 Web／CLI 记录](../evidence/character-closeout-20261020/README.md)与[脱敏观察及来源哈希](../evidence/character-closeout-20261020/observations.json)保留结果、失败、原图和实际下载。

| 范围 | 状态／证据 |
| --- | --- |
| 收口前基线 | main `d21dfcf0f717c2d25865a42b4094351bfdfe7069` 在 [PR #100](https://github.com/Derek-X-Wang/nvwa/pull/100) 后核验；[自然 main CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/39377322274)通过。实验 81／82 的冻结结论见原报告。此基线不是收口后提交的 CI。 |
| 集成源码控制 | 69 项 Core／CLI 与 16 项唯一运行时控制通过。旧 mutation cohort 独立保留，不加入这批计数。实际 Web 构建的 249 个源文件哈希与集成目录一致；Wasm SHA-256 为 `3c1a05e760648ebdc8f68b93d6dd09a15eaa6950a958ca2cd7094cbed940dec4`。 |
| #87 核心及普通 UI 错误路径 | VERIFIED — 实际版本 999 报错准确，当前人物／Work 保留；损坏 JSON 另有明确错误。两个拒绝后 Undo／Redo 仍恢复正确舞台设置。未改支持版本、身份或原子保护。 |
| #86 已有反馈及普通 Web 回归 | PARTIAL — 两种后端实际编辑、Undo／Redo、短播放、精确 2 秒定位、外观及舞台编辑、错误恢复均记录。三张空场景样本显示 Preparing，无错误 Ready；仍无连续呈现或最坏恢复保证，#86 保持 OPEN/HOLD。 |
| 实际保存与 CLI | VERIFIED — Web 下载 3700 字节，CLI 资产校验、inspect、save、复验退出 0，保存副本逐字节相同，并由普通 Web Open 成功重开。另一次 CLI 新建／保存为 3303 字节逐字节相同。 |
| 自动化偏差 | 保留 UNKNOWN：轨道点击先落在 8 秒，之后数字框准确设为 2 秒；意图输入 8000 却实际提交 8 lux。只接受实际值，不声明多位数输入通过，不归因产品或 #3。 |
| 发布门 | 最终独立审查、精确 PR head 的适用 CI、合并提交及自然 main CI 以 [#87 关联 PR 完成账本](https://github.com/Derek-X-Wang/nvwa/issues/87)为准。本页不提前宣称托管检查成功；只有该门完成后才宣告阶段冻结、ready for retro。 |

## 小型 Web／CLI 回归指南

这是执行入口，不是本页新增的运行结果。使用已标识的当前 CLI／Web 构建；缺少构建时按 [README](../../README.md#run)与[CLI 支持](../CLI-SUPPORT.md#build-and-run-requirements)准备，记录实际源与产物身份。既有依赖、工具和新输出目录是前提，不下载模型。较长检查按本地规则运行。

从仓库根目录，以已经构建的 CLI 执行以下真实文件路径；若使用独立包或自定义 target，按[独立 CLI 合同](../CLI-STANDALONE.md)替换二进制和完整 `assets/` 根：

```sh
mkdir -p .work
CLOSEOUT_OUT="$(mktemp -d .work/character-closeout.XXXXXX)"
CLI="$PWD/target/debug/nvwa-cli"
"$CLI" new-character assets "$CLOSEOUT_OUT/character.nvwa.json"
"$CLI" describe-capabilities "$CLOSEOUT_OUT/character.nvwa.json"
"$CLI" validate "$CLOSEOUT_OUT/character.nvwa.json" assets
"$CLI" save "$CLOSEOUT_OUT/character.nvwa.json" "$CLOSEOUT_OUT/saved.nvwa.json"
"$CLI" validate "$CLOSEOUT_OUT/saved.nvwa.json" assets
"$CLI" inspect "$CLOSEOUT_OUT/saved.nvwa.json"
cmp "$CLOSEOUT_OUT/character.nvwa.json" "$CLOSEOUT_OUT/saved.nvwa.json"
```

需要命令编辑时，执行 [README 的实际 `apply` 示例](../../README.md#programmatic-edits-with-the-native-cli)，先读取当前 Work 的 discovery；不要把其他 profile 的参数或 revision 直接复制过来。保留 stdout、stderr、退出码和实际文件。`apply`／`save` 只验证便携元数据，资产验证另行执行。

Web 使用仓库的 `python3 scripts/serve-web.py`，先确认所用 Nvwa 预留端口空闲；普通入口为 `http://127.0.0.1:9201/`，不加实验或 benchmark 参数。按[既有普通回归步骤](../evidence/web-edit-regression-20261018/README.md)在一次固定构建会话中检查：

1. 打开 `examples/b1-appearance.nvwa.json` 与 `examples/b1-character.nvwa.json`，分别做一个躯干编辑、释放滑块、一步 Undo／Redo；确认 Work 数值、角色与选中外观，记录反馈及稀疏画面。
2. 在八参数 Work 播放／暂停／定位，切换一个外观选择，再调一个舞台设置；只把实际观察到的动作与值记为通过。
3. 用临时损坏文件 Open，确认错误和原 Work 保留；重开有效 Work 恢复。记录 #87 实际版本错误时使用专门无效版本副本，不改原样例。
4. 实际 Save 下载，保留并用 CLI `validate`／`inspect` 读回该文件，按[外观交换记录](../evidence/b1-appearance-work/RESULTS.md)区分有意字段变化与文件丢失。

CPU 当前状态不等于完整画面已呈现。稀疏截图不能证明没有中断；不从本轮推导首次呈现、最坏空白间隔、GPU 成本或连续画面保证。关闭本轮创建的页面和服务器，保留构建身份、实际文件与失败记录。

## 复盘输入：事实、问题和候选分开

| 主题 | 已有事实 | 待复盘问题／假设 | 可讨论候选，尚未实施 |
| --- | --- | --- | --- |
| 重复采集与当前性 | [实验 80](../../experiments/80-hairline-export-diagnosis/REPORT.md)保留手动点击超时、自动 HTML 成功及原因 UNKNOWN；实验 82 的有界自动 A/B/A 成功，并单独检查请求、来源、当前性及恢复。 | 这些流程的哪些部分可复用？工具／流程分叉是否增加维护成本？不能把采集失败当成资产质量失败。 | 稳定的采集合同与适配层；保留有限窗口、失败和原始来源控制。 |
| 门禁成本 | [当前 CI](../../.github/workflows/ci.yml)含历史诊断、正常／`-O` 控制、源认证、实际 CPU 矩阵与原生／Wasm 检查，各门有不同证据边界。 | 哪些门抓到过真实失败？每门的冷／热时间、磁盘与重复编译成本是多少？当前没有统一成本测量，不能宣称可节省多少。 | 先做门禁清单及成本测量，再讨论组织方式；不删除断言、历史拒绝或合并后核验。 |
| 实际 CI 来源耦合 | [PR #101 首轮 CI](https://github.com/Derek-X-Wang/nvwa/actions/runs/39393535364)的 portable 在实验 72 历史来源门失败；随后完整本地 Python 步骤发现实验 73 的 309 文件冻结清单恰有本 PR 改动的四个 Rust 文件不匹配。 | 整文件源身份会让与数值合同无关的错误文案／测试帮助函数改动触发历史诊断拒绝，带来额外兼容维护；尚未量化成本或节省。 | 本轮仅处理 72／73 的完整来源认证兼容，保留不可变旧清单与拒绝测试；未开始基础设施重构。修复通过与最终 CI 以关联 PR 账本为准，不由本行预先声明。 |
| 实验与产品边界 | 实验 81 没有候选运行时；实验 82 的 B 是不写进 Work 的临时诊断；正式外观合同另有固定身份。 | 哪些实验适配可沉淀，哪些必须保持历史冻结？是否有读者把诊断成功误解为产品准入？ | 清楚标示产品能力、冻结实验和一次性诊断；不据此选择新肩部／发际方案。 |
| 依赖、缓存与构建重复 | 当前 CI 明确没有 cache restore/save；多个实验有独立 manifest／锁定依赖与准备步骤；本地曾复用源匹配的已有构建。 | 独立构建保护了哪些边界？依赖获取、准备和编译重复占比仍未测量，缓存收益与失效风险未知。 | 有界评估构建复用或缓存；先证明输入身份与隔离，不在本轮改 Cargo、CI 或缓存。 |
| 维护性 | #84 保留九项既有运行时 lint 告警，现有严格 Core／CLI 门仍保留。 | 先清理这一小块是否降低后续改动风险？它与更广重构的收益需要分别判断。 | 单独的 #84 维护任务；不借收口扩大为运行时或基础设施重写。 |

**PARTIAL — 本地有界收口与实际 Web／CLI 交换已验证，三张空场景及自动化偏差保留；阶段冻结／ready for retro 以关联 PR 发布门完成为条件。#86、质量 HOLD 与其他开放边界不变。**
