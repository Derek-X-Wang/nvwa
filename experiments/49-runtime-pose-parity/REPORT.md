# Same-frame runtime pose diagnostic

**Motion quality remains HOLD.** At the seven selected exact GLB keys, actual
native and Web Bevy poses agree with the independently evaluated serialized
experiment48 scene. The captured joint transforms, ancestors, root and skin
bindings do not explain the visible intersections as a runtime pose mismatch
at these keys. The serialized-scene CPU skin calculation already contains
weighted arm/torso triangle crossings. These results do not assign a cause to
the motion source, calibration, mapping, weights, or anatomy.

The retained Work has revision 0 and profile
`nvwa-experiment48-genuine44-calibrated47`. Its selected clip is
`genuine44_calibrated47`, GLB animation index 3. Source GLB SHA256 is
`c343f6cf47dc0a7c0b09f13ad7d21cf2706a08fb1cfdaca233f14edab02e44fc`;
source Work SHA256 is
`7668eb7a2a2f87070500cbf49fa27d6794aa1fb83f5392b75a0ff51667cde779`.
Experiments 41–48, original assets and source Work remain unchanged.

## Actual runtime evidence

The isolated [probe](probe/README.md) calls the shared
`nvwa_studio::build_app()` production graph. It requests paused exact seeks
before production transport. Its capture runs in PostUpdate after both
`AnimationSystems` and `TransformSystems::Propagate`. It requires two completed
passes with actual playback/player clip, pause, weight and time bits matching
the requested sample. No expected transform enters the collector. The raw
[schema](probe/SCHEMA.md) includes the complete actual Work, frame counter,
actual graph-to-clip identity, every local TRS and global matrix in the scene,
CharacterRoot, ordered runtime skin joints, inverse binds and mesh/primitive
asset identities. Missing or ambiguous state fails.

Both captures contain 35 scene entities, including all 24 GLB nodes, all needed
ancestors, the character host and all 9 skinned primitive instances. Each skin
records its actual 18 ordered joint entities. Actual clip/index/time bits agree
at every requested key. The final key is binary32(89/30),
`2.9666666984558105`seconds; no 3-second endpoint is substituted.

| Source key | Exact requested time(s) | Native capture frame | Web capture frame |
| ---: | ---: | ---: | ---: |
| 0 | 0.0 | 5 | 10 |
| 15 | 0.5 | 7 | 12 |
| 30 | 1.0 | 9 | 14 |
| 45 | 1.5 | 11 | 16 |
| 60 | 2.0 | 13 | 18 |
| 75 | 2.5 | 15 | 20 |
| 89 | 2.9666666984558105 | 17 | 22 |

The [native raw capture](probe/results/native.json),
[Web raw capture](probe/results/web.json), and their independent
[native](probe/results/native-comparison.json)/[Web](probe/results/web-comparison.json)
comparisons pass. Local quaternion signs are equivalent. Full hierarchical
matrices retain all root, axis and scale effects; no fitting or alignment is
used. Thresholds were frozen before exposing runtime results.

| Maximum absolute component error | Threshold | Native | Web |
| --- | ---: | ---: | ---: |
| Local translation(m) | 2e-06 | 0 | 0 |
| Local quaternion, sign equivalent | 2e-06 | 0 | 0 |
| Local scale | 2e-06 | 0 | 0 |
| Full global matrix | 2e-05 | 1.75870386476e-07 | 1.75870386476e-07 |
| Inverse bind matrix | 2e-06 | 0 | 0 |
| CPU reconstructed skinned vertex(m) | 3e-05 | 1.47817195428e-07 | 1.47817195428e-07 |

CPU deformation reconstruction uses serialized positions/weights with the
captured runtime ordered joints, globals and inverse binds. This verifies that
reconstruction against the independent scene evaluation. Loaded GPU vertex
buffers and shader vertex-output readback are **NOT-RUN**.

## Visible quality and bounded surface evidence

