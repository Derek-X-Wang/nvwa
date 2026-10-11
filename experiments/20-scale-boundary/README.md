# Issue 3: real Web input/scale boundary loop

Prepared on `codex/input-scale-validation` at merged main
`93c77d5d8409a6b142c1aeaa07a50b594bcecb29`. This experiment adds a passive
collector around the existing production Web package. It adds no Rust code,
dependencies, event replay, browser API override, or canvas/input geometry change.

**PARTIAL**: collector syntax, package preparation, whole-Work positive check and
three negative checks ran. Current WebGPU interaction and the original DPR
transition remain **NOT-RUN** by this worker. Root owns browser/GPU/server use.
No sizing fix or cause is proposed.

## Files and prepared package

- `collector.js`: actual DOM geometry and trusted pointer/input event classes.
  It does not read entered text or clipboard. A hidden `pre` receives bounded
  JSON (last 800 rows). Its hidden status does not change canvas layout.
- `prepare.py`: writes a private page whose original production HTML gains only
  source metadata and the collector script. JS, Wasm and assets are symlinks to
  the existing production package. The production package is never changed.
- `check.py`: numeric click/caret boundary check and complete saved-Work check.
- `.work/input-scale/issue3/web-probe/`: prepared using `.work/ui26/web-final/`.
  Its Wasm SHA256 is
  `884134fc98d54e3476dbc799ffdd5cc6b88f69121ddfb649ed9ba9be96156dba`, matching
  the final Web artifact recorded in `docs/evidence/m1-1-ui/ACCEPTANCE.md:26`.
  Root must verify the current served bytes/source identity before a new claim.

Preparation (already run):

```sh
node --check experiments/20-scale-boundary/collector.js
python3 -B experiments/20-scale-boundary/prepare.py \
  --web-package .work/ui26/web-final \
  --output .work/input-scale/issue3/web-probe
```

The output refuses a nonempty existing directory. Use another empty directory
under `.work/input-scale/issue3/` for a fresh package. Root should serve that
directory with its approved existing server/port workflow. Do not use benchmark
mode: it deliberately forces physical1280×720 with scale factor1.

## Root diagnostic protocol

1. Verify the root browser has real WebGPU and serve the private package. Open
   a fresh task-owned Work, for example
   `?work=works/exchanged.nvwa.json&scale_case=dpr1-baseline`. Preserve current
   user preview/input. Capture a current screenshot and source/Wasm hashes.
2. At a known CSS size and actual DPR1, record the screenshot-derived visible
   Work field rectangle as `[x,y,width,height]` in CSS coordinates. Use the real
   UI pointer to click its center. Wait at least250ms for rendering/caret update.
   Read the collector JSON. Do not call its mutating API through evaluation.
3. Type a task-owned Work filename using the real keyboard path. Capture the
   rendered field/sentinel and caret proxy. The collector intentionally does not
   read text. Save the complete baseline Work through the production Save button.
4. Capture the actual visible jaw-width slider and drag its real knob to change
   the value by at least0.05. Capture the pointer trace, current screenshot and
   complete changed Work through production Save. One Undo must restore the
   complete baseline Work; save that result. Work filename edits do not modify
   the portable document revision.
5. Apply an **actual supported DPR transition** while keeping CSS size fixed.
   Capture observed `devicePixelRatio`, canvas CSS/backing sizes and the current
   screenshot before choosing click/drag coordinates. Repeat steps2–4 at the
   changed scale. A width/height resize at DPR1 is a control, not the original
   trigger. A zoom shortcut that leaves reported DPR/scale unchanged does not
   establish a changed-scale case. Current IAB viewport capability only exposes
   width/height; keep DPR emulation **NOT-RUN** if no supported trigger exists.
6. Restore root's prior viewport/browser state. Preserve all actual JSON,
   screenshots, saved Works and source identifiers under the task evidence dir.

Read-only extraction through the root browser's permitted evaluation path:

```js
document.getElementById('nvwa-scale-probe-json').textContent
```

For a compact row inventory (also read-only):

```js
JSON.parse(document.getElementById('nvwa-scale-probe-json').textContent).rows
  .filter(r => r.kind === 'pointerdown' || r.kind === 'settled')
  .map(r => ({index:r.index,kind:r.kind,after:r.after,timeMs:r.timeMs,
    client:r.client,dpr:r.geometry.dpr,active:r.geometry.activeElement,
    caret:r.geometry.caret,canvas:r.geometry.canvas}))
```

