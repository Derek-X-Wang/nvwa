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
