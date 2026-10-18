# 新14帧原生数据对应核查

**PASS —14个新要求样本与同字节r4旧帧逐项语义对应；不是独立FK/LBS/表面检查重跑。**

先读取最后请求 `resume17_r4_tp1_b1_knee_flex_v1_2`，其phase确为`captured`后才开始核查；结束再次确认同一captured请求，并核对状态request与最终捕获request一致。未按文件存在单独判完成。

精确比较8248282个骨骼/两网格数值（无容差）。全部53个有序完整bone行均相同；body/garment的positions、normals、tangents、indices、source_ids、full_joint_influences、rest_positions、rest_normals、model_to_world、display_transform、name全部相同。只排除part的display_entity/mesh_handle这两个进程分配身份，各自新旧值均保留。没有排除任何骨骼或网格数值字段。

请求仅允许`resume17_`前缀变化，其他request字段精确相同；clip/source/position/timeline/playing/completed及参数也一致。每帧实际revision/generation/serial、完整sample和运行期实体/mesh身份均保留在JSON。它们没有被重写为旧值。

## 样本与原始哈希

| 新请求ID（前缀resume17_） | 新SHA256 | 旧SHA256 | 新rev/gen/serial | 旧rev/gen/serial |
|---|---|---|---|---|
| r4_tp0_b1_arm_rehearsal_v1_0 | 977f70844655fed0c4520d219a06618ed6041b28f5cd7583c5868d77224d677a | d99f0a6bc7aed3502c8472446ae7009535fda42f6f843084f3d4a033c202e819 | 12/1/1 | 9/1/1 |
| r4_tp0_b1_arm_rehearsal_v1_1 | 5449c3d1fbc4a0530bb76cfb5ae57dd662462a9bc1a45555bf0b947e18665af8 | 5f414a17fc593032c0971237eec9f1362bbf86a59ceed1a68d61bc219ddbe531 | 12/1/2 | 9/1/2 |
| r4_tp0_b1_arm_rehearsal_v1_2 | 10f61ae21816826035c0a07b9ef22ef4dfe7b3ff8d3e4b7cc0cbbab7929d5906 | 001fdd054ba532ec1d502e09f5f6dc376ca490eee3865ef121473c9fc528033b | 12/1/3 | 9/1/3 |
| r4_tp0_b1_arm_rehearsal_v1_3 | b51d489f8ec5234013032139411487c3604e4d3b08221a24c1525de7de5dd47e | 8402d2e23d66261729d5e4f1d92e9ab895bc69d82782b6d50e3960cafdc31452 | 12/1/4 | 9/1/4 |
| r4_tp0_b1_arm_rehearsal_v1_4 | 7546f96873f11b1482f54f5789aa8d8c4be87f4946f7525af2ad2e19e713cabf | 2958c39938eabbe64775bbee950cdb672e3bacaba8ea74dbe736996000a09764 | 12/1/5 | 9/1/5 |
| r4_tp0_b1_knee_flex_v1_0 | 23d9c256658ef184dd9d4a089a2ac27c424a1f570c85a96fd709646899b5137a | f8da0af5cdc0585c5adb9c1f5e1c2afaff55d727cd32114febb4538353bb8c52 | 13/1/6 | 10/1/6 |
| r4_tp0_b1_knee_flex_v1_1 | 2971cb1d2fa64725579761f0ce3196818ddc60e975618a5636cfe6dd27dcb8fc | a7a459c532a201f42566e617d7e9a736c6962c14e13dfae169470146a46bab0a | 13/1/7 | 10/1/7 |
| r4_tp0_b1_knee_flex_v1_2 | 4f2c442806fcf171f512f03b4686bcc03e61487c05f95c31e21146efe3274e5d | 5934b47d8bca6f12b4c1a2f66c6b4ec6b309410bbc424079f23e0538e329cf28 | 13/1/8 | 10/1/8 |
| r4_tp0_b1_knee_flex_v1_3 | 2aa81c88e21a6cbf22ff08e307530da000469103b96a15eabea85ed81b3a88f7 | 424d5f9d8714bf62dbd1808a562169a53c297334ddac93ca861e4fbb02637a7d | 13/1/9 | 10/1/9 |
| r4_tp0_b1_knee_flex_v1_4 | 209c040d31a433002b89db9cca12c3aa2596925c9f0cba0195e9e5df400eff07 | 612084e953207a7f9cbb6df7978a490c1c6afea961400c98e2ca381b594254e3 | 13/1/10 | 10/1/10 |
| r4_tm1_b1_arm_rehearsal_v1_2 | 645604a6a6b431f36d61432e8f69d5142d20a84e67dca707e278e8f589d5bbc6 | 32bacdb00f3b37d11a3a78e2f7037d49f38a96391e2bd78ef22638bab29bbd7a | 15/1/1 | 12/1/1 |
| r4_tm1_b1_knee_flex_v1_2 | 556735dad891f4c8a0bd8f8fdf4e037c568764e59bdab989e67e4024d78ac9a7 | 80601745531ff960e242d4ca3cf804850810cf894a7a2383f832bde9f8d5a489 | 16/1/2 | 13/1/2 |
| r4_tp1_b1_arm_rehearsal_v1_2 | 0ec1d742ad4511bb9f80779af7f66fdd637159ce3492812ce5d81f107290d618 | e9c65e1705e45b34c1aa3d6ecf1e23dedfb05b96e8850af8ce2f13b4a46f9746 | 18/1/1 | 15/1/1 |
| r4_tp1_b1_knee_flex_v1_2 | 9410342bb0e4f9e8b15e35936fa42c225230c469de1b542d557e1cc5c0dcc928 | 38e57ff953c2b918bb2032d10beab55da1be4018fc8fdb4f856c66f4798edca6 | 19/1/2 | 16/1/2 |

## 既有独立证据绑定

每个旧帧原始SHA/长度/request/sample/参数/revision均匹配公开`docs/evidence/b1-motion/captured-samples.json`的native条目；同一SHA匹配保留native-metrics中的file_sha256，其actual_bones、actual_bones_sha256、两part上传position/index哈希及技术/LBS PASS也逐项对应。公开platform-summary与保留summary字节相同，native14/14。JSON记录了所有证据文件hash。

边界：公开platform-summary本身不直接包含私有native-metrics文件hash。本审计新哈希该私有流，通过公开原始capture哈希、metric原始SHA/实际数组哈希和同一coverage summary建立明确对应，不夸大已有公开加密绑定。没有调用独立Checker或用旧指标冒称新运算。

当前正常应用与探针实文件SHA重新匹配build-r4闭包：正常`3c142ca7…`，探针`97847e93…`。root新normal-observations已读并记录其当时hash；其普通GUI/Save/Open/实际Web picker交换为root观察，本审计未操作GUI、未独立审图，不将此数据对应当成像素或物理呈现证明。

失败/缺失：无。

完整JSON：`probe/geometry-correspondence-final.json`，SHA256 `2a92f9d212c19908360cf640417fbce231e7661d83d1f671d29b303a0985c5a5`。

VERIFIED —14/14完整数据精确对应与公开/保留证据绑定。NOT-RUN —新FK/LBS/surfaces、完整checker/矩阵/构建、GPU/GUI/审图、性能及衣物/M2质量准入。
