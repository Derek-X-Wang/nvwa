# 联网方向归档：WebSocket 房间数据＋Relais 语音

日期：2026-10-17。Derek 已确认本方向归档，**暂不接入 Nvwa**。人物连续动作、体型适配和外观质量先于网络集成。

## 后续候选边界

```text
Nvwa Web/native 客户端
  ├─ 房间命令、权威状态、查询/恢复 → WebSocket → 独立房间服务
  └─ 语音 → WebRTC → Relais（目前每名参与者一个 call）
```

房间状态、玩家身份、动作裁决、命令记账和持久化属于应用服务；Relais 负责媒体。多人语音混音/转发尚不是现成 Relais 能力，后续设计见 [relais#170](https://github.com/relaishq/relais/issues/170)。DataChannel 仍 [HOLD](https://github.com/relaishq/relais/issues/162)，不作为 Nvwa 主线前置条件。

## 已有证据与可沿用的合同

Relais 的[归档原型](https://github.com/relaishq/relais/tree/archive/spike-nvwa-room/experiments/nvwa-room)已在本机完成双客户端、动作消息、真实媒体 relay/worker 通路和允许新连接的房间恢复。Linux [CI 39003679822](https://github.com/relaishq/relais/actions/runs/39003679822) 的五项网络 profile 对照成功；该 run 中其他未选择的质量/单元/容量任务为 skipped，不能当作全部 Relais 回归通过。

未来实现应重新审查并采用其应用语义：服务端绑定玩家身份、room epoch/version、服务端分配连接代次、稳定 command_id、同 ID 不同 payload 明确冲突；回执表示房间已应用并记账。断线后先查询结果再决定重试；高频状态按版本取最新。去重边界限于房间账本寿命，不能直接宣称进程崩溃后也恰好一次。

## 不扩大结论

- WebSocket 与 DataChannel 的恢复/延迟只代表该原型及拓扑；WS 为私网明文，DC 含 DTLS 和更多跳数，并非等价 WSS 产品基准。不可靠 DC 在部分远距离丢包条件下有状态新鲜度收益，不能概括为任一协议普遍更快。
- 恢复场景每 transport/profile 只有两次样本；测试音双向到达不证明真人音质。
- Relais 目前没有 TURN 或 TCP/TLS 回退，UDP 受阻网络的语音可达性未解决；单一公网 relay 的高可用也尚未交付。
- 房间内存账本没有实测进程崩溃后的持久恢复；新 epoch/reset/unknown 必须明确。
- 全球逻辑互通与多地区物理部署是两项设计，WebRTC 不消除传播延迟，也不自动提供跨区域状态一致性。

**NOT-RUN —** 正式 Rust/Nvwa native/Web 接入、公网/NAT/TURN/UDP受阻、跨主机/跨区域、Safari/mobile、房间进程持久恢复、多房间容量/长期稳定、真人语音质量、原 SCTP 通道无缝迁移。

后续只有在人物单机体验成立且有具体联网需求时，另开有界接入任务；它应单独验证 Rust/Web 客户端、认证与 WSS、断线恢复和语音房间处理。不在本次人物动作任务实现网络、部署服务或引入依赖。

来源：[stage3 报告](https://github.com/relaishq/relais/blob/archive/spike-nvwa-room/experiments/nvwa-room/evidence/REPORT.md)、[stage4 对照](https://github.com/relaishq/relais/blob/archive/spike-nvwa-room/experiments/nvwa-room/evidence/stage4-network/README.md)、[relais#163](https://github.com/relaishq/relais/issues/163)。
