# Bounded issue3 fixed-CSS actual-DPR comparison

Preparation only at merged main `8a922b39da9a83ac4735bf759babf17479f8f3f1`,
in `codex/bounded-scale-ime`. No product fix or cause is proposed. This is a
throwaway Web wrapper around the exact existing `dist/web` JS/Wasm/assets.
Root owns server, browser, GPU, screenshots and physical validation. This worker
ran no GUI, server, Cargo build, Git mutation or shared source edits.

PARTIAL — two packages and offline sensitivity checks pass; actual Chrome
normal/fixed comparison and original IAB condition remain NOT-RUN by this worker.

## Disclosed observer and geometry differences

`prepare.py` stages two disjoint pages using the same `collector.js`. `normal`
preserves the production canvas/body geometry. `fixed` puts the production canvas
inside a static top-left parent1100×640 CSS pixels, with no margin, border or
padding. The existing canvas100% CSS rule and production bootstrap remain intact.
No devicePixelRatio override, emulation API, event dispatch or Rust changes exist.
The static parent does not establish a new positioning context for the production
body-level caret proxy.

Normal Export/Stop buttons overlay the bottom-right90 CSS pixels of the canvas.
Fixed Export/Stop buttons are outside the canvas at left1110/top0 and top50. They
change focus after the tested interaction. Root must exclude their region from
interaction targets. Ensure the actual viewport is at least1200×640 at125% so the
fixed surface and buttons remain visible. A clipped surface fails the checker.

The passive observer records all-document pointer endpoints, pointer moves only
while buttons are held, focus classes, DOM caret/canvas metadata, whole-window
viewport, visualViewport, scroll, parent/canvas transforms, actual DPR and backing.
Targets outside the known canvas/proxy/buttons are classified `other`; no arbitrary
element IDs, input text, clipboard, keys or composition contents are collected.
Each settled pointer timer records its exact origin index, pointerId and timestamp.
The observer keeps1200 newest rows and accounts for dropped prefixes explicitly.
There is no global mutating probe API. Only real user-activated Export/Stop buttons
publish JSON. Stop cancels pending timers/listeners, disconnects the observer and
appends an explicit `stopped` end marker. Export is synchronous, with one geometry
snapshot per row. Document snapshots can span browser state changes; they are not
atomic Rust/egui state reads.

Production Rust scale factor, egui pixels-per-point and Rust control bounds are
not exposed. DPR and canvas arithmetic are DOM measurements, not those values.
Screenshot-derived Work bounds must include the actual canvas origin. The wrapper
at origin0 simplifies that conversion, but does not turn hidden DOM geometry into
visible control bounds.

## Preparation and identity

Already run, without rebuilding:

```sh
node --check experiments/22-fixed-css-dpr/collector.js
python3 -B experiments/22-fixed-css-dpr/prepare.py --layout normal \
  --output .work/bounded-scale-ime/issue3/web-normal
python3 -B experiments/22-fixed-css-dpr/prepare.py --layout fixed \
  --output .work/bounded-scale-ime/issue3/web-fixed
python3 -B experiments/22-fixed-css-dpr/check.py package \
  .work/bounded-scale-ime/issue3/web-normal/probe-package.json
python3 -B experiments/22-fixed-css-dpr/check.py package \
  .work/bounded-scale-ime/issue3/web-fixed/probe-package.json
python3 -B experiments/22-fixed-css-dpr/test_controls.py -v
```

The preparer refuses existing nonempty outputs. Use a new subdirectory under
`.work/bounded-scale-ime/issue3/` for a fresh staging run. Existing package checks
recompute all26 production file hashes, the exact wrapper hash and observer hash.
Capture source metadata must equal the independently pinned package sidecar.
Changing served source bytes makes the check fail. Root should preserve those
manifests with any actual captures and recheck identity before acceptance.

