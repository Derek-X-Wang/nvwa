# M2：同帧骨架对照与质量 HOLD 排查

**桌面与 Web 的七帧骨架对照通过；动作质量继续 HOLD。**

本轮复用 44 的原始动作、47 的既有标定和 48 的相同 Work/GLB。
计算只使用已有模型输出；角色与导出动作保持原字节，没有新增模型或工具下载。

| 问题 | 实际结果 | 证据 |
| --- | --- | --- |
| 两端是否播放了预期骨架？ | 七个精确关键帧、24 个 GLB 节点、9 个实际皮肤实例均通过。局部变换与离线结果一致，世界矩阵最大分量误差约 `1.76e-7`。 | [实际运行记录](REPORT.md)、[原生采样](probe/results/native.json)、[Web 采样](probe/results/web.json) |
| 相交是否已存在于导出数据？ | 按实际权重重建的离线表面，在七帧都有右臂/躯干严格三角形相交。该指标有明确范围，不是完整穿模或解剖验收。 | [离线方法与边界](offline/README.md) |
| 为什么部分上臂向内折？ | 现有 T→A 中立姿势对应的约 `45.7°` 差异，可解释这七帧的上臂方向变化。这是既定策略的效果；没有证明它是全部画面问题的唯一原因。 | [方向归因与复现](attribution/README.md) |
| 是否已改善动作？ | 尚未实施替代中立策略，也未验证改善效果。 | 质量保持 HOLD；#12/M2 开放 |

原生和 Web 画面分别保留在 [原生末帧](probe/results/native-canvas.png)和
[Web 末帧](probe/results/web-canvas.png)。两张图的显示尺寸不同，不能当作像素一致性测试。
骨骼、绑定和 CPU 表面重建的证据不等于 GPU 变形顶点回读。

从仓库根目录执行短时离线检查，不启动渲染器或模型：

```sh
python3 -B experiments/49-runtime-pose-parity/offline/test_evaluator.py
python3 -B -O experiments/49-runtime-pose-parity/offline/test_evaluator.py
python3 -B experiments/49-runtime-pose-parity/offline/compare.py experiments/49-runtime-pose-parity/probe/results/native.json
python3 -B experiments/49-runtime-pose-parity/offline/compare.py experiments/49-runtime-pose-parity/probe/results/web.json
python3 -B experiments/49-runtime-pose-parity/verify_native_failure.py
```

重新采集需另行构建并启动[隔离诊断程序](probe/README.md)。CI 只复核留存采样、运行控制测试并编译两个目标，不在 hosted runner 上重新执行 GPU 骨架采集。

其余实际关键帧、关键帧之间的插值、GPU 顶点回读、官方 decoder 一致性、完整动作语义/解剖质量和替代策略的实际效果均未验证。
#3 保持阻塞，#4 保留测量缺口。[#49 一页中文试用说明](../../docs/m12-unassisted-trial/PARTICIPANT-BRIEF.md)是独立文档改进，没有开始新真人试用。
