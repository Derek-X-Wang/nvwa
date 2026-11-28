# Native CLI support

The source-built native CLI is Nvwa's third supported entrypoint, alongside native macOS Studio/Player and Web Studio/Player. It edits portable Work files through the same Rust core and typed commands as Studio. Its motion query uses the same CPU motion evaluator as the Player.

## Supported work

The CLI supports these local operations:

| Command | Operation |
| --- | --- |
| `new` | Create a GLB Work from a character profile. |
| `new-b1` | Authenticate the admitted B1 assets, then create the static version1 Work. |
| `new-b1-motion` | Authenticate the same B1 assets, then create the continuous rehearsal version2 Work. |
| `new-character` | Authenticate the version2 base's 25 payloads, then create the eight-parameter character Work. |
| `describe-capabilities` | Read the profile, current revision, supported parameters and authored clips, the saved stage, plus the CLI command contract. |
| `inspect` | Read a Work as JSON. |
| `apply` | Apply `set_parameters`, `set_scale`, `set_timeline`, `set_stage`, `set_diagnostic_pose` (B1), `set_appearance`, `undo` or `redo` commands and save the result to an output file. |
| `validate` | Check a Work and optional GLB assets; B1 requires the explicit root and authenticates every payload of the selected body and appearance manifests, including roles that are off. |
| `motion-query` | Sample foot clearance and clip boundaries in a finite B1 rehearsal Work. Requires the `motion-query` build feature. |
| `contact-query` | Sample the running character’s left index fingertip against a named sphere saved in the Work. Requires the `motion-query` build feature. |
| `contact-fit` | Use the character's own joint response to propose a local edit that restores fingertip contact with a saved target. |
| `contact-recheck` | Reopen a saved edit, compare the selected sole with its stance, and measure press and release timing against the reference. |
| `travel-query` | Measure body and garment displacement in stage coordinates for a finite B1 running Work. Requires the `motion-query` build feature. |
| `save` | Validate and reserialize a Work without changing its revision. |

Successful machine-readable responses use JSON on stdout. Help uses text. Handled errors return exit code 1 and a `{ "code": "...", "message": "..." }` JSON diagnostic on stderr when stderr is writable. The exact response and recovery rules are in the [CLI authoring guide](agents/cli-authoring.md).

## Headless motion observation

`nvwa-cli motion-query` is the default observation step for a supported
rehearsal edit. It runs the production CPU evaluator without opening a window
or starting a renderer and leaves the input Work byte-for-byte intact.

```sh
cargo build --locked -p nvwa-cli --features motion-query
target/debug/nvwa-cli motion-query dance.nvwa.json assets 3.25 6.075 0.025
```

Check `cli_contract.motion_query.available` and `work_supported` in
`describe-capabilities`. The portable file-editor build stays available
without the feature and returns `motion_query_unavailable` for an observation
request. The supported Work is a finite B1 rehearsal timeline with its
admitted body assets. Static Work, GLB, the running profile and single-loop
transport are outside this query's scope.

The arguments after the asset root are inclusive start, end and step in
seconds. The maximum is 201 regular samples per query. Clip starts after the
requested start and through the end are also compared with the immediately
preceding representable runtime timestamp. The default JSON gives the Work
hash and revision, sample coverage, foot clearance extrema, near-floor
intervals and anomalies. Add `--samples` to inspect individual rows when a
summary needs more detail.

Foot clearance is the signed minimum height of the visible body-foot mesh
above the stage floor. The near-floor band is −0.05 to 0.5 cm. The query flags
sampled clearances below −0.05 cm and absolute changes over 0.5 cm at clip
starts. Interval endpoints are the first and last sampled times in a run,
with no interpolation. This measures geometry within the sampled interval.
It cannot establish support force, shoe clearance, between-sample behavior,
or visual quality. Use `nvwa-cli apply` to save an edit to a new Work and
repeat the query at the same range and step. Review the final candidate in
normal playback and take screenshots where a specific visual detail needs
inspection. See the [short dance comparison](evidence/motion-query/RESULTS.md)
for the measured workflow and its limits.

## Fit and recheck an existing button press

Build the native CLI with `cargo build --locked -p nvwa-cli --features motion-query`.
Use the checkout’s `assets` directory. These commands work on an existing version 18
shaped character with a single reference-motion clip. The input stance contains
the landing to keep. The original reference contains the press and release to
match. All inputs must use the same saved target. The fitted version 18 path
supports the V15 body parameters used by Iris and Mora. Positive
`bust_circumference`, `buttocks_volume`, and `belly_shape_strength` need
additional deformation support.

