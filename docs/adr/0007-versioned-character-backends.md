---
status: accepted
---

# Admit B1 through versioned character backends

B1 computes the approved MakeHuman body and sportsuit from raw geometry, signed targets, a fitted skeleton and full positive final aggregate CPU influences. Its two appearance parameters and five diagnostic poses are different from the original GLB morph streams and authored animation clips. An explicit versioned `CharacterBackend` distinguishes these meanings while the core keeps one Work, shared editor commands, history and file format for all three entry points.

Work schema3 stores the backend and a present nullable diagnostic pose. Exact schema1/2 Works upgrade to the original GLB backend, preserving their identity, timeline, revision and stage; schema1 retains the default legacy stage. New readers reject unsupported backends and versions instead of silently substituting a character. Old readers will reject schema3; backward reading by older releases is not promised.

Keep the existing profile fields to bound this integration. For B1, the profile is canonical and pins a descriptor for the exact same approved sample. Its `morph_index` values are inert legacy metadata and never address GLB morph streams. B1 has no continuous clips or timeline. Diagnostic poses use a separate shared command, so a held shoulder or knee pose cannot be mistaken for imported or generated motion. Future generalized profiles can replace the legacy parameter binding once there is evidence for another character.

A pinned descriptor enumerates thirteen raw files with byte lengths and hashes. CLI and runtime share its byte validators. Production source, data and notices live in product directories, with no dependency on ignored experiment output or a machine-specific source path. Original numeric experiments remain controls; their meshes, reference frames and sampled answers do not generate runtime output.

Open is a transaction. A candidate B1 Work becomes active only after its raw data, fit, pose and CPU display have succeeded. Rejection preserves the committed Work, undo/redo history and last good rendering. Saving during a pending open always targets the committed Work. The runtime owns generation-scoped temporary entities and meshes; the core owns neither renderer objects nor files.

This admits a limited character path. It does not accept continuous B1 animation, appearance quality, normals at extreme folds, texture/material equivalence, GPU4, arbitrary MakeHuman input or performance. The existing GLB backend remains available. Source admission and implementation evidence are recorded in `docs/evidence/b1-work/`.

## Continuous rehearsal extension (issue #78)

The restriction above remains exact for backend version1 and profile `nvwa-mpfb-b1-v1`. A separate backend version2 and `nvwa-mpfb-b1-motion-v1` profile add two explicitly Nvwa-authored continuous rehearsal actions for the same thirteen raw files. Work schema3 stays unchanged; old static B1 and original GLB Works keep their identity and behavior. CLI `new-b1` remains static, `new-b1-motion` explicitly creates the motion version, and Studio New B1 creates the current motion version. An older reader must reject version2 instead of silently interpreting its timeline as a diagnostic pose.

In version2, a nonempty timeline owns the skeleton even when paused; an empty timeline uses the stored diagnostic pose. Choosing a diagnostic pose atomically clears the timeline, and one Undo restores both. A fitted shape caches its complete positive joint influences; each frame applies authored rotations, propagates the skeleton and updates both existing CPU display meshes. Fixed rest placement is preserved through the cycle. There is no per-frame floor correction, IK or contact solver. This separates mathematical skinning and geometric foot-contact evidence from animation, clothing and appearance quality. Existing quality HOLD findings require their own evidence.

## Eight-parameter character extension (issue #85)

Backend version3 and profile `nvwa-mpfb-b1-motion-v2` add six signed target pairs from the already approved MPFB source to the existing torso and jaw parameters. The new base descriptor is `characters/mpfb-b1-v2/manifest.json`: it authenticates the thirteen unchanged existing payloads and twelve additional target texts. Work schema4 stays unchanged. Old GLB, static B1 and motion B1 Works retain their exact profile, base and appearance identities. Opening an old Work does not upgrade it. Older readers reject the new backend instead of interpreting its parameters using an older profile.

The alternative was to extend the existing canonical B1 profile in place. That would make a previously saved Work depend on new files and change the meaning of its pinned asset set. A separate version costs a second descriptor and explicit dispatch, but preserves the existing files and rejection behavior. Appearance version2 likewise binds the unchanged skin, eye and hair payloads to the new base. Cross-version base/appearance combinations reject.

