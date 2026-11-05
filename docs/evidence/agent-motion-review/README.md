# AI 自助审看动作试演：候选证据

当前为 **PARTIAL**，不是 Goal 完成或发布回执。两个独立创作者已自行用真实 Web 画面审看初稿；两例都没有提出有画面依据的创作修改。原定“至少一次有效看图修订获独立接受”的条件仍未满足，也没有获得豁免。是否修改该验收条件，需要人作明确决定。

| 案例 | 可编辑作品 | 正常原图 | 独立画面结论 | 创作修订 |
| --- | --- | --- | --- | ---: |
| [上肢—膝部—结束](case1/README.md) | 14秒、3段；final 与初稿字节相同 | 20张；两视角、10个时间 | 初稿局部接受 `ACCEPT_BOUNDED_INITIAL` | 0 |
| [慢速—通常节奏—收束](case2/README.md) | 16秒、3段；final 与初稿字节相同 | 24张；两视角、12个时间 | 初稿局部接受 `ACCEPT_BOUNDED_INITIAL` | 0 |

创作者实际检视了本例全部原图；整合会话没有代开正式创作预览。独立评审先检视原图并冻结画面判断，再完成字段／身份核查；两例均保留局部初稿接受。时间／视角标签及图中既有 UI 文字可见，因此不声称完全无元数据盲评。没有制作人为缺陷，也没有把改行标识、换相机或技术重开记成有效创作修订。[另4张功能重开原图](functional-reopen/README.md)单独保留，不属于第三个创作案例。

## AI 如何使用

先读[CLI 能力说明](../../CLI-SUPPORT.md)和[自助预览说明](../../agents/visual-preview.md)。用实际 Work 的 `describe-capabilities` 发现动作和命令字段。两例实际发现的目录均为已有四秒动作 `b1_arm_rehearsal_v1` 与 `b1_knee_flex_v1`；它们是预制动作，不是 AI 生成。

1. 通过普通 CLI 创建、编辑并保存原作品。保留原始人物、舞台和作品相机。
2. 通过普通 `set_stage` 创建两个相机副本；完整复制舞台，只改相机。固定视角和采样时点，包含受检交接的前后样本。
3. 用 `scripts/review-motion.py` 让命令自行启动已安装的 Chrome。检查退出码与终端 JSON，然后用图像工具打开实际 PNG；命令成功不代替看图。
4. 只有看见具体问题时，才在现有动作选择、顺序、重复、时长或停留能力内另存修改。按相同视角、时点和画质复看，保留两版作品和原图。没有具体问题时如实报告，不为完成条件制造修改。

下面从仓库根目录运行。`CLI` 指向已有源码构建的 CLI；`CHROME` 须预先设为本机已安装 Chrome 的可执行文件。预览适配器已在 `dist/preview` 构建，资产根目录为 `assets`。本轮没有下载浏览器或依赖。支持路径是 macOS、Python 3.12+ 和实际可用的 Chrome WebGPU；不保证任意 agent 的任意浏览器环境。

```sh
CLI=target/debug/nvwa-cli
python3.12 -B scripts/review-motion.py \
  --chrome "$CHROME" --cli "$CLI" \
  --work docs/evidence/agent-motion-review/case1/initial.nvwa.json \
  --view front=docs/evidence/agent-motion-review/case1/front.nvwa.json \
  --view side=docs/evidence/agent-motion-review/case1/side.nvwa.json \
  --seconds 0 --seconds 2 --seconds 3.8 --seconds 4 --seconds 4.2 \
  --seconds 6.5 --seconds 8.8 --seconds 9.2 --seconds 11 --seconds 14 \
  --output motion-review-case1-new --preview-root dist/preview --assets assets
```

输出目录必须是新目录。命令按视角顺序、再按时间顺序捕获真实画布。每帧使用独占浏览器进程与临时配置；失败、超时、占用端口和无法证明清理完成均返回失败。详细边界见[预览说明](../../agents/visual-preview.md)。案例2使用其[捕获清单](case2/capture-manifest.json)中的相同命名、Work 和有序时间列表。两份捕获清单均列出实际 `f32` 时间、原图哈希、相机和实际渲染 Work 身份。

## 重放实际创作命令

以下只重放已有语义命令与保存。它不渲染，不产生新的看图或修订证据。两例的起始 Work、命令 JSON 和最终规范化 Work 都保留原始字节。每个新输出目录只运行一次；`cmp` 检查结果是否与公开文件逐字节相同。

