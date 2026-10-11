# Experiment 01: original continuous character fixture

Date: 2026-10-10. Host: local macOS arm64. Authoring tool: Blender 3.3.1,
bundled Khronos glTF exporter 3.3.32. CPU authoring jobs use two threads.

## Question and hypothesis

Can an original, legally distributable fixture prove M0's continuous skin,
four useful face/body morph parameters, and skeletal clip integration without
a third-party character license or an AI motion service?

Hypothesis: an explicitly authored voxel-union humanoid can provide one smooth
connected clothed surface, normalized multi-bone skinning, independent geometric
shape keys, and manually authored idle/wave/turn presets in a portable GLB.

## Control and criteria

Control: the neutral A-pose surface, all four shape keys at zero, compared with
each individual shape key at one under the same CPU camera and lights.
The neutral skeleton is compared with the wave action at frame 25 (one second).

Pass criteria:

- Primary surface is one connected component after welding glTF material seams.
- Every primary vertex has valid normalized bone weights; most vertices blend
  more than one joint. It must deform as a smooth surface, not rigid primitives.
- Four distinct target vectors affect hundreds of vertices and visibly change
  face/body geometry. Actual exported indices must match the profile.
- Idle and wave have varying skeleton channels and useful duration; turn is
  optional. Clips are accurately labeled manually authored presets.
- Opaque clothing materials, readable head/neck/torso/arms/hands/legs, and an
  original reproducible source with bounded fixture-only license scope exist.
- Two independent exports record actual byte hashes, including drift.

Exit: ship the M0 fixture when these structural and authoring criteria pass.
Runtime import, runtime visuals, and performance remain separate integration
checks. Stop and report any failure instead of substituting rigid body parts or
claiming successful Web/native validation from Blender output.

## Implementation

`tools/blender/generate_fixture.py` constructs anatomical volume inputs and
immediately voxel-unions them at 0.013 m resolution. Five smoothing passes round
the result. The construction spheres/capsules do not survive as separate body
parts. The exported primary surface is a single connected mesh with skin and
opaque tunic/trousers/shoe regions assigned as materials. Four separate eyeball
surfaces are the only separate geometry. No textures or imported assets exist.

The original 18-joint skeleton has root/pelvis/spine/chest/neck/head and paired
upper-arm/forearm/hand/thigh/shin/foot chains. Per-vertex normalized Gaussian
weights blend nearby bones within the appropriate body region. Shape keys use
explicit coordinate displacement functions, authored directly in the script.
Actions use explicit bone pose keyframes and are exported through named NLA
strips. They are manually authored presets, not AI-generated motion or mocap.

## Commands and results

From the repository root:

```sh
/opt/homebrew/bin/blender --version
NVWA_RENDER_PREVIEWS=1 /opt/homebrew/bin/blender -b -t 2 --python tools/blender/generate_fixture.py
python3 tools/blender/check_reproducibility.py
python3 tools/blender/validate_fixture.py --publish
```

All commands completed with exit code zero. Logs are in this experiment folder.
The validator reads GLB JSON chunks and binary accessors directly. It checks
finite values, triangle topology, welded connectivity, inverse bind matrices,
joint references, normalized weights, multiple nonzero influences, each morph
delta accessor, distinct morph vector hashes, material opacity, clip duration,
and varying joint animation channels. It checks data rather than trusting names.

Actual export: `assets/fixtures/nvwa-humanoid.glb`, 3,827,840 bytes. Current SHA256:
`f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`.
`assets/character.profile.json` publishes the same hash and asset-root-relative
path `fixtures/nvwa-humanoid.glb`.

| Evidence | Actual result |
| --- | --- |
| Source primary vertices/polygons | 22,572 / 22,570 |
| Welded exported primary components | Exactly one, containing 22,572 vertices |
| Material-split exported vertices | 23,044 |
| Weighted primary vertices | All 23,044; normalized to one |
| Vertices with multiple influences above 0.01 | 21,648 |
| Skeleton joints / inverse bind matrices | 18 / 18 |
| Materials | Opaque skin, teal tunic, indigo trousers, charcoal shoes, dark facial features |

| Parameter | Actual morph index | Changed exported vertices | Maximum delta |
| --- | --- | --- | --- |
| `jaw_width` | 0 | 2,718 | 0.06886 m |
| `nose_width` | 1 | 296 | 0.06945 m |
| `smile` | 2 | 678 | 0.03926 m |
| `shoulder_width` | 3 | 9,390 | 0.08988 m |

