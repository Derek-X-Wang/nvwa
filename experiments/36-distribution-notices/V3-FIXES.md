# V3 content-role correction — pending independent R2

The original candidate `ab92b4816b18191e0d24d063e43a9e183cd3204114a4321da5d478455a403bf2` falsely promoted filenames to full-text coverage. It and all v2 source, anchors, receipts and tools remain preserved in `baseline-v2/`, with a 1249-file SHA-256 receipt. Prior v1 artifacts remain in `baseline-v1/`. Their original classifications and reported 21 missing records are historical facts, not rewritten results.

The independently accepted classification-family finding covers 27 false-positive references across 24 packages: four NSCopying Rust binding/test files and 23 author, copyright, choice, attribution, provenance or Apache application notices. The production collector now calls `select_documents`/`classify_document` in `notice_types.py`. It inspects actual content, never treats a filename or SPDX declaration as operative terms, retains notices distinctly, and excludes code files from notice/full-text coverage. The original source bytes remain separately indexed as excluded-source evidence. It does not select an OR branch or apply a license to first-party code.

Corrected candidate SHA-256: `2b551ed8c7fa22b347424c1056a3b6e5c935baaf7f4df7ebae4eb3e44ccb24fd`.

| Captured fact | Historical v2 | Corrected v3 |
|---|---:|---:|
| Package union | 323 | 323 |
| Native / Web normal+build inputs | 307 / 278 | 307 / 278 |
| Indexed files | 1039 | 1040 |
| Retained package notice references | 694 | 690 |
| Claimed / recognizable full-text references | 688 | 661 |
| Remaining notice-only references | 6 | 29 |
| Missing-text packages | 21 | 23 |
| Explicit gap records | 45 | 47 |
| First-party UNKNOWN licenses | 3 | 3 |

The index changes by removing four source files from `texts/packages`, retaining their unchanged bytes under `inputs/excluded-source-documents`, and adding `inputs/document-audit.json`. Twenty-nine useful notices remain retained, rather than removed. The 661 candidates contain recognizable operative text; that does not prove entire instruments, package applicability, every expression branch, final linked membership, copyright completeness or release obligations.

Only objc2-foundation 0.2.2 and 0.3.2 become newly missing. Both declare MIT. Version 0.2.2 previously counted only two Rust source files; its corrected full-text list is empty. Version 0.3.2 previously counted two Rust source files plus a separately retained notice-only root LICENSE.md; its corrected full-text list is also empty. The other 22 affected packages retain separate substantive candidates. Full exact file paths, hashes, original/corrected roles, retained candidates and per-package status appear in `evidence-v3/type-audit.json`.

## Content validation and proof

The checker recomputes content roles from fixed original-byte paths even when candidate roles, metadata anchors and counts have been edited consistently. It then verifies the complete captured schema, indexed hashes/provenance, source/manifest/supplement joins, excluded-source evidence, copyright lines, asset/font identities and all required gaps against the corrected anchor. Pinning the new capture alone is not the classification proof. The new anchor remains pending fresh independent R2 review.

Production-called real fixtures cover COPYING Rust source, declaration-only LICENSE/COPYING, AUTHORS, NOTICE, COPYRIGHT, ATTRIBUTION, short Apache application notices, full font/Unicode/CC0 instruments, substantive glam ATTRIBUTION, short adler2 0BSD, and mixed atomic-waker/futures-lite third-party files. The archived actual filename selector is red. Current production classification is green. Actual classifier source mutations that force false promotion or false negatives are red, then restored source is green. Mixed/short grants are preserved; no blanket filename or length exclusion is used. Misleading LICENSE filenames cannot turn the negative fixture bytes into full-text candidates.

Evidence caveat: the archived `--legacy` fixture calls the old filename selector alone. Its 13 raw failures include 12 actual source/notice/declaration promotions and one OFL miss because the fixture omits the old collector's explicit font-file augmentation. The old production pack correctly retained OFL; this extra fixture miss does not show missing font coverage. Font bytes/notices and genuine current positive fixtures remain unchanged. The raw failure counts are preserved.

Self-consistent coverage mutations update candidate roles, metadata, document audit, associated hashes and gaps together. They still fail against actual document content. This includes restoring the historical Rust-source promotion and old missing count. The original corruption, provenance, asset/gap and boundary controls are rerun on the corrected packet; historical failed raw runs remain retained.

The first classification-control wrapper stopped before emitting JSON when a deliberate assertion fired; its raw stderr/output remains in `evidence-v3/classification-controls` and private scratch. The corrected wrapper preserves structured failures for that same assertion. A boundary-copy run also exposed a real portability limit in the preliminary draft: excluded-source evidence was only outside the pack. The final packet carries those four original bytes with indexed provenance; the failed nonportable run and draft manifest remain retained. Neither failure was relabeled as green or discarded.

## Review and limits

Candidate completeness remains **BLOCKED**. Owner first-party licensing remains UNKNOWN. Signing, notarization, clean-machine launch, public distribution, final linker membership and legal/applicability approval are NOT-RUN. No new network request, crate download, build, UI/GPU, original-source edit, first-party license choice, shared-root or Git/GitHub write was made by this worker. Root owns publication and a fresh targeted Astra R2 review before acceptance.

Reproduction uses Python 3.11+, the existing exact source/cache cohort and locked/offline Cargo commands. Normal reproduction must match the sealed v3 capture. `--prepare-unreviewed-cohort` is an explicit capture path for a new bounded audit; it never provides review or legal approval. Original expressions, raw text bytes, original fixture/font/model distinctions and signing limits remain unchanged.

VERIFIED — Sealed v3 reproduction is byte-identical. The 121 fresh expected outcomes comprise 18 original controls, 66 R2/broader controls, six boundary controls, 25 self-consistent content/coverage controls and six actual old-source/current/mutated/restored classifier outcomes. The latter cover 21 real fixtures, including the required short/mixed substantive counterexamples. All raw results are retained under `evidence-v3/`; initial failures are retained separately. All 50 v1 and 1249 v2 baseline-file hashes match, all 696 retained original notice/asset text references match old bytes, and excluded source evidence matches all four original files. Finite processes are reaped; owned mutation/helper copies are removed after failed-context preservation. Candidate/baselines/evidence and bounded reproduction scratch remain for root review. Fresh independent Astra R2 remains PENDING.
