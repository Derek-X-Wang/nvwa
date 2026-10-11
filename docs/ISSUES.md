# GitHub work index

M0 was published as [`d74493d`](https://github.com/Derek-X-Wang/nvwa/commit/d74493df0ab14f786e798cee03efe5ef9e2e4670). Issues are the canonical task detail; this is a compact navigation index. Known gaps do not all gate thin M1.

## Known M0 gaps

- [Render Chinese text with redistributable CJK fonts](https://github.com/Derek-X-Wang/nvwa/issues/1) — ready-for-agent
- [Hand-test native and Web text, drag, clipboard and focus behavior](https://github.com/Derek-X-Wang/nvwa/issues/2) — ready-for-human
- [Fix or diagnose stale input scaling under IAB viewport and DPR changes](https://github.com/Derek-X-Wang/nvwa/issues/3) — ready-for-agent
- [Measure first presentation, cold Web startup and GPU/browser memory](https://github.com/Derek-X-Wang/nvwa/issues/4) — ready-for-agent
- [Make automatic Web screenshot export persist in embedded browsers](https://github.com/Derek-X-Wang/nvwa/issues/5) — ready-for-agent
- [Avoid duplicate GLB transfers while retaining asset integrity checks](https://github.com/Derek-X-Wang/nvwa/issues/6) — ready-for-agent
- [Explain or eliminate byte drift in repeated Blender fixture exports](https://github.com/Derek-X-Wang/nvwa/issues/7) — ready-for-agent
- [Bound editing history and command-retry memory for long sessions](https://github.com/Derek-X-Wang/nvwa/issues/8) — ready-for-agent
- [Validate additional native platforms and WebGPU browsers](https://github.com/Derek-X-Wang/nvwa/issues/9) — ready-for-human
- [Prepare dependency notices and signed distribution validation](https://github.com/Derek-X-Wang/nvwa/issues/10) — ready-for-human
- [Improve and validate humanoid hand shape and skin weighting](https://github.com/Derek-X-Wang/nvwa/issues/11) — ready-for-human
- [Validate genuine local AI motion readiness and output compatibility](https://github.com/Derek-X-Wang/nvwa/issues/12) — needs-triage
- [Visually verify controlled retarget derivatives before broader rig claims](https://github.com/Derek-X-Wang/nvwa/issues/13) — needs-triage

## User-approved thin M1

All three issues are closed. Implementation/evidence is published in [draft PR #17](https://github.com/Derek-X-Wang/nvwa/pull/17), code commit [4af6a19](https://github.com/Derek-X-Wang/nvwa/commit/4af6a1963783199f2b4bf4e5d2b44ca694900ecb). The PR remains unmerged; main retains M0.

- [Compose and exchange a three-action 5–10 second work](https://github.com/Derek-X-Wang/nvwa/issues/14) — completed; sequence/exchange acceptance recorded in [M1 verification](M1-VERIFICATION.md)
- [Click the character to trigger one authored action and resume the work](https://github.com/Derek-X-Wang/nvwa/issues/15) — completed; native/Web interaction acceptance
- [Open the saved work in an editor-free static Player](https://github.com/Derek-X-Wang/nvwa/issues/16) — completed; local release acceptance recorded; [release evidence and limits](evidence/m1/player-acceptance.md)

The native GitHub blocking edges are three-action work → click interaction → static Player; Player also depends directly on the three-action work. The user approved this decomposition. No accounts, general rig importer, physics, genuine AI generation, VaM compatibility or remote live GUI bridge is included.
