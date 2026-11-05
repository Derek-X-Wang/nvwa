# 功能对照：改标识后重开

这是案例1的文件身份／重开验证，不是第三个创作案例，也不是有效看图修订。

普通 Web→CLI→Web 交换所得的[读回 Work](web-readback.nvwa.json)为 revision3；它只改变原作品首行标识。[另一次实际 CLI 命令](row-label-command.json)再把该标识改为 `functional-reopen-opening-arm`，得到 revision4 的[重开 Work](edited-work.nvwa.json)。人物、外观、舞台、全部动作选择和时序保持不变。其 SHA-256 为 `a550c3a5f16f613cdb25aa248c4114597053fd9f67b7218343e0c8b461c8dd08`。

普通 CLI 创建了[正面副本](front.nvwa.json)和[侧面副本](side.nvwa.json)，然后独立执行者再次自行运行预览并检视全部4张新原图。每帧实际运行时报告新的 Work 哈希及 revision5；每张 PNG 又与初稿相同视角、相同时点的 PNG 逐字节相同。这与仅修改标识相符，支持正确文件重开，不支持创作收益。

| 请求秒／实际秒 | 正面新原图 | 侧面新原图 |
| ---: | --- | --- |
| 2／2 | [00](frames/00-front.png) | [02](frames/02-side.png) |
| 6.5／6.5 | [01](frames/01-front.png) | [03](frames/03-side.png) |

实际身份、哈希和对应初稿图片见[清单](capture-manifest.json)。实际命令：[首次交换标识](exchange-command.json)、[再次重开标识](row-label-command.json)、[正面相机](front-command.json)、[侧面相机](side-command.json)。清单中的图片均来自新捕获，没有用旧图替代新图。

功能命令可从仓库根目录重放；它不产生新的视觉证据：

```sh
set -e
CLI=target/debug/nvwa-cli
CASE=docs/evidence/agent-motion-review
OUT=motion-functional-replay-new
mkdir "$OUT"
"$CLI" apply "$CASE/case1/final.nvwa.json" "$CASE/functional-reopen/exchange-command.json" "$OUT/web-readback.nvwa.json"
"$CLI" apply "$OUT/web-readback.nvwa.json" "$CASE/functional-reopen/row-label-command.json" "$OUT/edited-work.nvwa.json"
"$CLI" apply "$OUT/edited-work.nvwa.json" "$CASE/functional-reopen/front-command.json" "$OUT/front.nvwa.json"
"$CLI" apply "$OUT/edited-work.nvwa.json" "$CASE/functional-reopen/side-command.json" "$OUT/side.nvwa.json"
"$CLI" validate "$OUT/edited-work.nvwa.json" assets
cmp "$OUT/web-readback.nvwa.json" "$CASE/functional-reopen/web-readback.nvwa.json"
cmp "$OUT/edited-work.nvwa.json" "$CASE/functional-reopen/edited-work.nvwa.json"
cmp "$OUT/front.nvwa.json" "$CASE/functional-reopen/front.nvwa.json"
cmp "$OUT/side.nvwa.json" "$CASE/functional-reopen/side.nvwa.json"
```

VERIFIED — 4张新捕获与新文件身份对应，且图像字节与相同条件初稿一致；0创作修订，0可见收益。完整动作质量与[总 Goal 状态](../README.md)不由此升级。
