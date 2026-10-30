# 日常验收：Web 与 CLI 优先

2026-10-19，按 Derek 的明确要求生效。Nvwa 仍正式支持桌面、Web、CLI 三种入口；调整的是验收频率，不是产品范围。

## 普通变更

按变更选择相关的共享核心测试、CLI 实际调用和 Web 实际操作。Web 主要验证人物画面与交互，CLI 主要验证无窗口创作、校验、保存和数据交换。不要求每个变更都运行与其无关的入口或全套人工检查。

普通功能不再以同步完成桌面窗口、截图、拖动、输入法或缩放验收作为逐次合并的前置条件。Mac 锁屏、用户切换应用或桌面采集工具失败时，记录缺口，继续可独立验证的 Web／CLI 工作；不反复要求用户解锁或保持应用在前台。

保留现有自动测试、数据及素材校验、原生／Wasm 编译和 CI 门禁。独立审查与适用 CI 通过后，按既有授权合并并验证 main。不得因调整人工验收频率而删除失败测试、放宽断言、吞掉错误或把 mock 当成实际运行。

## 完整 portable 检查

本地完整 portable 入口与 CI 的 portable job 共用同一命令目录：

```sh
python3 -B scripts/check-portable.py all
```

此入口按 CI 顺序运行全部 portable 组，包括实验 72／73 的真实控制、眼睛／头发控制、normal／`-O` 模式及原有 Node 缺失失败检查。需要 Bash、Git、Python 3.12 或更新版本、Node、仓库固定的 Rust 工具链及 Cargo 依赖。受支持的 Python 必须在 `PATH` 中以 `python3` 提供；嵌套命令仍调用 `python3`，只用绝对路径启动外层运行器并不足够。CLI 分发控制需要安全的 `tarfile.extractall(filter="data")` 接口。原有 fetch 与编译命令仍会运行。按资源政策安排完整执行。分组、前置条件、临时目录与环境说明见 [scripts/README.md](../../scripts/README.md)。

运行器从自身位置确定 checkout，打印调用目录、完整 HEAD、分支／detached 状态及 dirty 状态，然后在该 checkout 运行检查。它不切换或更新 checkout。身份信息只是当前本地观察，不认证忽略的缓存、工具版本或远端状态。dirty 与 detached 本身不是失败。

旧 `experiments/27-ci-baseline/check.sh portable` 仍只运行原有的核心／CLI 组，不能代替完整入口。`scripts/check-b1-work.sh` 保持原有的 native／Web 打包检查范围。portable 通过不替代既有 native、Wasm、源运行时或实际 Web／桌面验收。

## 需要桌面专项验证的变更

涉及桌面专属行为或平台差异时，仍验证受影响的原生路径。例如：

- 本地保存路径、覆盖确认、原子写入、权限和文件对话框。
- 原生输入法、剪贴板、快捷键、焦点、窗口与 DPI 行为。
- 桌面打包、签名、安装和原生专属渲染问题。

已知的原生回归、数据损坏或共享合同失败必须处理，不能仅凭 Web 通过就忽略。无法验证时，明确记录风险及受影响范围；需要用户实机操作时再提出具体、最小的请求。

## B1 自动检查的主机范围

2026-10-22，Derek 接受仅将 `b1-source-regression` 日常作业迁移到 Ubuntu 24.04。原 23 条命令、全部断言、十个 Wasm target、失败传播与 60 分钟预算保留，新增九条精确 locked dependency fetch。其他 Mac 作业、缓存安全条件、依赖和频率保持原样。

这会减少每次 PR/main 对 57/58 独立依赖图的 Mac SDK、arm64 编译／链接、sampled 与 viewer 测试、viewer build/check 和实际无窗口执行证明，以及十个 Wasm target 的 Mac 编译主机证明。保留的产品 workspace Mac 作业不覆盖这些独立图。

在既有较大版本或发布节点执行[完整 B1 Mac 命令清单](b1-macos-milestone.md)，保留相应 Mac 证据及失败控制。本次不新增周期作业或改变其他 Mac 作业频率。此项是明确接受的自动检查主机范围变更，日常桌面画面验收延后本身不授权减少其他自动测试。

## 原生 producer 作业预算例外

