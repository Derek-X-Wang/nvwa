# Bounded Linux execution request

## Purpose

Measure whether the existing macOS CPU/source/Wasm checks work on Linux, using
exact source commit `baa0b6bbda0d9709f0fab37c9e7d962fd8d926c1`. This does not
change a required check or its frequency.

## Execution budget

- Existing public repository: `Derek-X-Wang/nvwa`.
- Standard GitHub-hosted `ubuntu-24.04`, x86_64; no paid or larger runner.
- One experimental workflow run, two jobs, at most 60 minutes per job.
- One Cargo compile worker in each job; at most two builds at once; no GPU.
- No local VM start, Docker start, host package install, model invocation,
  character re-export or new model/character asset.
- No automatic retry, cache seed, macOS rerun or change to `ci.yml`.

## Inputs acquired by the fresh runner

- The existing pinned `actions/checkout` revision and the exact source commit.
- Repository Rust `1.95.0`, `rustfmt`, `clippy`, and `wasm32-unknown-unknown`,
  using the same installation command as current CI.
- Cargo registry and Git dependencies selected by the committed lockfiles.
  `--locked` is mandatory. No version upgrade or dependency addition.
- Pinned `actions/upload-artifact` revision
  `ea165f8d65b6e75b540449e92b4886f43607fa02` for experiment evidence only;
  retention seven days. Durable results will also be archived separately.

These tool/dependency files are the normal pinned CI inputs, but fresh runners
may need to download them again. Their byte total depends on the hosted image
and preinstalled caches and has not been measured. No download size is claimed.
Inspect available system prerequisites first; if a system package is missing,
fail and report it. There is no authorization to run `apt install` or to add
other downloads under this request.

## Evidence retained

Job/queue timings, exact source and harness identities, original command
inventory, tool/dependency time, compile/test timings, all exit codes, real
production fault detection and restored passes, full motion/source receipts,
and source/lock integrity. A failed Linux run is a valid experiment result.

## Approval state

Derek approved the fresh-runner tool/dependency acquisition in this request on
2026-10-22. Execution still requires the independent harness review. This is
authorization for one bounded experimental run, not for changing current gates,
adding downloads, or repeating the run automatically.
