# M1 offline CLI sequence

The portable work in `examples/m1-sequence.nvwa.json` starts from
`examples/default.nvwa.json` at revision 0. The single envelope in
`examples/m1-commands.json` replaces the timeline and advances the revision to
1. It uses stable segment IDs and places idle at 0 seconds, wave at 3 seconds,
and turn at 6 seconds. Each segment lasts 3 seconds, runs at speed 1, and has
looping disabled. The character appearance stays at the profile defaults.

The saved document was produced and asset-checked with the existing release
CLI:

```text
target/release/nvwa-cli apply examples/default.nvwa.json examples/m1-commands.json examples/m1-sequence.nvwa.json
[{"revision":1,"summary":"Set 3 timeline clip(s)","duplicate":false}]

target/release/nvwa-cli validate examples/m1-sequence.nvwa.json assets
{"asset_checked":true,"revision":1,"valid":true}
```

`crates/nvwa-cli/tests/sequence.rs` adds actual-binary integration coverage.
It applies the checked-in batch from the default work, validates the result
against repository assets, saves and reloads it, then compares the complete
document, including the character recipe, timeline, and revision. Its failure
case applies a valid edit followed by an out-of-range edit and checks that the
input and an existing saved work keep their original bytes.

The timeline describes a 9-second arrangement of authored action references.
This fixture and its CLI checks do not assert that runtime playback works.