| File | SHA256 |
| --- | --- |
| production index | `73ea243ebc795ec5d405489e8aaeaca4ebe18b537e4b90fa433f5bbe0e2f5114` |
| production JS | `9ff532cbedc6a814c4b8337c4b82f436de452e7b7fbc8c9e58bfda2e90ad6c5c` |
| production Wasm | `884134fc98d54e3476dbc799ffdd5cc6b88f69121ddfb649ed9ba9be96156dba` |
| collector | `ba902ae5fcb87966cd95aac3f81c46049870554250cd09a855914245565db8d2` |
| normal wrapper | `ab4872b12cd344905d40e7d7712d38d3aac1346fe73b9329a3ccf22c8ac945fc` |
| fixed wrapper | `721bbd78596d6949d27979a92db9ba2e27f436919772dd684c1dd6b19978ce1c` |

Preparation JSON, both package check logs and the25-control log are under
`.work/bounded-scale-ime/issue3/`. Controls are synthetic offline verifier inputs,
not invented current captures. The Work positive control uses the actual historical
`docs/evidence/viewport/viewport-{base,drag,undo}.nvwa.json` documents. Mutants reject
no jaw change, collateral Work edits, extra commits and incomplete Undo.

## Small root UI protocol

1. Use one real Chrome product page. Navigate to the staged `web-normal/index.html`
   with `?work=works/m1-sequence.nvwa.json`. Never use benchmark mode. Confirm
   the source manifest and real WebGPU character, then capture current viewport,
   canvas and browser zoom100%. Do not enlarge or change the window during the
   comparison once the whole fixed surface will fit at125%.
2. At each actual100→125→100 phase, capture the visible Work rectangle in CSS
   coordinates, click its center with the native pointer, wait at least250ms,
   capture the visible caret and click Export. Select pointerdown and the settled
   row whose originIndex equals that pointerdown index. Record actual DPR; expected
   on this host is2→2.5→2, but a different value is measured evidence, not a value
   to replace. Stop and export after the final normal phase.
3. Navigate the same tab to `web-fixed/index.html` with the same Work. Repeat the
   exact100→125→100 sequence. Verify BOTH parent and canvas remain1100×640 CSS at
   each phase while backing tracks actualDPR (expected2200×1280 →2750×1600
   →2200×1280). Window viewport is expected to change with Chrome zoom. Capture it
   separately. The normal case is the comparison control, not original-bug proof.
4. In the fixed case, at each phase save complete baseline Work, visibly drag the
   jaw knob by at least0.05, save changed Work, perform one Undo and save restored
   Work. Keep current screenshots and pointer trace for the actual slider target.
   Work filenames are UI state, not portable document fields. Save/export focus
   activity occurs outside the selected click interval. Final Stop/export proves
   observation ended; a retained prefix still limits whole-session coverage.
5. Restore Chrome100% and preserve exact raw JSON, manifests, screenshots and
   complete saved Works. Stop after this one normal/fixed comparison; add one
   focused follow-up only if an observed failure or evidence gap justifies it.

Root may read the exported packet without modifying application state:

```js
document.getElementById('nvwa-fixed-css-json').textContent
```

Numeric checks, substituting real capture names/indices/screenshot observations:

```sh
# Normal control: current CSS is separately measured, e.g.1512x806 at100%.
python3 -B experiments/22-fixed-css-dpr/check.py geometry NORMAL.json \
  --manifest .work/bounded-scale-ime/issue3/web-normal/probe-package.json \
  --pointer POINTER --row SETTLED --expected-dpr DPR \
  --expected-css WIDTH HEIGHT --work-rect X Y WIDTH HEIGHT
# Fixed canvas: exact1100x640 contract is built into the checker.
python3 -B experiments/22-fixed-css-dpr/check.py geometry FIXED.json \
  --manifest .work/bounded-scale-ime/issue3/web-fixed/probe-package.json \
  --pointer POINTER --row SETTLED --expected-dpr DPR --work-rect X Y WIDTH HEIGHT
python3 -B experiments/22-fixed-css-dpr/check.py transition FIX100.json FIX125.json FIXRESET.json \
  --manifest .work/bounded-scale-ime/issue3/web-fixed/probe-package.json \
  --pointers P100 P125 PRESET --rows R100 R125 RRESET --dprs 2 2.5 2 \
  --work-rects X100 Y100 W100 H100 X125 Y125 W125 H125 XR YR WR HR
python3 -B experiments/22-fixed-css-dpr/check.py work BASE.nvwa.json DRAG.nvwa.json UNDO.nvwa.json
python3 -B experiments/22-fixed-css-dpr/check.py inventory FINAL-STOP.json
```

