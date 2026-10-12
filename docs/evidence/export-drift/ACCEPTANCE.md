# Export byte drift acceptance

2026-10-12, main base `de4ddef`. This completes issue #7's investigation alternative, pending evidence PR merge. It does not make exports deterministic.

- Two real serial CPU exports, installed Blender 3.3.1/exporter 3.3.32, original generator/options, exit 0/0. No extra exports were launched for repair or review.
- GLB variation: eye triangle sequence/sharing/storage changes and 485 normal components, maximum absolute delta `1.1920928955078125e-7`. Position/UV/skin data, morph POSITION and animation samples are exact after resolving references. Tiny normal differences are retained as real differences.
- Both unchanged validators pass 18 joints/four morphs/three clips and profile metadata. Frozen fixture/profile/source/provenance remain unchanged: 28 hashes equal before/after/current and base Git blobs.
- `.blend` block shape matches; 27,623 stored addresses and 156,683 payload bytes differ. Payload semantics are not fully decoded.
- Fourteen tests and fresh independent R2 rereview pass. The exact-byte gate rejects real-file serialization, `.blend` and source-proof mutations. Retained original-red/mutation-red evidence establishes those tests detect the repaired failure.

[Full report/reproduction](../../../experiments/26-export-drift/REPORT.md), [review](REVIEW.md), [measurement and protected-input identity](manifest.json). Generated comparison binaries stay under ignored `.work/export-drift/control`; a fresh checkout must generate its own pair before running the comparator tests. Future pairs can have different counts. The experiment is excluded from generic CI diagnostics because it requires those explicit Blender-generated inputs.

The root removed only the exact untracked validator bytecode file produced during the experiment, after checking its identity; its parent directory and all pre-existing caches were preserved. Generation/test processes have ended. The attached worktree, existing `.tools`/`target` symlinks and private source/measurement evidence are retained for review.

VERIFIED — Bounded actual export investigation, failure tests and unchanged frozen inputs. NOT-RUN — A determinism fix, full `.blend` equivalence, rendered shading impact or cross-host/version/platform repeatability. #3 remains blocked; M2 is outside this work.
