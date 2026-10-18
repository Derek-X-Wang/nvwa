# Native CLI support

The source-built native CLI is Nvwa's third supported entrypoint, alongside native macOS Studio/Player and Web Studio/Player. It edits portable Work files through the same Rust core and typed commands as Studio. This support promotion documents the existing file operations; it adds no service or product behavior.

## Supported work

The CLI supports these local operations:

| Command | Operation |
| --- | --- |
| `new` | Create a GLB Work from a character profile. |
| `new-b1` | Authenticate the admitted B1 assets, then create the static version1 Work. |
| `new-b1-motion` | Authenticate the same B1 assets, then create the continuous rehearsal version2 Work. |
| `describe-capabilities` | Read the profile, current revision, supported parameters and authored clips, the saved stage, plus the CLI command contract. |
| `inspect` | Read a Work as JSON. |
| `apply` | Apply `set_parameters`, `set_scale`, `set_timeline`, `set_stage`, `set_diagnostic_pose` (B1), `undo` or `redo` commands and save the result to an output file. |
| `validate` | Check a Work and optional GLB assets; B1 requires the explicit root and authenticates all thirteen raw files. |
| `save` | Validate and reserialize a Work without changing its revision. |

Successful machine-readable responses use JSON on stdout. Help uses text. Handled errors return exit code 1 and a `{ "code": "...", "message": "..." }` JSON diagnostic on stderr when stderr is writable. The exact response and recovery rules are in the [CLI authoring guide](agents/cli-authoring.md).

## Rehearsal stage files

New and saved Works use schema 3, including the explicit character backend and a present nullable diagnostic pose. Exact schema 1/2 Works upgrade to the original GLB backend without changing their revision, identity, timeline or saved stage; schema 1 receives the default white stage. Unknown fields, duplicate keys and missing schema 3 fields are rejected. Saving writes schema 3, which older Nvwa versions cannot read. Historical fixtures retain their original format. B1 has two signed parameters and five static diagnostic poses. Static version1 has no timeline. Motion version2 adds two Nvwa-authored four-second rehearsal clips in a separate profile; it preserves static Works without silent upgrades. A nonempty timeline owns the motion pose, including when paused. Choosing a diagnostic pose clears that timeline atomically, and Undo restores both. Apply/save edit Work metadata without claiming asset or renderer readiness.

`set_stage` replaces the complete stage through the same atomic command as Studio. `describe-capabilities` returns the loaded stage, a serialized command example, numeric bounds and the quality profiles. `inspect`, `validate`, `save` and `apply` use the shared validator. Light intensity is lux, colors are three sRGB channels in `[0,1]`, and angles are degrees. Camera distance and target height use character-relative units, multiplied by the character scale only in the runtime. The floor remains at world height zero. Core scale validation remains finite and positive; the fixed presentation runtime reports an explicit camera error outside scale `0.001..=100` and preserves the Work.

Low quality requests no MSAA and no shadows. Balanced requests 4× MSAA and a 2048 key-light shadow map. High requests 4× MSAA and a 4096 key-light shadow map. Optional screen-space contact shadows are disabled after an actual Web comparison showed stable self-shadow speckle on the face and body. The saved shadow switch can disable the key shadows in Balanced and High; fill shadows stay off. These are shared runtime settings. Actual native/Web rendering, memory and frame times require separate acceptance. The CLI does not render them.

## Build and run requirements

Build the CLI from the repository root with the pinned Rust 1.95.0 toolchain and lockfile:

```sh
cargo build --locked -p nvwa-cli
```

Cargo needs the locked Rust crates available locally. A first build may fetch crates that are not cached. After the build, supported CLI operations read and write local files. They do not require an open Studio window, a browser, a GPU or local motion weights. Asset validation reads the supplied asset directory. The repository does not provide a public CLI installer or signed binary; users build from source.

## File handoff and limits

The CLI operates on Work files. It does not connect to a running Studio and exposes no server, daemon, MCP endpoint or remote API. Save the output Work to a new path, then open that exact file in native Studio or Web Studio to view, render, play or continue editing it.

Revision checks compare the requested revision with the document loaded by that CLI invocation. The filesystem has no compare-and-swap or cross-process lock. Separate processes can read the same revision and overwrite a shared output path, so use a distinct output path and inspect the actual Work before retrying a mutation. Undo, redo and successful command IDs exist only within one `apply` invocation; they do not persist when the Work is saved and reopened. If stdout delivery fails after a mutation, the output may already be saved; inspect it before retrying.

The bundled GLB idle, wave and turn clips and the B1 arm/knee rehearsal clips are authored actions. The CLI selects and sequences them; it does not generate actions. The current data CLI does not sample poses or produce offscreen screenshots, video or exports of genuine generated motion. Studio remains the path for interactive rendering when it is useful.

## Validation boundary

On 2026-10-15, the six-operation path (`new`, `describe-capabilities`, `apply`, `validate`, `save`, `inspect`) passed locally on macOS arm64 using a private output directory and the bundled asset. Discovery supplied the parameter, character ID and authored clip used by the command batch. The final `inspect` response matched the saved Work. This was file-operation verification; it did not start Studio, a browser, a GPU or a motion model.

The exact calls, stdout/stderr, source identities, command batch and saved Work are in the [CLI third-entry evidence record](evidence/cli-third-entry/README.md).

The latest completed [Bounded CI run for this source head, 38790750484](https://github.com/Derek-X-Wang/nvwa/actions/runs/38790750484) passed on `8dfc8a8c05ac2f5794498a76b36e8c747e27054c`. Its Ubuntu 24.04 `Core, CLI, and diagnostic controls` job passed formatting, strict core/CLI Clippy, and core/CLI tests, including the actual CLI paths. This is Linux CI evidence for that runner and source head. It does not establish support for every Linux distribution or toolchain. Windows and other platform combinations remain unverified.

This CI result covers the base source head only. CI for the integration candidate and final main remains a separate pending gate.

This CLI support statement does not change the open acceptance boundaries: [#3 remains blocked](https://github.com/Derek-X-Wang/nvwa/issues/3), [#4 retains unverified startup and performance gaps](https://github.com/Derek-X-Wang/nvwa/issues/4), and [#49 remains open for the unassisted Alpha gate](https://github.com/Derek-X-Wang/nvwa/issues/49).