The retained [native final canvas](probe/results/native-canvas.png) and
[Web final canvas](probe/results/web-canvas.png) show the actual paused final
pose, with arms hidden by or intersecting the torso and hands at the waist.
Both were viewed. The native image came from the existing product `--capture`
path without `--smoke`; its callback records a ready scene, nine meshes/skins,
eighteen joints, one paused player and the exact final clip time. Web used a
user-activated PNG download of the actual rendered canvas. Images were not
edited. They have different display sizes and are not a pixel-parity test.

The independent [surface result](offline/surface-crossings.json) measures
strict noncoplanar triangle crossings between arm-weighted and torso-weighted
partitions of the serialized expected skin. Every triangle vertex must have
at least 0.8 weight in its named joint set; transition triangles are excluded.
At key 89 it finds 261 left-arm/torso and 193 right-arm/torso triangle pairs;
right-arm/torso crossings occur at all seven selected keys. This is a narrow
surface criterion, not a full body-intersection, contact or anatomy metric.
No neutral-pose crossing baseline was measured, so the counts do not establish
that the motion introduced every crossing. See the
[offline method and limits](offline/README.md).

## Build, controls and evidence limits

Native and Web compilation, launch, capture, visual inspection and numerical
comparison each passed separately. Both native app binaries match the
snapshot-built executable. The refreshed Web run used the actual WebGPU-only probe build. Root operated
its own eligible in-app browser because the worker browser adapter was unavailable.
[Native](probe/results/native-cohort.json) and
[Web](probe/results/web-cohort.json) cohort receipts compare the actual Wefty
snapshot source/input hashes against the final checkout and artifact.
[Web staging](probe/results/web-staging.json) also binds the served Wasm,
JavaScript, HTML, Work and GLB. Final builds used cached dependencies, `--locked
--offline`, two Rust jobs and owned output directories. Existing pinned
wasm-bindgen 0.2.129 produced the Web glue; no tool was installed.

An initial predecessor native dependency build failed on the collector's
borrowed graph index. The corrected predecessor snapshot passed. This
portability refresh compiled fresh cached native and Web snapshots in
30.63 seconds and 39.25 seconds respectively. Web preparation took
28.259 seconds separately. These are build/preparation observations, not
runtime performance measurements. The only product seam is the additive Studio
`manual-start` feature: it suppresses the library's Web auto-entrypoint only
when explicitly enabled by this probe. Default Studio entrypoints remain
selected by default. Hosted CI and default-product build results are separate
from these local probe receipts.

The actual native failure control launches the normal default fixture. It
emits [failed raw state](probe/results/native-negative.json) with
`wrong Work/profile`, zero samples and
[child OS exit 1](probe/results/native-negative-exit-code.txt). Positive and
visual runs exit 0. The refreshed negative CUA call opened the failed diagnostic window, then a
local REPL variable assignment raised a binding error after the launch. It
was not replayed. Fresh raw state and the actual child exit independently
verified execution. During the predecessor session a window screenshot had
exposed a startup frame despite the completion title. The retained final
canvas therefore uses the existing product capture callback after readiness;
a separate bounded visual launch was repeated for this refreshed binary.
These operator observations are retained in
[native execution](probe/results/native-execution.json).

Independent comparator controls cover wrong clip/time/pose, missing bones and
skin instances, changed Work revision/types/content, root double application
and scale, wrong ancestors, wrong joint order, perturbed inverse binds,
nonfinite values and quaternion sign equivalence. Their synthetic fixtures
are not runtime captures. Nine packaging controls pass normally and with
Python `-O`: three native controls and six Web preparation controls. Native
controls include exact removal of log-parent creation causing the real
generated launcher to fail, then restored-green. Web controls cover explicit
pinned-tool selection, custom paths containing spaces, missing tools or Wasm,
wrong tool version and failed version probes before staging. Packaging uses a fake
executable and cannot count as renderer evidence. See
[staging controls](probe/results/staging-controls.json).

All 90 keys have independent offline expected transforms. Actual runtime
sampling covers only the seven keys above; the other keys and between-key
interpolation are **NOT-RUN**. Official decoder parity, anatomical or semantic
quality validation, generalized rigs, physical human trials, and the separate
unassisted Alpha trial are **NOT-RUN**. There was no inference, model-cache
access, retargeting change, asset replacement or performance claim.


