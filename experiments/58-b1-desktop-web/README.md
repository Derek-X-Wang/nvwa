# B1 native + Web source viewer

Isolated experiment. The same Rust viewer uses `57-b1-pose-runtime/derived` and
`b1-pose-adapter` on native and Wasm. It executes original approved input
encodings at runtime. There are no baked frames, GLBs or pose playback assets.

## Build and launch

Run `bash experiments/58-b1-desktop-web/build.sh native` or `web` from the repo.
Both builds are offline and use one compilation job. The preparation step checks
every approved manifest file and the existing source-input encoding hashes.
No dependency/tool download is performed. The Wasm target and pinned local
wasm-bindgen tool must already exist.

Native bundle: `.work/b1-pose-viewer/Nvwa B1 Pose Lab.app` with bundle ID
`dev.nvwa.b1-pose-lab`; window title `Nvwa B1 Pose Lab`.

Before launch root must grant the graphics token. Root owns GUI testing and
server launch. Preserve occupied ports and existing apps/tabs. After checking a
free port in the Nvwa 9200–9299 range (excluding 9201/9202), root can start:

```
python3 experiments/58-b1-desktop-web/serve.py --port 9203
```

The server binds loopback only and fails if that exact port is occupied.
Launch a fresh browser tab at the assigned loopback URL. WebGPU is required by
the existing Bevy 0.19.1 renderer. No browser fallback is silently selected.

## Runtime and inspection

The recipe selector uses the eight frozen body recipes. The pose selector uses
exactly the five poses in `56-b1-pose-reference/poses.json`. Pose changes call
57's shared `apply_pose_canonical`, which resets actual fitted transforms and
expresses the frozen Blender-local postrotations through source-derived frame
gauges. It preserves the candidate's fixed-rest policy. Bevy propagates the
hierarchy before frame inspection.

Actual B1 fits the body/garment and writes mesh positions, normals, tangents,
joint indices and weights. The renderer flattens the selected actual morph into
its rest mesh and uses Bevy's real GPU `SkinnedMesh` with actual ECS joints and
fitted inverse binds. The full candidate geometry is retained for numeric
inspection. Display-only body triangles whose source IDs are MakeHuman helpers
or joint cubes (13380+) are omitted. No evaluated skin positions feed rendering.

Frame matrices and skinned positions are **original CPU LBS diagnostic readback**
over the actual B1 ECS and mesh attributes, from 57's adapter. They are not a
source CPU skinning kernel, GPU vertex readback, or pixel validation. The export
labels this distinction. The inspection coordinate space is MakeHuman Y-up
metres with column-major matrices, cancelling only the display skeleton root.

The renderer selector retains **GPU4 · quality HOLD** as a separate option.
The additive **positive-influence CPU, no four-cap** contrast uses 57's original
LBS adapter over source-derived RigWeights/MHCLO transfer. It retains positive
aggregate influences (`> 0`) without a four-influence cap. The prototype state
shorthand `full-weight-cpu` denotes this explicit policy, rather than unchanged
signed transfer. MPFB reference evaluation retains weights `> 0.001`; the measured
comparison keeps that distinction.
It uploads deformed positions, normals and tangents to a separate display mesh.
That mesh has neither `SkinnedMesh` nor morph data, so it cannot deform twice.
The actual skeleton global display matrix is applied exactly once. No reference
geometry, expected matrices or reference weights enter this renderer. A ready
frame means loading/computation completed; product admission is undecided.

Native: click **Export state**, **Import state**, **Inspect selected frame** or
**Write selected-frame.json**. The latter writes into the owned private
`.work/b1-pose-viewer/selected-frame.json`. Frame inspection includes full body
and garment vertices/source IDs, skin weights, normals/tangents, and all bones. The live inspector selects one vertex and bone at a time; it
shows actual skinned positions and rest/pose matrices without laying out a
full multi-megabyte frame as editable text.

Browser typed controls:

```js
b1.command({action:'select',recipe:'combined',pose:'combined',backend:'gpu4'});
b1.command({action:'import',state: /* parsed prototype state object */});
b1.report(); // status, visible error, state, selected frame, attachment status
b1.frame();
b1.download('frame');
b1.download('state');
```

The bridge updates only when the selected frame, state or status changes; it
does not serialize full vertex arrays at the display frame rate.
The collapsed **Prototype diagnostic controls** disclosure provides typed JSON
commands, small state output and **Download frame JSON**. Complete frames are
downloaded rather than inserted into the page's text layout.

## Scoped state and negative controls

