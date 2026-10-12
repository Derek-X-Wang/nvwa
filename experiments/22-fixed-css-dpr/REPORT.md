# Bounded actual Chrome fixed-CSS DPR result

Actual Chrome100→125→100 zoom changes observed DPR2→2.5→2. The fixed wrapper
keeps BOTH parent and production canvas1100×640 CSS pixels, while backing changes
2200×1280→2750×1600→2200×1280. Six exact visible Work click/caret intervals pass,
including three normal-parent controls. At every fixed phase a slider CLICK
changes only jaw width with one revision, and one Undo restores the complete
baseline Work with one further revision. This is a bounded Chrome zoom control.
It is not reproduction of the original IAB simulated-DPR condition.

PARTIAL — actual fixed-CSS DPR/click/caret and whole-Work click/Undo checks pass;
continuous drag at fixed CSS, physical display migration and original IAB
reproduction remain NOT-RUN. No product source change or upstream cause is claimed.

## Attribution and scope

Root alone ran actual native Chrome UI, GPU, loopback server and screenshots.
This worker prepared experiment22 and rechecked root's exact raw JSON and complete
saved Works offline. Root reports installed Chrome154.0.8037.97 from application
metadata; captured User-Agent gives the less specific Chrome154.0.0.0. That UA
does not measure host OS or exact browser build. Native Studio regression and
human physical input checks are separate root-owned evidence, not acceptance
supplied by this report. This worker contacted no human, controlled no desktop,
and made no Git mutation, Cargo build, server or product edit.

The only wrapper geometry difference is the fixed static top-left CSS parent.
Production JS/Wasm/assets remain the existing `dist/web` bytes. The paired normal
control preserves body/canvas geometry. Both v2 pages use the same observer.
Normal export/stop buttons cover an unused bottom-right90 CSS-pixel area; fixed
buttons sit outside the canvas at left1110. Export changes focus after each judged
interval. Root established Work focus before the separate measured click at each
phase. No benchmark, DPR override or synthetic input replay was used by the
wrapper. Its download anchor activation exports JSON only.

## Actual selected intervals

Root's independently observed screenshot Work bounds are `[258,3,220,22]` in CSS
coordinates for all six cases, including canvas origin0/0. They are screenshot
observations, not hidden Rust/egui control geometry. Each selected trusted canvas
pointerdown associates with its own250ms timer via origin index, pointerId and
timestamp. Within each interval the canvas/DPR/viewport/parent/scroll phase is
stable, document focus stays true, and focus transfers internally between the
production canvas and textarea. The visible caret proxy lands inside Work bounds.

| Case | DPR | Canvas CSS | Backing | Exact pointer→settled | Age ms | Caret anchor CSS |
| --- | --- | --- | --- | --- | --- | --- |
| normal100 | 2 | 1512×806 | 3024×1612 | 11→17 | 254.4 | 363.78125/21.25 |
| normal125 | 2.5 | 1209.6×644.8 | 3024×1612 | 44→50 | 251.6 | 363.88126/21.40625 |
| normal reset100 | 2 | 1512×806 | 3024×1612 | 73→79 | 251.2 | 363.78125/21.25 |
| fixed100 | 2 | 1100×640 | 2200×1280 | 13→19 | 250.7 | 363.78125/21.25 |
| fixed125 | 2.5 | 1100×640 | 2750×1600 | 126→132 | 251.0 | 361.88126/21.40625 |
| fixed reset100 | 2 | 1100×640 | 2200×1280 | 229→235 | 250.9 | 361.78125/21.25 |

The whole-window viewport is1512×806 at100%, integer `innerWidth/innerHeight`
1209×645 at125%, and1512×806 after reset. VisualViewport at125% reports the
fractional1209.5999756×644.7999878, scale1 and offsets0/0. Fixed parent AND canvas
remain exactly1100×640 in the selected intervals despite that viewport change.
Scroll is0/0 and parent/canvas transforms are `none`. Normal canvas client size at
125% rounds to1210×645; the measured fractional CSS rectangle/backing arithmetic
is checked with the existing bounded rounding tolerances.

All normal snapshots share session `54340409-b3d7-4fa2-99b7-aac9a09b2492`;
all fixed snapshots share `c875276f-5c48-4cbd-9aee-3d1243365dbb`. Fixed transition
verification confirms chronological selected phases and unchanged common rows
across cumulative exports. The normal final Stop/export has87 contiguous rows0–86.
Fixed final Stop/export has321 contiguous rows0–320, zero drops and an explicit
`stopped` marker. This establishes completed observer publication and recorded-row
coverage. It does not turn selected-interval checks into whole-session product
proof or establish events outside the document/observer surface.

