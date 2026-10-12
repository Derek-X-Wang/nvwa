# CPU paint-oracle review

2026-10-12. Fresh independent Astra R2 reviewer, separate from the Sol prototype author. Agent-authored review accepted retention of the experiment with no remaining Standards or Spec findings. It does not approve permanent product/CI adoption.

The reviewer inspected the production-called seam, independent literal palette/state table, real clicks, unambiguous output requirements, two viewports and whole Work/history invariance. It also checked stale-source refusal and exact positive test names/counts, so a successful zero-test filter cannot masquerade as a pass.

It then executed the complete `reproduce.py` wrapper: normal paint2/state1 green, paint-only mutant paint exit101 with one named fill failure/state1 green, restored paint2/state1 green, wrapper exit0. All50 protected inputs were restored exactly; root also compared all50 with base Git blobs and reran the prior archive verifier (60 entries/31 production inputs PASS). Source SHA remains `da45cb7183d28e80cf8b15d1f08f8aa06463e0c5fe4af2b9067fbf8737878b5c`.

Reviewed executable reproduction SHA-256: `dd89cf985c4b2239c0dc37fd052e439221926a1438d15d9a3b571523a90fd77b`; strict stage driver: `14c8e93b8100f05a8f544fa8b76c01d1f5bacd90c2d3b4973ee17ec85a4b31fd`. Code/patches did not change after review. The root refreshed report timings/provenance and the artifact inventory because reviewer replay replaced12 author-stage logs/results. Original API/texture-error evidence remains; the old inventory is labelled historical.

Root additionally exercised the actual wrapper via `runpy`, injecting a first-child `CalledProcessError(37)` after the candidate source write. The error propagated, later child commands did not run, and all50 inputs were restored. [Probe receipt](child-failure-restoration.json). No Cargo or rendering ran in that probe.

[Report and executable commands](../../../experiments/28-ui-paint-oracle/README.md), [fresh replay log](../../../experiments/28-ui-paint-oracle/review-replay.log), [verification](../../../experiments/28-ui-paint-oracle/review-verification.json). Local compilation reused the existing cache. No test or mutation remains in production code. Processes ended and the sole local compiler token was released.

VERIFIED — Independent full replay, meaningful mutation-red/state-green/restored-green, base-equivalent restoration and injected child-failure recovery. NOT-RUN — GPU/framebuffer pixels, native/Web/IME/DPR, hosted/cold execution and abrupt interruption recovery.
