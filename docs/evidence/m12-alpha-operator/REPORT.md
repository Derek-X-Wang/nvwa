# Independent Alpha runbook operator

**GO for the bounded fresh agent operator pass.** This reviewer followed `docs/M1.2-ALPHA.md` and its linked CLI authoring guide before reading CLI code, tests or implementer reports. This is agent operation evidence, not physical-human usability, a new adaptive-author run or a complete GUI regression.

CLI code cohort: `aa9f942136f00d154ffe650936579d056fb637d1` (critical fixed CLI source integrated from4db1b5f). The corrected guide and linked CLI guide copies followed are retained; `01-build.*` preserves the original failed command. The public runbook changed during this pass to address the observed build-directory problem.

## Actual CLI operation

The original guide's default-target build failed with exit101: the checkout's existing `target` symlink did not resolve to a usable directory. `01-build.*` retains that failure. No shared target or symlink was changed. Root authorized a fresh owned `CARGO_TARGET_DIR=.work/m12-alpha-build`, then updated the guide to that exact target and CLI path. The build directory and `.work/m12-alpha` were absent before this operator created them. The fresh build used `--locked --offline -j1` and exited0.

The fresh CLI binary SHA-256 is `c86518413dde4afe6000dda9092e09eaaf071d7a89924f621c0e051eeb5a102e`. It is a new local build, distinct from previously recorded process binaries.

| Actual guide step | Result |
| --- | --- |
| new → describe-capabilities | exit0; character-1, revision0; profile parameters/actions and additive cli_contract discovered |
| appearance apply | exit0; revision1; jaw_width0.42/smile0.2 |
| stale timeline apply | expected exit1, structured revision_conflict, empty stdout; no rejected.json; input bytes unchanged |
| inspect actual input → corrected timeline apply | both exit0; corrected revision2 |
| validate authored Work with assets | exit0; asset_checked:true |
| save → inspect final | both exit0; final bytes equal authored bytes; revision2 preserved |
| retained-evidence verifier | exit0; historical and accepted records explicitly distinguished |

This sequence uses the guide's recorded command files and is a deterministic replay operated by a fresh agent. It does not independently establish authorship of the earlier adaptive run.

The final Work is [final.nvwa.json](final.nvwa.json), SHA-256 `e33356b490cb8d6c01118958c3d22409f4546cfa6164a7d69d496be292eb25cc`. The entire expected document matches the output under the Rust contract's exact binary32 float representation: source speed1.0138889 and saved1.013889 encode the same float. No epsilon was used, and a one-binary32-step changed speed is rejected by the comparison control. All profile/character/timeline fields were checked, not only the two appearance values. The inspect response equals the full saved document. See [operator-document-check.json](operator-document-check.json).

Raw argv/stdout/stderr/exit and before/after Work byte hashes are retained in numbered receipts. The recorder captures the actual child exit, even though its own wrapper returns success after recording an expected failure.

## Minimal native and Web operation

Root granted this operator the exclusive GPU/UI token after the previous controller closed its children and server. This operator loaded computer-use-routing, checked its own CUA inventory and verified the actual targets. Parent adapter readiness was not inherited.

The existing checkout's retained native executable hashes to `72d3df8cfdeea062282c8731b0a95cb971f90976fe881772f3e3c24afe76973a`; its Web Wasm hashes to `d890dfee73e9eeeee6ce3d82f255c79979e8c8b6bed90243c6101f8e1c1763a8`. The primary checkout's older artifacts differ and were not used. This operator did not build Studio or Wasm. Source-cohort reuse proof belongs to the separately reviewed full GUI packet.

Native command used the guide's `./dist/Nvwa.app/Contents/MacOS/Nvwa --work <absolute own final.json>`. CUA observed the real skinned character, revision2, jaw0.42/smile0.20 and all three nine-second sequence rows. Typing4.5 into transport produced Play (paused), Active:agent-wave and the raised arm. Play resumed; the retained next frame shows Pause and5.533s with a changed pose. See [native-open.jpg](native-open.jpg), [native-seek.jpg](native-seek.jpg), [native-resume.jpg](native-resume.jpg).