From the repository root, use a fresh output directory:

```sh
case_dir=crates/nvwa-cli/tests/fixtures/contact-fit/iris
cli=target/debug/nvwa-cli
out=$(mktemp -d)
"$cli" contact-fit "$case_dir/start.nvwa.json" assets "$case_dir/reference.nvwa.json" \
    2.50 4.00 .025 --hand right > "$out/plan.json"
jq '.commands' "$out/plan.json" > "$out/edit.json"
"$cli" apply "$case_dir/start.nvwa.json" "$out/edit.json" "$out/revised.nvwa.json"
"$cli" contact-recheck "$out/revised.nvwa.json" assets "$case_dir/start.nvwa.json" \
    "$case_dir/reference.nvwa.json" 3.25 --hand right --sole left --support right
```

The fit uses the specified hand, the character’s geometry and the rotation tracks
already present. Inspect the plan before applying it. The recheck reads all three
Works from disk. It compares landing XYZ, heel and forefoot heights, pitch,
heading, and pelvis position relative to the support foot at the specified
instant. For contact it samples the full clip at 25 ms, then samples at 1 ms
around both Works’ observed edges. Positive timing differences mean later than
the reference. Events entirely between coarse samples can go undetected.
Read the JSON `status` (`passed`, `failed`, or `unassessable`) and the signed
uncertainty range for each edge. A completed measurement writes JSON even if the
motion misses the goal. The tolerance is one frame at 24 fps for each edge,
0.001 mm per landing component and 0.001 degrees per angle. In these two
fixtures the stance must miss and each finished Work must have one complete
press. Both cases retain their original first drafts under
[`tests/fixtures/contact-fit`](../crates/nvwa-cli/tests/fixtures/contact-fit).

## Fingertip contact with a saved target

Place a target **before** editing the reach. The existing `set_stage` command
replaces the whole stage. Start from the saved stage so other settings survive.
The optional target has a nonblank ID (up to 128 UTF-8 bytes, no control characters),
three finite stage-world coordinates in metres (+Y up, +Z forward), and a positive
radius in metres. Omit `contact_target` to remove it. The point stays fixed as the
character moves or changes scale.

```sh
nvwa-cli inspect reach.json | jq '{command_id:"place",expected_revision:.revision,
  command:{type:"set_stage",stage:(.stage + {contact_target:{
    id:"switch-a",position_metres:[0.5,1.62,2.18],radius_metres:0.015}})}}' > place.json
nvwa-cli apply reach.json place.json reach-with-target.json
nvwa-cli contact-query reach-with-target.json assets 6 6.5 0.01
```

`describe-capabilities` exposes `cli_contract.contact_query`. Use an admitted
finite B1 running Work at scale 0.001 through 100. A fresh CLI opens the Work
and reads the **displayed distal left index surface** on the authenticated running
body at Level 0. When the experimental Level 1 surface is active, the query
returns `contact_query_unsupported_display`. To query Level 0, reopen the Work
with `NVWA_B1_LEVEL1_DISPLAY` unset. Each sample tests whether the distance to the saved centre is at most
the radius. The output includes start, end, nearest sample and an adjacent-time
bracket for each observed entry or exit. The earliest sample wins a nearest-distance
tie. A query starting inside reports that state directly. A crossing and return
between two samples can be missed. Narrow the range or step to resolve it.
Add `--samples` for each position and distance. The range is inclusive with at
most 201 samples and a minimum 0.001 s step. Button events and physical forces
belong to the game host. This observation needs no renderer.

## Headless travel observation

To check how far a running character moves, read
`cli_contract.travel_query` in `describe-capabilities`. The command takes the
Work, asset root, inclusive start and end times, and sampling interval in seconds.
The production display supports saved character scales from 0.001 through 100.

```sh
target/debug/nvwa-cli travel-query forward.nvwa.json assets 0 5 1
```

The summary gives start and end positions for the body and garment display
origins and their end-minus-start displacement in stage XYZ metres (+Y up, +Z
forward). The saved scale is applied. Add `--samples` to find the first sampled
time when the character reaches a position. Each row includes the Work time,
source clip time, and timeline entry ID. Use a smaller interval to narrow an
arrival time. The query reads the Work without starting a renderer or changing
the file. [Reproduce the two-metre example](examples/game-character/README.md)