All parameter ranges are 0–1 with default zero. Changed counts include glTF
material seams. The four target-vector hashes differ. CPU source stills show
separate changes to lower-jaw silhouette, nose volume, smiling cheeks/mouth,
and shoulder/upper-body width. The wave still shows the right arm overhead with
the torso/arm junction deforming continuously.

| Preset | Actual animation index | Duration | Moving joints |
| --- | --- | --- | --- |
| `idle` | 0 | 3.0416667461395264 s | chest, head, pelvis, both upper arms |
| `turn` | 1 | 4.041666507720947 s | root |
| `wave` | 2 | 3.0416667461395264 s | right upper arm, forearm, hand, head |

### Exported frame offset and profile correction

A later read of every actual animation input accessor found a one-frame start
offset retained by the exporter: Blender frame 1 at 24 fps becomes float32 time
`0.0416666679084301 s`, rather than zero. Idle/wave sample 73 frames (1–73), so
their final keyframe is `3.0416667461395264 s`. Turn samples 97 frames (1–97), so
its final keyframe is `4.041666507720947 s`.

The original table/profile values 3 s and 4 s described authored first-to-last
spans. Their decoded float32 spans are respectively `3.0000000782310963 s` and
`3.999999839812517 s`. A playback clip measured from time zero must use the
largest exported keyframe time. The integration owner authorized correcting
only the profile duration fields to these actual float32 endpoints before
runtime compilation. Animation indices and the frozen GLB/source bytes were
preserved. This metadata correction is not an export or runtime validation.

The integration owner then authorized the validator/manifest consistency fix.
`validate_fixture.py --publish` now uses each clip's actual maximum input time
as the profile duration without rounding away float32 data. Its structural
report records the positive first keyframe and authored span separately; nominal
3/4-second spans still form the intended motion-length check. The profile keeps
only the contract's clip fields. The CPU-only publish validation passed and
refreshed the manifest's profile/validator/proof hashes. The GLB, `.blend`, and
generator hashes remain unchanged. Older repeat-export snapshots preserve the
historical span measurements; no Blender jobs were rerun for this correction.

## Reproducibility result

`reproducibility.json` records two fresh Blender processes, individual hashes,
JSON/binary chunk hashes, and both structural validator results. The current
two exports are **not byte-identical** for either GLB or `.blend`. Their source
topology metadata, structural metrics, and all four morph delta hashes are
identical. Both GLB JSON and binary chunk hashes differ; the precise cause of
that exporter drift has not been isolated. Do not claim byte reproducibility.
The source script regenerates the original fixture, but the profile and manifest
must be republished after each export so they describe the actual current bytes.
Cross-version and cross-platform repeatability has not been tested.

Re-export experiments write isolated `reexports/run-1` and `run-2` folders in
this experiment directory. They never overwrite the published main GLB/profile
while runtime consumers build. Initial exports happened before this isolation
rule; the final published main SHA above is frozen independently of experiment
outputs.

The saved `.blend` is the editable generated source. The Python script is
the higher-level reproducible construction recipe. Blender's `.blend1` backup
is discarded by the reproducibility tool. No randomness is intentionally used.

## Provenance and limits

`assets/fixtures/LICENSE.txt` and `provenance-manifest.json` record original
agent-authored coordinates/topology, materials, deformation functions, weights,
and preset motions. The user authorized this original distributable M0 fixture.
CC0-1.0 applies only to the fixture and associated authoring/validation sources,
previews and metadata. It does not assign a license to the repository or tools.
The manifest includes current source, export, profile, proof and preview hashes.

This is a stylized engineering fixture. Hands are mitten-like, facial features
are coarse painted mesh regions, and there is no finger rig or realistic hair.
Large morph values are deliberately pronounced. Simple skin weights can pinch
at the raised armpit, and exaggerated shoulder/jaw changes are not a production
character-quality claim. Blend combinations have not received exhaustive visual
inspection. No third-party body library, Blender add-on, or paid API was used.

VERIFIED — GLB export, binary structural validation, single continuous skinned
surface, four distinct nonzero morphs, three skeletal clips, matching profile
indices/hash, CPU source authoring previews, and honest two-export hash report.

NOT-RUN — Native Bevy/Web rendering, runtime morph/clip application, interactive
UI, GPU performance, 16 GiB pressure testing, and cross-host/version export
repeatability. The integration owner is responsible for runtime validation.