## Portable preparation refresh and predecessor comparison

The reviewed predecessor is commit
`e9a5ef1bcf907c7e412f968a151372bfe111fee3`. Its raw data, images, source/hash
records, app binaries and served Web files were preserved privately before
changing the preparation helper. The helper now requires an explicit existing
`--wasm-bindgen` executable reporting exactly `wasm-bindgen 0.2.129`. It also
accepts explicit `--wasm` and `--stage` paths. Missing or wrong tools fail
before staging; no installation or download is attempted.

A complete normalized reproduction command is:

```sh
WASM_BINDGEN=/path/to/existing/wasm-bindgen
python3 experiments/49-runtime-pose-parity/probe/prepare_web.py --wasm-bindgen "$WASM_BINDGEN" --wasm .work/runtime-pose-build/wasm32-unknown-unknown/debug/nvwa_runtime_pose_probe.wasm --stage .work/runtime-pose-web-portable
```

The executable path is a caller-supplied parameter, not literal captured argv.
[Preparation evidence](probe/results/web-preparation.json) binds the actual
tool version and SHA256; actual argv is retained privately. Cargo snapshot
receipts bind the changed Python sources as well as Rust/Cargo inputs. The
post-build README URL clarification is current documentation, not a compiled
snapshot input; both final cohort `files` maps include its current hash.

The stage must be opened with the complete production Work query:

```text
http://127.0.0.1:9204/?work=works/genuine44-calibrated47.nvwa.json
```

Root initially opened bare localhost 9204. That selects the normal default
fixture, whose GLB is absent from this narrow stage, and produced zero samples
with `Asset byte load failed: Path not found: assets/fixtures/nvwa-humanoid.glb`.
That operator entrypoint error is retained privately and is separate from the
valid explicit-Work run. It supports no broad failure-path conclusion. Root
then used the exact URL above, observed all seven samples and downloaded the
actual JSON and canvas PNG from owned tab 8. Root closed that tab. The worker
verified the download/copy hashes, ran both comparisons and viewed the image.
See [Web execution](probe/results/web-execution.json).

The [raw recapture audit](probe/results/recapture-diff.json) uses typed recursive
JSON comparison, including parsed float bits, without alignment or field
normalization. New native, visual-native and negative raw files are byte
identical to the preserved predecessor. Web raw differs only in its seven
frame counters, each increasing by one (9..21 to 10..22 at step 2). Every local
TRS, global matrix, inverse bind, ordered skin binding and other raw field
remains exact. Web canvas bytes are also identical. Native canvas bytes differ;
no pixel-parity claim is made. All numerical conclusions and the quality HOLD
remain unchanged.

## Cleanup and reproduction

The owned native renderers exited. Root closed refreshed diagnostic tab 8,
and the bounded localhost 9204 server expired and has no listener. The pre-existing 9201 and
9203 server processes remained live and were not changed. Existing Alpha
browser state was not exposed in this worker's IAB session; no claim is made
that an old tab was still active. No old tab was navigated, reloaded or edited.
Owned compiled outputs/app bundles and temporary staged byte copies remain
available for review; they are not product or publication artifacts.

From the repository root:

```sh
python3 experiments/49-runtime-pose-parity/offline/run_controls.py
python3 -O experiments/49-runtime-pose-parity/offline/run_controls.py
python3 experiments/49-runtime-pose-parity/offline/compare.py experiments/49-runtime-pose-parity/probe/results/native.json
python3 experiments/49-runtime-pose-parity/offline/compare.py experiments/49-runtime-pose-parity/probe/results/web.json
python3 -m unittest discover -s experiments/49-runtime-pose-parity/probe -p 'test_*staging.py'
```

The [probe guide](probe/README.md) documents separately granted runtime
reproduction. No renderer is started by the offline commands above.

**VERIFIED — Native and Web exact-key capture/comparison, actual final canvas
inspection, native failure OS exit, and owned renderer/server cleanup. Motion
quality remains HOLD.**
