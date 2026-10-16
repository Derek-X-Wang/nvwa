# Provisional Path B input manifest gate

These fields describe validation, not authorization. Do not create a manifest with `approved: true` until root has the user's exact source/data approval. Root must reconcile this schema with Path A's common sample manifest first; the exact common file bytes and digest must match both paths.

`approval.json`, schema version 1:

- `route_id`: `source-runtime`.
- `local_source_read_approved`: true only after approval.
- `offline_build_approved`: true only for an approved source/build-script scope.
- `candidate_commit`: `286d33124648501535655a0de811cef55152b9fd`.
- `candidate_path`: exact absolute resolved immutable source-snapshot path.
- `upstream_inventory_sha256`: fixed `3c0d8c4d2aac9c398d3b7eb75272ced08f6babafd6bd4577f895e50f10b661ab`. The checked-in inventory contains exactly 45 upstream source files / 561,909 bytes with pinned paths, sizes and Git blob SHA-1 identities. No `.git`, original Cargo.lock or assets are accepted.
- `candidate_files_sha256`: map of exactly those 45 paths to approved local SHA-256 values. Both upstream Git blob identities and local hashes must match. A free-form local tree hash is insufficient.
- For a future build only: `derived_path`, `derived_tree_sha256`, `offline_build_approved`. The derived package must be outside the immutable source and contain Cargo.toml, a fresh Cargo.lock and patch.json with the exact `upstream_inventory_sha256`. Tree digest concatenates sorted relative path, NUL, file SHA-256, newline; `.git`/`target` trees excluded; symlinks rejected. Actual derived package is absent and unapproved today.
- `sample_manifest_sha256`: exact common sample-manifest SHA-256.

`sample.json`, schema version 1:

- `parameter_schema`: `paired-local-targets-v1` for the approved torso/chin paired-target probe. Other schemas receive an explicit unsupported error until a real adapter exists.
- `sample_class`: `makehuman-approved-sample`; `approved`: true only after approval.
- `reference_manifest_sha256`: common offline reference identity. This field records identity; it does not prove reference execution.
- `basis`, `units`, `transforms`: explicit coordinate convention and transform identity.
- `files`: list of unique relative paths with `role`, `path`, `sha256`, `license`, `source_url`. Required common roles: `basemesh`, `vertex_groups`, `target`, `rig`, `weights`, `garment`, `reference`. `target_manifest`, `macro_manifest` and `body_proxy` are schema-dependent derived inputs, not unconditional requirements or permission to expand the common sample. The first paired-local-target probe does not require world macro parameters.
- `cases`: unique `case_id`, `kind`, exact `recipe`; includes kinds `neutral`, `body`, `face`, `combined`. More intermediate cases are allowed and required later for continuous-edit acceptance.

All file paths resolve below the sample manifest's directory. Target paths/parameter ranges/defaults/axes are derived from approved content, not guessed here. The reference files must already be present. Neither runner nor manifest triggers downloads or produces reference output.

This gate checks identity and presence; it does not parse or validate MH geometry, semantics, rig compatibility, licensing sufficiency or visual quality. Those require the real adapter and separate evidence.

## Candidate-specific format conversion boundary

The common approved MH/MPFB inputs stay identical for A and B. Humentity's composite `target.json`, macro `.macro`, vertex-group JSON and rig/weight JSON may be derived artifacts rather than files MPFB exports in these exact schemas. Never substitute Humentity's bundled example rig or silently fetch its assets. First inspect the approved common data and execute the candidate loaders. If schemas differ, record the precise failed field/format, then implement only the necessary conversion into a separate derived-data directory. Record the converter version and each source/derived digest. No MPFB/GPL implementation code is copied by this proposal.

Mandatory for comparison: exact shared base/rig/garment/parameter/case/reference identity, source provenance and hashes; actual mesh/joint/rest/inverse-bind outputs or explicit unsupported errors; candidate format metadata needed for every chosen parameter. Humentity-specific files must be generated solely from the same approved source inputs, or enter an explicit new bill. Optional and excluded initially: physics, crowd GPU data, LOD variants, hair, skin textures, author example animation files and arbitrary other rig mappings.

Root contract extension needed before a real run: an agreed common manifest schema; source vs derived input roles; deterministic converter/patch identity; exact common rig representation and any loss/unsupported fields; measured coordinate conversion; reference tolerances; authored test-motion provenance. This is a schema/adapter gate, not permission to enlarge the sample. If a rig field cannot be faithfully mapped, report that Path B does not support this common sample yet; keep the rig fixed for both routes.

## Output preservation

Use a new receipt path for every run. The runner creates receipts and separate metadata/build logs exclusively and never overwrites existing files. Existing output paths, input aliases and output paths within the candidate source are rejected nonzero. Receipt/log collisions may intentionally produce no new receipt. Sentinel controls prove approval/sample/source bytes survive rejection, including symlink and hardlink aliases.
