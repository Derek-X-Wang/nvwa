# R2 fixes for notice tooling

The notice candidate stays unchanged at SHA-256 `ab92b4816b18191e0d24d063e43a9e183cd3204114a4321da5d478455a403bf2`, manifest schema 1. Tooling version 2 hardens validation of those captured facts. This is not a new license selection or a new production artifact build.

The independent R2 review found that the original checker accepted removal or alteration of source-comparison records, notice provenance, distinct assets/default fonts, gap families and root licensing uncertainty. Its seven named false-green mutations are re-run on actual copied candidate packs by `controls_v2.py`, alongside broader field and inventory controls. The historical 18 controls, original tools/report and candidate manifest remain intact under `baseline-v1/`; their hashes are retained in `baseline-v1/preservation.json`. `evidence/` remains the original v1 receipt directory. New checks are under `evidence-v2/`.

## Independent trust and semantic joins

`anchors/cohort-v1-manifest.json` contains the separately preserved, factually verified original capture. `cohort.py` pins its full SHA-256 in checker code. It includes an independently indexed source/file inventory, exact metadata/provenance, fixed asset and default-font payload hashes/notices, and every required unknown/gap record. A candidate cannot supply its own substitute reference hash. The checker rejects unknown/missing fields and changes anywhere in the captured schema before following candidate source paths. Indexed-file reads use the trusted frozen inventory. The collector refuses a changed capture and requests an explicit new audit rather than silently extending this cohort.

The trust boundary is the checker code plus that external pinned record. Changing both checker code and its pin is outside this integrity guarantee. This is not a signature, authentication system, general SPDX policy, or legal-compliance engine. Future production cohorts require a new independently verified capture and deliberate anchor change. No unknown is promoted to approved.

The checker also verifies semantic relationships among the preserved facts and copied bytes:

- Exact required source path set and per-path hashes against retained `build-inputs-after-lint-fix.json`, including duplicate/empty list rejection. With `--source-root`, it rehashes all 32 actual current source inputs and checks that root `LICENSE`/`COPYING` files are still absent. Without that flag, the portable check validates retained observations; fresh live source verification is `NOT-RUN`.
- Package manifest path/name/version/license where directly declared; indexed manifest bytes against captured origin hash; package source and each local notice's exact package/path/origin join. Workspace-inherited license metadata remains a pinned captured fact; the normalized child manifest alone is not claimed to resolve it.
- Every supplement matched to package repository and exact `.cargo_vcs_info.json` commit; exact indexed path/hash; public response URL/status/hash/length against retained request receipts; local shared-root donor manifest/commit and original notice hash. These are offline checks of previously retrieved evidence. No HTTP request is made.
- Copyright lines recomputed from the copied text files, exact notice-only/full-text distinction, and preserved text-coverage uncertainty.
- Exact three distinct asset records and four default-font payload records, fixed notice references/hashes, Nvwa Sans derivative payload/OFL joins to font provenance, original fixture payload join to fixture provenance, and font names in pinned `include_bytes!` declarations. Default-font payload hashes are retained source observations pinned independently; font payload bytes are not copied into the notice pack and fresh payload reading is not claimed by the portable checker.
- All 45 exact gap records, legacy expressions and unresolved scope families, plus the exact root owner `UNKNOWN` statement. Removing SDK/system/JS/CC0/signing boundaries fails even when some missing-text gaps remain.

The count and legal boundary remain 323 package inputs, 1039 indexed files, 307 native / 278 Web input closures, 21 missing-text packages, three first-party UNKNOWN licenses and 45 explicit gaps. No final linker membership, legal readiness, signing, notarization, clean-machine or public-distribution approval is inferred.

## Reproduce

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/36-distribution-notices/check.py experiments/36-distribution-notices/sample-production-pack --source-root .
PYTHONDONTWRITEBYTECODE=1 python3 experiments/36-distribution-notices/collect.py --output .work/issue10-notices/new-v2-pack --scratch .work/issue10-notices/new-v2-inputs --supplements experiments/36-distribution-notices/primary/supplements.json
PYTHONDONTWRITEBYTECODE=1 python3 experiments/36-distribution-notices/controls_v2.py experiments/36-distribution-notices/sample-production-pack --scratch .work/issue10-notices/new-v2-controls --evidence .work/issue10-notices/new-v2-controls-evidence
```

The locked/offline v2 collection reproduced the original candidate bytes exactly. No new primary retrieval, build, UI, GPU, signing, first-party license choice, product/shared-root file change or Git/GitHub write was made by this worker. Targeted R2 re-review remains required before root publication.

VERIFIED — Ninety fresh checker/control runs: the original 18 outcomes under v2, 32 R2/broader mutations with 32 restored greens plus baseline/completeness checks (66), and six boundary outcomes. The seven named R2 false greens now fail. Boundary controls reject an altered independent anchor, an unindexed file and missing live sources, then pass restored real inputs. All 50 preserved baseline files retain their original hashes; v2 collection reproduces the original candidate bytes. Raw red/green outputs and hashes are retained under `evidence-v2/`.

PARTIAL — Coverage and owner unknowns remain unchanged. Targeted R2 re-review is pending; no publication approval is claimed. Finite subprocesses are reaped and all mutation-copy/checker-bundle directories are empty. The original candidate, anchors, baseline evidence and reproduction scratch remain for root review.
