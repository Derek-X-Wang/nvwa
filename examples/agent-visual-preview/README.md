# 独立 AI 创作的两版作品

两份 Work 由新上下文 agent 实际创建和修改，图片来自第2秒真实 Web 渲染。
它先查询能力，制作20秒举臂／抬膝编排，再看全身图并按审核反馈只修改相机。

- `full-body.nvwa.json`：全身初稿。
- `face-review.nvwa.json`：同一人物、舞台和编排的脸部审阅镜头。
- `create-commands.json`、`camera-commands.json`：当次实际使用的命令批次；
  不是每个 Work 都可直接套用的通用模板。先发现当前能力、角色 ID 和 revision。

用现有 CLI `validate` 配合完整 `assets` 根目录校验，或在 Studio 中正常 Open。
使用[预览说明](../../docs/agents/visual-preview.md)取指定时间点的真实图像。
图片、字段差异、独立重放和明确限制见[验收记录](../../docs/evidence/agent-visual-feedback/README.md)。

这些动作是已有预制动作。实例不代表 AI 生成动作或现有质量 HOLD 解除。
