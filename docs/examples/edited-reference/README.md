# 在已编辑人物上局部改编参考动作

这个实例从已经过人工复看的 4.004 秒双脚支撑动作出发。先加宽人物头部，再减小右前臂在 1.5015 秒的局部旋转幅度。两次编辑各另存一个 Work，可以分别在 Studio 打开比较。

在本目录执行下列命令。使用当前仓库的 assets 目录校验作品。将 out 设为自己的任务输出目录。

```sh
out=./output
mkdir -p "$out"
nvwa-cli apply baseline.nvwa.json character-command.json "$out/character.nvwa.json"
nvwa-cli apply "$out/character.nvwa.json" forearm-command.json "$out/forearm.nvwa.json"
nvwa-cli reference-pose "$out/character.nvwa.json" 1.5015
nvwa-cli reference-pose "$out/forearm.nvwa.json" 1.5015
nvwa-cli save "$out/forearm.nvwa.json" "$out/reopened.nvwa.json"
nvwa-cli validate "$out/reopened.nvwa.json" ../../../assets
nvwa-cli reference-pose "$out/reopened.nvwa.json" 1.5015
```

第一条编辑把 `head_width` 从 0 调到 1。第二条只修改 `lowerarm_r` 在 1.5015 秒的关键帧，从 −56° 改为 −32°。相邻关键帧位于 1.376375 和 1.626625 秒。可以在两个边界及中间点重复同一条姿势查询，观察局部插值。用 Studio 的「打开」选择另存的文件，以正常速度播到结尾，再保存并在新会话打开。

在 `fec9ea2` 上重放时，人物编辑后的 Work 的 SHA-256 为 `67c958650a951463d3e798148e774b196d5f7a81041a54f8a3a0db2da5a86fe2`。右前臂编辑后，CLI 另存副本的 SHA-256 为 `3315db9781fb849a8c687e2b11bc81802e4474ae5ec1217829a4628041ebdc39`。这些值可用来核对浏览器下载的实际文件。

参考视频为 Fabiola Mastache 的《Drop con cadera》。创作使用约 0.50–4.50 秒的无声剪辑，单机位估计姿势。这里提供可编辑的动作数据；此动作改编沿用 CC BY-SA 4.0。[原视频与署名](https://commons.wikimedia.org/wiki/File:Drop_con_cadera.webm) · [许可](https://creativecommons.org/licenses/by-sa/4.0/)
