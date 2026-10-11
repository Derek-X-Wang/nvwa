# Independent PR17 review and repair

Reviewed frozen base d74493df0ab14f786e798cee03efe5ef9e2e4670 to head9a7bde49ff9457912c9b5f82442fffe9b26de30a. Two fresh read-only sessions used the code-review skill's separate axes, without the implementer's confidence or previous review conclusions as a first-pass packet. Local Codex Desktop/native collaboration route; no reviewers ran compilers, graphics or network servers. Root separately executes validation.

## Standards

GPT-6.1 Sol high found no documented-standard violation or material correctness/security defect. Rust-first ownership, typed atomic commands, portable document state, platform boundaries and transient interaction agree with ADR0004/0005 and the accepted M1 contract. One P3 heuristic: Studio and Player duplicated Play/Pause/Replay/Restart and seek widgets, making a future transport change require two edits.

A separate Sol-high implementation worker extracted draw_transport_buttons and draw_transport_seek in Studio lib.rs only. Studio's composition controls still occur between buttons and seek; each caller retains its own readiness/loading/interaction gates. No new abstraction without a caller, schema change, keyboard change or runtime clock consolidation. Targeted Standards rereview accepted the repair with no new findings.

## Spec

Fresh GPT-6 Astra high found no actionable missing/incorrect/scope-creep requirement within the user-approved thin M1. Reviewed finite sequence boundaries/gaps/repeated actions, pause/seek/restart, replacement players, interaction restoration/cancellation, atomic overlap rejection, file recovery and static URL/stream limits. Explicit native GUI recovery/platform/hotspot evidence gaps remain limits rather than undisclosed implementation defects. Read-only artifact comparisons verified native5→Web6, full-document roundtrip/interaction equality and the canonical fixture hash.

Targeted cross-model R2 rereview of the transport extraction accepted the actual diff with no new findings: button behavior, M0 source-time versus finite global-time seek, caller gates, Player immutability, shortcut and discarded-pass behavior remain intact.

Frozen repaired Studio source SHA256: e29c7bbe2fb6b1440c6e298fe1e515f058a3c9fce573d596e0eb547bc99e7a0b.

VERIFIED — Independent Standards and Spec review; one nonblocking Standards finding repaired and accepted by both targeted rereviews. Fresh tests/builds/runs are separately recorded in ACCEPTANCE.md. No hosted CI workflow is configured; hosted CI is NOT-RUN.
