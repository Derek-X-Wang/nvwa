# Independent R2 review — initial 53/54 checkpoint

Scope: assigned `codex/character-foundation-research` worktree only; 53 comparison/download/reference, 54 compiled route, and research documents. Experiment 55 excluded because its writer was active. No product adoption conclusion. No reviewed code modified.

## Finding

**P2 — Reusing an approved download can replace it with an unchecked stale partial.**
`experiments/53-character-comparison/delivery/download_approved.py:73-80` (reuse selection at 44-48).
`fetch()` reads and validates an existing destination, but later selects any existing sibling `.part` and unconditionally promotes it. A prior interrupted partial can therefore overwrite approved bytes while the returned receipt still claims the approved destination hash and `status: verified`. For archives without Git-blob validation, no check covers the promoted bytes. This violates source identity and preservation on retry.

Offline reproduction: `reproduce_stale_part.py` calls this actual function with an approved existing control file and a different stale `.part`. It reports verified, replaces the approved bytes, and leaves an actual hash different from the receipt. No network was used; only reviewer-owned control files were changed. Evidence: `stale-part-reproduction.json`.

Fix recommendation: track the exact validated input path; on reuse, return/preserve the existing verified destination and never promote an unrelated `.part`. Only promote a temporary created and validated by that call. Add the reproduced regression case.

The actual retained approved inputs all hash-match now. This defect does not invalidate the current geometry evidence.

## Independent verification

- Verified the exact frozen manifest and public snapshot bytes, all 23 named source/reference files, all extracted MPFB receipt hashes (2,422 files), all selected garment receipt hashes, and all download inventory file hashes.
- Verified all eight retained A result hashes, exact case/recipe/common/package identities, body/joint/garment cardinality, parent identity, finite positions and reference body/rig/garment identity world transforms.
- Independently recalculated reference comparison maxima: body `3.807830809554602e-7 m`, joints `2.539825438852006e-7 m`, garment `3.0110187632104157e-7 m`, each below the declared `1e-5 m` component tolerance.
- Recompiled A with a Python audit hook that rejects every attempt to open any of the nine reference files. Compilation succeeded and reproduced the retained 2,117,964-byte package byte-for-byte. This provides executed evidence that the full-sample compiler does not use reference-output geometry as an oracle.
- Independently evaluated the package's signed sparse targets, helper centroids, bone endpoints and garment weighted triples/scaled offsets in pure Python for all eight recipes. Difference from retained Rust results was at most `2.220446049250313e-16 m`.
- Recomputed retained-result continuity: seven non-neutral cases change body geometry; positive half linearity maximum `2.220446049250313e-16 m`.
- Read actual retained Blender log showing MPFB initialization, offline state, base/garment import, eight-case completion and Blender 5.2.2 build identity. Inspected preservation control implementation and retained failure receipts; did not re-execute Rust rejection cases in this read-only pure-Python review.
- Current scope/limits reporting correctly separates numerical endpoints from bone roll/rest matrices, inverse binds, skinning, graphics, appearance, exchange and adoption. Historical research documents remain explicitly research-stage snapshots.

## Commands executed

From the assigned worktree:

```sh
python3 -B .work/character-actual-independent-review/verify_retained.py
python3 -B .work/character-actual-independent-review/reproduce_stale_part.py
python3 -B .work/character-actual-independent-review/verify_operators.py
python3 -B experiments/54-compiled-character-package/measure_continuity.py --comparison experiments/54-compiled-character-package/.work/full-common-run1/comparison --out .work/character-actual-independent-review/continuity-verification.json
```

The scripts retain assertions and outputs in this directory. `verify_retained.py` invokes `compile_common.py` with `runpy` and forbids reference opens via `sys.addaudithook`. The scripts use fresh reviewer-owned outputs; a repeated run needs a fresh compiled-no-oracle output name. No Cargo build, Blender/GPU, downloads, network calls, external writes, or new Rust runtime checks were performed.

## Identities and bounds

Manifest: `2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7`.
Package: `dcdc82b42a86d9b8ffd6e57803171eae73df4a564bcec04cc4d13d30183ef022`.
Complete source/evidence snapshot hashes: `retained-verification.json`.
Selected reviewed source hashes:

- `experiments/53-character-comparison/delivery/download_approved.py`: `7e7fa9032bf6b33cf49795fb6d7dd04848d868ac05afcbb927ff16c74dbf0867`
- `experiments/53-character-comparison/reference/core_smoke.py`: `f3cef6aa9d7cd2c9610d3332260835a2cdfee8ef293b7d0c3a118c141cb2321c`
- `experiments/53-character-comparison/reference/freeze_sample.py`: `0747f50cd363ddaad13f05419613802fc96260b3e8506d7ca2ec107b972ef795`
- `experiments/54-compiled-character-package/compile_common.py`: `de6ae8698ad0aae3489fb313fb8a789205e143e5f2ca5f53fa39fa673869ba58`
- `experiments/54-compiled-character-package/compare_common.py`: `0f6747946a1f4a2d521d476a0dae3d8b2bb4c3acb45d1ff1d3139c25cc7d41bb`
- `experiments/54-compiled-character-package/src/bin/compiled-numeric-probe.rs`: `50d40298989c07d5392b970b4270856ddce46956de44647b1e3f23e05e4f3c7b`
- `experiments/54-compiled-character-package/src/fit.rs`: `95a29ad96d1241b23407f94821facb1abcb599a7fe833c8e20a12941334a0443`
- `experiments/54-compiled-character-package/src/signed.rs`: `65a7e9fc857a66952f43ff79a2f57ce7778cc9a288fe5e8ce9b715dce52f6f01`

PARTIAL — One P2 retry-preservation defect. 53/54 retained numeric evidence independently corroborated within stated scope. 55, fresh Rust/Blender runs, posed skinning, rest/inverse binds, graphical/visual acceptance, performance and product adoption NOT-RUN. No independent legal conclusion; reviewed recorded source/data/license boundaries only. No processes remain owned/running. Review artifacts retained for root publication and cleanup.
