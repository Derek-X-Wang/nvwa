# R2 targeted re-review — stage A

**ACCEPT stage A. Finding 3 is resolved.** No new material finding in the observer repair or the reviewed `docs/SOURCES-LICENSES.md` correction. This does not clear experiment 36 or the overall publication gate; findings 1/2 remain pending stage B. Its moving files were not read in this stage.

Reviewed future observer SHA-256: `309eeb47f4ca5279e23cbb16189c010e50ad770a472211621236b2bc7f320d7a`.
Reviewed license document SHA-256: `45aafb2e294d51b0d0bbf5c80b6b4942b328e382b05e4740318da6533f0b1d27`.

VERIFIED — Six DOM/forwarding Node tests and seven Python tests pass. Independently reran all three named actual-source mutants (overflow-dom-stale, dom-error-blocks-original, record-bound-65); each exits 1, and each exact current-source restoration exits 0. Mutant hashes match the owner's receipts. Copies and full outputs are retained only under this private stage-a directory.

Added an independent CPU control whose DOM write first fails after successful initialization, thus directly exercising wrapped console calls rather than only initialization. Original return value/object identity, borrowed receiver and original exception identity are preserved. A later successful journal publication exposes two prior write failures, the exact 64 retained record bound and 39 drops after 102 console calls. The helper does not alter Blob/anchor/rendering/runtime timers or download actions.

All 36 historical experiment-35 evidence files match the reviewer's original before-hashes receipt byte-for-byte, including old observer copies, raw browser packets, network log, evidence manifest, both PNGs and both original screenshots. Historical case-2 observer remains `08b34dec…`; the new future helper was not substituted into the historical record. Offline historical verifier passes. No new browser/download/render/server/build occurred. The report correctly keeps CPU hardening separate from actual observations and discloses that persistent DOM write failure leaves a stale last successful snapshot, while failed creation leaves no supported DOM journal.

The source-license correction matches actual pinned craft-libs workspace metadata (`MIT OR Apache-2.0`) inherited by craft-ui. The existing packaged MIT file matches the pinned root MIT bytes. Actual first-party crate manifests have no declared license and root `LICENSE` is absent. The document preserves owner choice, candidate incompleteness, NOT-RUN signing/notarization/clean-machine scope and does not claim that notices were installed or a licensing branch selected.

Limits: future hardened observer actual-browser execution NOT-RUN; no legal/completeness/distribution approval; original issue 5 cause remains unknown; experiment 36 findings 1/2 and final publication documents await stage B. No reviewed source files edited. Finite subprocesses reaped; no persistent reviewer-owned processes. **QUIESCENT**.
