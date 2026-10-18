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