## Slider click and Undo, not continuous drag

The100% attempted CUA drag records row51 pointerdown at `[834,138.5]`, then row52
pointerup at `[885,138.5]` only6.3ms later, with NO intervening held pointermove.
Root observed the Work revision unchanged. There is no separate complete saved
Work immediately after this failed attempt in the packet, so that unchanged
revision observation is root-attributed, not an independent JSON state comparison.
The attempt and its `fixed-100-drag.png` filename do not prove continuous dragging.

The subsequent real click is rows55/56 at `[885,138.5]`. At125% the click is
rows164/165 at `[880,138.800003]`; reset100 uses rows267/268 at `[885,138.5]`.
The final fixed trace has zero canvas pointermove records with buttons held.
Accordingly, the saved-document checks prove CLICK/SINGLE-UNDO behavior only.
The checker's inherited wording mentions drag, but no continuous gesture is
inferred from document revision arithmetic.

| Fixed phase | Jaw baseline→click→Undo | Revisions | Complete-document check |
| --- | --- | --- | --- |
| 100% | 0→0.57→0 | 1→2→3 | Only jaw changes; complete baseline content restored |
| 125% | 0→0.51→0 | 3→4→5 | Only jaw changes; complete baseline content restored |
| reset100% | 0→0.57→0 | 5→6→7 | Only jaw changes; complete baseline content restored |

## Observer/checker repairs and preserved failed evidence

The initial v1 normal100/125/reset captures remain unchanged. They are rejected
by the conservative checker because the collector's capture-phase window listener
misclassified descendant DOM blur/focus as window events. Omitted event targets
cannot be recovered from the old raw JSON. All those apparent blur rows report
`documentFocused:true`; no OS/CUA focus-loss or product defect is inferred from
their labels. Exact capture hashes and rejection limits are preserved in
`v1-observation-limits.json`. The v1 packages retain their original collector bytes.

Root authorized one focused follow-up. V2 changes exactly two observer callbacks
to filter `event.target === window`. The actual-collector offline VM control is
red before this repair and green afterward for descendant-event rejection and
genuine-window-event retention. No checker focus relaxation or pointerup
substitution occurred. The fresh v2 captures above supply acceptance.

Independent review also identified fabricated retained-tail accounting. The
checker now requires `retained=min(recorded,1200)` and
`dropped=max(0,recorded-1200)`. A genuine1200-row synthetic retained tail passes;
trimming it to two rows fails. The new control is red before the repair and all26
controls pass after. These are offline evidence-checker controls, not production
regression tests. Before/after logs remain in the owned task directory.

## Source and raw identities

Both served v2 manifests pin26 production file hashes plus their wrapper and
observer. This worker recomputed those identities before the actual-data checks.
Their capture metadata equals the corresponding independently pinned manifest.

| Source | SHA256 |
| --- | --- |
| production index | `73ea243ebc795ec5d405489e8aaeaca4ebe18b537e4b90fa433f5bbe0e2f5114` |
| production JS | `9ff532cbedc6a814c4b8337c4b82f436de452e7b7fbc8c9e58bfda2e90ad6c5c` |
| production Wasm | `884134fc98d54e3476dbc799ffdd5cc6b88f69121ddfb649ed9ba9be96156dba` |
| v2 observer | `8cd6a3c9fc19878acdc06f5d520c49864c7cf046c6d998f0ada71dce65802477` |
| normal v2 wrapper | `15e60ff02944da72e0a7e98259e25371d45feaf54635b695265dbb95f2872fba` |
| fixed v2 wrapper | `2969b70aa1cb0f0a224075ccd406a8d9e66ae2894ede45928fe2782a05acd23d` |

Raw files are under `.work/bounded-scale-ime/issue3/`; they are root-owned actual
captures, not test fixtures. This report does not publish or relocate that packet.

