# Explicit historical experiment48 audit

This adapter audits the retained experiment48 evidence against its historical
source bytes. It does not replay a GUI, build a binary, or claim that the old
screenshots were produced by the current experiment49 sources. Quality remains
`HOLD`. Current experiment49 native/Web runtime evidence remains separate.

The unchanged experiment48 verifier rejects the current checkout because its
source cohort predates the two reviewed Studio `manual-start` additions. That
actual rejection is retained in [direct-current-red.json](results/direct-current-red.json).
The adapter never turns that invocation into a success. It invokes the unchanged
historical verifier in a separate, disposable source snapshot.

## Exact boundary

[POLICY.json](POLICY.json) permits exactly two substitutions:

- `crates/nvwa-studio/Cargo.toml` from [the archived source](sources/nvwa-studio-Cargo.toml.txt).
- `crates/nvwa-studio/src/lib.rs` from [the archived source](sources/nvwa-studio-lib.rs.txt).

The archive bytes were extracted with `git show
03ab0d87eb5281bcf497d3adc179a1ee321a41a6:<repo_path>`. Each archive matches the
byte count, SHA256, and Git blob recorded by the original experiment48 source
cohort, whose source commit is
`7cfe171ea7d0bd2ba8e777b188e68ab9cbd85bf8`. The different commit labels do not
substitute for content identity. No Git executable or historical checkout is
needed to run the adapter.

Before staging, the adapter requires all of the following:

1. The exact policy digest and exactly the two named substitution entries.
2. Both archived historical identities and both separately pinned current Studio
   identities. A further current Studio edit fails even when the old archive is valid.
3. All other 52 live source inputs match the old cohort byte count, SHA256, and
   Git blob, and every original runtime file and four source artifacts match the
   pinned identities and exact runtime file set.
4. Both pinned current experiment49 native/Web cohort JSON files match their own
   retained identities. Their platform, completed matching build status, binary
   metadata, and all current file/source maps are checked. Both source maps must
   bind the current Studio identities. These checks audit retained build metadata;
   they do not rerun the binaries or require the large build outputs in CI.

The snapshot contains those 54 historical source inputs, the original runtime
archive, and the four original source artifacts. Checked bytes are read once and
then written into the snapshot. The original staged CLIs execute as subprocesses;
no original module is imported, patched, rewritten, or skipped. The staged control
script retains its own original repository-relative source lookup. The adapter
checks its live inputs again before reporting success. Temporary snapshots are
removed on exit. The repository and protected historical files are not modified.

## Commands

Run from the repository root, using the existing Python standard library only:

```sh
python3 experiments/49-runtime-pose-parity/historical48/audit.py
python3 experiments/49-runtime-pose-parity/historical48/audit.py --check controls
python3 -O experiments/49-runtime-pose-parity/historical48/audit.py --check controls
python3 experiments/49-runtime-pose-parity/historical48/test_audit.py
python3 -O experiments/49-runtime-pose-parity/historical48/test_audit.py
```

Default `--check audit` executes the original staged verifier once and emits
`PASS_HISTORICAL48_AUDIT`. `--check controls` executes the original staged control
suite once and requires its baseline green plus all 26 mutation-red and 26
restored-green cases before emitting `PASS_HISTORICAL48_CONTROLS`. The parent's
`-O` mode is explicitly propagated to each original child. Audit-only success
makes no claim that the control suite ran. Child failure or a timeout is failure.

The adapter controls exercise 20 cases in each Python mode: 18 real CLI or staged
original-CLI red/restored-green pairs, and two forced OS child failures through
the production execution seam. The forced child failures use a local executable
that exits 7, leaving the original scripts unchanged; the complete original
suites are run separately, rather than repeated for every adapter mutation.
Cases cover corrupt/missing archives, each current Studio source, another live
source, missing/extra/duplicate/broadened policy entries, a broadened current
cohort pin, crossed native/Web cohorts, an altered original verifier, a changed
current build source, damaged staged source/artifact bytes, and propagation of
both verifier and control child failures. All requirements use explicit checks
that remain active under `-O`.

Retained JSON receipts are under [results](results/audit-normal.json): audit in
both modes, original controls in both modes, adapter controls in both modes,
and the separate original current-source rejection. The receipt commands execute
no GUI, downloads, model access, Rust compilation, or machine configuration.
