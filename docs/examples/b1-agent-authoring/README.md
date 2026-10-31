# Agent 用 CLI 编排一个 20 秒 B1 作品

本例对应 [#127](https://github.com/Derek-X-Wang/nvwa/issues/127)。Agent 通过现有离线 CLI 创建八参数 B1 Work，选择 short01 外观与舞台，编排五行动作，再修改第三行。这里的“创作”指参数选择与编排。两段四秒动作由 Nvwa 预先编写；本例不生成新动作。

## 运行

需要 Python 3、可执行的 `nvwa-cli` 和完整的文件系统 `assets` 根目录。无需新增依赖。下面从仓库根目录运行。三个参数分别是 CLI 路径、素材根目录、新输出目录：

```sh
python3 docs/examples/b1-agent-authoring/author.py \
  /absolute/path/to/nvwa-cli \
  /absolute/path/to/assets \
  /absolute/path/to/new-output-directory
```

输出目录必须不存在。脚本拒绝任何已有目录或文件，包括空目录；它不覆盖原作品。若中途失败，保留目录及收据供检查，换一个新目录重跑。输出包含两份可打开的作品：`first-saved.nvwa.json`（revision 4）与 `final-saved.nvwa.json`（revision 5）。同名的仓库文件是本次实际 CLI 运行的原字节副本。

## Agent 的执行步骤

1. 用 `new-character` 创建 Work，再对该文件调用 `describe-capabilities`。从实际响应读取 `character_id`、`document_revision`、参数范围、动作 ID、兼容外观及命令合同。脚本保存为 `capabilities.json`；不把各自独立的 discovery 示例直接当成批次。
2. 按发现的范围设置八个非默认参数。从 `compatible_sets` 选完整的 short01 外观对象，保留其身份与哈希。复制当前舞台后，修改背景、地板、相机与灯光。完整输入见 [author.commands.json](author.commands.json)。批次四条命令的 revision 依次为 0、1、2、3。
3. 用现有的 `b1_arm_rehearsal_v1` 与 `b1_knee_flex_v1` 编排五行，各四秒、速度 1、非循环。先 `apply`，再带显式素材根目录 `validate`，然后 `save` 并再次 `validate`。成功输出须为 exit 0，验证响应须含 `valid: true` 与 `asset_checked: true`。
4. 对刚保存的文件 `inspect`，读取该 Work 的实际 revision。`set_timeline` 替换整个列表，因此复制实际列表，只将第三行的动作改成 knee，再提交新命令 ID。完整输入见 [edit.command.json](edit.command.json)。再次 apply、validate、save、validate、inspect，确认 revision 5。
5. 如需画面或播放证据，在另一个已授权的 Web／Studio 会话中打开精确的保存文件。CLI 不控制运行中的 Studio。

| 时间 | 首次保存 | 修改后保存 |
| --- | --- | --- |
| 0–4 秒 | arm | arm |
| 4–8 秒 | knee | knee |
| 8–12 秒 | arm | knee |
| 12–16 秒 | knee | knee |
| 16–20 秒 | arm | arm |

八个参数值：`torso_length=0.25`、`jaw_drop=-0.20`、`head_width=0.15`、`nose_width=-0.15`、`mouth_width=0.20`、`chin_width=-0.25`、`neck_width=0.10`、`hip_width=0.20`。short01 的 skin／eyes／hair 全开。舞台背景为深蓝灰，相机方位 24°、距离 4.2；这些选择保存在 Work 中，不代表已做画面验收。

## Revision、重试与证据

`expected_revision` 对比本次调用载入的文件。每条成功且非重复的命令增加一次 revision；`save` 不增加。遇到 `revision_conflict`，先 inspect 实际输入，再重新考虑修改并构造请求。本例的负向调用用 revision 4 修改 revision 5，实际返回 exit 1：

```json
{"code":"revision_conflict","message":"expected revision 4, current revision is 5"}
```

输入及已有输出均保持原字节，详见 [拒绝收据](evidence/stale-revision-refusal.json)。Undo、Redo 与成功命令 ID 的去重只存在于同一次 `apply` 调用；不跨文件保存，不提供持久幂等或跨进程锁。若出现 `stdout_write`，输出可能已保存，重试前必须检查实际文件。完整合同见 [CLI 创作说明](../../agents/cli-authoring.md)。

[实际调用收据](evidence/calls.jsonl) 保留本次 12 次 CLI 调用的 stdout、stderr 与 exit code。只有 argv/cwd 中的机器路径改为 `$CLI`、`$ASSET_ROOT`、`$OUTPUT_DIR`；stdout/stderr 未改写。`stale.command.json` 是真实负向输入。重跑会在新目录生成含精确机器路径的原始收据。[验证汇总](evidence/verification.json) 记录两次新目录运行、作品与输入哈希、已有目录拒绝及单行修改对比。

CLI 使用已保留的验证构建，SHA-256 为 `3bdc412f87122aa92bc0507c091335d1e2d2db7eccf87312a48facfae36b4459`。基线为 `4d091aad0f234a3071c44ea493a1cab02e8c0ced`。本次将保留的 Web build receipt 中 10 个 CLI、13 个 core、112 个 assets 文件及 Cargo.toml／Cargo.lock 共 137 个输入与该 checkout 逐字节哈希比较，全部一致。完整清单见 [构建身份](evidence/build-identity.json)。这支持重用已有 CLI；本例没有重新编译。

VERIFIED — 两次各 12 个实际 CLI 调用 exit 0；两份 Work 与命令输入分别逐字节相同；已有目录拒绝保留全部文件；真实 stale revision 拒绝保留输入与已有输出。NOT-RUN — 本例未做 Web／桌面打开、播放、人体／衣物／动作质量验收或新构建；这些证据须单独取得。它不解除已有质量 HOLD。
