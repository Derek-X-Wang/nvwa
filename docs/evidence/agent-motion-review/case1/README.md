# case1：上肢—膝部—结束

初稿获独立局部画面接受。初稿与 final 完整字节一致；实际创作修订为0次，没有修订收益声明。2026-11-04，用户针对本 Goal 明确“接受合格首稿”；据此本例本地验收完成，发布仍待正常 PR 完整 CI 和自然 main 验证。

原始要求：请为我制作一段人物动作试演。让观众能清楚看见上半身动作和膝部动作，有明确先后与结束，节奏紧凑但不要急促。保留你选择的人物形象和舞台；不要靠换脸、换衣服、特殊灯光或候选之间变镜头来让修改显得更好。

可编辑作品：[初稿](initial.nvwa.json)、[final（与初稿相同）](final.nvwa.json)；[起始 Work](seed.nvwa.json)、[正面副本](front.nvwa.json)、[侧面副本](side.nvwa.json)。正侧副本只允许相机与 revision 不同，原作品相机保留。实际命令为[创作批次](initial-commands.json)、[正面命令](front-command.json)和[侧面命令](side-command.json)。

## 编排与画面

以下字段来自保存的 Work，时长为14秒，共3段。它们与画面结论分开。

| 行 | 已有动作 | 开始秒 | 持续秒 | source speed |
| --- | --- | ---: | ---: | ---: |
| opening-arm | b1_arm_rehearsal_v1 | 0.0 | 4.0 | 1.0 |
| central-knee | b1_knee_flex_v1 | 4.0 | 5.0 | 0.8 |
| closing-arm-hold | b1_arm_rehearsal_v1 | 9.0 | 5.0 | 1.0 |

创作者自行打开并检视了全部20张正常原图；整合会话未代开。独立评审也检视了全部原图，先冻结画面判断，再完成字段／身份核查。举臂、膝部弯曲、再次举臂及最终直立姿态在已采样画面中可读。侧面有助于辨认弯膝与抬起的脚。没有提出有画面依据的修改；没有为了制造迭代而修改初稿。

下表按请求时间排列；每张原图保留原始 PNG 字节。相机值、实际单精度时间、Work 身份及图片哈希见[捕获清单](capture-manifest.json)。请求小数与实际 `f32` 表示的差别不是静默夹取时间。

| 请求秒 | 实际采样秒 | 正面 | 侧面 |
| ---: | ---: | --- | --- |
| 0 | 0 | [原图 00](frames/00-front.png) | [原图 10](frames/10-side.png) |
| 2 | 2 | [原图 01](frames/01-front.png) | [原图 11](frames/11-side.png) |
| 3.8 | 3.799999952316284 | [原图 02](frames/02-front.png) | [原图 12](frames/12-side.png) |
| 4 | 4 | [原图 03](frames/03-front.png) | [原图 13](frames/13-side.png) |
| 4.2 | 4.199999809265137 | [原图 04](frames/04-front.png) | [原图 14](frames/14-side.png) |
| 6.5 | 6.5 | [原图 05](frames/05-front.png) | [原图 15](frames/15-side.png) |
| 8.8 | 8.800000190734863 | [原图 06](frames/06-front.png) | [原图 16](frames/16-side.png) |
| 9.2 | 9.199999809265137 | [原图 07](frames/07-front.png) | [原图 17](frames/17-side.png) |
| 11 | 11 | [原图 08](frames/08-front.png) | [原图 18](frames/18-side.png) |
| 14 | 14 | [原图 09](frames/09-front.png) | [原图 19](frames/19-side.png) |

## 限制

这是同一初稿的多个静态样本，不是修订前后对照。独立结论仅覆盖已见姿态、样本顺序和受检交接；静态图不证明整段连续流畅、自然程度、完整节奏或所有未采样时刻。预览图中的既有 UI 文字不是姿态的证明。人物、衣物、接触、M2 和其他[原有 HOLD](../../../ROADMAP.md)均保留。

运行方式见[中文说明与重放步骤](../README.md)。

VERIFIED — 本例20张真实原图、可编辑初稿和实际命令已保留；按2026-11-04 本 Goal 的合格首稿调整完成本地验收，实际创作修订0次。发布 PARTIAL，待正常 PR 完整 CI 和自然 main 验证。
