# Experimental B1 V15 belly shape (native CLI source candidate)

**HOLD for compiled, fitted/skinned, rendering and visual acceptance.** This
is an opt-in V10 derivative, not the historical rounded V2 experiment, a
gestation model, a 3D measurement, or any character's canonical shape. No
pregnancy stage, fetus count, chronology, postpartum behaviour, outfit, motion,
or combined maximum has been approved by this change. It does not change the
default profile, old Works or their asset identities. The unrelated V11–V14
profiles are not ancestors of this profile.

The profile `nvwa-mpfb-b1-belly-shape-v1` (backend schema 17) inherits V10's
25 controls unchanged and adds `belly_shape_strength` in [0, 1], default 0.
Zero does not enter the active morph set. A positive value contributes one
unmodified CC0 target with weight `value × 0.25` before the existing native
fit and full-weight skin path. No negative direction is loaded. Beyond this
source coefficient, effects on adjacent geometry, garments, posed height and
anchors are not yet established. See the V15 asset's provenance directory for
exact MPFB commit and source hashes. Existing immutable V10 payloads are copied
unchanged to a separate asset directory, matching the repository asset layout.

After building with the repository's pinned toolchain, create a distinct Work
with `nvwa-cli new-character-belly-shape assets example.work.json`. Use
`describe-capabilities` for the parameter contract and use regular
`set_parameters`, `validate` and `save`. The native CPU build can attempt
`render example.work.json --assets assets --output preview --mode body-reference`
with appearance none. No Web bundle or Studio preset is introduced.

## Validation required

- `cargo test --locked -p nvwa-core --test belly_shape`
- `cargo test --locked -p nvwa-cli --test belly_shape --features cpu-render`
- `cargo test --locked -p nvwa-runtime belly_shape_v15_reopens_after_each_old_branch_without_altering_zero`
- Compare actual same-camera 0, 0.25, 0.5, and 1 images and same-pose ground
  and scale, finite fitted bones and bad silhouette/stretch. Compare zero
  against V10 with mixed body controls, check neutral and diagnostic poses.
  Do not infer garment fit, production quality or lifecycle behaviour from images.

The pinned toolchain was unavailable in the authoring environment; the Rust
tests and render commands above have not run there.
