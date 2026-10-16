# Independent R2 review — 55 first pass

Scope: actual native headless Humentity adapter, source/data preparation, build wrappers, runner, comparator, rejection controls, threshold prediction and isolated B1 preparation. Source was frozen for inspection; final documentation/hash packet was not yet received. Product adoption remains excluded. No reviewed files modified.

## Finding

**P2 — Bind compared output bytes to successful execution receipts.** `experiments/55-source-character-runtime/compare.py:26–36` reads the run summary only to check variant. It does not require the recorded common manifest, route/sample class, execution success, complete unique case set, per-case exit/actual-execution status, or output hashes. Self-reported fields inside an edited candidate file can therefore stand in for actual executed output.

Proof: `verify_55.py` copied the original B0 summary unchanged into a reviewer-owned directory and wrote copies of its eight outputs with measured geometry replaced by converted reference coordinates. All eight files then disagreed with the output hashes already recorded in the execution summary. The actual comparator nevertheless returned exit 0 and `within_numeric_tolerance` for B0. This demonstrates a false acceptance path at the evidence boundary; it does not imply that the original files were altered.

Reproduction/evidence: `.work/character-actual-independent-review/verify_55.py`, `55-verification.json`, `B0-corrupted-output-control/`, `B0-corrupted-comparison.json`. **These corrupted control outputs are review counterexamples, not experiment measurements.**

Fix: validate successful run identity and the exact complete unique frozen case set; require per-case successful exit/execution fields; compare candidate file bytes against their existing execution-receipt hashes before parsing/comparison. Keep original execution outputs immutable, add negative controls from copied real outputs, and rerun the corrected comparator on both original variants.

## Original retained evidence independently corroborated

- Original raw Humentity 45-file inventory matches pinned Git identities and recorded SHA256 hashes.
- B0 derived candidate matches upstream except declared packaging/physics-feature guards. B1 differs only by `DELTA_SQ_THRESHOLD: f32 = 1e-6` to `0.0` in `src/loaders/target.rs`; adapter source bytes are identical. Separate local crate name/dependency path and lock rename distinguish B1 builds.
- B0 binary, derived source tree, adapter tree, and every run3 output/log/summary match the preservation checkpoint recorded before B1.
- Approved raw sample and all derived data files match their data-adapter hashes. Code inspection supports source-only geometry derivation: raw OBJ scaling, target gzip decoding, proxy length scaling and explicit identity body proxy. Reference files are verified by hashing but are not parsed into geometry by preparation.
- All eight original outputs for each variant match their execution output hashes and final comparator hashes. Original per-case exits and execution flags are successful; logs match their recorded hashes. Both on-disk binaries match their execution identities.
- Running the unchanged comparator against original data reproduced its retained final JSON exactly: B0 exit 3 / `numeric_parity_failed`; B1 exit 0 / `within_numeric_tolerance`.

| Channel | B0 maximum component error, metres | B1 maximum component error, metres |
| --- | ---: | ---: |
| Helpers | 0.0009001374244689275 | 4.0531158440604287e-7 |
| Body | 0.0009001374244689275 | 4.0531158440604287e-7 |
| Garment | 0.0007945865392684909 | 7.581710815385279e-6 |
| Joint heads | 3.4570693963065224e-7 | 3.4570693963065224e-7 |

Same frozen `1e-5 m` tolerances and eight recipes apply. Candidate execution is real but does not mean unchanged B0 satisfies numeric parity. B1 changes a candidate algorithm and cannot be represented as unchanged upstream execution. Its garment maximum is below tolerance but substantially closer to the threshold than its body result.

The adapter calls actual Humentity target loading, target resolution, helper adjustment, CPU mesh/proxy building, and skeleton generation. It records candidate rest/inverse-bind matrices, but exact local-frame rest/IBM parity is explicitly unmeasured. Joint tails, posed skinning, graphics, browser execution and adoption remain separate gates. Presence of skin attributes or finite matrices does not prove them.

## Exact verification command and identities

```sh
python3 -B .work/character-actual-independent-review/verify_55.py
```

This pure-Python verification invokes only the existing Python comparator, writes fresh reviewer-owned outputs, checks source/data/preservation hashes, and runs the private corruption counterexample. No Cargo, Rust process, Blender, GPU or network invocation.

Common manifest SHA256: `2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7`.
B0 binary: `80785de84c72a542c979be5a0d24a74a3315b87ffebfe083ab019eaf41429a1b`.
B1 binary: `d237db1ac959aeb795aceee4767aa8caab4472d2ceb73e9835e631290c57d0e2`.
Reviewed comparator: `c61e5d20ce871d440c3f8887afed064b53142e6d1264c0380fa73619054aea91`.
Reviewed runner: `a5eaf62748498127c7061775a1e3e4d32a6788575b70026008991a97c0e12b4b`.
Reviewed adapter: `f8fde1866a88ee2f845be87304bd943bbb6c0cba58069706cf1d554f37458e94`.
Additional reviewed source hashes are in `55-verification.json`.

PARTIAL — Original source/execution identities and B0/B1 numerical comparison corroborated. One P2 comparator evidence-binding defect requires correction. Final documentation/hash packet pending. Fresh candidate execution, rest/IBM-frame parity, tails, poses, graphics, browser, performance acceptance and adoption NOT-RUN. No reviewed code changed or owned processes left running. All review evidence retained for root.
