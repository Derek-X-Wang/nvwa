# Permanent CPU selected-tab paint checks

Recorded on 2026-10-13 in `codex/m11-ui-paint-permanent`, based on main
`045d8abc685760d09ba05afec0e40a811a282d1f`. This is a fresh evidence cohort;
`experiments/28-ui-paint-oracle` remains a historical experiment.

The permanent `editor_layout::paint_tests` module invokes the same
`draw_editor_ui` path as Studio, using the existing CPU harness. It observes
`egui::FullOutput` text and filled rectangle shapes. It does not read the
selected tab state to choose expected paint.

At both 1280×720 and 1024×768, the test starts with Shape, clicks the actual
Profile control, then clicks the actual Shape control. A literal table requires
Shape/Profile fills of active/inactive, inactive/active, then active/inactive.
It also requires the corresponding literal inspector text and absence of the
other inspector. Each tab requires exactly one label and exactly one containing
100×26 background painted before its label. The backgrounds must not overlap.

The test uses distinct literal sentinel colors, fixed test-only time, scale,
theme, and animation settings. It releases the pointer and removes hover before
each paint observation. Complete Work JSON and the complete editor/history
Debug snapshot must remain equal to the pre-click snapshots. The fixture must
contain both undo and redo snapshots. Each viewport completes in eight frames.
Existing tests retain their original time behavior; only this paint test opts
into fixed time.

Five named rejection controls require failure for empty output, a deleted tab
label, a deleted tab background, a duplicate tab label, or a duplicate tab
background. Four controls alter actual production output after first verifying
that its original observation is complete. Test discovery is checked against the
exact six-name set before every proof run; an empty or partial selection fails
the evidence runner.

## Local proof

All builds used the pre-existing shared `target` symlink and
`CARGO_BUILD_JOBS=1`. Only the Studio library test executable was rebuilt. Its
fresh Cargo artifact and SHA-256 are recorded in `identity-and-results.json`.
The selected six tests and the exact existing state test were then run directly
from that newly emitted executable, with one test thread. Lists, full output,
and exit codes are retained for each stage.

| Stage | New paint module | Existing state/Work/history test |
| --- | --- | --- |
| Green | 6 passed, exit 0 | 1 passed, exit 0 |
| Paint-only mutation | 5 passed, 1 failed, exit 101 | 1 passed, exit 0 |
| Restored green | 6 passed, exit 0 | 1 passed, exit 0 |

`paint-only-mutation.patch` inverts only the production paint branch from
`if selected` to `if !selected`. Tab selection, input handling, inspector content,
and Work commands remain unchanged. The new assertion reports a literal fill
mismatch at 1280×720, initial Shape. The existing
`actual_studio_layout_controls_preserve_work_history_and_guard_focused_space`
test stays green at both viewports. Production source was restored byte-for-byte
before the final compile and restored-green checks.

The first Cargo compile emitted a successful fresh artifact. Its shell wrapper
then failed while assigning zsh's read-only `status` variable. The green test run
used the verified artifact from that successful compile. Later compile wrappers
checked subprocess exit codes directly. This wrapper issue and the successful
Cargo `build-finished` records are explicit in the identity metadata.

Normal permanent-test commands:

```sh
CARGO_BUILD_JOBS=1 cargo test --locked -p nvwa-studio --lib editor_layout::paint_tests::
CARGO_BUILD_JOBS=1 cargo test --locked -p nvwa-studio --lib editor_layout::tests::actual_studio_layout_controls_preserve_work_history_and_guard_focused_space -- --exact
```

Proof compile command:

```sh
CARGO_BUILD_JOBS=1 cargo test --locked -p nvwa-studio --lib editor_layout::paint_tests:: --no-run --message-format=json
```

The existing macOS CI job calls `cargo test --workspace --locked` through
`experiments/27-ci-baseline/check.sh native`, so it includes the new module.
No workflow or historical source manifest changed.

VERIFIED — targeted CPU green/mutation-red/restored-green, exact source restore,
exact test discovery, `rustfmt --check`, and source `git diff --check`.
Raw test logs preserve their original blank line at EOF; the publication check
disables only Git's `blank-at-eof` diagnostic for those unchanged receipts.

## Integration follow-up

The original green/mutation-red/restored-green records above retain the
pre-lint source identity. Strict native clippy found three nested `if` clauses;
integration collapsed only those clauses into equivalent Rust2024 let chains.
No assertion, condition order, observation or production painter changed.
The failure and repair logs are retained in [fresh build evidence](../build/).

The final module SHA-256 is
`15a36a3b51a5f8fe79883e39353251edf6130ec145149380567667a77d1a2f6c`.
The final integrated workspace passes113 tests, zero failed/ignored/filtered;
strict native and actual Wasm clippy pass. A [fresh targeted independent review](post-lint/review.md)
accepts clause equivalence and independently replays all6 paint tests plus the
exact state/history control from the final executable. Its SHA-256 is
`2466193b055464984b7502f837803b4bf7c201124f10f246517db2c35538746f`.
Fresh mutation reenactment for the formatting-only change was NOT-RUN; the
historical mutation receipt is not relabeled as a new-source execution.

NOT-RUN — whole workspace, hosted CI, Web compile, native window, browser,
raster pixels, GPU presentation, and later dual-end acceptance. The root
orchestrator owns integration and those later checks.

All owned compile/test subprocesses exited. The compile lease was returned.
The pre-existing `target` and `.tools` symlinks and private historical logs were
preserved. Fresh raw Cargo output and the one-time proof runner remain under
`.work/m11-ui/` for root inspection; the committed evidence here is sufficient
to inspect the named test runs and executable/source identities.
