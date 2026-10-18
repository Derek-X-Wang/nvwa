# B1附件离线拟合小实验63

**结论：两件附件都算通；仅为实际cage/骨骼上的离线拟合与峰值LBS，不是运行时或外观准入。**

输入为本轮实际r4原生torso−1/0/+1、jaw0，arm/knee source2的六份完整snapshot。输出12份附件结果。无下载、依赖、编译、Blender、GPU、桌面或生产文件修改。

## 实际计算与控制

- 每帧body22077个render顶点恢复完整19158 source cage，域0..19157；2919个重复render条目逐source rest位置精确一致，两个动作同torso的完整cage精确相同。snapshot不含UV坐标，不能据此称当前body UV绑定已验。附件OBJ按face-corner(v,vt)保留UV接缝，原UV与一次V翻转分别记录，不按source ID唯一赋UV。
- 读取当前vendored Humentity `shape_mesh_from_helpers_mhclo`、`get_offset_scale_mhclo`及adapter `full_proxy_influences`/`PreparedSkin`规则。原附件OBJ坐标、MHCLO offset/reference长度均×0.1转米，无轴交换；有序helper轴向分量差不取绝对值。signed源系数按原规则归一化，不夹负数。
- 每个骨骼汇总signed helper贡献后，只保留严格正的最终聚合，全部归一化；不top4，不阈值裁剪。实际53骨骼skin矩阵执行LBS。结果model-local→实际body display_transform只一次；不再叠乘model_to_world。
- 先用已准入运动服逐帧复现相同fit/weight/LBS路径：最大静置分量误差 1.09593036e-07m，最大normalized权重L1 7.26495248e-08，最大实际上传位置误差 1.72386626e-07m。均通过原有1e−5算术guard，不是为新附件设质量阈值。

## 附件摘要

| 附件 | source/UV/render(v,vt) | 负源系数 | 正影响最少–最多 | >4影响顶点 | 非head权重>1%顶点 |
|---|---|---:|---|---:|---:|
| eyes | 96/96/96 | 0 | 1–1 | 0 | 0 |
| hair | 865/991/991 | 42 | 1–5 | 2 | 242 |

眼睛96顶点原始权重实际全部head=1；这是源数据结果，没有硬编码成head。头发保留42个负源系数，2个负的最终bone aggregate按现行规则舍去；865顶点中242个具有>1%非head权重，2个顶点保留5影响，不能替换为刚性头帽。六帧的归一化权重摘要哈希完全相同。

三种torso下实际stage-space峰值Y范围如下；完整XYZ rest/posed/model/stage bounds在RESULTS.json，原始数组与完整权重在忽略的.work/final/meshes/。

| Torso | 动作 | 眼睛Y min–max(m) | 头发Y min–max(m) |
|---|---|---|---|
| -1 | b1_arm_rehearsal_v1 | 1.488259962–1.515889932 | 1.420865853–1.625661767 |
| -1 | b1_knee_flex_v1 | 1.488259962–1.515889932 | 1.420865853–1.625661767 |
| +0 | b1_arm_rehearsal_v1 | 1.531359900–1.558989870 | 1.463965879–1.668761704 |
| +0 | b1_knee_flex_v1 | 1.531359900–1.558989870 | 1.463965879–1.668761704 |
| +1 | b1_arm_rehearsal_v1 | 1.634159965–1.661789935 | 1.566765922–1.771561769 |
| +1 | b1_knee_flex_v1 | 1.634159965–1.661789935 | 1.566765922–1.771561769 |

这两动作主要改变手臂/小腿，head链没有专门动作；眼睛相对rest的最大分量位移约0.000289mm，头发约0.004324mm。接近静置并不证明头发是刚性帽，也不证明自然动态、贴头、眼睑接触或任意动作适用。

Alpha复用实验62经实际解码的固定manifest，且重新核对全部已准备source/image字节与manifest SHA。眼睛RGBA1024²：alpha0=13238，partial=44；头发RGBA2048²：alpha0=1745154，partial=562370。没有选定mask/blend策略或渲染验证。

## 复现

仅使用已有显式本地captures目录；output必须新建，并放在本实验已忽略的.work/内。脚本不导入私有代码，不查找/下载新数据。

```sh
python3 -B experiments/63-b1-accessory-fit/test_controls.py
python3 -B -O experiments/63-b1-accessory-fit/test_controls.py
python3 -B experiments/63-b1-accessory-fit/fit.py \
  --captures "$ACTUAL_R4_NATIVE_CAPTURES" \
  --output experiments/63-b1-accessory-fit/.work/NEW_RUN
```

实际最终运行：.work/final/，六帧12附件，8测试正常/−O均PASS。输入六份raw capture的SHA/size/request/revision/generation/sample均在RESULTS.json；当前脚本/规则/资产来源SHA也记录其中。网格gzip固定mtime0，保持可复现字节。

控制覆盖错/缺cage ID、重复source不一致、错MHCLO helper域、无效/零和/非有限系数、无效scale、未声明新delete mask、signed最终聚合与非正舍弃、完整5影响LBS、非法权重/关节ID/重复关节/不归一化、一次placement、缺/错OBJ/UV及UV接缝。

失败记录保留：run1最初拒绝已准入garment的既有delete_verts段；修正仅允许在garment复现控制中记录该已存在mask，未应用/修改mask，accessory新mask仍拒绝。初次synthetic测试对0.2浮点求和过度要求bit-exact，改为binary-exact五权重fixture；未放宽实际fit容差。不是附件调参或几何修复。

## 未解决与停止边界

- 无独立MPFB/Blender oracle；这是基于当前规则、实际cage与实际skin矩阵的f64离线实现，并以原衣物复现作控制。不能把服装控制等同于附件独立参考。
- 没有当前Humentity附件运行时构造、Bevy mesh上传、法线/切线/三角化一致性；保存OBJ多边形与UV，offline fan计数不冒称Bevy索引完全相同。
- 未渲染眼睛/发卡；没有眼睑穿插、发际线、alpha、材质/阴影、碰撞/自相交、gaze、头发物理或质量结论。jaw变体未采样。既有衣物/M2 HOLD不变。
- 没有缺cage或不可复现scaled-offset gap；两条当前路径均在所声明六帧算通。若输入/权重/域/单位控制失败，脚本停止写FAILED，不猜公式。

VERIFIED —六个实际r4输入上的眼睛/头发离线fit+完整正影响LBS，运动服复现控制，8项正常/−O拒绝/算术控制。NOT-RUN —独立MPFB oracle、运行时附件、GPU/原生Web画面及质量准入。

## 独立复核

[独立复核记录](evidence/independent-review.md)未发现 P1/P2。复核校验全部来源与产物身份，独立重算一个真实样本及衣物控制；六项纯内存控制普通/−O通过。整合时另行重跑完整八项普通/−O控制，均通过。此复核只接受本实验的限定离线结果，不等于运行时、外观质量或 #79 准入。