CLI `new-character` and Studio New character create this version explicitly. The existing `new-b1` and `new-b1-motion` constructors retain their previous output. The shared Core parameter catalogue bounds all eight values to `[-1, 1]`; CLI, commands, runtime and Studio use that catalogue. The runtime authenticates every selected descriptor payload before activating a candidate, including when shared inputs are already cached. It then fits the existing skeleton and applies all positive aggregate influences. No new rendering, animation, model inference or material policy is introduced.

This extends character creation, not the quality acceptance of the current low-poly eyes, hair or clothing. Extreme shapes, actual motion, ordinary UI and desktop/Web file exchange require separate current evidence. It does not admit arbitrary MakeHuman files, additional skeletons, generated actions, physics or performance claims.


## Explicit bilateral cheek fullness extension

Backend version4, profile `nvwa-mpfb-b1-motion-v3`, and base
`mpfb-hm08-game-engine-female-sportsuit01-v3` add one symmetric `cheek_fullness`
control in `[-1, 1]`, default `0`. Work schema4 stays unchanged. The original
constructors, eight parameter meanings, and old Work identities remain fixed.
CLI `new-character-contour` and Studio's New character menu offer the new profile
explicitly. Old Work Open does not migrate or add parameters.

Two bilateral leaf files preserve the existing negative/positive binding. Each
is the sorted union of the corresponding original left and right cheek-volume
rows, whose stored vertex ID sets are disjoint. All numeric tokens and zero rows
are retained. There is no averaging, reflection, sign inversion, or source unit
change. The existing target loader still converts units once. The four pinned
original CC0 gzip sources and exact derivation receipt ship with the V3 base.
The signed runtime mapping and full positive aggregate CPU influences stay fixed.
A generic composite binding would change the global manifest lifecycle and the
mapping interface for one control, so this version uses the existing leaf pair.

Appearance schema3 adds exact V3 bindings for both short04 and short01 with
unchanged payload bytes. Cross-version bindings reject. Runtime cache readiness
and typed-load failures inspect only the selected version's required targets;
cached V3-only handles cannot make old Works depend on the cheek files. Explicit
Open authenticates the selected descriptor and every payload even after caching.

This controls cheek fullness rather than jaw width. Adjoining surfaces can change;
mouth or nose isolation is not promised. It does not resolve the prior #133,
M2 motion, clothing, or full hair-quality holds. Visual reference usefulness,
CPU numeric agreement, actual product UI, motion, and release acceptance remain
separate evidence.

## One-sided lower-face squaring extension

Backend version5, profile `nvwa-mpfb-b1-motion-v4`, and base
`mpfb-hm08-game-engine-female-sportsuit01-v4` add `lower_face_squareness` with
finite inclusive range `[0,1]`, default0. Work schema4 and all previous profile,
constructor, parameter, base and saved-Work identities remain unchanged. CLI
`new-character-lower-contour` and Studio's explicit new-character menu choice
create this version. Old Open never upgrades a Work.

Zero contributes no new deformation;1 applies the exact original MPFB
`chin-bones-incr` endpoint. Fractions weight that source displacement. The
control describes lower-face contour squaring, not literal jaw-bone width,
measured squareness, equal perceptual steps or anatomical isolation. Adjacent
height/depth and jaw-to-neck transitions can change. Source-reference evidence
is conditional; actual-product interpolation, fitting, appearance and independent
review remain separate acceptance requirements.

The existing fixed pair loader remains unchanged. Both original chin-bones
leaves are retained, expanded without changing bytes, authenticated and loaded.
The canonical new minimum is0, so the decrease leaf always has zero active
weight; negative public input rejects before fitting. Its retention does not
adopt the held negative source reference. No fake endpoint, sign inversion,
source crop or endpoint repair is introduced. The29-file descriptor contains
the27 unchanged V3 runtime payloads and these two exact leaves. Compressed source
files and expanded hashes are retained in its provenance.

Appearance schema4 adds exact V4-base bindings for both existing hairstyles.
Their13/14 payloads stay byte-identical; runtime may reuse the authenticated V3
embedded byte tables under the distinct new descriptors. Base selection and
appearance keys already distinguish these versions. Shared source aliases and
extension-handle prefixes remain safe because all shared bytes and parameter
ordering are unchanged. Every explicit Open still authenticates its selected
manifest and all required files; V4-only failures cannot make old Works depend
on the new files. No Work-schema, renderer, cache-policy, rig or material-policy
change is included. Existing contour and motion quality HOLDs remain intact.
