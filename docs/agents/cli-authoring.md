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
asset's hash and structure. Without the asset root, `validate` checks the work
document only. `save` validates and reserializes a work without changing its
revision. Import the exact saved file into native Studio or Web Studio for
separate rendering and continuing-edit proof.

The [M1.2 adaptive agent evidence](../../experiments/38-agent-cli/REPORT.md)
records a real LLM authoring run. Its raw calls and input/output snapshots are
separate from the synthetic integration tests. `record.py` records one chosen
call at a time and contains no preset or authoring sequence.