2026-10-29，仅将 `native-and-wasm` 整个作业的预算从 60 分钟提高到 75 分钟。
此前完整正式作业达到 60 分钟上限；同一 source 的独立 [Mac 诊断运行](https://github.com/Derek-X-Wang/nvwa/actions/runs/40882014685)
已完成完整 matrix（8 分 18 秒）和 normal／`-O` 的实际 frame 衣物控制。mutation 步骤
保持 12 分钟，完整 matrix 步骤保持 20 分钟；所有命令、断言、素材、依赖、
单 worker、runner、cache 规则和运行频率不变。portable 保持 20 分钟，Linux B1
与未启用的 optional warm 作业保持 60 分钟，cache action 保持 4 分钟。

三个独立合同先验证当前 producer 75／warm 60，再只将 producer 的 cap 与对应
matrix 注释还原为历史 60 分钟字节，继续验证原有整份 workflow 与命令哈希。
历史取消结果与全部负向控制保留。此例外不改 B1 的 Mac 版本节点政策，不代表
性能改善或保证完成；新身份仍须通过完整正式 CI。若 75 分钟仍失败或超时，
保留证据和 release HOLD，不自动再次加时。

## Portable eye/hair 步骤预算例外

2026-10-29，仅将具名 eye/hair/character-parameter 步骤从 3 分钟调整到
5 分钟，整个 portable 作业仍为 20 分钟。此前同一命令曾完整通过，随后两次
在原 180 秒步骤上限取消。此调整是有限的步骤分配，不保证新步骤或整个作业完成。
authenticated-source 保持 3 分钟、offline-motion 保持 6 分钟、frozen-upper-arm
保持 5 分钟；native75、其他所有作业／步骤上限和 cache 规则不变。

四个独立合同验证具名步骤的位置、唯一性和原命令，再只还原 eye5 为历史 eye3，
保留原有断言和哈希。全部 48 个 run body、catalog 顺序／用例、normal／`-O`、
source admission 与既有 HOLD 均保留。仍须通过新身份的完整正式 PR／main CI；
若 eye5 或 portable20 再次超时，保留 release HOLD，停止此路径的继续加时与
无变化重跑，不自动拆作业或删减用例。

## 大版本节点的桌面回归

下一个较大可玩版本或发布节点，集中核验该版本的桌面启动、人物及连续动作、编辑与撤销／重做、保存／重载、与 Web／CLI 的作品交换、错误恢复，以及相关输入与窗口行为。具体矩阵随版本确定；当前不另加每个小变更的人工桌面门禁。

| 当前延后项 | 后续处理 |
| --- | --- |
| [#79](https://github.com/Derek-X-Wang/nvwa/issues/79) 发际 A/B 的八组原生配对画面 | 保留已有 Web、CPU 与失败证据，在桌面集中回归时补；缺图本身不阻塞普通 Web／CLI 推进 |
| [#3](https://github.com/Derek-X-Wang/nvwa/issues/3) 原始缩放复现 | 继续保持阻塞，等原始复现条件；普通回归不能替代它 |
| [#4](https://github.com/Derek-X-Wang/nvwa/issues/4) 性能测量缺口 | 原缺口继续保留；功能验收不能替代首帧、完全冷启动或 GPU／内存测量 |

## 证据与质量边界

分开记录编译、实际启动、功能、画面和性能。延后的桌面检查写为 `NOT-RUN（按策略延后）`，说明覆盖范围；不能从 Web、CLI 或 CI 推断桌面画面已通过。若任务结论依赖仍未验证的桌面专属行为，整体结论保持 `PARTIAL`。

此约定替代旧任务书中日常双端同步验收的要求。历史报告、失败、哈希和实验结果原样保留，不改写为通过。人物审美与动作质量仍按其实际证据决定：#79 保留 A。早期 fringe-B 的额头／眼睛遮挡属于旧候选；[实验 82](../../experiments/82-hairline-aba/RESULTS.md)的当前 `BLocalAlpha` 是另一候选，在已测 source0 中未见新增遮挡，但实际发际改善不足，结论为 INCONCLUSIVE / NO-ADOPT，不扩大采集。完整发际／眼睑、#80 衣物与 M2 动作质量的 HOLD 不因验收频率变化或阶段冻结而解除。

## B1 动作编排的 eye8 明确例外

2026-10-29，Derek 明确批准“批准仅5→8分钟修正（推荐）”。此新决定只将
具名 eye/hair/character-parameter 步骤从5分钟改为8分钟，覆盖上文 eye5
失败后停止自动加时的规则；保留该历史规则与失败，不将其改写为通过。
实际 [40941068061](https://github.com/Derek-X-Wang/nvwa/actions/runs/40941068061)
和 [40958552457](https://github.com/Derek-X-Wang/nvwa/actions/runs/40958552457)
均已输出全部20次 suite 的 OK，随后步骤超时。第二次包含 `7ca5ab0` 的有界
测试初始化优化；该局部节省没有保证 hosted 步骤完成。

portable 整个作业仍为20分钟，native75、B1/optional-warm60、auth3、offline6、
upper-arm5、cache action4及所有其他设置保持不变。四个独立消费者先验证唯一
具名步骤、原命令和 exact8，再只将该步骤8还原为历史3，继续原有断言与哈希。
保留全部旧负向控制，增加 stale5、非整数／字符串／表达式8及错误步骤的拒绝。
全部48个 run body、catalog顺序／用例、normal／`-O`、来源309及各上下文／fixture、
运行时、素材、依赖、缓存行为和既有 HOLD 不变。

这只是步骤预算分配，不是运行时提速，也不保证8分钟或整个20分钟作业完成。
旧编译与实际 Web/CLI 验收仍属于 `30aa99e`；本次 policy/docs 提交不是新的编译
或画面验收。旧 Web build receipt 的3个非运行时 policy/docs 输入随本次改变，
其余269个输入保持原字节。仍须通过新的完整正式 PR／main CI。若 eye8 或
portable20 再次失败或超时，触发 critical STOP；不继续加时、不拆作业、不删用例。
