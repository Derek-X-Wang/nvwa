# Bounded-history integration acceptance

Parent `de9dac026321fbe57ce2c9bc09ae2d5c1bbd7e42`; final containing commit plus [source/artifact manifest](build-manifest.json) identify this snapshot. Core SHA256 `4c2f06d56b43e3849ee9040c8c5c5f999401816f8b64431d0dbfa240d952b797`, CLI SHA256 `8ddf575e24de088b319aed601214055ce2fa3abba916e3effb04e612d9b0700b`. No manifest/dependency/lock/schema/fixture change.

## Behavior and review

128 combined undo/redo snapshots and16MiB compact document bytes;1024 FIFO successful retry records and8MiB compact envelope/result bytes. Valid edits still succeed when adjacent content is too large: history gains a barrier, retry records expire. Expired original envelopes fail revision checks; fresh current-revision envelopes may reuse expired IDs. Failed commands do not evict. Save/Open transfers only the work and revision. [Policy and worker experiment](../../../experiments/10-bounded-history/REPORT.md) document public semantics and overhead exclusions.

Independent R2 [review](REVIEW.md) accepted the core but found a real additive CLI float-widening regression. Its failed real CLI output and rejected source remain in experiment10. [Targeted rereview](REREVIEW.md) independently executed the corrected CLI probe and accepted the repair. Original profile fields/values stay equal; only editor_retention is added.

## Root verification

-79 full workspace tests pass, zero failed/ignored. Fmt and strict native/Wasm clippy exit0. Native release build/package and Web release build exit0. Real release CLI capability probe exit0. Exact commands/exits/logs are adjacent; root verified integrated hashes match the reviewed worker source.
- Root repeated the long-session test:10,000 edits,10,000 duplicate reads,10,000 invalid submissions and1000 Undo/Redo pairs. Final12,000 successes retain128 snapshots/133,834 compact bytes and1024 retries/185,986 compact bytes. This establishes retained-content/count bounds, not exact heap/RSS.
- Actual packaged native Player loaded the revision6 exchanged work, rendered skin/morph/animation, captured a fresh image and exited0. After the Web edit/reload below, a second actual native Player loaded revision9, reported ready=true/error=null,18 joints,4 morph weights,3 timeline clips and1 active animation, captured native-exchanged.png and exited0.
- Actual rebuilt Web Studio at1280×720/DPR1 displayed the real character at revision6. One continuous jaw drag changed0.53→0.90 at revision7. One Undo gave revision8 and complete baseline equality except revision. Redo gave revision9 and complete edited equality except revision. Actual GUI Save produced the five adjacent history-*.json files. The real file chooser opened history-redo.json; subsequent Save equals it including revision9. [Comparison](document-comparison.json), screenshots and `python3 docs/evidence/bounded-history/compare_saved.py` preserve the result. The comparison script checks saved evidence, not GUI execution.

## Reproduction and limits

From repo root: `cargo test --workspace --locked`; `cargo build -p nvwa-studio -p nvwa-cli --release --locked`; `python3 scripts/package-native.py`; `bash scripts/build-web.sh`; `python3 experiments/10-bounded-history/capability_probe.py target/release/nvwa-cli`. Run the packaged native Player with an absolute --work path, or `python3 scripts/serve-web.py` and open the loopback9201 Studio. Edit/Undo/Redo/Save/Open should retain the full document. `python3 experiments/10-bounded-history/reproduce.py` provides an isolated core/CLI rerun.

Native images are real render captures at2560×1440/scale2; Web images are task-owned1280×720 surfaces. Smoke telemetry is preserved, but this was functional acceptance while other CPU work could run: formal frame/GPU/cold-start/RSS measurement is NOT-RUN. New native physical input, Chinese IME, zoom/DPR, other browsers/platforms and hosted CI are not claimed. Earlier physical acceptance remains attributed to its earlier build. The current unique initial gzip sum is20,533,526bytes (Player20,534,049), file-size data only.

VERIFIED —79 tests, strict checks, dual release builds, native/Web actual startup, real CLI capabilities and complete GUI edit/Undo/Redo/reload/cross-target work checks pass. PARTIAL — exact allocator/RSS and broader platform/input/performance coverage remain open.
