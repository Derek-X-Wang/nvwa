# Actual agent authoring task

Original human authority: “主线做真实 agent 的 CLI 创作闭环”.

Concrete acceptance request (exact root-authored text, not exact human words):

> 先查看这个角色支持的参数和动作。把 jaw width 设为 0.42、smile 设为 0.2，编排 idle、wave、turn 各三秒，保存成一份九秒作品。若提交遇到 revision 错误，读取真实状态后修正，再校验作品和资产。

`scenario_source=orchestrator_acceptance_task`.

The acting agent is the LLM worker dispatched as `m12_agent_cli` under `/root`.
The orchestrator declared its route as GPT-6.1-Sol, high reasoning effort,
native Codex Desktop collaboration on the local Mac. This is route attribution
from the dispatch, not an independently signed model/host attestation. The
worker did not install or call another model, inference service, daemon, MCP
server, or cloud authoring tool. Tools launch the actual production CLI binary.

The agent reads actual CLI outputs between authoring decisions. `record.py`
captures exactly one chosen process call, including argv, stdout, stderr, exit
code, binary hash and JSON argument snapshots. It contains no preset,
decision policy or authoring sequence. These receipts are self-captured process
evidence. Native conversation/tool trace export and signed host traces are
NOT-RUN. The tool route is `functions.exec` → `exec_command` → recorder → CLI.
Steps and decisions are recorded in `DECISIONS.md`.

The requested motion uses the fixture's authored actions. No generated action
or motion-model provenance is claimed. Native/Web rendering and continuing
edits are separate acceptance work owned by root.