## Rehearsal stage files

New and saved Works use schema 4, including the explicit character backend, a present nullable diagnostic pose and a required non-null appearance. Exact schema 1/2 Works upgrade to the original GLB backend without changing their revision, identity, timeline or saved stage; schema 1 receives the default white stage. Exact schema 3 Works preserve their backend and pose. Schemas 1/2/3 migrate absent appearance to `{"type":"none"}` and reject any appearance field, including null. Unknown fields, duplicate keys and missing schema 4 fields are rejected. Saving writes schema 4, which older Nvwa versions cannot read. Historical fixtures retain their original format. B1 has two signed parameters and five static diagnostic poses. Static version1 has no timeline. Motion version2 adds two Nvwa-authored four-second rehearsal clips in a separate profile; it preserves static Works without silent upgrades. A nonempty timeline owns the motion pose, including when paused. Choosing a diagnostic pose clears that timeline atomically, and Undo restores both. Apply/save edit Work metadata without claiming asset or renderer readiness.

`set_appearance` replaces the saved selection through the same atomic command, revision, retry and Undo/Redo path as Studio. `{"type":"none"}` is supported on every backend. B1 accepts the fixed `b1_cc0` schema version 1 asset set `mpfb-b1-cc0-appearance-v1` and manifest SHA-256 `c3cf2b1040eed083fb1a328f0494b0c978cec42c71f3b7c826e14992f97cef04`. Required booleans `skin`, `eyes` and `hair` select roles independently; at least one must be true. Use `none` to clear all roles. Unknown identities, hashes, fields and unsupported backends fail before commit. `apply` and `save` validate portable metadata. `validate` with an asset root also authenticates the descriptor and all thirteen appearance files before reporting asset success. Rendering remains a separate acceptance.

The eight-parameter B1 character also accepts the separate schema 2 set
`mpfb-b1-cc0-appearance-v2-short01-v1`, whose manifest SHA-256 is
`8c2044ee524a700abd75479c457d2e269f7e280a67509749c9fd780794c6d49a`.
This set has fourteen payloads, including its original source metadata. It uses
the existing skin and eyes with short01 hair. Existing defaults remain short04.
Use `describe-capabilities` and its `cli_contract.set_appearance.compatible_sets`
to discover complete, compatible selections for the actual loaded character.
These examples have all three roles on; `current` describes the saved selection.
The [short01 Work](../examples/b1-short01.nvwa.json) can be opened in Studio or
Player. No new command or Work schema is required.

`set_stage` replaces the complete stage through the same atomic command as Studio. `describe-capabilities` returns the loaded stage, a serialized command example, numeric bounds and the quality profiles. `inspect`, `validate`, `save` and `apply` use the shared validator. Light intensity is lux, colors are three sRGB channels in `[0,1]`, and angles are degrees. Camera distance and target height use character-relative units, multiplied by the character scale only in the runtime. The floor remains at world height zero. Core scale validation remains finite and positive; the fixed presentation runtime reports an explicit camera error outside scale `0.001..=100` and preserves the Work.

Low quality requests no MSAA and no shadows. Balanced requests 4× MSAA and a 2048 key-light shadow map. High requests 4× MSAA and a 4096 key-light shadow map. Optional screen-space contact shadows are disabled after an actual Web comparison showed stable self-shadow speckle on the face and body. The saved shadow switch can disable the key shadows in Balanced and High; fill shadows stay off. These are shared runtime settings. Actual native/Web rendering, memory and frame times require separate acceptance. The CLI does not render them.

## Build and run requirements

Build the CLI from the repository root with the pinned Rust 1.95.0 toolchain and lockfile:

```sh
cargo build --locked -p nvwa-cli
```

Cargo needs the locked Rust crates available locally. A first build may fetch crates that are not cached. After the build, supported CLI operations read and write local files. They do not require an open Studio window, a browser, a GPU or local motion weights. Asset validation reads the supplied asset directory. The repository does not provide a public CLI installer or signed binary; users build from source.

