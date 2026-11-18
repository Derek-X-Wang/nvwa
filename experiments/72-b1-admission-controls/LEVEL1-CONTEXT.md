# Level 1 display source successor

`input-context-level1-display-v1.json` admits the opt-in B1 display integration
as one exact successor of `b1-upper-arm-muscle-v14-product-v1` at
`bac24197e0c2c329180550b0ce8f5b2a0c54a2ad`. It changes exactly
`crates/nvwa-runtime/src/b1.rs` and `lib.rs`, and adds exactly
`b1_level1_geometry.rs` and `b1_level1_display.rs`. All other 1,126 predecessor
entries retain their exact byte counts and SHA-256 hashes. The manifest itself
has a code-pinned SHA-256 in `run.py`.

The two overwritten predecessor source files are copied verbatim into
`fixtures/pre-level1-display/`. Admission checks their byte counts and hashes
against the already pinned v14 context before considering the successor. No
historical manifest, fixture, baseline receipt or HOLD control is rewritten.
The v14 source remains independently admissible in the historical test copy.
Partial additions, mixed old/new files, changed source bytes, missing files,
symlinks and unreviewed v14 assets still reject. The existing five unchanged
numeric sections of `b1.rs` remain hash checked by `check_unchanged_sections`.

The frozen-source consumer in `experiments/73-high-poly-eyes` independently
pins the same successor manifest SHA and predecessor fixture bytes. Its
historical v14 test continues to check the old files, while its current-root
test checks the new full union. This consumer is part of the portable
eye/hair group and must pass before the successor is considered admitted.

This is source identity admission only. It does not establish display quality,
runtime performance, physical GPU behavior, or acceptance of the body shape.
