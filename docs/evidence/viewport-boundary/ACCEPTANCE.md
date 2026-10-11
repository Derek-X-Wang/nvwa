# Actual viewport and native HiDPI acceptance

The current PR21 release was reused without rebuilding or changing product files. The disposable diagnostic preserves the Wasm, generated JS and assets; only the copied HTML and its gzip sidecar change. The actual gzip-negotiated response contains the collector. See [manifest](bundle-manifest.json) and [served identity](served-index.json).

| Actual case | CSS/client and canvas buffer | DPR | Real edit / one Undo |
|---|---|---:|---|
| Initial Web |1280×720 /1280×720|1|Opened exchanged revision9; typed task-owned Work name and saved baseline|
| Larger Web |1600×900 /1600×900|1|Jaw0.90→0.37→0.90; revision9→10→11|
| Smaller Web |1024×768 /1024×768|1|Jaw0.90→0.30→0.90; revision11→12→13|
| Restored Web |1280×720 /1280×720|1|Focused Work and typed again; drawn caret and geometry retained|
| Ordinary native HiDPI |Prior same-artifact smoke: physical2560×1440, scale2; GUI screenshot includes decoration|2|Track click0.90→0.34→0.90; revision9→10→11; ordinary GUI Save|

The two Web cases used actual continuous pointer drags. Each release created one revision. Whole saved documents differ only in jaw width and revision; each Undo restores every baseline field except revision. [Web comparison](web-document-comparison.json) and [native comparison](native-document-comparison.json) retain these assertions. The small case starts from revision11; comparison uses the revision9 document with revision excluded.

Screens show the real character, focused Work text and drawn caret. Passive geometry records canvas CSS/buffer, resize observations and the invisible input proxy while focused. Samples run at1Hz and may precede the last typed character; they do not prove exact per-frame caret alignment or observe egui scale directly. No clipboard or input value is collected by the diagnostic.

The native action was a track click, not automated continuous dragging. Earlier user-performed native drag/IME/clipboard/refocus acceptance remains separately attributed. This run does not repeat physical IME testing. A second default native process was unintentionally launched by app selection; it was identified by exact path/PID and terminated after the GUI test. Both owned native processes exited before startup measurements.

The initial reset screenshot briefly represented the previous viewport scaled into the restored surface. The next settled DOM sample and screen reported1280×720 atDPR1, and focused typing worked. No persistent stale ratio was reproduced.

Two diagnostic failures remain retained: an unchanged gzip sidecar initially bypassed the collector, and Python3.9 lacked `hashlib.file_digest`. The installer now regenerates the sidecar deterministically and hashes in chunks. Independent R2 rereview accepted both fixes; actual Python3.9 installation and actual HTTP delivery passed.

VERIFIED — Actual Web resize, focused text/caret, drag/one Undo, whole-document persistence and viewport reset; native scale2 track-click/Undo/Save. Task renderer tabs closed, override reset and diagnostic server stopped.

NOT-RUN — Actual browser zoom or changed Web DPR, real browser-tab hide/show, arbitrary browsers/platforms, exact egui/camera scale observation and current physical IME retest. The original DPR simulation failure remains unreproduced; #2/#3 stay open.

Raw passive geometry captures are retained losslessly as `web-*-geometry.json.gz`; [stage summaries](web-geometry-summary.json) preserve settled dimensions and focused proxy rectangles. Decoded hashes/byte counts are recorded. Decode with Python stdlib: `json.load(gzip.open("PATH.json.gz"))`.