For use outside the checkout, `scripts/package-cli.py` creates a local source-built
directory and archive containing the binary and a complete `assets/` root.
Both B1 bases, all three fixed appearance sets and the original GLB are included, with
the existing asset licenses and provenance. The packager authenticates the
supplied Works with that binary before publishing; `scripts/test-cli-package.py`
checks the actual extracted archive, relocation, creation/editing, and asset
rejection paths. Use the standalone `assets/` root explicitly. Native Studio
and Web rendering directories omit filesystem appearance payloads. See the
[standalone contract](CLI-STANDALONE.md) and [packaging commands](../README.md#standalone-offline-cli-distribution).
Public binary release, first-party licensing and complete dependency notices
remain separate gates.

## File handoff and limits

The CLI operates on Work files. It does not connect to a running Studio and exposes no server, daemon, MCP endpoint or remote API. Save the output Work to a new path, then open that exact file in native Studio or Web Studio to view, render, play or continue editing it.

Revision checks compare the requested revision with the document loaded by that CLI invocation. The filesystem has no compare-and-swap or cross-process lock. Separate processes can read the same revision and overwrite a shared output path, so use a distinct output path and inspect the actual Work before retrying a mutation. Undo, redo and successful command IDs exist only within one `apply` invocation; they do not persist when the Work is saved and reopened. If stdout delivery fails after a mutation, the output may already be saved; inspect it before retrying.

The bundled GLB idle, wave and turn clips and the B1 arm/knee rehearsal clips are authored actions. The CLI selects and sequences them; it does not generate actions. The optional query samples foot geometry. Use the separate Web preview for screenshots and Studio or Player for interactive rendering.

For an agent's visual feedback loop, the separate [Web preview workflow](agents/visual-preview.md)
accepts a B1 Work and timeline time, then captures the actual saved camera through
the existing renderer. It requires a WebGPU browser and the built preview adapter;
it does not add rendering to this native data CLI or connect to a running Studio.

For ordered motion inspection, `scripts/review-motion.py` wraps that
preview with an explicit installed Chrome executable on macOS and Python 3.12+.
Give it a Work, one or more times, and the saved camera or a temporary camera.
It owns each browser process and writes actual canvas PNGs and frame receipts
to the requested output directory. B1 motion receipts include left and right
foot clearance in centimetres. Use `--start`, `--end` and `--step` to
[sample a window and locate near-floor intervals](agents/visual-preview.md#sample-foot-clearance-over-a-time-range).
Use `scripts/measure-frame.py` to measure
chosen pixel segments against a frame receipt. Save any creative edit as a
separate Work and repeat the same camera and times. See the
[self-service commands](agents/visual-preview.md#inspect-several-times-without-opening-a-browser-by-hand).

The [Chinese workflow and editable examples](evidence/agent-motion-review/README.md)
retain two first drafts and all 44 normal images, plus four separate functional
reopen images. Both drafts received bounded visual and identity acceptance with
zero creative revisions. On 2026-11-04, the user explicitly accepted qualified
initial drafts for this Goal. Local acceptance is complete under that amendment;
actual creative revisions remain zero, with no revision benefit claimed. Release
remains PARTIAL pending normal PR CI and natural main verification. This wrapper
does not add rendering to the data CLI.

## Validation boundary

On 2026-10-15, the six-operation path (`new`, `describe-capabilities`, `apply`, `validate`, `save`, `inspect`) passed locally on macOS arm64 using a private output directory and the bundled asset. Discovery supplied the parameter, character ID and authored clip used by the command batch. The final `inspect` response matched the saved Work. This was file-operation verification; it did not start Studio, a browser, a GPU or a motion model.

The exact calls, stdout/stderr, source identities, command batch and saved Work are in the [CLI third-entry evidence record](evidence/cli-third-entry/README.md).

The latest completed [Bounded CI run for this source head, 38790750484](https://github.com/Derek-X-Wang/nvwa/actions/runs/38790750484) passed on `8dfc8a8c05ac2f5794498a76b36e8c747e27054c`. Its Ubuntu 24.04 `Core, CLI, and diagnostic controls` job passed formatting, strict core/CLI Clippy, and core/CLI tests, including the actual CLI paths. This is Linux CI evidence for that runner and source head. It does not establish support for every Linux distribution or toolchain. Windows and other platform combinations remain unverified.

This CI result covers the base source head only. CI for the integration candidate and final main remains a separate pending gate.

This CLI support statement does not change the open acceptance boundaries: [#3 remains blocked](https://github.com/Derek-X-Wang/nvwa/issues/3), [#4 retains unverified startup and performance gaps](https://github.com/Derek-X-Wang/nvwa/issues/4), and [#49 remains open for the unassisted Alpha gate](https://github.com/Derek-X-Wang/nvwa/issues/49).
