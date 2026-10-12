# Issue 2 browser return diagnostic

This is a passive wrapper around the existing production Web bundle. It installs no production hooks. It never dispatches composition, changes focus, reads clipboard contents or records arbitrary input text. Root owns browser operation, package identity, serving and screenshots. No product defect has been reproduced by this worker.

## Root preparation

Run from this checkout:

```sh
python3 experiments/19-input-focus-recovery/prepare.py
```

Preparation stages `recovery.html`, `recovery-capture.js` and an artifact hash manifest under `.work/input-scale/issue2/`. It reads the existing bundle without changing it. Root can copy the two staged wrapper files beside the unchanged `dist/web/index.html`, then use the root-owned server. Do not copy `preparation.json` into the served package. Confirm the JS/Wasm hashes against the root's accepted PR30 build provenance before calling this a current-source run. If that provenance is absent, label the browser result bundle-specific.

## Natural tab-return loop

1. Open `http://127.0.0.1:9201/recovery.html?work=works/m1-sequence.nvwa.json` using the actual root-owned browser URL/port. The collector starts automatically and writes metadata JSON into hidden `pre#nvwa-recovery-json`.
2. Click the real canvas Work field. Use Command+A and type `nvwa-issue2-before`. Capture the rendered baseline Work value.
3. Activate another browser tab through a real supported UI action. Creating a background tab does not prove departure. A captured `pageFocused=false` or `visibility=hidden` must occur after baseline input.
4. Return through browser tab UI. Do not click the Work field or canvas again. Type `-after.nvwa.json`. Capture the rendered Work value. Exact required outcome: `nvwa-issue2-before-after.nvwa.json`, with baseline preserved and suffix inserted once.
5. Click Save. Record the real download filename. Production `platform.rs` takes that filename from the canonical `StudioUi.file_path`; this is independent corroboration when no slash is in the sentinel. A filename collision may cause the browser to append a suffix; use a clean task-owned download destination or record the browser adjustment explicitly. Download alone does not prove durable filesystem completion.
6. Extract `document.getElementById('nvwa-recovery-json').textContent` with read-only browser evaluation and save its returned string as `.work/input-scale/issue2/tab-return.json`. Extraction changes no page state. Do not call `nvwaRecovery.start/mark` through evaluation.
7. Root writes `.work/input-scale/issue2/tab-return-observation.json` with only task sentinel evidence, for example:

```json
{
  "observer": "root CUA; rendered canvas inspection",
  "returnTrigger": "browser-tab",
  "baselineWork": "nvwa-issue2-before",
  "baselineEvidence": ".work/input-scale/issue2/tab-return-baseline.png",
  "renderedWork": "nvwa-issue2-before-after.nvwa.json",
  "renderedEvidence": ".work/input-scale/issue2/tab-return-final.png",
  "downloadFilename": "nvwa-issue2-before-after.nvwa.json"
}
```

```sh
python3 experiments/19-input-focus-recovery/check.py \
  .work/input-scale/issue2/tab-return.json \
  --observation .work/input-scale/issue2/tab-return-observation.json
```

Exit 0 requires baseline trusted proxy input, actual departure attributed to browser-tab activation, visible focused return, trusted committed proxy input without an intervening canvas click, one visible active proxy, and exact observer-attributed baseline/final canonical text. Exit 1 reports a concrete mismatch. Exit 2 reports incomplete evidence. An observed trusted event means browser-generated input; it does not prove an OS IME candidate was visible. Root must inspect the screenshot itself; the checker validates attribution and the recorded result, not pixels.

If text disappears or the proxy fails to resume, preserve trace and screenshots privately before any retry. Inspect the chronological rows around blur/return, especially active element, hidden flag, proxy count and composing state. Do not change the adapter until the actual failure has been reproduced.

## Separate physical IME and scale checks

Use a fresh wrapper session for each physical IME/zoom condition, or reload before a new capture. The passive trace records trusted composition/input classes, payload character counts, composing flags, active element, document focus, device pixel ratio, viewport scale, proxy rectangle and canvas geometry. It intentionally stores no arbitrary composition text.

For physical Chinese IME, root/human must record candidate UI visibility and position before confirmation, Space/Enter candidate confirmation, exact committed Work outcome, cancellation behavior and app/tab-return recovery. Synthetic DOM composition, trusted input flags, callback logs or the absence of errors cannot replace that physical observation.

For zoom/DPR, record the exact browser zoom setting, observed `dpr`/`visualScale`, and a screenshot with the OS candidate menu relative to the actual Work caret. Geometry alone cannot establish correct candidate placement because the Rust caret rectangle is not exposed in the DOM. Tab-return checker always leaves physical IME and zoom/DPR as NOT-RUN.

## Scope and cleanup

Only `experiments/19-input-focus-recovery/` and `.work/input-scale/issue2/` are worker-owned. Root owns retention/integration and any copied diagnostic files in `dist/web/`. Close/reload the diagnostic page to remove the collector. No worker server/process was started, and no Rust/Cargo/dependency/source change or test compilation was performed. Raw traces and failed attempts stay in `.work/input-scale/issue2/`, outside public reports.
