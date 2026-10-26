# Author a work through the offline CLI

The CLI edits portable work files through the same core commands as Studio.
It does not control a running Studio. Authored actions remain authored actions;
choosing and sequencing them does not generate motion.

Build with `cargo build --locked -p nvwa-cli`. Start a work with
`nvwa-cli new assets/character.profile.json work.nvwa.json`, or use an existing
work. Run `nvwa-cli describe-capabilities work.nvwa.json` before authoring.

Discovery preserves the character profile's existing top-level keys and
`editor_retention` response. It adds `document_revision`, `character_id`, and
`cli_contract` with its own `schema_version: 1`. Read profile `parameters` for
supported IDs and inclusive ranges, and `clips` for supported authored actions
and source durations. Read `cli_contract` for entrypoints, executable envelope
shapes, timeline constraints, file/session limits, error recovery, and output
conventions. These additions do not change the portable document schema.

Each `command_examples` entry is an independent shape for the loaded work.
Examples use that work's actual character ID, parameters, timeline and revision.
They are not a ready-made batch. Undo and redo require history created earlier
in the same `apply` invocation. Choose new command IDs and values that express
the requested work. `set_parameters` changes only named values; `set_timeline`
replaces the entire timeline. Timeline duration is wall time. Source pose time
advances at `speed`; profile source durations do not set the wall-time span.
Spans must not overlap. Adjacent spans and gaps are allowed.

Save an envelope or array in a JSON file. Run
`nvwa-cli apply input.nvwa.json commands.json output.nvwa.json`.
Each successful nonduplicate command advances revision by one. A later envelope
in a batch must use the revision after preceding envelopes. The full batch must
succeed before the output is saved. Input, command, validation and persistence
failures before successful save leave the input and existing output unchanged
and do not create an absent output. Success emits JSON on stdout with exit
code 0. Handled errors exit with code 1 and emit
`{ "code": "...", "message": "..." }` if stderr is writable. Help emits text.

Saving a file and delivering its response are separate operations. A closed
stdout consumer or another response write error produces `stdout_write` rather
than a panic. A mutating command may already have saved its output, and stdout
may contain a partial response. Inspect the actual output work before retrying
the mutation. Do not infer that exit code 1 means no file was saved. Errors
before response delivery have empty stdout; unavailable stderr cannot carry a
diagnostic. The CLI does not roll back a saved work after transport failure.

After `revision_conflict`, run `inspect` on the actual input file. Reconsider
the intended edit against that state, then build a corrected request. A failed
batch does not persist its earlier commands, even if an error message refers
to a revision reached temporarily within the batch.

Revision checks compare against the document loaded by that invocation. There
is no filesystem compare-and-swap or cross-process lock. Two processes can read
the same revision and overwrite the same output. The CLI does not provide
persistent idempotency. Undo, redo and remembered successful command IDs belong
only to one `apply` invocation; opening a saved work starts a fresh session.
The discovered retention policy describes the bounded editor session.

Run `nvwa-cli validate output.nvwa.json assets` to check the actual referenced
asset's hash and structure. For the original GLB backend, omitting the asset root checks the Work document
only. B1 validation requires the explicit root and authenticates the selected
base descriptor and every raw payload; omitting it returns `asset_root_required`.
`save` validates and reserializes a work without changing its revision. Import the exact saved file into native Studio or Web Studio for
separate rendering and continuing-edit proof.

The [M1.2 adaptive agent evidence](../../experiments/38-agent-cli/REPORT.md)
records a real LLM authoring run. Its raw calls and input/output snapshots are
separate from the synthetic integration tests. `record.py` records one chosen
call at a time and contains no preset or authoring sequence.

## B1 character Work

Create the admitted body and sportsuit without opening a window. Choose a new output path for each Work:

```sh
nvwa-cli new-b1 assets my-character.nvwa.json
nvwa-cli describe-capabilities my-character.nvwa.json
nvwa-cli validate my-character.nvwa.json assets

# Continuous authored rehearsal; same raw assets, distinct backend/profile.
nvwa-cli new-b1-motion assets my-motion.nvwa.json
nvwa-cli describe-capabilities my-motion.nvwa.json
nvwa-cli validate my-motion.nvwa.json assets
```

B1 creation authenticates the exact shipped descriptor and thirteen raw files
before saving. Its two signed appearance values and five fixed diagnostic poses
use the same atomic commands and history rules. Read discovery for command IDs
and examples, including `set_diagnostic_pose`. Static version1 has no timeline.
Motion version2 provides `b1_arm_rehearsal_v1` and `b1_knee_flex_v1`, each four
seconds, through the shared `set_timeline` command. They are authored actions,
not AI-generated actions. A nonempty timeline owns the skeleton even when
paused. `set_diagnostic_pose` atomically clears the timeline; Undo restores it
and the previous diagnostic pose. Old static B1 Works are not upgraded. Apply/save edit the portable Work only; they do not inspect
assets or claim that a renderer has opened it. Native/Web rendering is a
separate check. Schema1/2 GLB Works and schema3 Works upgrade to schema4 when saved; old readers
will reject schema4. Schemas1/2/3 require appearance to be absent and migrate it
to `{"type":"none"}`. Schema4 requires explicit non-null appearance.

## Portable B1 appearance

Use `set_appearance` with the loaded character ID and revision to save the
selection. `none` has exactly `{"type":"none"}`. B1 accepts `b1_cc0` with
the exact schema version, asset set ID and SHA-256 returned by discovery,
and all three required booleans `skin`, `eyes`, `hair`. V1 uses appearance
schema1; the eight-parameter V2 base uses appearance schema2. Work schema4 and
the seven appearance fields stay unchanged. Select any independent
combination with at least one true; use `none` for no roles. GLB supports `none`.
The command uses the existing atomic transaction, retry, Undo and Redo rules.
Unknown fields, missing/null values, duplicate keys, changed identities and
unsupported backends reject without saving the batch.

`apply` and `save` edit portable metadata. `validate work.json asset_root`
authenticates the fixed body asset and, when appearance is selected, its
descriptor and every appearance payload, including unselected roles. Legacy
sets have thirteen payloads; short01 has fourteen, including full original
package metadata. The existing size limits still apply.
These commands do not establish rendered appearance readiness.

`set_appearance.compatible_sets` contains complete, typed appearance objects
that can be copied into a `set_appearance` envelope. Its role flags are all
true as selectable defaults; they do not describe the current Work. Read
`current` for the actual selection. V1 lists its existing short04 set. V2 lists
its existing short04 set and `mpfb-b1-cc0-appearance-v2-short01-v1`. Unsupported
backends list no sets. The existing `schema_version`, `asset_set_id` and
`asset_set_sha256` fields keep their base-default meaning, so old examples
continue to select short04. Selecting short01 is explicit; saving old Works
does not upgrade their appearance. `works/b1-short01.nvwa.json` in the standalone
package (or `examples/b1-short01.nvwa.json` in the checkout) demonstrates the
V2 selection with the existing authored timeline and stage.

For use outside the source checkout, the complete standalone package provides
an `assets/` root with both admitted B1 bases and all three appearance sets. Set an
absolute root explicitly; do not substitute Studio's or the Web export's
rendering asset directory, which omits filesystem appearance payloads.
See `README.md` in the extracted standalone package for offline usage and
distribution limits, or `docs/CLI-STANDALONE.md` in the source checkout.
