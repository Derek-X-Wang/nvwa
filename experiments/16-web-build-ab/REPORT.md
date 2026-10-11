# M1.1 Web build A/B report

Verdict: **DEFER default adoption; runtime comparison INCONCLUSIVE.** The size gate passes, but two matched cadence pairs exceed the10% regression limit. Existing behavior and test gates pass.

Sole build lease `WEB-SIZE-2026-10-11-1` released after successful Cargo/packaging and freeze checks. Exact approved profile, shared primary target, jobs 1, locked/offline and 2,700-second hard cap. No fat LTO or second compile. Compiler log and memory samples are retained under `.work/m11-web/evidence/`.

A is the frozen accepted Web bundle. B proposed and root-approved: release inherited, opt-level `s`, thin LTO, one codegen unit, jobs 1. Root-approved target cache `<primary-checkout>/target`; first candidate build hard limit 45 minutes. No fat LTO approved.

| Resource | A raw bytes | A gzip bytes | B raw bytes | B gzip bytes |
|---|---:|---:|---:|---:|
| HTML | 2,690 | 1,438 | 2,690 | 1,438 |
| JS | 123,555 | 19,069 | 124,500 | 19,135 |
| Wasm | 85,583,469 | 19,389,608 | 75,582,774 | 16,884,494 |
| GLB | 3,827,840 | 1,129,081 | 3,827,840 | 1,129,081 |
| First-screen total | 89,537,554 | 20,539,196 | 79,537,804 | 18,034,148 |
| Fixed player Work | 1,942 | 523 | 1,942 | 523 |
| Player total | 89,539,496 | 20,539,719 | 79,539,746 | 18,034,671 |

These are actual rehashed filesystem artifacts, not old checked-in size reports. B first-screen gzip is **12.1964% smaller**, a 2,505,048-byte reduction, and passes the at-least-10% size gate. Both arms fit 30,000,000 compressed bytes. B largest raw file remains 75,582,774 bytes; no file-host limit or hosting provider is inferred. All existing static resources and their encoding policy are retained. Only bindgen-generated JS/Wasm and declarations differ. Every raw/gzip pairing passes identity. Source/lock/tool and accepted native/Web artifact manifests are `.work/m11-web/evidence/freeze-before.json`, `baseline-manifest.json`, `candidate-manifest.json` and `artifact-freeze.json`.

Preparation and stdlib checks: Python syntax passes; tracked generated inputs are unchanged except exact root-approved profile; baseline and wasm-bindgen hashes unchanged; repeated deterministic gzip fixture identity green; deliberate raw-side mutation rejected `gzip identity mismatch: index.html`; restore green. Independent review found cancellation/error process cleanup missing. Fixed production-called `run_owned` helper uses finally plus bounded TERM/KILL cleanup and persists error metadata. Sleeper checks pass normal completion, KeyboardInterrupt, snapshot exception and timeout; each spawned TERM-ignoring descendant is absent, every owned group is absent, and direct children are reaped. Evidence: `owned-process-checks.json`. All temporary fixtures deleted. Those preparation checks ran before the compile lease, with no Cargo invocation or GUI launch.

Candidate compile **VERIFIED**: Rust/Cargo 1.95.0, wasm-bindgen 0.2.129; Cargo exits 0 without timeout/error/interruption. Wall time 596.875 seconds (9m57s); bindgen/package/gzip/freeze checks 9.810 seconds. Forty 15-second process-tree samples observe a peak aggregate owned RSS of 1,579 MiB; shared pages may be counted twice. macOS `/usr/bin/time -l` retains raw maximum resident-set field 1,812,611,072 and peak-memory-footprint field 133,890,720 in build.log; these fields measure different scopes. No inference about full-system memory. Post-build host/Wasm profile directories occupy 1,603,188 KiB (about 1.53 GiB); this is profile-cache occupancy, not proven marginal disk cost. Cost evidence: `build.json`, `memory.jsonl`, `package-cost.json`, `cost-summary.json`.

Source and accepted native/Web artifact hashes remain equal before/after. Frozen Git product inputs equal all 45 prepared inputs; generated manifest differs only by root's exact approved profile. Reproduction reads Git blobs at the base and does not require current HEAD equality. Native binary, features, dependencies, fonts, GLB, profile, Work and licenses remain fixed. The Cargo child is reaped and owned group 46634 is absent. No worker GUI/server process was launched.

Root actual HTTP body audits and browser-UA request logs pass. First-screen server writes and separate Python received-body/hash checks agree with frozen package totals. Browser/TCP receipt is NOT-RUN. Root reran the original93 tests successfully11.31s after formal GPU measurement; UI overlay99 tests are separate. Native accepted artifact and both Web arms actually load the real skin/morph rig, edit, Undo/Redo, save/reload, exchange full JSON and play an authored click-wave. Every finite Player run completes the fixed9-second sequence with hidden editor. Prior native9.366/Web18ms figures are not used in this comparison.

Cold-cache startup, exact first presentation, GPU timing and browser memory: **NOT-RUN.** No default-profile adoption: at least10% size reduction passes; the conservative per-pair cadence check does not pass. Failed/inconclusive results are retained.

Cleanup: no task-owned long-lived processes; sole compile lease explicitly released. Generated source, candidate and evidence are intentionally retained for root runtime measurement and review. Shared cache and managed worktree cleanup remain root-owned. No commit/push/PR/issue/merge or production edits by this worker.

## Root matched measurement

Apple M2 Pro /16GiB, same Codex IAB Chrome155 BrowserWebGpu,1280×720 scale1, identical no-store gzip server on127.0.0.1:9201. One Nvwa renderer, no task compilation during formal measurements. Order A1,B1,B2,A2,A3,B3; each navigation records600 recent samples after readiness+1s warmup and15s observation. Both arms use untouched product HTML, fixed default Work for Studio idle and identical fixed9s Work for Player. Logs are explicitly sliced into the two navigations; duplicate/missing/incomplete product requests fail the sum. Startup first_asset_ready_seconds uses Bevy TimeReal since first update, not navigation-to-ready. Finite sample windows mix active animation and completed held pose because observation occurs around15s after completion at9s; they are not motion-only cadence.

| Workload | A p95 ms, repetitions1/2/3 | B p95 ms, repetitions1/2/3 | Median change | Pair limit |
|---|---|---|---|---|
| Continuous idle |19.7 /18.8 /18.6|19.1 /20.9 /20.1|+6.91%|pair2 +11.17%, exceeds10%|
| Finite sequence + held endpoint |18.1 /20.4 /19.5|20.0 /18.9 /18.2|-3.08%|pair1 +10.50%, exceeds10%|

These are Rust main-loop cadence, not GPU/display timing. Small sample count and variation do not establish a causal regression, nor prove equivalence. Medians do not erase pair breaches. Keep B as a reproducible candidate, preserve current default, and predefine a bounded quieter follow-up. Root independently reran native with the exact frozen artifact: visible nonblack1280×720 capture,600 samples, Metal, p95 main-loop18.5903ms. The earlier all-black native capture remains FAILED and is excluded.

[Matched raw reports and arithmetic](../../docs/evidence/m1-1/matched-comparison.json), [B HTTP audit](../../docs/evidence/m1-1/B-http-audit.json), [functional states](../../docs/evidence/m1-1/B-functional-checks.json), and [root acceptance](../../docs/evidence/m1-1/ACCEPTANCE.md) retain the evidence and limits. Build evidence is tracked in `evidence/`; exact local artifacts survive under the primary checkout's `.work/m1-1/web-size/web`.
