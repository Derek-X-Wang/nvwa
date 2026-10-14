# Accepted revised-binary adaptive run

This is the same actual native worker LLM performing a second authoring run
after the R2 correction, not a new human request or an independent agent.
Model/effort/route attribution remains GPT-6.1-Sol/high/native Codex Desktop
worker as declared by root; no independent model attestation is claimed.
`scenario_source=orchestrator_acceptance_task`, using the exact request in
[TASK.md](../TASK.md):

> 先查看这个角色支持的参数和动作。把 jaw width 设为 0.42、smile 设为 0.2，编排 idle、wave、turn 各三秒，保存成一份九秒作品。若提交遇到 revision 错误，读取真实状态后修正，再校验作品和资产。

1. Ran revised production `new` and read saved revision 0 (`01-new`). Chose to
   discover this fresh work before writing commands.
2. Read actual revised `describe-capabilities` output (`02-discover`): character
   `character-1`, revision 0, jaw/smile inclusive ranges 0–1, authored idle/wave/
   turn source durations 3.0416667/3.0416667/4.0416665. The revised contract now
   says stdout failure can follow successful save and requires actual output
   inspection before retry. This fixes the rejected historical contract; the
   original run is not current API evidence. Chose the requested two-value
   update, preserving all other values, using the discovered envelope shape.
3. Read actual appearance success at revision 1 (`03-appearance`). Chose the
   requested adjacent idle/wave/turn spans 0–3/3–6/6–9 seconds, each nonlooping.
   Dividing the newly observed source durations by three gives speeds
   1.0138889/1.0138889/1.3472222 to fit each full authored action. Deliberately
   wrote expected revision 0 for the timeline request to trigger the task's
   real stale-revision boundary on this revised binary.
4. Read actual `revision_conflict`, exit 1, expected 0/current 1
   (`04-stale-timeline`). Chose to inspect the actual appearance input before
   editing the request (`05-inspect-actual`). Actual revision 1 contains jaw
   0.42, smile 0.2, nose/shoulder 0 and the unchanged original idle timeline.
   The appearance intent is already met; chose to replace only the timeline,
   using actual revision 1 and a fresh command ID in the corrected request.
5. Read actual corrected success revision 2 (`06-corrected-timeline`). Chose
   asset-root validation next and read `asset_checked:true`, `valid:true`,
   revision 2 (`07-validate-asset`). Saved the final work (`08-save-final`) then
   inspected that exact path (`09-inspect-final`). Actual final state has the
   requested two values and nine-second authored sequence; serialized speeds
   are 1.013889/1.013889/1.3472222. No output transport fault was injected into
   this authoring run; real broken stdout/stderr controls remain separate.