Save the returned text as a task-local capture JSON. Select the trusted
pointerdown index and its `settled`/`after:pointerdown` row. Do not select a later
typing snapshot to prove the earlier click. Supply the independently
screenshot-derived Work rectangle:

```sh
python3 -B experiments/20-scale-boundary/check.py geometry CAPTURE.json \
  --row SETTLED_INDEX --pointer POINTERDOWN_INDEX \
  --expected-dpr ACTUAL_REQUIRED_DPR --expected-css CSS_WIDTH CSS_HEIGHT \
  --work-rect X Y WIDTH HEIGHT
python3 -B experiments/20-scale-boundary/check.py work \
  BASE.nvwa.json DRAG.nvwa.json UNDO.nvwa.json
```

`geometry` goes red when a real click inside the visible Work field fails to
focus the production textarea proxy, or its caret is outside the visible field.
It also checks the actual CSS/client/backing/DPR arithmetic. That arithmetic
failure alone is a boundary observation, not proof of the user's exact symptom.
`work` goes red if a visible jaw drag makes no real edit, commits more than once,
changes another Work field, or one Undo fails to restore the complete document.
For failure diagnosis, retain the pointer drag start/end screenshot targets and
trusted trace; the saved value alone does not establish where the pointer landed.

Both checks and screenshots together form the intended symptom loop. Until root
runs them against real before/after DPR captures, Phase1 of diagnosing-bugs is
incomplete. These scripts do not drive the GUI unattended.

## Source identifiers and observability limit

- `web/index.html`: canvas CSS fills the page; bootstrap starts production Wasm.
- `crates/nvwa-studio/src/lib.rs:97`: regular Web window selects `#nvwa` and
  `fit_canvas_to_parent=true`. Lines111–118 give benchmark-only scale override.
- `crates/nvwa-studio/src/lib.rs:1026`: production Work TextEdit call.
- `crates/nvwa-studio/src/web_input.rs:649`: actual caret conversion is egui
  points × pixels-per-point × CSS/backing ratio; lines661–670 set the proxy
  position and lines671–673 transfer focus through the normal path.

Collector reports actual CSS/client rectangles, physical canvas width/height,
devicePixelRatio, visual viewport, caret rectangle/style and pointer coordinates.
The app does not expose live Rust `Window.scale_factor`, egui
`pixels_per_point`, egui control rectangles or cursor-rect values in the DOM.
Those remain **unknown**, rather than values inferred and labeled as measured.
The available `NVWA_EVIDENCE` output reports physical window and scale once in
smoke mode; smoke/benchmark runs do not substitute for this interactive loop.

## Verification actually run

The historical actual viewport documents pass the stronger complete-Work check:

```sh
python3 -B experiments/20-scale-boundary/check.py work \
  docs/evidence/viewport/viewport-base.nvwa.json \
  docs/evidence/viewport/viewport-drag.nvwa.json \
  docs/evidence/viewport/viewport-undo.nvwa.json
```

Result: `PASS`, jaw0.53→0.85, revisions6→7→8, all other fields preserved.
Offline sensitivity checks using copies of those actual documents reject a
missing jaw delta, a collateral smile edit and an incomplete timeline Undo.
Results are `.work/input-scale/issue3/checker-negative-results.json`.
These prove checker behavior only. No current browser capture was fabricated.

No server, GUI, browser process, Cargo build/test, commit, push, production source
write, shared contract change or accepted-record edit ran from this worker.
Only experiment20 and `.work/input-scale/issue3/` were written.

## Targeted checker rereview

Root supplied an actual Chrome packet at
`.work/input-scale/chrome-tab-return-scale.json`. This worker read it without
changing it. Reviewer screenshot bounds are approximately `[257,1,222,22]`;
these remain screenshot observations, not exported Rust control rectangles.

The original checker falsely passed pointer54 at55450.6ms paired with typing
row242 at92661ms. It also passed both exact reviewer JSON mutants: only click
geometry changed toDPR1/backing1512×806, and an intervening outside canvas click
inserted as index999 immediately before row242. These mutations are in-memory
checker sensitivity inputs, never browser events or fabricated current captures.

The repaired checker requires:

- A `settled`/`after:pointerdown` row249–1000ms after the tested click. Frozen
  collector schedules this timer250ms after each pointerdown. One ms allows timer
  precision; the1s deadline allows750ms of scheduler delay. A delayed observation
  beyond1s cannot establish this bounded click result; it is not proof of a
  product defect. Select a new real click capture instead of extending the age.
- Matching actual DPR, CSS/client/backing and viewport geometry at the pointer,
  settled row and every retained intervening record. Any resize/scale event,
  second pointerdown or cancellation invalidates the pair, even if the final
  geometry is restored. Real typing and caret movement are allowed.
