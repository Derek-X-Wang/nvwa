# Shared document and command contract — integration-owned

This contract is intentionally limited to one character and a portable JSON document.
Rust fields use snake_case. Core has no Bevy/egui dependency and forbids unsafe.

- `SceneDocument { schema_version: u32, revision: u64, profile: CharacterProfile, character: CharacterRecipe, timeline: Vec<TimelineClip>, stage: StageSettings }`.
- `CharacterProfile { backend: CharacterBackend, id: String, asset_path: String, asset_sha256: String, license: String, parameters: Vec<ParameterSpec>, clips: Vec<ClipSpec> }`.
- `ParameterSpec { id: String, morph_index: usize, min: f32, max: f32, default: f32 }`.
- `ClipSpec { id: String, animation_index: usize, duration_seconds: f32 }`.
- `CharacterRecipe { id: String, profile_id: String, parameters: BTreeMap<String, f32>, scale: f32, diagnostic_pose: Option<String>, appearance: CharacterAppearance }`.
- `TimelineClip { id: String, clip_id: String, start_seconds: f32, duration_seconds: f32, speed: f32, looping: bool }`.
- `CommandEnvelope { command_id: String, expected_revision: u64, command: Command }`.
- `Command` is Serde internally tagged `type` in snake_case: `SetParameters { character_id, values }`, `SetScale { character_id, scale }`, `SetTimeline { clips }`, `SetStage { stage }`, `SetDiagnosticPose { character_id, pose_id }`, `SetAppearance { character_id, appearance }`, `Undo`, `Redo`.
- `Editor::new(document) -> Result<Editor, CoreError>`; `document(&self) -> &SceneDocument`; `apply(&mut self, envelope) -> Result<CommandResult, CoreError>`.
- `CommandResult { revision: u64, summary: String, duplicate: bool }`; `SceneDocument::validate() -> Result<(), CoreError>`; `SceneDocument::from_json(&str) -> Result<Self, CoreError>`; `to_json(&self) -> Result<String, CoreError>`.
- `SceneDocument::from_profile(profile) -> Result<Self, CoreError>` makes default character `character-1`, scale 1, parameters at defaults, timeline idle if present.
- CoreError must be serializable and displayable, carrying a stable error `code` and useful message. Reject unknown fields, unsupported version, empty/duplicate IDs, invalid references, nonfinite/range values, unsafe relative asset paths. Maximum JSON input 2 MiB.
- A command is atomic. Successful edits increment revision once. Undo/redo restore content but revision stays monotonic. Duplicate command IDs are idempotent only for the same payload; conflicting ID reuse is an error. A slider preview uses a validated cloned document, and commits one command on drag release.
- Runtime owns Bevy resources that mirror `Editor`; the document remains authoritative. Runtime must report load errors and backend-specific readiness from actual meshes/bones; GLB includes skin/morph/player evidence.
- Studio uses one native/window or browser canvas and Bevy main loop. Native/web save/open lives only in platform.rs. CLI file edits are offline, not live GUI control.
- PlatformIo delivers `FileCompletion::Opened(String)` or `Saved`, never an empty-string sentinel. Imports are bounded regular files on native and picker-selected bounded data on Web. Browser downloads confirm initiation; native writes complete before Saved. Explicit successful Open creates a new asset-load generation, including when profile/path are unchanged.
- Asset workflow publishes assets/character.profile.json, assets/fixtures/nvwa-humanoid.glb, sources/license/hash manifest. Animation indices and morph indices must match actual exported data; other workflows consume rather than modify the asset files.
- Integration owner is /root. Proposed interface changes go to /root first; only /root changes this contract, root dependencies, Cargo.lock and toolchain.

## Portable rehearsal stage (introduced in schema 2)

New documents and saves use schema 4 and require a complete validated `stage`.
The strict schema 1 wire shape upgrades to `StageSettings::white_studio()` without
changing character, timeline, profile or revision. Unknown fields, duplicate keys,
null or missing schema 2/3/4 stage settings, and unsupported versions are errors.
Saving the upgraded Work writes schema 4; earlier applications cannot read it.
Original schema 1 examples and historical experiment inputs remain unchanged.

`StageSettings` contains key/fill light intensity, sRGB color and direction;
ambient brightness and color; background; floor visibility, color and shadows;
camera framing; and requested `low`, `balanced` or `high` quality. Numeric bounds
and serialized examples come from `describe-capabilities`, not UI defaults.
Camera distance and target height are character-relative. The runtime multiplies
them by the character scale and reports unsupported rendering scale outside
`0.001..=100`, preserving the Work. Core's finite-positive scale rule is unchanged.

`SetStage` replaces the complete stage atomically. Studio previews and commits a
completed stage or camera gesture as one command; Escape restores the prior
stage. Player camera movement is temporary. Runtime quality effects are verified
on each target separately; requesting `high` does not claim a measured frame rate.
High uses a 4096 key-light map and 4× MSAA; screen-space contact shadows stay off
after a real same-pose comparison showed skin speckle. Scene framing uses the
available Studio/Player canvas through the same projection as picking. Layout
and DPI changes do not mutate the Work.
See [ADR 0006](../adr/0006-portable-rehearsal-stage.md).

