# Bounded scale and IME provenance validation

PR31 merged to main at `8a922b39da9a83ac4735bf759babf17479f8f3f1`.
This follow-up addresses #3 and #32 through experiments22/23. It changes no
production Rust, asset, dependency or Cargo.lock. Three workers prepared the
isolated diagnostics and independently reviewed them; root exclusively operated
the shared desktop and serialized native/WebGPU runs. No heavy compilation,
paid service or hosted CI was requested.

## Actual results

| Scope | Result | Evidence and limit |
| --- | --- | --- |
| Formal native app | VERIFIED | Same frozen native binary actually rendered the real18-joint/4-morph/three-clip character. Logged physical2560×1440 at scale2.0, screenshot callback and exit0. Separate default-Work GUI clicks0→0.51→0, window enlargement/resize, click0→0.60→0 and single Undo passed. Native screenshots include the title bar; smoke dimensions describe content. This is not a display-scale transition. |
| Normal Chrome | VERIFIED | One actual100%→125%→100% session: canvas1512×806→1209.6×644.8→1512×806 and DPR2→2.5→2. Three exact Work click/caret intervals pass. |
| Fixed CSS Chrome | VERIFIED | Same production runtime in a disclosed static wrapper: parent AND canvas remain1100×640; backing2200×1280→2750×1600→2200×1280. Three exact Work click/caret intervals and source identity checks pass. |
| Whole Work editing | VERIFIED for clicks | At all three fixed-CSS phases, jaw changes by a single click, one Undo restores the entire baseline content, and revision increments once for each command. Nine exact downloaded Works are retained. This proves clicks, not continuous dragging. |
| Attempted tool drag | PARTIAL | Actual down/up endpoints at rows51/52, no held pointermove, no parameter change. The complete321-row trace contains no held canvas pointermove. Physical continuous dragging in this wrapper remains NOT-RUN. |
| IME hook selftest | VERIFIED for synthetic control | Actual Chrome Start→known local synthetic dispatch→Stop→Export yields three untrusted length2 composition events with exact event/dispatch IDs and witnessed callstacks. This establishes the local realm hook only. |
| Physical plain/Nvwa IME pair | PENDING | Two prepared125% tabs use the same collector/package. Root requested one actual input/Space confirmation in each, candidate placement, once-only text result and exact OS input-method identity. A synthetic selftest never supplies this evidence. |
| Original #3 trigger | NOT-RUN | Current IAB viewport API has no simulated-DPR control. Ordinary Chrome zoom and the fixed wrapper do not reproduce or explain the original IAB condition. Physical display migration and other platforms remain unverified. |
| Original #32 event710 | UNKNOWN | The prior untrusted length2 compositionend retains its original uncertainty. A new witnessed event would identify that new local dispatch; it would not retroactively identify event710. |

Engine: installed Chrome154.0.8037.97, macOS27.0.1 build26A434. The native GPU is
Apple M2 Pro/Metal. [Runtime identity](runtime-metadata.json) pins the reused
native/JS/Wasm hashes. The31 production inputs still match the accepted PR30
build cohort. Its103 Rust tests and dual builds are historical results, not new
compilation/test claims. This turn reran actual apps and diagnostic controls.
The native smoke logs contain cadence samples; this was a functional capture,
not a formal isolated performance measurement.

## Rejected evidence and repairs

The initial passive scale observer used capture-phase window focus/blur listeners
without checking the event target. Descendant canvas/proxy focus changes were
therefore labeled window events. The strict checker rejected all three initial
intervals. Their exact raw files and v1 observer/package are retained. The raw
rows do not contain event targets for these categories, so their origin cannot
be recovered from the files alone.

The actual-collector semantic control failed before the two callbacks were
filtered to `event.target === window`. It passes afterward, retaining actual
window focus/blur while rejecting descendant misclassification. New v2 packages
and captures use new hashes; v1 captures are never relabeled. A separate initial
click establishes focus; the judged second click occurs after250ms. The
existing experiment20 focus/scale checks are unchanged. This was one justified
normal/fixed comparison repeat after a diagnostic gap, not a speculative product
workaround.

Independent review also found two false-pass paths: impossible rolling-buffer
truncation and contradictory IME hook/module/case timestamps. Both checkers now
reject them. Scale inventory/focus red-before/green-after logs are archived.
The35 IME chronology failures were reported by the worker's truncated tool
output; no complete original red log was saved. Current20-test green output is
archived and independently reproduced. In total26 scale and20 IME checker tests
pass, plus three package mutation controls and actual-collector forwarding/focus
controls. The missing native capture in an initial shell attempt
was caused by a relative `--work` argument. The visible error was preserved,
that run was terminated130, and the corrected absolute-path command exited0.

## Reproduction and offline review

From repository root, no browser, `.work`, `dist` or third-party Python packages
are needed to inspect the committed packet:

```sh
python3 -B docs/evidence/bounded-scale-ime/verify.py
python3 -B experiments/22-fixed-css-dpr/test_controls.py -v
node experiments/22-fixed-css-dpr/test_collector.js
python3 -B experiments/23-ime-event-provenance/test_checker.py
```

Preparation mutation controls are separate. They require the unchanged accepted
`dist/web` bundle (index/JS/Wasm) and this private parent directory:

```sh
mkdir -p .work/bounded-scale-ime/issue32
python3 -B experiments/23-ime-event-provenance/test_prepare.py
```

The [manifest](MANIFEST.json) hashes every raw artifact and the executed checkers.
Archived wrapper/collector bytes are checked against their sidecars. IME captures
do not embed source hashes; root binds each exact run UUID/page/package hash in
[observations](observations.json). The verifier checks that binding, but cannot
prove unobserved physical input, complete UI behavior or an unknown origin.
Visible Work bounds are screenshot estimates, with canvas origin included;
the hidden1px proxy is an anchor, not a visible OS candidate-box measurement.

For actual UI reproduction, rebuild/package normally if `dist` is absent, then
use the fresh-output preparation and root-owned server commands in
[experiment22](../../../experiments/22-fixed-css-dpr/README.md) and
[experiment23](../../../experiments/23-ime-event-provenance/README.md).
Do not reuse nonempty staging outputs. Use one active renderer at a time.
The diagnostic dispatch hook has disclosed identity/timing effects and cannot
observe other realms, saved native methods, browser/OS internals or providers.
Unwitnessed origins remain UNKNOWN. Close/reload the diagnostic page to remove
the instrumentation.

PARTIAL — Current Mac/native and Chrome click/scale/Undo controls pass. Physical
IME comparison is pending; original IAB cause, fixed-CSS continuous dragging,
physical display migration and other platforms remain unverified.
