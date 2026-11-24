# 用同一人物制作游戏姿势参考、顶胯动作和前移动作

人物 A 的头宽为 +1，髋宽为 +0.7，躯干长度为 +0.4。人物 B 用于对照。先用正面看头宽和髋宽，再用侧面看躯干比例和屈膝。两种身形均可在同一机位比较伸手与单腿收回两个姿势。[姿势参考图和生成方法](poses/README.md)

## 改编一段参考动作

从本目录运行。把 `assets` 指向仓库的资源目录，输出使用自己的任务目录。以下命令用同一个人物 A 生成可分别交给下一个 Agent 的原版和改版。

```sh
assets=../../../assets
out=./output
mkdir -p "$out"
nvwa-cli apply ../edited-reference/baseline.nvwa.json motion/character-a.json "$out/hip-original.nvwa.json"
nvwa-cli apply "$out/hip-original.nvwa.json" motion/hip-accent.json "$out/hip-accent.nvwa.json"
nvwa-cli validate "$out/hip-accent.nvwa.json" "$assets"
nvwa-cli reference-pose "$out/hip-original.nvwa.json" 2.25
nvwa-cli reference-pose "$out/hip-accent.nvwa.json" 2.25
nvwa-cli save "$out/hip-accent.nvwa.json" "$out/reopened.nvwa.json"
cmp "$out/reopened.nvwa.json" "$out/hip-accent.nvwa.json"
```

创作要求是加强第二次向人物右侧顶胯，保持肩平、双脚支撑和整段节奏。独立操作者选择了 2.25 秒的重音。可在 2.127125 和 2.627625 秒查询修改区间的两端，并在区间内另选一个时间查询插值。Work 的总长为 4.004 秒。姿势查询中的骨盆位移使用父骨骼局部坐标，单位为米。

本例的运行时复查覆盖了 1.95–2.70 秒的 61 个正向采样点。以两肩附近固定表面点为标志，两版肩线倾角都约为 0.20°。修改版相对原版，同一时刻脚底标记点的额外水平移动，左脚不超过 0.23 厘米，右脚不超过 0.31 厘米。修改版在这段仍有轻微穿地，左右脚最低点约为 −0.33 和 −0.36 厘米。两版都在运行时播放至 4.004 秒并结束。以上为几何和播放测量，连续动作的自然度留待视觉审核。

动作源自 Fabiola Mastache 的《Drop con cadera》。参考段为约 0.50–4.50 秒的无声剪辑。此例据单机位参考制作关键姿势，并局部改编第二次顶胯。动作改编沿用 CC BY-SA 4.0。[来源与署名](https://commons.wikimedia.org/wiki/File:Drop_con_cadera.webm) · [许可](https://creativecommons.org/licenses/by-sa/4.0/)

## 从 A 点跑到 B 点

在本目录运行，可单独复现跑步作品。

```sh
assets=../../../assets
out=./output
mkdir -p "$out"
nvwa-cli new-character-running "$assets" "$out/running-base.nvwa.json"
nvwa-cli apply "$out/running-base.nvwa.json" motion/forward-run.json "$out/forward.nvwa.json"
nvwa-cli save "$out/forward.nvwa.json" "$out/forward-reopened.nvwa.json"
nvwa-cli validate "$out/forward-reopened.nvwa.json" "$assets"
```

跑步使用专用 Work 配置。命令保留人物 A 的八个身形参数、角色 ID 和比例，将跑步配置额外的两个参数保持为零。对本例的两份中立姿势，运行时读回了相同的骨架矩阵和逐顶点相同的身体、服装几何。这项结论只覆盖这里的参数和资源组合。

站在 A 点时以显示模型原点作为起点，沿场景 +Z 前进。2 秒时，身体和衣物原点都比起点前移 1 米，4 秒时前移 2 米。随后保持终点位置，5 秒时播放结束。该位移取自运行时的场景变换；顶胯例中的关节角度和骨盆局部位移另行查询。
