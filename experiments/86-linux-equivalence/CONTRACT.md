# Same-source Linux equivalence pilot

This is a bounded experiment. It does not migrate a required check or change the
frequency of the existing macOS jobs.

## Frozen source

- Repository: `Derek-X-Wang/nvwa`
- Source commit: `baa0b6bbda0d9709f0fab37c9e7d962fd8d926c1`
- Source tree: `f14ea4fa6ea749fdd06c36e0fca5d622feb5bb95`
- Reference macOS run: <https://github.com/Derek-X-Wang/nvwa/actions/runs/39742202675>
- Rust: `1.95.0`; Bevy: `0.19.1`; committed lockfiles retained.

The experiment harness is checked out separately from that exact source commit.
It must record both identities. No product, vendor, asset, source manifest,
lockfile, historical assertion, or existing workflow may be edited for a pass.

## Comparison

Run the existing native Cargo commands on Linux with the existing feature
selection. Record a platform build failure as a failure. The resolved workspace
graph already enables X11 through `bevy_egui`; do not add a backend feature merely
because the root manifest disables Bevy defaults. This is static dependency
evidence, not a successful Linux compilation. Any later build-argument change
requires a separate, explicitly labelled comparison arm.

Run the full original CPU, source, continuous-motion, mutation, and Wasm command
inventory. The macOS-only shell guard and Apple cache machinery are classified
separately; they cannot be called Linux successes. Preserve test filters,
offline/locked flags, normal and optimized Python controls, all 594 frames, and
the existing production-source mutation witnesses. Missing commands, unexpected
source drift, missing evidence, or an empty test inventory must fail.

## Execution and evidence

Use a bounded standard `ubuntu-24.04` GitHub runner experiment. At most two heavy
compile jobs may run concurrently. No GPU, paid runner, model invocation, model
download, new character asset, or local VM provisioning is part of the pilot.
The existing `ci.yml` remains byte-for-byte unchanged. Do not rerun the macOS
reference just to collect a second timing sample.

Before execution, review the dependency and resource request. Inspect available
system packages first. Do not install extra system packages or change the
dependency graph without reporting the exact missing prerequisite.

Record queue time, tool/dependency acquisition, compilation and tests separately.
Record real run IDs, per-command exit status, mutation failures and recovery,
source/lock integrity, and explicit unrun scope. One cold observation per lane
does not establish a stable performance distribution or a CPU architecture
comparison: the reference is macOS ARM64, the Linux runner is x86_64.

## Decision boundary

Report measured results before proposing which checks move to daily Linux and
which macOS checks remain at platform-sensitive or release milestones. No
automatic adoption follows from a green experimental run. Desktop graphics,
Metal, input methods, window/DPI behavior and packaging remain outside the
headless equivalence claim. Issue #3 remains blocked; issue #4 keeps its gaps.