The inherited experiment20 checks require249–1000ms click/settled age, trusted
canvas click, matching phase geometry, internal focus transfer, no intervening
pointer/focus/scale/resize change and a caret inside the independently observed
Work bounds. New checks require exact recorded timer identity, parent/scroll
coherence, complete drop accounting and matching source identity. The transition
checks one session, chronological phases, actual1.25 DPR ratio and immutable common
rows across cumulative exports. Whole Work checks require exactly one drag commit,
one Undo revision, only jaw change and complete baseline content restoration.

Passing these together with current visible screenshots establishes only the
bounded actual Chrome control. Browser zoom changes CSS and DPR together in the
normal case. The fixed wrapper isolates canvas CSS but does not reproduce original
IAB simulated-DPR behavior or physical display migration. Original IAB capability
remains unavailable; Rust scale/cause remain unknown. A failed checker can indicate
an observation gap and does not by itself establish a product defect.

## Bounded observer follow-up

The initial actual normal100/125/reset captures remain immutable in the owned
task directory. They fail conservative click checks. A capture-phase `window`
focus/blur listener incorrectly classified descendant canvas/textarea focus/blur
as window events because its callback omitted an event-target filter. The raw
packets report `documentFocused:true` at those rows. Their omitted targets cannot
be recovered from raw JSON, so the initial traces remain observation limits.
No CUA focus-loss or product defect is inferred from those event labels.

Root authorized one focused observer follow-up. The collector change is exactly
two callback filters, `event.target === window`. The actual collector semantic
control in `test_collector.js` fails before this change on descendant canvas blur;
afterward it passes descendant blur/focus rejection and genuine window blur/focus
retention. This is an offline DOM-shaped VM control, not a browser capture.
The checker retains its existing window-blur rejection and pointerdown association.
Switching to a pointerup timer would change the tested interval and is not accepted.

Revised source is staged in NEW `web-normal-v2/` and `web-fixed-v2/` directories.
The v1 packages, manifests, observer bytes and captures remain unchanged. The v2
collector SHA256 is `8cd6a3c9fc19878acdc06f5d520c49864c7cf046c6d998f0ada71dce65802477`.
Normal v2 wrapper is `15e60ff02944da72e0a7e98259e25371d45feaf54635b695265dbb95f2872fba`;
fixed v2 wrapper is `2969b70aa1cb0f0a224075ccd406a8d9e66ae2894ede45928fe2782a05acd23d`.
Use their v2 manifests for fresh capture checks.

The initial125/reset clicks also begin while the export button owns focus. This
falls outside the strict inherited app-internal focus interval. For fresh v2
phases, first click Work to establish focus, wait250ms, then make one separate
Work click for the measured interval. Preserve both clicks. This changes capture
setup, not the checker policy. Root owns fresh screenshots and actual interaction.

Independent review also found that inventory arithmetic accepted a fabricated
two-row retained tail with1200 drops. Inventory now requires
`retained=min(recorded,1200)` and `dropped=max(0,recorded-1200)`. The positive
retained-tail fixture has all1200 real synthetic rows; trimming it to two rows
is an explicit rejection control. The new control is red before the checker
repair and all26 controls pass afterward. Before/after logs, immutable v1 capture
hashes and rejection limits are in `.work/bounded-scale-ime/issue3/`.

```sh
node experiments/22-fixed-css-dpr/test_collector.js
python3 -B experiments/22-fixed-css-dpr/test_controls.py -v
python3 -B experiments/22-fixed-css-dpr/check.py package \
  .work/bounded-scale-ime/issue3/web-normal-v2/probe-package.json
python3 -B experiments/22-fixed-css-dpr/check.py package \
  .work/bounded-scale-ime/issue3/web-fixed-v2/probe-package.json
```

VERIFIED — offline observer semantics and26 verifier controls pass; all four
staged package identities match. Fresh v2 browser acceptance remains root-owned.
