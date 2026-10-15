# Initial independent R2 review

Reviewed base `a094baa048e6e50056e3288ecfa85bb4ac62e140` to candidate `a6cb13eeadeae0e30b42c9307286d9c84c49286b`. Scope: CLI discovery, its tests and documentation, and experiment 38. No reviewed source was changed.

## Finding: P2 response-transport contract overstates failure atomicity

Candidate `crates/nvwa-cli/src/main.rs:150`, lines 158-171, and `docs/agents/cli-authoring.md:34` advertised unchanged output on failure and structured JSON errors with exit 1. Independently closing the child's stdout pipe made the retained production binary save revision 1, then panic with exit 101 and non-JSON stderr. Save preceded println at main.rs:263. The implementation behavior predated this change, but the unconditional discovery guarantee was new. Corrective requirement: distinguish precommit failures from response/process failure and require inspecting output before retry; do not promise rollback after save.

Raw evidence: `boundary-results.json`, `closed-stdout.stderr`, and `closed-stdout-output.json`. Original binary SHA-256: `a35bce6b43b7e06d8f352441e7abf4e6505feab19163074df95fabc91ae078a4`.

## Actual verification

- All eight CLI integration tests passed with `cargo test -p nvwa-cli --locked --offline -j 1` in a reviewer-private target.
- Existing `verify.py` passed.
- Bound every retained JSON argument snapshot to its versioned artifact and independently replayed all nine calls using the original retained binary. Process outputs and produced document bytes matched.
- Independent probes passed profile JSON compatibility, duplicate retry/undo/redo, late stale-command atomicity for absent and existing output, conflicting IDs, unknown fields, duplicate keys, and output rename-failure cleanup.
- All 74 scoped source files matched the candidate byte-for-byte. `source-hashes.json` and `evidence-hashes.json` retain identities.

No additional findings in this scope. Replay verifies process behavior, not LLM authorship. Native authorship confirmation and GUI/Web acceptance remained root-owned. Experiments 39/40 and whole-publication approval were excluded. All reviewer processes exited; private Cargo target and test temporary directories were removed. Raw evidence was retained. Original binary was not changed.

This report records the actual first pass and its original finding; it is not a new test run or a statement that the finding remains open after the later fix.