IAB and semantic Chrome creation each returned unavailable. Root's permitted native Chrome UI fallback was available. A fresh owned tab used `http://127.0.0.1:9201/index.html?operator=m12-alpha`; the native Open picker selected the exact own `.work/m12-alpha/final.json`. Web Studio displayed the real character, revision2, jaw0.42/smile0.20 and0–3/3–6/6–9 sequence. Pause and slider seek showed a raised-arm wave; Play resumed and the next retained frame changed pose. The narrow window clips the numerical time field, so this packet does not claim an exact Web seek time. See [web-open.jpg](web-open.jpg), [web-seek.jpg](web-seek.jpg), [web-resume.jpg](web-resume.jpg). Full unedited screenshots are JPEG bytes with matching `.jpg` extensions.

An early Chrome URL autocomplete went to a historical Player URL and returned404. It is not an accepted load. Setting a unique exact Studio URL and visibly verifying it preceded the successful file-picker operation. Native picker text input also needed visible path verification before submission. No product behavior was inferred from unsuccessful UI actions.

This bounded smoke does not repeat the full edit/Undo/save/reload or Player interaction regression from the separate GUI worker. Those parts of the guide remain NOT-RUN by this operator and must use that separate actual evidence. Physical-human usability remains NOT-RUN.

## Independent source and test review after operation

The operator step completed before this reviewer read the fixed CLI code and implementer report. Then the reviewer inspected production `respond`, its callers and main error handling; additive discovery shape; new discovery/response transport integration tests; retained evidence verifier/controls; manifests; and the new CLI-evidence workflow.

No blocking code finding was identified in this bounded pass. Every response path uses the common fallible write/flush helper. A post-save response failure is explicitly `stdout_write`/exit1 and may follow persistence; stderr failure is best effort and does not panic. The discoverable contract and guide preserve that boundary and preserve session-local history/idempotency and absent filesystem CAS.

Fresh `CARGO_TARGET_DIR=.work/m12-alpha-build cargo test -p nvwa-cli --locked --offline -j1` passed10 actual-binary integration tests. The transport test exercises all seven response verbs through an OS pipe with no reader, verifies exit1/structured stdout_write/no panic, checks saved outputs for new/apply/save and preserves input bytes. The separate closed-stderr domain test also passes. Discovery tests use a nondefault character/revision, execute production-serialized examples and exercise stale second-envelope atomicity plus recovery and cross-process history absence. Raw results are `13-cli-tests.*`.

The retained-evidence verifier and all five actual tamper/restored controls pass (`12-verify.*`, `14-tamper-controls.*`). The workflow uses pinned checkout, read-only permissions and stdlib offline audits; it accurately separates retained process evidence from model authorship, GUI/runtime and release claims. Its remote CI execution is NOT-RUN here. This source review is independent of implementation but does not replace the required different-model R2 review or the final publication audit.

## Cleanup and limits

Native PID37657 closed through its owned window and is absent. Owned Chrome tab closed through its exact tab close control; the pre-existing New Tab remains. Web server exec session16579 received Ctrl-C and exited0; port9201 has no listener. No native renderer remains owned by this operator. Root was informed that GPU/UI ownership was released. The successful CLI build directory and private receipts are intentionally retained for root audit; no shared cache/target was changed.

NOT-RUN — physical-human usability, new adaptive LLM authorship, full GUI editing/Undo/reload/Player regression, current publication freeze, remote CI, merged-main verification, extra platforms, inference, weight acquisition and release approval.

VERIFIED — Fresh CLI build and discovery→expected error→inspection/correction→asset check→save/whole-document verification; native/Web real-character pause/seek/resume smokes;10 CLI integration tests; offline verifier and five actual tamper/restored controls. Cleanup verified separately as above.
