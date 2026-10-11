# M1.1 production UI integration contract

Authorized scope: issue #26. Implement the accepted experiment15 tab/split pattern in production, with one Bevy loop and the existing Rust command/runtime/Web-input paths. Issue #27 runs independently against its frozen A/B artifacts; this integration does not adopt the size-oriented profile.

## Session state and behavior

The private `editor_layout` adapter is the only production module that imports pinned `craft-ui` types. Shape/Profile selection, timeline height, lock and in-progress separator cancellation are app-owned session state. They receive no Work or command handler and are not serialized. Actual production UI tests and saved full JSON comparisons must establish document/history invariance; layout-only tests cannot substitute for those observations.

The timeline starts at 210 logical points. Its visible height clamps to available viewport policy; zero-delta redraws preserve the preferred height through temporary window shrink. Escape restores the separator height at drag start and suppresses further drag deltas until release. Lock prevents resizing. Reset restores Shape and 210 while retaining lock. Both-axis scrolling retains access to timeline controls in smaller viewports. Layout state installs only on the final egui pass, preserving the existing command commit boundary.

The original `scene.nvwa.json` default, save/open semantics, drag-preview/one-command transaction, Undo/Redo, Work schema, error display, Player read-only surface and Web text adapter remain in scope for regression verification. Remove all experimental A/B UI and debug metadata.

## Evidence gates

Retain all original 93 tests, meaningful real-control regressions, failed logs and fixes. Record separately: tests, native build, Web build, actual real-rig native GUI, actual real-rig Web GUI, both 1280×720 and 1024×768 viewports, full Work saves/reloads/exchange, and independent source/evidence review. Prior prototype human confirmation is prior evidence only. Physical IME, unsupported DPR/zoom and other OS/browser cases remain NOT-RUN unless actually verified on this artifact.

No docking framework, layout persistence, new assets/rigs, M2 or Web default profile change. Build/GPU leases and notice packaging remain root-owned. Complete the concrete reviewable PR before proposing main promotion.