| Raw capture | SHA256 |
| --- | --- |
| normal-v2-100.json | `14c00709ff5247442b2816363c2eeebc94a9d928c92853c392da9e5774956f02` |
| normal-v2-125.json | `1f673c465c9d53da5d5cab0467bb218c7d710d115cc59c9588799bd469703a0d` |
| normal-v2-reset.json | `f477b1c2838e60dce369d172188c0e904b178266a763e36607d8e95000c17f3e` |
| fixed-100.json | `c51cc73ac347a47d18d60ca828908c82bcbb7c690ce68f98728cd900d59d3882` |
| fixed-125.json | `1793895dbcd2757b620e67fed4eaf8a3416fdeac805f75abe88994fcfbdb1bc6` |
| fixed-reset.json | `79b804ae3e0aac7b7faa7beb09d835ebac097da2de3084dfab14b1f03becf7b0` |
| fixed-final.json | `685bba34206cb2b091ec364e6334be2d705eebe490495fd2f48b59d55cee2494` |

## Offline reproduce against the exact actual packet

From the repository root. Python standard library and Node are sufficient.

```sh
node experiments/22-fixed-css-dpr/test_collector.js
python3 -B experiments/22-fixed-css-dpr/test_controls.py -v
python3 -B experiments/22-fixed-css-dpr/check.py package \
  .work/bounded-scale-ime/issue3/web-normal-v2/probe-package.json
python3 -B experiments/22-fixed-css-dpr/check.py package \
  .work/bounded-scale-ime/issue3/web-fixed-v2/probe-package.json
python3 -B experiments/22-fixed-css-dpr/check.py geometry \
  .work/bounded-scale-ime/issue3/normal-v2-100.json \
  --manifest .work/bounded-scale-ime/issue3/web-normal-v2/probe-package.json \
  --pointer 11 --row 17 --expected-dpr 2 --expected-css 1512 806 \
  --work-rect 258 3 220 22
python3 -B experiments/22-fixed-css-dpr/check.py geometry \
  .work/bounded-scale-ime/issue3/normal-v2-125.json \
  --manifest .work/bounded-scale-ime/issue3/web-normal-v2/probe-package.json \
  --pointer 44 --row 50 --expected-dpr 2.5 --expected-css 1209.6 644.8 \
  --work-rect 258 3 220 22
python3 -B experiments/22-fixed-css-dpr/check.py geometry \
  .work/bounded-scale-ime/issue3/normal-v2-reset.json \
  --manifest .work/bounded-scale-ime/issue3/web-normal-v2/probe-package.json \
  --pointer 73 --row 79 --expected-dpr 2 --expected-css 1512 806 \
  --work-rect 258 3 220 22
python3 -B experiments/22-fixed-css-dpr/check.py transition \
  .work/bounded-scale-ime/issue3/fixed-100.json \
  .work/bounded-scale-ime/issue3/fixed-125.json \
  .work/bounded-scale-ime/issue3/fixed-reset.json \
  --manifest .work/bounded-scale-ime/issue3/web-fixed-v2/probe-package.json \
  --pointers 13 126 229 --rows 19 132 235 --dprs 2 2.5 2 \
  --work-rects 258 3 220 22 258 3 220 22 258 3 220 22
python3 -B experiments/22-fixed-css-dpr/check.py inventory \
  .work/bounded-scale-ime/issue3/fixed-final.json
for phase in 100 125 reset; do
  python3 -B experiments/22-fixed-css-dpr/check.py work \
    ".work/bounded-scale-ime/issue3/fixed${phase}-base.nvwa.json" \
    ".work/bounded-scale-ime/issue3/fixed${phase}-click.nvwa.json" \
    ".work/bounded-scale-ime/issue3/fixed${phase}-undo.nvwa.json"
done
```

All selected-interval, transition, inventory and Work assertions above were
rechecked against the actual raw files by this worker. The transition command
includes all three fixed geometry checks. Root logs include the same fixed
transition, normal checks, fixed100/125 checks and three Work comparisons.

## Remaining limits

Original IAB simulated-DPR trigger is unavailable and NOT-RUN. Actual physical
display-scale migration is NOT-RUN. Fixed-CSS continuous slider drag is NOT-RUN:
the automated attempt supplied no held pointer movement, and the later actions
were clicks. Human IME/shortcut checks and the separate untrusted composition
event investigation are not established here. Rust `Window.scale_factor`, egui
`pixels_per_point`, cursor/control rectangles and upstream cause remain unknown.
No speculative sizing or input fix follows from these bounded controls.

VERIFIED — six actual trusted Work click/caret intervals, fixed parent/canvas
CSS and backing DPR triplet, exact observer/source identities and three complete
Work click/single-Undo sequences pass. Original IAB, physical display migration
and fixed-CSS continuous drag remain NOT-RUN.
