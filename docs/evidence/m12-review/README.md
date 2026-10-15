# M1.2 independent review record

These are selected, unchanged reports and raw outputs from actual independent agent review sessions. They record the scopes and source hashes at each pass; a later source state is not implicitly approved by an earlier report. `copied-evidence.json` maps these exact copies to their retained task paths. Additional referenced scratch, duplicate numerical GLBs, full API pages and third-party source responses are intentionally not published here.

- `r2-initial/`: different-model GPT-6 Astra review found the real P2 stdout failure; the original run is retained as red evidence.
- `r2-correction/`: the same independent reviewer rechecked the Sol-authored fix, real pipe failures and all ten CLI tests; experiment/readiness/history checks remain bounded as described.
- `independent-initial/`: fresh GPT-6.1 Sol reviewer independently reconciled archival paths, controlled visual/numerical A/B and model-readiness claims.
- [Fresh Alpha operator](../m12-alpha-operator/REPORT.md): the latter reviewer followed the guide before inspecting CLI code, then reviewed the fixed CLI/workflow and ran the real tests.
- [Full native/Web continuation](../m12-agent-loop/REPORT.md): separate actual edit/save/Undo/reload/Player proof. Renderer reuse has an explicit unchanged-source identity check.

The root controller observed the actual native agent dispatch and adaptive CLI interaction underlying experiment38. Retained stdout/JSON and deterministic replay corroborate process behavior; the offline evidence auditor does not independently establish LLM authorship. Human Alpha usability is separate issue49 and remains NOT-RUN.

Final publication review and exact-head hosted CI are recorded in the integration PR. Approval requires both; merged-main CI is a separate gate. These files do not claim a hosted result in advance.