## Additive offline CLI discovery (M1.2)

`describe-capabilities <work.json>` preserves every existing profile and
`editor_retention` key. It adds `character_id` from the loaded character recipe,
`document_revision` from the loaded work, and `cli_contract` with its own
`schema_version: 1`. This does not change the portable document schema.

`cli_contract` describes entrypoints, strict JSON input and envelope fields,
production-serialized command examples, parameter and timeline constraints,
revision rules, atomic batch output, structured errors, stdio/exit status and
asset validation. Examples use the loaded work's actual IDs and revision. Each
is an independent command shape, not a ready-made batch; undo/redo require
earlier history in the same `apply` invocation. Numeric JSON and retention
limits come from the core constants; profile ranges and source clip durations
remain authoritative for the loaded character.

CLI editing remains offline. Each `apply` starts a fresh editor and saves only
after every envelope succeeds. Input, command, validation and persistence
failures before successful save leave the input and existing output unchanged
and do not create an absent output. Response delivery is separate: a handled
stdout write failure exits 1 with `stdout_write`, and structured stderr is best
effort when writable. The output may already be saved and stdout may be partial;
inspect the actual output before retrying a mutation. No rollback or atomicity
between filesystem persistence and response transport is promised.
Revision checks compare to the loaded input document only; there is no
cross-file or cross-process
compare-and-swap, persistent idempotency or cross-invocation undo/redo history.
Discovery does not introduce live Studio control or generated motion. See the
[CLI authoring guide](../agents/cli-authoring.md) for recovery and file exchange.

## Versioned character backends (schema3)

`CharacterProfile.backend` is an explicit `{type:"glb",schema_version:1}` or `{type:"b1_cpu",schema_version:1,asset_id:"mpfb-hm08-game-engine-female-sportsuit01-v1"}`. `CharacterRecipe.diagnostic_pose` must be present: null for GLB; neutral, shoulder, elbow, knee or combined for B1. Exact legacy schema1/2 documents upgrade to the original GLB backend and null pose. Schema1 receives the existing white default stage. Other old values, IDs, revision and timeline are preserved. Schema3 never infers missing backend or pose fields. Readers predating schema3 cannot open the new format.

The limited B1 profile is `nvwa-mpfb-b1-v1`. `CharacterProfile::b1()` constructs its exact canonical definition. `torso_length` and `jaw_drop` range from -1 to 1 and default to zero. The retained `morph_index` values 0 and 1 are inert compatibility metadata for this backend, and never address GLB morph streams. B1 has no continuous animation clips or timeline. `SetDiagnosticPose {character_id,pose_id}` changes one fixed inspection pose through the existing editor, revision, retry and undo/redo semantics. It is not a generated action. Existing GLB commands and timeline playback retain their meaning.

The B1 profile pins `characters/mpfb-b1-v1/manifest.json` by SHA256. Its exact thirteen-file set includes raw geometry, target deltas, skeleton/weights and sportsuit inputs; no pose reference output generates the character. Shared core byte validators check the descriptor and the same data bytes consumed by a loader. Bounds are 32 KiB per manifest, 4 MiB per data file and 8 MiB total. CLI B1 creation and validation require an explicit asset root and check every required raw file with bounded regular-file reads within that canonical root. B1 validate without a root fails with `asset_root_required`. Portable apply/save edit Work metadata only and do not claim asset readiness; GLB metadata-only validation stays compatible. GLB validation retains its semantic and hash checks with a 64 MiB asset-read bound. Work JSON retains the 2 MiB bound.

Runtime B1 opening is pending until asset validation, fitted skeleton, canonical pose, transform propagation and both full-influence CPU display meshes succeed. A rejected or superseded candidate must preserve the committed Work, undo/redo and last good render. Saving while pending saves only the committed Work. A successful commit retires the previous generation. Temporary preview and renderer handles remain outside the Work. Camera and stage edits never become parameter edits or rebuild the character unnecessarily.

B1 readiness records real CPU display publication and actual bones, with no artificial GLB morph/player counters. Two parameter controls and five diagnostic poses are the admitted scope. Numerical evidence covers the retained eight recipes by five poses. Continuous motion, arbitrary assets, appearance quality, GPU4 and performance remain separate gates. See [backend decision](../adr/0007-versioned-character-backends.md) and [integration evidence](../evidence/b1-work/).

## Saved B1 appearance (schema 4)

`CharacterAppearance` is either `none` or the pinned `b1_cc0` asset identity with independent skin/eyes/hair booleans. `SetAppearance` uses the same atomic revision and Undo/Redo route. Old schemas1–3 keep their original strict wire shapes and migrate absent appearance to None; schema4 requires an explicit non-null appearance. Studio, Player and CLI consume the same selection. See [the complete appearance contract](appearance-v1.md) for identity, asset authentication and runtime failure boundaries.