- Continuous document focus and paired focus handovers inside the production
  canvas/textarea. The normal Work click briefly emits canvas `focusout` before
  textarea `focusin`; rejecting that handover would reject the real valid case.
  External or unresolved focus loss invalidates the pair.
- Unique, strictly increasing, gap-free indices and chronological timestamps.
  Every result inventories first/last index, count, gaps and prefix truncation.
  A retained tail can prove only its selected click interval. It cannot become
  whole-session proof; every result explicitly reports that scope.

Frozen collector limits remain: only canvas pointer events are recorded, so
outside-DOM clicks may be unobserved. The checker rejects any intervening pointer
record it receives and any observed loss of focus. It cannot assert that the
collector observed every global event. Settled records lack an explicit origin
event ID; the repaired assertion gives bounded chronological association, not
an independently recorded timer-origin identity. Collector and live package were
not changed during this rereview.

Actual valid pair70→127 passes. It spans250.9ms atDPR2, canvas CSS1512×806,
backing3024×1612, and caret373.375/21.25. Real typing occurs inside that interval.
The full packet has243 records, indices0–242, with no gaps or duplicates. The
packet does not end with `stopped`, so it also cannot establish completed-session
coverage.

Recorded original targeted red/green commands used the private packet above.
Those runs and paths are preserved in the rereview report. For a current rerun
against that private packet, explicitly set
`NVWA_GEOMETRY_CAPTURE=.work/input-scale/chrome-tab-return-scale.json`:

```sh
# Preserved old checker: expected red13 missing-rejection assertions and one
# missing-inventory result-schema error. Positive actual pair still passes.
NVWA_GEOMETRY_CAPTURE=.work/input-scale/chrome-tab-return-scale.json \
CHECKER_PATH=.work/input-scale/issue3/check-before-rereview.py \
  python3 -B experiments/20-scale-boundary/test_geometry.py
# Repaired checker: all15 tests pass, including exact actual/reviewer mutants.
NVWA_GEOMETRY_CAPTURE=.work/input-scale/chrome-tab-return-scale.json \
python3 -B experiments/20-scale-boundary/test_geometry.py
# Actual close pair: PASS.
python3 -B experiments/20-scale-boundary/check.py geometry \
  .work/input-scale/chrome-tab-return-scale.json \
  --pointer 70 --row 127 --expected-dpr 2 --expected-css 1512 806 \
  --work-rect 257 1 222 22
# Original mismatched pair: FAIL; row242 is a later typing snapshot.
python3 -B experiments/20-scale-boundary/check.py geometry \
  .work/input-scale/chrome-tab-return-scale.json \
  --pointer 54 --row 242 --expected-dpr 2 --expected-css 1512 806 \
  --work-rect 257 1 222 22
# Explicit capture coverage inventory.
python3 -B experiments/20-scale-boundary/check.py inventory \
  .work/input-scale/chrome-tab-return-scale.json
```

This repairs the evidence checker. It does not establish the original IAB DPR
failure or select a production scaling fix. Root owns subsequent live captures,
integration, review and publication.

## Fresh-checkout replay

The targeted test defaults to the exact published raw packet at
`docs/evidence/input-scale/observed/chrome-tab-return-scale.json`. Root owns that
copy and its publication. No private `.work/` directory is needed for the normal
targeted test:

```sh
python3 -B experiments/20-scale-boundary/test_geometry.py
python3 -B experiments/20-scale-boundary/check.py geometry \
  docs/evidence/input-scale/observed/chrome-tab-return-scale.json \
  --pointer 70 --row 127 --expected-dpr 2 --expected-css 1512 806 \
  --work-rect 257 1 222 22
python3 -B experiments/20-scale-boundary/check.py inventory \
  docs/evidence/input-scale/observed/chrome-tab-return-scale.json
```

`NVWA_GEOMETRY_CAPTURE` accepts a task-specific explicit capture override. Relative
paths resolve from the repository root; absolute paths are also accepted. A
missing or invalid packet fails the test. The test does not skip, manufacture a
fixture, or silently select a different packet. Original private capture paths,
before/after results and hashes remain recorded in the private rereview report.

## Integrated actual results

Root subsequently ran actual Chrome tab/zoom and physical acceptance. See
[the attributed acceptance packet](../../docs/evidence/input-scale/ACCEPTANCE.md)
for results, exact raw copies, offline commands, review fixes and explicit limits.
Worker-only NOT-RUN statements above describe the preparation stage.
