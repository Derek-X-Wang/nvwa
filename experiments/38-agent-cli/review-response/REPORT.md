# R2 response-transport correction

Independent R2 found that closing the stdout consumer caused the original CLI
to save the output, then panic in `println!` with exit 101 and non-JSON stderr.
Thus the original discovery claim that all errors exit 1 without committed
output was too broad. Root's actual finding evidence was read in
`.work/m12-cli-r2/boundary-results.json` and `closed-stdout.stderr` in the retained
`m11-ui-integration` worktree. This is an original-implementer correction;
independent re-review remains root-owned.

## Change and contract

Every success response, including help and read-only calls, now goes through
one explicit fallible stdout write and flush. A response delivery failure
returns `stdout_write` and exit 1. Structured stderr delivery is best effort;
writing a diagnostic to a closed stderr no longer causes a second panic.
Successful response shapes remain the same.

Persistence and response delivery are separate operations. A mutating command
may already have saved its output when the response fails, and stdout may be
partial. The diagnostic and machine-readable discovery direct the caller to
inspect the actual output before retrying. The CLI does not attempt rollback.
The existing batch failure guarantee covers input, command, validation and
persistence errors before successful save. There is no promise of atomicity
between filesystem persistence and acknowledgment transport. Guide and shared
contract wording now state this boundary. Core/schema/session semantics did
not change.

## Red/green evidence

The added `response_transport` integration tests ran against the real binary
before the fix. `red-tests.stdout` / `red-tests.stderr` retain actual failures:
closed stdout and closed stderr both returned 101 instead of 1. The source of
the error was directly established by the production panic trace; no broad
instrumentation or speculative dependency changes were needed.

After the fix, the same tests pass. The stdout test closes an actual OS pipe's
read end before starting the CLI. It exercises `new`, `apply`, `save`, `inspect`,
`describe-capabilities`, `validate` and `help`, checks exit 1, parses structured
`stdout_write` stderr and rejects panic text. For mutating commands it checks
the already-saved work and correct revision; for every call it checks unchanged
input. A separate closed-stderr domain-failure test requires exit 1.

`final-tests.stdout` / `final-tests.stderr` retain the final
`CARGO_TARGET_DIR=/Users/derekxwang/.codex/worktrees/m12-agent-cli/target-cli cargo test --locked -p nvwa-cli -j 1`
run. All ten actual-binary integration tests pass. Existing late-batch
atomicity and absent/existing-output tests remain intact and green.

The separate [differential probe](check_transport.py) ran original and revised
production binaries against the same real closed-pipe boundary for `new`,
`apply` and `save`. All original calls exit 101; all revised calls exit 1 with
structured `stdout_write`; both versions have already saved valid outputs at
revisions 0/1/0 respectively. Complete argv, binary hashes, raw stderr and saved
files are retained in `process-probe/`, with summaries in `results.json` and
`process-probe.stdout`. Revised read-only discovery, inspect and asset-validation
calls are retained there too. This is synthetic boundary evidence, not a new
adaptive-agent authoring claim. The probe creates a fresh evidence directory
and intentionally refuses to overwrite an existing one.

`stderr-controls.json` separately records two actual revised-binary controls:
a domain failure with closed stderr, and a read-only response with both stdout
and stderr consumers closed. Both exit 1. Closed streams are recorded as
unavailable, not as observed empty diagnostics. Regression tests and the
differential transport probe remain separate from the repeated actual agent
run in `../accepted-run/`.

## Retained original evidence and resource handoff

Before rebuilding, the original agent binary was copied to:

`/Users/derekxwang/.codex/worktrees/m12-agent-cli/original-agent-nvwa-cli`

Its SHA256 is
`a35bce6b43b7e06d8f352441e7abf4e6505feab19163074df95fabc91ae078a4`.
The revised binary remains at:

`/Users/derekxwang/.codex/worktrees/m12-agent-cli/target-cli/debug/nvwa-cli`

Its SHA256 is
`e0da6b3e5759801b9d5e4898a2ecda716111ee05159415163521fb01eb6ea637`.

The original nine adaptive call receipts, command files and exact work remain
unchanged. The historical receipt auditor still passes. The final work SHA256
remains `e33356b490cb8d6c01118958c3d22409f4546cfa6164a7d69d496be292eb25cc`.
Revised `inspect` and `validate` read that exact work successfully, so there is
no need to regenerate the accepted authored sequence. Native/Web acceptance
must continue to use that exact work.

The worktree, both binaries, private target and raw evidence remain retained
for root QA. No server or background process remains active. No resource
disposal is claimed. Native/Web rendering and independent re-review are
NOT-RUN by this worker.
