# Final headless evidence

This directory records the production candidate after the borrowed
`EditorUiSession` integration and strict clippy repair. Earlier files in the
parent directory remain checkpoint evidence. Their source identities are not
the final source identities below.

| Source | SHA256 |
|---|---|
| `crates/nvwa-studio/src/lib.rs` | `876329eb625aed45ce4229ea0277c8949a1337d2ff147e5caa25e17e48981f8e` |
| `crates/nvwa-studio/src/editor_layout.rs` | `da45cb7183d28e80cf8b15d1f08f8aa06463e0c5fe4af2b9067fbf8737878b5c` |

`tests-session.log` records 103 passing workspace tests. `clippy-session.log`
records a successful strict workspace/all-targets clippy check.
`mutations-final/` records five separate targeted runtime-red trials against
the exact source above, with exact-byte restore after each. The subsequent
`tests-session-final.log` records all 103 workspace tests passing on the restored
source, including all 31 original Studio tests and 10 new regressions.
Exit files and `session-final-checkpoint.json` retain the corresponding results.

The initial failed mouse-focus test, the test-only shortcut hardening and the
earlier green checkpoints are retained separately in the parent directory.
They are not rewritten as final-source runs. The draw/commit body remained
byte-identical through the borrowed-session refactor.

Only the exact task worktree path was replaced with `<UI_WORKTREE>` in copied
logs. `MANIFEST.json` records original and public file hashes, replacement
counts and the final source hashes. Assertions, test counts, mutation diffs and
source identities remain unchanged. These are headless checks. This directory
does not establish actual native/Web rendering, physical input, Save/Open or
Work exchange. Root owns that later acceptance evidence.

## Reproduction

Run from the repository root with the exact final source above, the pinned
dependencies/toolchain available, and no existing `.work/ui26/mutations-final`
directory. Use a fresh checkout for reproduction when the original evidence
directory already exists. The runner checks both source hashes before writing
anything and refuses to overwrite its output directory.

```sh
python3 -B docs/evidence/m1-1-ui/final/run-mutations-final.py
CARGO_BUILD_JOBS=3 cargo test --workspace --locked
CARGO_BUILD_JOBS=3 cargo clippy --workspace --all-targets --locked -- -D warnings
```

The runner writes fresh logs, diffs and `manifest.json` under
`.work/ui26/mutations-final`. It restores both source files in `finally` after
each trial and at exit. Its five tests must fail at their named runtime
assertions with exit101. The runner exits0 only after all expected red trials
and exact restores succeed. The subsequent full workspace run must pass.

The public reproducer is a hardened copy of the executed private runner. It
adds exact final-source preconditions and creates missing output parent
directories. The hardened copy was syntax-checked during evidence packaging;
it was not executed again during root's compile lease.

VERIFIED — final-source103 tests, strict clippy and five separate runtime-red
trials with exact restores. Actual GUI acceptance is outside this evidence.
