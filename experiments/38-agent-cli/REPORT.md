# M1.2 actual agent CLI authoring

This report and its nine raw process receipts describe the original authoring
run. Its pre-fix transport contract was rejected and is not current API evidence.
The [revised-binary actual run](accepted-run/REPORT.md) records the current
nine-call adaptive chain and byte-identical final work. Independent review
found a response-transport error boundary in the original
binary. The [review response](review-response/REPORT.md) records red/green proof
and the correction. The original binary, receipts and exact saved work remain
unchanged. Current transport guidance is in the linked agent guide.

The actual LLM worker discovered the supplied character's capabilities,
authored the requested appearance and nine-second sequence, encountered an
intentional real stale-revision failure, inspected actual state, corrected the
request, validated the work against the asset, saved it and read it back.
The final work is [agent-nine-second.nvwa.json](agent-nine-second.nvwa.json).
This is authored action sequencing, with no generated motion.

The exact root-authored acceptance request, human authority and model/effort/
route attribution are in [TASK.md](TASK.md). The worker's actual choices and
observations between calls are in [DECISIONS.md](DECISIONS.md). These are not
inferred from a passing test or replay script.

## Product change

`describe-capabilities` preserves the existing profile and retention keys and
adds the loaded `document_revision`, stable `character_id`, and a versioned
`cli_contract`. Its five command examples use production serialization and
the actual loaded work. The response explains command inputs, ranges,
wall-time constraints, revisions, structured errors, batch saving, process
boundaries, asset validation and output conventions. No core, document schema,
runtime, Studio, daemon or command semantics changed.

Revision checks only compare to the loaded input. This does not add cross-file
or cross-process compare-and-swap, persistent idempotency or saved undo history.
Undo and redo only use history from earlier commands in the same invocation.
The [agent guide](../../docs/agents/cli-authoring.md) explains these limits.

## Actual calls

Each numbered receipt folder contains exact `argv`, cwd, time, exit code and
binary hash in `invocation.json`, raw `stdout.txt` / `stderr.txt`, and complete
before/after JSON argument snapshots. The generic [recorder](record.py) launches
one selected call and has no workflow or authoring policy. The agent selected
each later call after reading actual earlier output. Native signed/tool trace
export is NOT-RUN; these are self-captured production process receipts plus
the native conversation's tool calls.

| Receipt | Production call | Result |
| --- | --- | --- |
| `01-new` | `new` | Saved revision 0 |
| `02-discover` | `describe-capabilities` | Actual profile, IDs, ranges, commands and semantics |
| `03-appearance` | `apply` appearance | Revision 1, two values changed |
| `04-stale-timeline` | `apply` intentionally stale timeline | Exit 1; `revision_conflict`; empty stdout; no output file |
| `05-inspect-actual` | `inspect` actual appearance input | Revision 1; appearance preserved; old timeline unchanged |
| `06-corrected-timeline` | `apply` corrected timeline | Revision 2; three authored actions |
| `07-validate-asset` | `validate` with actual asset root | `asset_checked: true`, `valid: true` |
| `08-save-final` | `save` | Saved final revision 2 |
| `09-inspect-final` | `inspect` exact final saved file | Expected parameters and timeline read back |

Input work and command files are retained alongside the output. No failed
output exists; the failed receipt's argument snapshots and auditor establish
absence and unchanged input. The CLI binary hash is identical across all nine
calls. Absolute build paths are provenance, not portable executable locations.

## Exact work for Studio

Revision 2, `character-1`, profile `nvwa-original-humanoid-v1`.
Jaw width 0.42, smile 0.2, nose width 0, shoulder width 0, scale 1.

| Authored action | Wall-time span | Saved speed | Looping |
| --- | --- | --- | --- |
| idle | 0–3 seconds | 1.013889 | false |
| wave | 3–6 seconds | 1.013889 | false |
| turn | 6–9 seconds | 1.3472222 | false |

The agent chose source-duration/3 speeds to fit each full authored source
action into the requested three-second span. Saved speed spellings reflect
actual core f32 serialization. The sequence ends at nine wall-time seconds.
Native/Web reload, rendering and continuing edit remain NOT-RUN by this worker;
root owns that acceptance step with this exact file.

## Verification

`CARGO_TARGET_DIR=/Users/derekxwang/.codex/worktrees/m12-agent-cli/target-cli cargo test --locked -p nvwa-cli -j 1`
passed all eight actual-binary integration tests. Raw stdout/stderr are in
`receipts/cargo-test.stdout` and `receipts/cargo-test.stderr`. Two new tests
exercise discovery examples against a nonfixture character ID/revision and
real stale-second-command failure for absent and existing output, actual
inspection/correction, and cross-invocation undo rejection. Existing tests
still cover typed command equivalence, asset validation, failed batch output
preservation, duplicate keys, FIFO rejection and M1 round trips.

These tests are synthetic regression checks. They are not the actual agent
authoring proof. `python3 -B experiments/38-agent-cli/verify.py` audits stored
process evidence and final state; its stdout is `receipts/verify.stdout`.
Formatting was checked for changed Rust files. Only the core/CLI compilation
path ran, with one job and a private target directory. No GPU, Studio build,
server or background process was started. The Cargo task completed and was
reaped. Independent review and root GUI acceptance remain outstanding.
