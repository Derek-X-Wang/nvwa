# 下半脸轮廓与独立 AI 创作

本阶段为显式十参数人物增加 `lower_face_squareness`：有限范围 `[0,1]`，默认0。
它使用原始 MPFB `chin-bones-incr` 位移，让下半脸轮廓更方正；不是下颌骨宽度测量，
也不保证嘴鼻、相邻高度或深度完全不变。旧八／九参数入口和 Work 不自动升级。
使用方式见[中文 CLI 说明](../../agents/cli-authoring.md#下半脸轮廓方正度显式十参数人物)。

三个新上下文的 AI 依次修改同一个人物，按不同的自然语言目标自行发现控制、选择值，
再看真实正常图片。没有提前给创作者参数答案。前两例首稿达标，未强行制造修订；
第三例看图后认为修长感不足，实际修订一次，创作者和独立视觉审查均接受。
审查先看正常图片，再核对字段与捕获身份。第二、三例的审查者已有前例经验，不能称为新鲜盲评。

| 案例 | 目标与实际结果 | 可编辑作品和真实命令 |
| --- | --- | --- |
| 1 | 下半脸更有力量、更方正，保留整体头宽及其他设置。首稿局部接受，0次修订。 | [原始人物](case1/baseline.nvwa.json)、[命令](case1/command.json)、[最终作品](case1/final.nvwa.json) |
| 2 | 保留有力下颌，面颊更柔和饱满，下巴仍清楚收束。首稿局部接受，0次修订。 | 输入为案例1最终作品；[命令](case2/command.json)、[最终作品](case2/final.nvwa.json) |
| 3 | 更清楚的修长头脸比例，同时保留柔和面颊、下颌转角和圆润收束的下巴。一次看图修订有可辨收益。 | 输入为案例2最终作品；[初稿命令](case3/first-draft-command.json)、[初稿](case3/first-draft.nvwa.json)、[修订命令](case3/revision-command.json)、[最终作品](case3/final.nvwa.json) |

## 正常图片

图片均为原始1280×720画面，没有裁切、标记或美化。固定姿态、0秒、灯光、画质、
人物素材与比较视角；正面和35度使用共同审阅相机副本，原始作品的舞台设置保持。
这些作品明确使用 `appearance:none`，因此没有请求皮肤纹理、眼球或头发插入物；
不能用它们证明这些外观的加载或质量，也不能把空眼眶或无头发误判为本次加载失败。

| 案例 | 修改前 | 最终结果 |
| --- | --- | --- |
| 1 | [正面](case1/before-front.png)／[35度](case1/before-quarter.png) | [正面](case1/final-front.png)／[35度](case1/final-quarter.png) |
| 2 | 复用案例1最终图片，审阅 Work 字节与对应捕获完全一致。 | [正面](case2/final-front.png)／[35度](case2/final-quarter.png) |
| 3 | [正面](case3/before-front.png)／[35度](case3/before-quarter.png) | [正面](case3/final-front.png)／[35度](case3/final-quarter.png) |

案例3的[初稿正面](case3/first-draft-front.png)和[初稿35度](case3/first-draft-quarter.png)
保留用于判断实际修订收益。最终收益是相对轮廓比例更清楚；不声称绝对长度增加。
侧前方冠顶高度差的具体原因没有单独建立，不将复合参数修改解释为单一宽度作用。

案例1／2使用带有未采用诊断原型的预览构建，Wasm SHA256为
`e85df6875b3127c82ad986609ae1051f74e7d9eb33f7325c0802d590def24bc4`，观察选项关闭。
案例3全部图片使用移除原型后的正常预览，Wasm SHA256为
`3ee0ac9cca01bffba046ee047143d8b2b5b7763d54b837dc84566d9fa060ef21`。
一个完全相同 Work 的正面控制在两版间 Work 与 PNG 字节均相同；这不是所有旧图片的最终构建证明。

## 用公开 CLI 重放

在仓库根目录运行，`nvwa-cli` 指向现有编译产物；输出放在独立临时目录。
以下命令保留真实版本、修订号和字段。最后的 `validate` 显式认证本地素材；
`apply` 和 `save` 本身只编辑、持久化作品元数据。

```sh
task_dir=$(mktemp -d "${TMPDIR:-/tmp}/nvwa-contour.XXXXXX")
nvwa-cli new-character-lower-contour assets "$task_dir/baseline.nvwa.json"
nvwa-cli describe-capabilities "$task_dir/baseline.nvwa.json"
nvwa-cli apply "$task_dir/baseline.nvwa.json" docs/evidence/b1-lower-contour/case1/command.json "$task_dir/case1.nvwa.json"
nvwa-cli apply "$task_dir/case1.nvwa.json" docs/evidence/b1-lower-contour/case2/command.json "$task_dir/case2.nvwa.json"
nvwa-cli apply "$task_dir/case2.nvwa.json" docs/evidence/b1-lower-contour/case3/first-draft-command.json "$task_dir/case3-first.nvwa.json"
nvwa-cli apply "$task_dir/case3-first.nvwa.json" docs/evidence/b1-lower-contour/case3/revision-command.json "$task_dir/case3-final.nvwa.json"
nvwa-cli validate "$task_dir/case3-final.nvwa.json" assets
```

## 已验证与保留的边界

VERIFIED — 默认体型的新控制端点及中间值共10张无纹理轮廓图；另有两张同时请求
既有short01皮肤／眼睛／头发的2秒手臂动作对照。三个创作案例分别通过正常图像判断和字段审计。
真实 Studio 新建、编辑、Undo／Redo、Reset、播放／暂停／归零、无效 Open 保留最后正常作品及画面，
以及正常 Web Save→CLI校验／修改／保存→正常文件选择器 Web Open／Save 已实际完成；最终读回逐字节一致。

NO-ADOPT — 一次投影实际上传体网格位移的辅助实验通过同画面开关等价及失败拒绝控制，
但辅助侧在看辅助前就已决定增加饱满度，没有证明新增事实改变了具体操作。
较受偏好的正常结果不能证明辅助导致改善。原型未纳入产品，实验及拒绝记录保留。

PARTIAL — 收益限已检查的默认体型、视角、姿态和目标；不证明全体型、连续动作、精细接触、
解剖独立性或整体人物美术质量。普通桌面 UI 按大版本节点延后。#133、#120、M2、#80、完整#79的HOLD，
#112原失败、#3阻塞、#4缺口与#49边界保持。正式 PR／main CI 和发布结果见[#136最终回执](https://github.com/Derek-X-Wang/nvwa/issues/136)。
