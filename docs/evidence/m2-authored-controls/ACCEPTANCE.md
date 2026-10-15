# M2 isolated experiments and parent authored playback

**Retain experiments 41–43 and their model-free regression controls. No product provider or retargeter is adopted.** The parent validated and played three authored Works in the unchanged native/Web application. Naive mapping visibly folds limbs; calibrated mapping gives the declared asymmetric arm/torso motion. Calibrated mapping still loses up to **0.277118877976 m** of source hand/foot position. This is not genuine generated motion or general retargeting acceptance.

Recorded 2026-10-15. Integration base and actual renderer source: `7cfe171ea7d0bd2ba8e777b188e68ab9cbd85bf8`. The integration worker ran only the local model-free controls below. The supplied parent runtime/CLI records are copied unchanged into this directory; no new renderer, human trial or performance measurement ran during integration.

## Frozen experiments and decisions

| Experiment / ticket | Accepted evidence | Remaining boundary |
| --- | --- | --- |
| [41 CPU preflight](../../../experiments/41-real-short-motion/REPORT.md), [#54](https://github.com/Derek-X-Wang/nvwa/issues/54) | Private CPU backend build/help, native-float prerequisite and actual failure/guard controls. The [latest targeted R2 rereview](provider-ps-rereview.json) resolves a later ps-diagnostic false-absence finding on the refreshed freeze. | Three model/encoder/tokenizer artifacts and one bounded CPU attempt still need explicit permission. No weights, model loading, inference, genuine output, measured model resources or verified provider handedness. Review clearance is not permission. |
| [42 motion import](../../../experiments/42-motion-import/REPORT.md), [#55](https://github.com/Derek-X-Wang/nvwa/issues/55) | Frozen standalone Rust importer; 19 real executable boundary tests; authored GLB/Work control. [P3 rereview](importer-p3-rereview.json) accepts explicit input/output normalized hashes. | Generated input is rejected, including forged success receipts. No product import UI/schema/dependency integration or general rig admission. |
| [43 rig mapping](../../../experiments/43-rig-mapping/REPORT.md), [#56](https://github.com/Derek-X-Wang/nvwa/issues/56) | Authored 30/77-layout numeric A/B; independent matrix/FK oracle, negative controls, root-once and exact target-scale checks. Parent separately imported and played naive/calibrated controls. | Authored source rest data is not official provider calibration. Rotation-only mapping fails source endpoint preservation. No contact/IK, arbitrary rigs, actual provider convention or genuine generated playback acceptance. |

All 70 current copied files (38 provider, 25 importer, 7 mapping) match the frozen sibling bytes. [frozen-inputs.json](frozen-inputs.json) lists every file, byte count and SHA-256. The refreshed provider index is `b0e2bc532342dc916199decaf74f4f420a334a49767498a9e1709da170244bc7`; importer current index remains `78be896e1f532ee56754604ca4379f2df8742da2591a39b4aff3d09f2d723006`; mapping manifest remains `fa60a9740a8f269d63f89c36aa169b31802e7d8e2986b60ada8e465a1e746c63`. The [initial 64-file inventory](r2-first-review/frozen-inputs-before-provider-refresh.json) and initial integration inventory are retained as history. Provider41 alone was replaced by an explicitly authorized exact copy from its original worker after the ps fix; its initial copy is privately archived. Frozen42/43 bytes and their historical indexes/reports remain unchanged. Their earlier playback NOT-RUN statements describe those worker stages; later parent observations below supply that bounded playback evidence.

Provider review chronology is **initial GO → demonstrated ps HOLD → targeted GO on the new freeze**. The [original GO](r2-first-review/provider-before-ps-review.json) and [actual HOLD proof](r2-first-review/provider-ps-hold-proof.json) remain distinct. The final rereviewer replayed 13 classification cases and an actual TERM-ignoring child: KILL/reap succeeded while a durable receipt retained cleanup uncertainty; independent real ps confirmed absence. Eight earlier rerun receipts were inspected, not replayed again in this narrow follow-up. No review state supplies human model permission.

Integration additions are separately listed in [integration-files.json](integration-files.json). They are the model-free driver, this acceptance/evidence directory, experiment/roadmap summaries and one added portable CI step. Frozen source, fixtures, indexes and archived logs were not rewritten. Root dependencies/lock, product/native/Web source and assets remain unchanged.

[Source metadata attribution](upstream/NOTICE.md) retains the exact supplied pinned Apache license texts and NVIDIA copyright header for the metadata extractions. This publication notice does not approve weights redistribution or close #10's wider distribution audit.

## Parent CLI and actual playback

[Parent CLI validation](parent-cli-validation.json) returned exit 0, `valid:true`, `asset_checked:true`, revision 0 for each complete Work. CLI binary SHA-256: `c86518413dde4afe6000dda9092e09eaaf071d7a89924f621c0e051eeb5a102e`. [Parent staging identities](parent-runtime-stage.json) bind the exact Work/GLB bytes and runtime cohort.

| Authored case | Work SHA-256 | GLB SHA-256 |
| --- | --- | --- |
| Original authored wave | `99e67ba6dbc532609e761d35d069937e33c46fb9d0493881f3b1d687306735f0` | `06ded48fbf464e5014f4f529c38a43e4958ef30f3304a9e25a08842a61544a35` |
| Naive asymmetric mapping | `b19f035714f29b9928f4fab4f1e6600ca61e3a8cd6ce9d82ac49b292876e277b` | `8de02cfbe9f9622a27126fc20c67c582f5185de457997a27f7b8f3578802c79e` |
| Calibrated asymmetric mapping | `ce00d25217b8082200632f1c4e5718d846ac6794d737d0191b1ced20e7bf11e7` | `1be18c859824980989916b83f30d53f03419038e648f3c5f7a75637231f0f71c` |

All three reached Ready with a real character and `imported_authored_control` in both targets. [Web observations](parent-web-observations.json) record original-wave Restart/Pause, visibly folded naive limbs, and calibrated asymmetric arm raise/torso lean with Pause and seek. [Native authored](parent-native-authored.json), [naive](parent-native-naive.json) and [calibrated](parent-native-calibrated.json) observations record the same bounded visual distinction and advancing playback. Native Pause changed to Play for authored/calibrated cases. A native calibrated seek drag had no visible effect: **native seek is NOT-RUN**, with no success claim.

Actual native executable SHA-256: `bc063d68bf5009aafe7ee104bafaa317e27c9c82bbbe0a8a565d97e743272b38`; served Wasm SHA-256: `648dfe770b5f903569e77fa35c5ec2a96311931dcb6878b7d2e69e526ab429c3`. The generated test bundle changed only its bundle identifier to `dev.nvwa.m2.authored-controls` to isolate it from the human application; the unchanged executable and product title behavior were retained. Before/after plist hashes are in the stage record.

Screenshots were visually observed in CUA tool outputs. No local screenshot file is claimed or linked. Every case is `authored_control`, `ai_generated:false`. Tool-driven playback is not physical-human acceptance, model generation, artistic quality, endpoint/contact preservation or performance evidence. [Parent cleanup](parent-cleanup.json) records task processes absent and task tab closed; native process exit statuses were not collected. Existing human Work was not written.

## Model-free reproduction and CI

Run from the repository root with Rust 1.95.0 and Python 3 standard library. The frozen standalone importer has its own workspace/lock. One explicit dependency preparation command is allowed in CI; it fetches only the locked Rust source packages:

```sh
cargo fetch --locked --manifest-path experiments/42-motion-import/Cargo.toml
python3 -B experiments/42-motion-import/check_model_free.py
```

The second command always builds `--locked --offline --jobs 2` into `.work/m2-model-free-ci/target`, runs all 19 frozen executable tests and 22 integration comparison/process controls, copies/verifies the frozen contract, and runs all stdlib mapping/negative controls. It checks the frozen source inventory before/after. Logs and per-command receipts remain in a fresh `.work/m2-model-free-ci/run-*` directory. No archived fixture/log is regenerated. Python assertions must remain enabled.

The 36 [published reference JSON files](mapping-reference/) were copied from the earlier frozen mapping run and verified against every entry in the unchanged experiment43 manifest. They are authored controls, not generated during comparison. Each new run must match the exact file set, validate every generated file's own SHA/size against its generated manifest, and validate all 18 raw/envelope digest and exact-payload bindings. Decoded contents then match those independent reference bytes: schema, types, keys, shapes, integer counts, identities, policies, source/input pins and provenance remain exact. Only finite float leaves use `abs(actual - expected) <= 1e-13 + 1e-13 * abs(expected)`. This permits binary64/libm rounding, including near-zero residual metrics, without relaxing the frozen mapper's numerical/negative-control assertions. Nonfinite values, bool-as-number, material changes, forged provenance and stale hashes are rejected. A varying envelope raw digest is allowed only after its binding to actual generated raw bytes has been verified.

The added step stays in the existing portable job, with a six-minute step timeout. The driver limits commands to a 300-second shared budget (per-command ceilings: build 180s, boundary tests 60s, integration controls 30s, mapping 30s; each receives only the remaining shared budget). Its production-called owned-command seam attempts bounded group TERM→KILL and leader reap on timeout, SIGINT/SIGTERM and post-spawn exceptions, including receipt/log failures. Signals during spawn, teardown and persistence are deferred; a signal that arrives during the final write triggers bounded re-persistence before default signal exit. Failed group inspection remains `cleanup_unconfirmed`; failure to persist reports the receipt on stderr. Cleanup/receipt work can add a small bounded tail to command deadlines. No extra CI job or provider acquisition/setup/build/GPU/model command is added. The explicit fetch is necessary: frozen importer serde/core/derive `1.0.228` and serde_json `1.0.149` differ from root portable `1.0.229` and `1.0.152`; root CI does not implicitly populate those four packages. The driver has no online fallback and fails if dependencies are unavailable. Root and standalone locks remain unchanged.

For mapping alone, create its required input explicitly, then choose a new output directory:

```sh
mkdir -p .work/m2-mapping-inputs
# If a copy already exists, compare it first; do not overwrite a different input.
test ! -e .work/m2-mapping-inputs/CONTRACT.md || cmp experiments/42-motion-import/CONTRACT.md .work/m2-mapping-inputs/CONTRACT.md
cp -n experiments/42-motion-import/CONTRACT.md .work/m2-mapping-inputs/CONTRACT.md
python3 -B experiments/43-rig-mapping/spike.py --out .work/m2-mapping/repro-new
```

Contract SHA-256 must be `74bb268930428195242a99cffe6fd3307338be2dbd435583212607185a6bb257`. The driver performs the same copy without replacing a different existing contract. Mapping requires no model, package installation, provider source or network. To export its calibrated control with the just-built standalone importer:

```sh
.work/m2-model-free-ci/target/debug/nvwa-motion-import-experiment \
  .work/m2-mapping/repro-new/30-asymmetric-calibrated.normalized.json \
  .work/m2-mapping/repro-new/30-asymmetric-calibrated.raw.json \
  assets/fixtures/nvwa-humanoid.glb .work/m2-mapping/calibrated-clip-new
```

The destination must be new. This produces an isolated clip, not an attached current Work or product provider.

## Verification and retained gates

VERIFIED — The initial local offline standalone build completed in 6.78s; 19 actual CLI tests passed in 3.165s. [Initial command receipts](local-checks.json), [build log](local-build.log), [boundary log](local-boundary.log), [mapping log](local-mapping.log) retain that first 64-file checkpoint and its then byte-identical current-Python mapping result. Parent CLI and six actual native/Web case observations are separately attributed above.

## Integration R2 corrections

The [first integration review](r2-first-review/review.json) requested changes: Python3.9.6's valid last-bit differences were falsely rejected by byte comparison, and actual SIGINT left the detached Cargo stand-in group alive. [Original arithmetic differences](r2-first-review/python-version-differences.json) and [actual surviving-child proof](r2-first-review/lifecycle-result.json) remain unchanged. Those two findings caused the comparison/ownership changes described above; a further [post-write cancellation red control](r2-repair/postwrite-cancellation-red.log) exposed a missing pending-signal receipt, which was repaired with bounded re-persistence.

VERIFIED — All 22 focused controls pass on existing Python3.9.6, 3.9.23, 3.12.11 and 3.14.7; each interpreter also ran the frozen mapper and validated all 36 files/18 pairs. [Four-runtime results](r2-repair/python-results.json) retain the genuinely different 3.9 manifest, accepted by the content comparison. Controls reject material numeric, schema/type/shape, hash, provenance, missing-file and nonfinite mutations, while accepting last-bit rounding with recomputed honest hashes. Actual CPU controls exercise SIGINT/SIGTERM with TERM-ignoring descendants, timeout, post-spawn filesystem failure, deferred signals during teardown/persistence, inspection uncertainty, successful cleanup and the actual driver with a Cargo stand-in. No real compiler or provider is used by those lifecycle controls.

The [final combined offline driver check](r2-repair/final-driver.log) also passed against the refreshed 70-file cohort: cached standalone Cargo build (no source compilation), 19 importer tests, 22 integration controls and mapping/content comparison. [Final command receipts](r2-repair/final-driver-commands.json) record verified cleanup for its commands. Frozen42/43 remained byte-identical; provider41 matches only the explicitly refreshed source cohort. Hosted integration CI and targeted independent integration rereview are still pending.

PARTIAL — Hosted integration CI and final independent integration review remain pending at this handoff. Native seek, physical-human assessment, performance, models/inference, signed-axis/provider admission and generated playback are NOT-RUN. #3 stays blocked; #4 retains all performance gaps; #49's unassisted Alpha gate and #12's genuine-output/playback criteria remain open. No milestone is closed by this integration. Model downloads/extra compute still require explicit scope approval.
