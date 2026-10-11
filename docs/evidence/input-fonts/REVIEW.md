# Independent CJK review

Budget: R1, one independent cross-model reviewer. Implementer GPT-6.1 Sol high; reviewer GPT-6 Astra high, fresh read-only context. Scope: diff against merged main `96c00de`, font/module/startup hook, font provenance/license/derivation, packaging and CPU tests. The reviewer did not implement the scope or run a renderer/compiler.

No actionable source findings. The reviewer independently inspected the installed bevy_egui scheduling and egui font implementation, parsed the shipped TTF, checked weight 400, hashes, matching source/derivative cmap semantics and glyph order, and measured standalone compression. The hook runs after context initialization/deferred commands and before BeginPass; appending one fallback preserves Latin/symbol defaults for both families and both app modes.

Actual root test execution exposed two distinct test-harness problems. Both failed attempts are retained: [first](tests-first-attempt.log), [second](tests-second-attempt.log). First, egui 0.36 guards against dropping unapplied texture deltas; the CPU harness now explicitly discards unused renderer commands. Second, `has_glyph` compares font-face identity to the replacement face, producing false negatives for supported Monospace ASCII in Hack. The unchanged full mixed corpus now checks actual parsed non-NOTDEF character maps, actual layout character identity, positive finite advances and atlas images for visible glyphs. Unsupported supplementary Han, Latin preservation and per-context lifecycle assertions remain. No test was deleted, ignored or turned into an unconditional pass.

The same independent reviewer accepted each targeted repair by inspecting the owning source and the revised assertions. Final reviewed `fonts.rs` SHA-256: `626af6577806de19310691a28891b00cc8cc1a89cc9ed95a4df930fc472ee0c2`. Runtime font configuration was unchanged by these test repairs.

Review limits: source and CPU coverage cannot prove visual glyph shapes, physical IME/clipboard behavior, startup/memory, or actual packaging output. Root-owned native/Web runs and final checks are separate in [acceptance](ACCEPTANCE.md).