```sh
set -e
CLI=target/debug/nvwa-cli
CASE=docs/evidence/agent-motion-review/case1
OUT=motion-replay-case1-new
mkdir "$OUT"
"$CLI" new-b1-motion assets "$OUT/seed.nvwa.json"
"$CLI" describe-capabilities "$OUT/seed.nvwa.json"
"$CLI" apply "$OUT/seed.nvwa.json" "$CASE/initial-commands.json" "$OUT/authored.nvwa.json"
"$CLI" save "$OUT/authored.nvwa.json" "$OUT/initial.nvwa.json"
"$CLI" apply "$OUT/initial.nvwa.json" "$CASE/front-command.json" "$OUT/front.nvwa.json"
"$CLI" apply "$OUT/initial.nvwa.json" "$CASE/side-command.json" "$OUT/side.nvwa.json"
"$CLI" save "$OUT/initial.nvwa.json" "$OUT/final.nvwa.json"
"$CLI" validate "$OUT/initial.nvwa.json" assets
cmp "$OUT/seed.nvwa.json" "$CASE/seed.nvwa.json"
cmp "$OUT/initial.nvwa.json" "$CASE/initial.nvwa.json"
cmp "$OUT/front.nvwa.json" "$CASE/front.nvwa.json"
cmp "$OUT/side.nvwa.json" "$CASE/side.nvwa.json"
cmp "$OUT/final.nvwa.json" "$CASE/final.nvwa.json"
```

案例2使用相同的实际调用顺序，将 `CASE` 改为 `docs/evidence/agent-motion-review/case2`，并选择另一新 `OUT`。两例的 `final.nvwa.json` 均与初稿字节相同，只是普通保存，不是修订版。命令重放不会把初稿变成修订。

## 功能证据与保留边界

新包装器修复后源码复审为 `READY`，其含义是允许进入有界实际浏览器技术验证；不是完整产品或创作接受。20项新增流程／生命周期测试在 Python 3.12 普通模式及 Python 3.14 `-O` 各通过一次；原13项预览测试在普通与优化模式通过。修复后的实际双视角四帧技术验证通过，耗时31.715秒。清理轨迹中五次 `signal0` 权限拒绝被记为未知，随后均由实际 `ESRCH` 证明进程组不存在；不推断操作系统拒绝的根因。原清理取消失败、首次真实浏览器清理失败及一次16项测试中1项失败保留，未改写为通过。

普通 Studio 的真实 Open／Save 和 Web→CLI→Web 文件交换已通过。首次 Web 保存与案例1原作品逐字节相同。功能交换只把首行 `id` 改为 `exchange-row-1`，revision 从2变为3；CLI 保存与 Web 再保存逐字节相同，SHA-256 为 `a4873feb361406f8ea4d8b86961b6a8e0c30acf3cc3ff013d2d96ef7eb9374cd`。人物、舞台、外观及全部动作时序保持不变。这个标识修改没有创作收益，不计入有效修订。

该交换复用了普通 Studio `--lib` 构建（Wasm SHA-256 `ca19eb09411b9c452c859833a0bbb703f7fda0b68374213c355b7d179b43004f`）。宽范围旧构建回执的459项中454项相同，5项独立预览来源有差别：`crates/nvwa-studio/examples/nvwa-preview.rs`、`scripts/contour-observation.py`、`scripts/preview.py`、`scripts/test-preview.py`、`web/preview.html`；实际 Studio 库输入相同，不声称全部459项相同。动作预览另复用了430项来源全部匹配的适配器（Wasm SHA-256 `3ee0ac9cca01bffba046ee047143d8b2b5b7763d54b837dc84566d9fa060ef21`）。本轮没有修改渲染器、资产、Work schema、CI 或既有门禁。

PARTIAL — 两例自助初次看图、独立局部画面及身份核查、实际文件交换、另存后的同条件功能复看已有证据；有效看图修订条件仍未满足。44张创作初稿图和4张独立功能重开图分开计数。新 Rust／Wasm 构建和本候选 CI 尚为 NOT-RUN；没有发布、合并或自然 main 验证回执。静态图不证明整段流畅；[旧人物／衣物／M2 质量 HOLD 和其他阻塞](../../ROADMAP.md)保留。