The JSON format is `nvwa-b1-pose-prototype` version 1. It stores recipe, pose, camera yaw and the diagnostic renderer backend.
Omitted backend fields default to `gpu4` for earlier prototype JSON. It is explicitly distinct from production Nvwa Work. Imports reject
unknown fields, versions, recipes/poses and nonfinite/out-of-range cameras.
Invalid imports preserve the active selection and keep an error visible.
A fatal asset/build error freezes its first error and current state/frame until
reload. Commands are rejected and native controls disabled in that state; valid
JSON cannot recover a failed loader. Reports expose `fatal_reload_required` and
a rejected-command count. Ordinary invalid JSON errors remain recoverable through
a valid import.

`?omit_target=1` requests only three of the four original target files. The
viewer validates the complete frozen required target set after loader readiness
and fails visibly with `Explicit target missing`; it emits no ready frame.
Individual asset loader failures also become visible viewer errors.

Headless original-source execution (no window/GPU):

```
B1_HEADLESS=1 B1_FRAME_FILE=/absolute/owned/frame.json \
  experiments/58-b1-desktop-web/target/debug/b1-desktop-web
```

`B1_INITIAL_STATE` accepts the serialized prototype state; `B1_COMMAND_FILE`
watches changed typed JSON commands, without deleting the file. Add a unique `request_id` field to repeat identical actions. `B1_OMIT_TARGET=1` is the native omission
negative control. These paths execute source loading/morph/mesh/rig and CPU
frame inspection, not graphical proof.

See `evidence/STATUS.md` for observed verification; a build is not a GUI test.

Portable CI staging uses the same thirteen authenticated source-input encodings:

```
python3 experiments/59-b1-ci-inputs/prepare_ci_inputs.py --out .work/b1-pose-viewer/ci-seed
python3 experiments/57-b1-pose-runtime/prepare.py --ci-inputs .work/b1-pose-viewer/ci-seed
python3 experiments/58-b1-desktop-web/prepare.py --ci-inputs .work/b1-pose-viewer/ci-seed
```

Preparation pins the approved archive/manifest, verifies all extracted files and
original data-adapter provenance, and rejects missing runtime library source.
It rejects output symlinks and limits output to the viewer's owned directories.
The authenticated identity is unchanged by repeated staging. Generated sidecars
are excluded from their own input hashes. Python `-O` does not remove these gates.

For a clean checkout with the portable seed, use the extraction/materialization
commands above, then run:

```
B1_CI_INPUTS="$PWD/.work/b1-pose-viewer/ci-seed" bash experiments/58-b1-desktop-web/build.sh native
B1_CI_INPUTS="$PWD/.work/b1-pose-viewer/ci-seed" B1_WASM_BINDGEN=/absolute/path/to/wasm-bindgen bash experiments/58-b1-desktop-web/build.sh web
```

The Web build checks that the supplied local tool reports exactly
`wasm-bindgen 0.2.129`; it never downloads one. A missing portable seed fails.
The native bundle remains a local prototype: the compiled asset root points
into this checkout's private staged input directory. Relocating the app alone
is not a supported distribution route.

Display visibility uses the actual approved garment's parsed `delete_verts`.
Only original body quads whose four source IDs are covered are omitted; mixed
boundary quads remain. Helper faces are omitted separately. The selected-frame
export records the exact rule, garment hash, mask counts and displayed index
counts. The full numerical cage and its weights remain intact. This visibility
rule does not establish collision or cloth physics quality. Root observed visible
shoulder/waist poke-through and a folded garment in diagnostic poses. Appearance
and collision acceptance remain unestablished. Camera orbit targets
and distance use actual selected character bounds and the actual display-root
matrix, rather than an assumed ground origin.

The source GPU4 transfer can retain signed aggregate weights from MHCLO
barycentric helper coefficients. Those legacy attributes remain unchanged and
are exported as diagnostics in both routes. CPU display meshes remove them.
The strict frame parity gate requires finite legacy values and reports negative
counts/minimum; it does not turn parity into weight-quality acceptance. Selected
positive CPU rows must contain positive finite influences. GPU4 quality remains
HOLD. No weights are clamped to make a test pass.

`verify_native.py --binary /absolute/binary --asset-root /absolute/assets --out
NEW_OWNED_DIRECTORY` verifies actual source execution, strict full coverage,
independent CPU arithmetic, JSON restoration, explicit target omission, and a
real headless command-file loop. The latter checks camera-only metadata without
a skin rerun, invalid-schema import preservation and valid recovery. Output must
be new; prior captures are never removed. It reports CPU evidence only. The
prototype's native clipboard integration is incomplete; the command bridge and
state JSON controls do not imply production clipboard or Work adoption.
